"""Disposable enforcing Unbound DNSSEC experiments; production is read-only.

fixture: controlled six-second authority delay, no public queries.
recursive: four fresh processes, eight at most ordinary public queries.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import socket
import subprocess
import tempfile
import time
from acceptance import check_query
from local_runtime import Authority

ROOT = Path(__file__).resolve().parents[1]


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def fingerprint():
    return {'pid': command('systemctl', 'show', 'unbound', '-p', 'MainPID', '--value'),
            'restarts': command('systemctl', 'show', 'unbound', '-p', 'NRestarts', '--value'),
            'config': hashlib.sha256(Path('/etc/unbound/unbound.conf').read_bytes()).hexdigest(),
            'anchor': hashlib.sha256(Path('/var/lib/unbound/root.key').read_bytes()).hexdigest(),
            'nft': hashlib.sha256(command('nft', '-s', 'list', 'ruleset').encode()).hexdigest(),
            'sshd': hashlib.sha256(command('sshd', '-T').encode()).hexdigest()}


def child_limits():
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))


def experiment(args, name, tcp, limit):
    authority = None
    proc = None
    log = None
    with tempfile.TemporaryDirectory(prefix='vynalth-dnssec-', dir='/var/lib/unbound') as folder:
        base = Path(folder)
        conf = (ROOT / 'plans/phase-b-unbound.conf').read_text()
        conf = conf.replace('username: "unbound"', 'username: ""')
        conf = conf.replace('directory: "/etc/unbound"', f'directory: "{folder}"')
        conf = conf.replace('port: 53', 'port: 15355')
        conf = conf.replace('    interface: 100.95.65.20\n', '')
        conf = conf.replace('/var/lib/unbound/root.key', str(base / 'root.key'))
        conf = conf.replace('/run/unbound.ctl', str(base / 'control.sock'))
        conf += f'\nserver:\n    pidfile: "{base}/unbound.pid"\n    use-syslog: no\n    verbosity: 1\n    val-log-level: 2\n    log-servfail: yes\n'
        if args.discard_timeout is not None:
            conf += f'    discard-timeout: {args.discard_timeout}\n'
        if args.mode == 'fixture':
            authority = Authority(delay_seconds=6)
            (base / 'fixture.key').write_text(authority.keys.to_text() + '\n')
            # Only the pinned fixture-zone anchor: no root probe/signaling traffic.
            conf = '\n'.join(line for line in conf.splitlines() if 'auto-trust-anchor-file:' not in line) + '\n'
            conf += f'    trust-anchor-file: "{base}/fixture.key"\n    do-not-query-localhost: no\n    local-zone: "test." nodefault\nstub-zone:\n    name: "signed-fixture.test."\n    stub-addr: 127.0.0.1@15354\n    stub-first: no\n'
        (base / 'root.key').write_bytes(Path('/var/lib/unbound/root.key').read_bytes())
        (base / 'unbound.conf').write_text(conf)
        control = ['unbound-control', '-c', str(base / 'unbound.conf')]
        try:
            subprocess.run(['unbound-checkconf', str(base / 'unbound.conf')], check=True)
            log = open(base / 'unbound.log', 'w')
            proc = subprocess.Popen(['unbound', '-d', '-c', str(base / 'unbound.conf')], stdout=log, stderr=log, preexec_fn=child_limits)
            # Readiness is only a local socket observation, never a priming query.
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError((base / 'unbound.log').read_text())
                if (base / 'control.sock').exists():
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError('Isolated control socket not ready')
            label = Path(f'/proc/{proc.pid}/attr/current').read_text().strip()
            if args.require_apparmor and label != 'unbound (enforce)':
                raise RuntimeError('Not enforcing: ' + label)
            forwards = command(*control, 'list_forwards')
            if forwards:
                raise RuntimeError('Unexpected forwarder')
            def stats():
                return dict(line.split('=', 1) for line in command(*control, 'stats_noreset').splitlines() if '=' in line)
            before = stats()
            if before['total.num.queries'] != '0':
                raise RuntimeError('Cold process already has client queries')
            expected = 'SERVFAIL' if name.startswith('bogus.') or name == 'dnssec-failed.org.' else 'NOERROR'
            cold = check_query('127.0.0.1', name, port=15355, tcp=tcp, expected=expected,
                               ad=expected == 'NOERROR', timeout=20, latency_limit=limit,
                               scenario='cold-process', cache_evidence=f'fresh PID {proc.pid}, client queries=0')
            after_cold = stats()
            cold['legacy_5s_would_fail'] = cold['elapsed_seconds'] > 5 or cold['response'] is None
            warm = {'pass': False, 'outcome': 'skipped_after_cold_failure', 'attempts': 0}
            if cold['pass']:
                warm = check_query('127.0.0.1', name, port=15355, tcp=tcp, expected=expected,
                                   ad=expected == 'NOERROR', timeout=2, scenario='warm-after-successful-cold',
                                   cache_evidence=f'same PID {proc.pid}, prior cold response accepted')
            after_warm = stats()
            hit_delta = float(after_warm['total.num.cachehits']) - float(after_cold['total.num.cachehits'])
            if warm['pass'] and hit_delta < 1:
                warm['pass'] = False
                warm['outcome'] = 'warm_cache_hit_not_observed'
            summary = {'mode': args.mode, 'fixture_delay_seconds': 6 if authority else None,
                       'pid': proc.pid, 'apparmor': label, 'forwards': forwards,
                       'discard_timeout_ms': command(*control, 'get_option', 'discard-timeout'),
                       'cold': cold, 'warm': warm, 'warm_cache_hit_delta': hit_delta,
                       'stats_after_cold': {k: v for k, v in after_cold.items() if k.startswith('total.') or k.startswith('num.answer') or k.startswith('num.query') or k.startswith('mem.')},
                       'proc_status': [s for s in Path(f'/proc/{proc.pid}/status').read_text().splitlines() if s.startswith(('VmRSS:', 'VmHWM:'))],
                       'proc_open_files_limit': [s for s in Path(f'/proc/{proc.pid}/limits').read_text().splitlines() if s.startswith('Max open files')]}
            proc.terminate()
            proc.wait(timeout=5)
            log.close()
            log = None
            summary['controlled_query_logs'] = (base / 'unbound.log').read_text()
            if authority:
                summary['local_authority_request_count'] = authority.count
            return summary
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            if log:
                log.close()
            if authority:
                authority.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['fixture', 'recursive'], default='fixture')
    parser.add_argument('--authorized-recursion', action='store_true')
    parser.add_argument('--require-apparmor', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--discard-timeout', type=int, help='Explicit isolated A/B variation in milliseconds; never zero')
    parser.add_argument('--legacy-comparison', action='store_true', help='Fixture only: predeclare separate 5s and 15s acceptance experiments')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Use sudo on the authorized local lab host')
    if args.mode == 'recursive' and not args.authorized_recursion:
        parser.error('Recursive experiment requires --authorized-recursion')
    if args.discard_timeout is not None and not 1 <= args.discard_timeout <= 30000:
        parser.error('Isolated discard-timeout must remain finite and <=30000ms')
    before = fingerprint()
    rows = []
    names = ['valid.signed-fixture.test.', 'bogus.signed-fixture.test.'] if args.mode == 'fixture' else ['cloudflare.com.', 'dnssec-failed.org.']
    limits = [5, 15] if args.mode == 'fixture' and args.legacy_comparison else [15]
    cgroup_name = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1]
    cgroup = Path('/sys/fs/cgroup') / cgroup_name.lstrip('/')
    result = {'reviewed_config_sha256': hashlib.sha256((ROOT / 'plans/phase-b-unbound.conf').read_bytes()).hexdigest(),
              'execution_limits': {'cgroup': cgroup_name,
                                   'memory_max_bytes': (cgroup / 'memory.max').read_text().strip(),
                                   'tasks_max': (cgroup / 'pids.max').read_text().strip()},
              'production_before': before, 'experiments': rows, 'production_after': None}
    try:
        for limit in limits:
            for name in names:
                for tcp in (False, True):
                    # Distinct predeclared fresh-process experiments, never retry a case.
                    row = experiment(args, name, tcp, limit)
                    rows.append(row)
                    print(json.dumps({k: row[k] for k in ['mode', 'pid', 'apparmor', 'cold', 'warm', 'warm_cache_hit_delta']}), flush=True)
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    finally:
        result['production_after'] = fingerprint()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if before != result['production_after']:
        raise RuntimeError('Production fingerprint changed; investigate before proceeding')
    if args.mode == 'fixture':
        if all(int(row['discard_timeout_ms']) < 6000 for row in rows):
            expected = all(row['cold']['outcome'] in ('timeout', 'transport_error') and row['warm']['attempts'] == 0 for row in rows)
        else:
            expected = all(row['cold']['outcome'] == 'latency_exceeded' and row['warm']['attempts'] == 0
                           if row['cold']['latency_limit_seconds'] == 5 else row['cold']['pass'] and row['warm']['pass']
                           for row in rows)
    else:
        expected = all(row['cold']['pass'] and row['warm']['pass'] for row in rows)
    print('PASS isolated experiment expectations and unchanged production' if expected else 'FAIL isolated acceptance; failures preserved, no retry', flush=True)
    raise SystemExit(0 if expected else 1)


if __name__ == '__main__':
    main()
