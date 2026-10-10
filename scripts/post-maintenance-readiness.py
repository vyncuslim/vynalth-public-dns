"""Read-only, pinned baseline review. No service, package or network mutations.

Capture is an explicit review operation, never an automatic preflight refresh.
Pending reboot blocks deployment readiness; a new boot needs a new reviewed
baseline, not an updated PID substituted into an old approved transaction.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'd6db3048b2c8dce15bf3ebe50be89ce12680345f48ce72eb466b715d29317634'
LOCKS = ['/var/lib/dpkg/lock', '/var/lib/dpkg/lock-frontend', '/var/lib/apt/lists/lock', '/var/cache/apt/archives/lock']


def run(*args, allowed=(0,)):
    proc = subprocess.run(args, text=True, capture_output=True, timeout=10,
                          env={**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC'})
    if proc.returncode not in allowed:
        raise RuntimeError(f'{args[0]} failed ({proc.returncode}): {proc.stderr}')
    return proc.stdout.strip()


def properties(unit, names):
    return dict(line.split('=', 1) for line in run('systemctl', 'show', unit,
                  *[arg for name in names for arg in ('-p', name)]).splitlines())


def is_upgrade_process(args):
    names = [Path(arg).name for arg in args]
    if 'unattended-upgrade-shutdown' in names and '--wait-for-signal' in args:
        return False
    return any(name in {'apt', 'apt-get', 'aptitude', 'dpkg', 'needrestart',
                       'unattended-upgrade', 'unattended-upgrades', 'apt.systemd.daily'} for name in names)


def idle_failures(services, processes, locks, timers, now):
    failures = []
    for name, props in services.items():
        if props['ActiveState'] != 'inactive' or props['SubState'] != 'dead':
            failures.append('Maintenance service not idle: ' + name)
    if processes:
        failures.append('Package/needrestart process running')
    if any(locks.values()):
        failures.append('Package lock occupied')
    for name, props in timers.items():
        text = props['NextElapseUSecRealtime']
        try:
            next_time = datetime.strptime(text, '%a %Y-%m-%d %H:%M:%S %Z').replace(tzinfo=timezone.utc).timestamp()
            if next_time - now < 900:
                failures.append('Maintenance timer within 15 minutes: ' + name)
        except ValueError:
            failures.append('Maintenance schedule unverified: ' + name)
    return failures


def sample(connection):
    unit = properties('unbound', ['MainPID', 'NRestarts', 'ActiveState', 'SubState',
                 'InvocationID', 'ExecMainStartTimestampMonotonic', 'DropInPaths',
                 'MemoryMax', 'TasksMax', 'LimitNOFILE', 'FragmentPath'])
    pid = int(unit['MainPID'])
    if pid <= 0:
        raise RuntimeError('No Unbound process')
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    config_files = sorted(Path('/etc/unbound/unbound.conf.d').glob('*.conf'))
    paths = [Path('/etc/unbound/unbound.conf'), *config_files, Path('/usr/sbin/unbound'),
             Path(unit['FragmentPath']), Path('/usr/sbin/sshd'), Path('/usr/sbin/tailscaled'),
             Path('/etc/apparmor.d/usr.sbin.unbound'), Path('/usr/share/dns/root.hints')]
    optional = Path('/etc/apparmor.d/local/usr.sbin.unbound')
    if optional.exists():
        paths.append(optional)
    listeners = sorted((line.split()[0], line.split()[4]) for line in run('ss', '-lntup').splitlines() if '"unbound"' in line)
    fingerprint = {'hostname': run('hostname'), 'architecture': run('uname', '-m'),
       'kernel': run('uname', '-r'), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'unit': unit, 'apparmor': Path(f'/proc/{pid}/attr/current').read_text().strip(),
       'files_sha256': {str(path): digest(path) for path in paths},
       'package_versions': run('dpkg-query', '-W', 'unbound', 'systemd', 'openssh-server', 'tailscale', 'libssl3t64', 'libc6'),
       'listeners': [list(item) for item in listeners],
       'nft_sha256': hashlib.sha256(run('nft', '--stateless', 'list', 'ruleset').encode()).hexdigest(),
       'sshd_sha256': hashlib.sha256(run('/usr/sbin/sshd', '-T').encode()).hexdigest(),
       'tailscale_ipv4': run('tailscale', 'ip', '-4'),
       'tailscaled_active': run('systemctl', 'is-active', 'tailscaled'),
       'ssh_active': run('systemctl', 'is-active', 'ssh'),
       'boot_activation': {name: run('systemctl', 'is-enabled', name, allowed=(0, 1))
                           for name in ['tailscaled.service', 'unbound.service', 'ssh.service', 'ssh.socket']},
       'forwards': run('unbound-control', '-s', '/run/unbound.ctl', 'list_forwards')}
    services = {name: properties(name, ['ActiveState', 'SubState']) for name in ['apt-daily.service', 'apt-daily-upgrade.service']}
    timers = {name: properties(name, ['NextElapseUSecRealtime', 'RandomizedDelayUSec']) for name in ['apt-daily.timer', 'apt-daily-upgrade.timer']}
    processes = []
    helper = []
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():
            continue
        try:
            args = (folder / 'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if is_upgrade_process(args):
            processes.append({'pid': folder.name, 'argv': args})
        elif any(Path(arg).name == 'unattended-upgrade-shutdown' for arg in args):
            helper.append({'pid': folder.name, 'argv': args})
    for path in LOCKS:
        if not Path(path).is_file():
            raise RuntimeError('Cannot verify missing package lock: ' + path)
    locks = {path: run('fuser', path, allowed=(0, 1)) for path in LOCKS}
    now = datetime.now(timezone.utc)
    failures = idle_failures(services, processes, locks, timers, now.timestamp())
    source = connection.split()
    if len(source) != 4 or source[0] != '100.85.132.14' or source[2] != '100.95.65.20':
        failures.append('Unapproved SSH source/destination')
    wanted = [['tcp', '127.0.0.1:53'], ['tcp', '[::1]:53'], ['udp', '127.0.0.1:53'], ['udp', '[::1]:53']]
    if fingerprint['listeners'] != wanted or fingerprint['apparmor'] != 'unbound (enforce)':
        failures.append('Baseline DNS listener or AppArmor mismatch')
    if unit['ActiveState'] != 'active' or unit['SubState'] != 'running':
        failures.append('Unbound not running')
    if unit['DropInPaths'] or len(config_files) != 2:
        failures.append('Original service include/drop-in set differs')
    if fingerprint['tailscale_ipv4'] != '100.95.65.20' or fingerprint['forwards']:
        failures.append('Private address or recursion differs')
    activation = fingerprint['boot_activation']
    if activation['tailscaled.service'] != 'enabled' or activation['unbound.service'] != 'enabled':
        failures.append('Private service boot activation unverified')
    if not any(activation[name] == 'enabled' for name in ['ssh.service', 'ssh.socket']):
        failures.append('SSH boot activation unverified')
    timer = properties('vynalth-rollback.timer', ['LoadState', 'ActiveState', 'SubState', 'FragmentPath'])
    pending = Path('/var/lib/vynalth-dns/rollback').exists()
    if timer['ActiveState'] != 'inactive' or pending:
        failures.append('Pending rollback transaction')
    run('sha256sum', '--check', str(ROOT / 'plans/phase-b-active.sha256'))
    run('sha256sum', '--check', str(ROOT / 'plans/phase-b-service.sha256'))
    if digest(ROOT / 'plans/phase-b-unbound.conf') != CONFIG:
        failures.append('Proposed configuration hash differs')
    run('unbound-checkconf')
    anchor = Path('/var/lib/unbound/root.key')
    raw = anchor.read_text()
    return {'recorded_utc': now.isoformat(), 'ssh_connection': connection,
       'fingerprint': fingerprint, 'operational_failures': failures,
       'maintenance': {'services': services, 'processes': processes, 'shutdown_helper': helper,
                       'locks': locks, 'timers': timers},
       'reboot_required': Path('/var/run/reboot-required').exists(),
       'reboot_packages': Path('/var/run/reboot-required.pkgs').read_text() if Path('/var/run/reboot-required.pkgs').exists() else '',
       'timer': timer, 'pending_snapshot': pending,
       'root_anchor': {'sha256': digest(anchor), 'uid': anchor.stat().st_uid, 'mode': oct(anchor.stat().st_mode & 0o777),
           'metadata': [line if line.startswith(';;') else line[line.index(';;'):] for line in raw.splitlines() if ';;' in line]},
       'time_sync': run('timedatectl', 'show', '-p', 'NTPSynchronized', '--value'),
       'free_memory': run('free', '-m'), 'disk': run('df', '-h', '/'),
       'proposed_config_sha256': CONFIG}


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true', help='Review only; never overwrite an approved baseline')
    mode.add_argument('--baseline', type=Path)
    parser.add_argument('--interval', type=int, default=60)
    parser.add_argument('--ssh-connection', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 60 <= args.interval <= 300:
        parser.error('At least 60 seconds of stability is required')
    result = {'capture_only': args.capture, 'deployment_ready': False, 'samples': [], 'failures': []}
    expected = json.loads(args.baseline.read_text())['fingerprint'] if args.baseline else None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        for index in range(2):
            row = sample(args.ssh_connection)
            result['samples'].append(row)
            result['failures'] += row['operational_failures']
            if row['time_sync'] != 'yes':
                result['failures'].append('NTP unsynchronized')
            if row['reboot_required']:
                result['failures'].append('Pending reboot: maintenance approval required')
            if expected is not None and row['fingerprint'] != expected:
                result['failures'].append('Pinned baseline drift: new review required, never auto-refresh')
            args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps({'sample': index + 1, 'pid': row['fingerprint']['unit']['MainPID'],
                             'operational_failures': row['operational_failures'], 'reboot_required': row['reboot_required']}), flush=True)
            if index == 0:
                time.sleep(args.interval)
        if result['samples'][0]['fingerprint'] != result['samples'][1]['fingerprint']:
            result['failures'].append('Service/host fingerprint changed during stability interval')
        result['deployment_ready'] = not result['failures'] and not args.capture
    except Exception as exc:
        result['failures'].append(type(exc).__name__ + ': ' + str(exc))
    finally:
        args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'deployment_ready': result['deployment_ready'], 'failures': result['failures']}), flush=True)
    raise SystemExit(0 if result['deployment_ready'] else 1)


if __name__ == '__main__':
    main()
