"""Actual shell transaction in private mounts; service/OS commands are strict shims.

No production service or timer operations. Real timer timing is tested separately
by service_rollback_lab.sh and timer_guard_lab.py. Receipts here are synthetic
contract fixtures, not live DNS acceptance evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def inside(folder, mode):
    lab = Path(folder)
    assert lab.name.startswith('vynalth-transaction-') and (lab / 'marker').is_file()
    assert Path('/proc/self/ns/mnt').readlink().as_posix() != (lab / 'host-mount').read_text()
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/tmp'], check=True)
    Path('/tmp/vynalth-transaction').mkdir()
    subprocess.run(['mount', '--bind', str(lab), '/tmp/vynalth-transaction'], check=True)
    lab = Path('/tmp/vynalth-transaction')
    for source, destination in [('etc-unbound', '/etc/unbound'), ('units', '/etc/systemd/system'),
                                ('var-lib', '/var/lib'), ('run', '/run')]:
        subprocess.run(['mount', '--bind', str(lab / source), destination], check=True)
    os.environ['PATH'] = str(lab / 'bin') + ':' + os.environ['PATH']
    os.environ['VYNALTH_LAB_MODE'] = mode
    sock = socket.socket(socket.AF_UNIX)
    sock.bind('/run/unbound.ctl')
    repo = lab / 'repo'
    config_hash = hashlib.sha256((repo / 'plans/phase-b-unbound.conf').read_bytes()).hexdigest()
    baseline_hash = hashlib.sha256((repo / 'plans/post-boot-baseline.json').read_bytes()).hexdigest()
    rendered = lab / 'rendered'
    rendered.mkdir()
    shutil.copy(repo / 'plans/phase-b-unbound.conf', rendered / 'unbound.conf')
    proc = subprocess.run(['bash', str(repo / 'scripts/deploy-private.sh'), str(rendered), config_hash,
                           baseline_hash, '100.85.132.14 1 100.95.65.20 22', str(time.monotonic()+130),
                           Path('/proc/sys/kernel/random/boot_id').read_text().strip()], capture_output=True, text=True)
    if mode == 'bad-timer':
        assert proc.returncode != 0, proc.stdout + proc.stderr
    else:
        assert proc.returncode == 0, proc.stdout + proc.stderr
        installed = Path('/var/lib/vynalth-dns/rollback.sh').stat()
        assert installed.st_uid == 0 and installed.st_mode & 0o777 == 0o700
        sys.path.insert(0, str(repo / 'tests'))
        from test_confirmation import receipt_fixture
        receipt = receipt_fixture()
        receipt['expected_config_sha256'] = config_hash
        for state in (receipt['before'], receipt['after']):
            state['config_sha256'] = config_hash
            state['unit']['MainPID'] = (lab / 'production-pid').read_text().strip()
            state['nft_sha256'] = hashlib.sha256(b'LAB rules').hexdigest()
            state['sshd_sha256'] = hashlib.sha256(subprocess.check_output(['/usr/sbin/sshd', '-T'], text=True).strip().encode()).hexdigest()
        if mode == 'missing-receipt':
            receipt = {}
        if mode == 'marker-missing':
            Path('/var/lib/vynalth-dns/rollback/service-only').unlink()
        if mode == 'deadline':
            path = Path('/var/lib/vynalth-dns/rollback/transaction.json')
            transaction = json.loads(path.read_text())
            transaction['started_monotonic'] = time.monotonic() - 140
            path.write_text(json.dumps(transaction))
        path = lab / 'receipt.json'
        path.write_text(json.dumps(receipt))
        confirm = subprocess.run(['bash', str(repo / 'scripts/confirm.sh'), str(path), '100.85.132.14 1 100.95.65.20 22'], capture_output=True, text=True)
        assert (confirm.returncode == 0) == (mode == 'success'), confirm.stdout + confirm.stderr
        if mode == 'marker-missing':
            # Coordinator/timer recovery remains strictly service-only even if
            # the routing marker was lost; no legacy firewall branch is legal.
            subprocess.run(['bash', '/var/lib/vynalth-dns/rollback.sh', '--service-only'], check=True)
    active = Path('/etc/unbound/unbound.conf').read_bytes()
    if mode == 'success':
        assert active == (repo / 'plans/phase-b-unbound.conf').read_bytes()
        assert list(Path('/var/lib/vynalth-dns').glob('confirmed-*'))
        assert Path('/run/systemd/transient/vynalth-rollback.timer').is_file()
    else:
        assert active == (lab / 'original.conf').read_bytes()
        assert not Path('/etc/systemd/system/unbound.service.d/private.conf').exists()
        assert list(Path('/var/lib/vynalth-dns').glob('rolled-back-*'))
    assert Path('/etc/systemd/system/unbound.service.d/unrelated.conf').read_text() == 'retained\n'
    assert not Path('/var/lib/vynalth-dns/rollback').exists()
    print(json.dumps({'mode': mode, 'pass': True, 'scope': 'private mounts / strict service shims / synthetic receipt'}))


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--inside':
        inside(sys.argv[2], sys.argv[3])
        return
    for mode in ('success', 'bad-timer', 'missing-receipt', 'deadline', 'marker-missing'):
        with tempfile.TemporaryDirectory(prefix='vynalth-transaction-', dir='/var/lib/unbound') as folder:
            lab = Path(folder)
            (lab / 'marker').touch()
            (lab / 'host-mount').write_text(Path('/proc/self/ns/mnt').readlink().as_posix())
            (lab / 'production-pid').write_text(subprocess.check_output(['systemctl', 'show', 'unbound', '-p', 'MainPID', '--value'], text=True).strip())
            shutil.copytree(ROOT, lab / 'repo', ignore=shutil.ignore_patterns('.git', '.venv', 'artifacts', '__pycache__'))
            for name in ('etc-unbound/unbound.conf.d', 'units/unbound.service.d', 'var-lib/unbound', 'run/systemd/transient', 'run/sshd', 'bin', 'repo/.venv/bin'):
                (lab / name).mkdir(parents=True, exist_ok=True)
            shutil.copy('/etc/unbound/unbound.conf', lab / 'original.conf')
            shutil.copy('/etc/unbound/unbound.conf', lab / 'etc-unbound/unbound.conf')
            for name in ('remote-control.conf', 'root-auto-trust-anchor-file.conf'):
                source = Path('/etc/unbound/unbound.conf.d') / name
                target = lab / 'etc-unbound/unbound.conf.d' / name
                if source.exists():
                    shutil.copy(source, target)
                else:
                    target.write_text('# Private-mount baseline fixture\n')
            # Only the disposable checkout's host-specific baseline manifest is
            # adapted. Actual source/config/guard hashes remain pinned separately.
            names = ['/etc/unbound/unbound.conf', '/etc/unbound/unbound.conf.d/remote-control.conf',
                     '/etc/unbound/unbound.conf.d/root-auto-trust-anchor-file.conf']
            active_manifest = lab / 'repo/plans/phase-b-active.sha256'
            active_manifest.write_text(''.join(hashlib.sha256((lab / 'etc-unbound' / name.removeprefix('/etc/unbound/')).read_bytes()).hexdigest()
                                              + '  ' + name + '\n' for name in names))
            service_manifest = lab / 'repo/plans/phase-b-service.sha256'
            service_manifest.write_text('\n'.join(
                hashlib.sha256(active_manifest.read_bytes()).hexdigest() + '  plans/phase-b-active.sha256'
                if line.endswith('  plans/phase-b-active.sha256') else line
                for line in service_manifest.read_text().splitlines()) + '\n')
            shutil.copy('/var/lib/unbound/root.key', lab / 'var-lib/unbound/root.key')
            (lab / 'units/unbound.service.d/unrelated.conf').write_text('retained\n')
            for name in ('systemctl', 'systemd-run', 'busctl', 'ip', 'dig', 'nft', 'ss'):
                path = lab / 'bin' / name
                path.write_text('#!/bin/sh\nexec ' + PYTHON + ' /tmp/vynalth-transaction/repo/tests/transaction_command_shim.py ' + name + ' "$@"\n')
                path.chmod(0o700)
            wrapper = lab / 'repo/.venv/bin/python'
            wrapper.write_text('#!/bin/sh\ncase "$1" in */verify-post-boot.py) echo "LAB-only baseline OS stub"; exit 0;; esac\nexec ' + PYTHON + ' "$@"\n')
            wrapper.chmod(0o700)
            subprocess.run(['unshare', '--mount', PYTHON, str(ROOT / 'tests/private_transaction_lab.py'), '--inside', folder, mode], check=True)


if __name__ == '__main__':
    main()
