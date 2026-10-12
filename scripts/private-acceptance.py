"""Windows protected-transaction acceptance; Android release gate is separate.

SSH key is passed only as a filename to OpenSSH; this program never reads it.
The operator must immediately roll back on a nonzero result or missing receipt.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from acceptance import case_plan, check_query

SERVER = '100.95.65.20'
SOURCE = '100.85.132.14'
REMOTE = '/home/ubuntu/vynalth-public-dns'


def inspect_remote(key, local_refused=False):
    command = (f'cd {shlex.quote(REMOTE)} && sudo -n .venv/bin/python '
               'scripts/private-service-inspect.py --ssh-connection "$SSH_CONNECTION"')
    if local_refused:
        command += ' --local-refused'
    reply = subprocess.run(['ssh', '-i', key, '-o', 'IdentitiesOnly=yes', '-o',
                            'StrictHostKeyChecking=yes', '-o', 'BatchMode=yes', '-o',
                            'ConnectTimeout=4', f'ubuntu@{SERVER}', command],
                           text=True, capture_output=True, timeout=8, check=True)
    return json.loads(reply.stdout)


def validate_state(state, expected_hash):
    connection = state['ssh_connection'].split()
    if len(connection) != 4 or connection[0] != SOURCE or connection[2] != SERVER:
        raise RuntimeError('Unexpected SSH source/destination')
    unit = state['unit']
    if (state['hostname'] != 'vynalthai-dns' or unit['ActiveState'] != 'active'
            or unit['MemoryMax'] != '402653184' or unit['TasksMax'] != '64'
            or unit['LimitNOFILE'] != '1024' or state['apparmor'] != 'unbound (enforce)'
            or state['config_sha256'] != expected_hash or state['discard_timeout_ms'] != '15000'
            or state['forwards'] or state['tailscale_ipv4'] != SERVER
            or state['tailscaled_active'] != 'active' or not state['rollback_timer_active']
            or not state['rollback_snapshot_pending']):
        raise RuntimeError('Private service preconditions differ from the reviewed plan')
    lines = [line for line in state['listeners'].splitlines() if '"unbound"' in line]
    endpoints = {(line.split()[0], line.split()[4]) for line in lines}
    wanted = {(proto, f'{ip}:53') for proto in ('udp', 'tcp') for ip in ('127.0.0.1', SERVER)}
    if endpoints != wanted:
        raise RuntimeError('Unbound listeners differ from the private plan')


def accept(args, inspect=inspect_remote, query=check_query, clock=time.monotonic):
    receipt = {'pass': False, 'expected_config_sha256': args.config_sha256,
               'before': None, 'after': None, 'queries': [], 'error': None,
               'scope': 'windows-protected-transaction',
               'android_live_acceptance': 'PENDING LIVE ACCEPTANCE; separate bounded release gate'}
    started = clock()

    def budget(seconds):
        if args.deadline_seconds - (clock() - started) < seconds:
            raise RuntimeError('Insufficient acceptance deadline; no next query attempted')

    try:
        budget(27)  # Initial SSH + two PTR cases + first cold-case reservation.
        before = receipt['before'] = inspect(args.ssh_key)
        validate_state(before, args.config_sha256)
        # Deployment readiness sends exactly one localhost query. Any other
        # client query means we cannot attest first-use cold state; fail closed.
        if float(before['stats']['total.num.queries']) != 1:
            raise RuntimeError('First-use cache state unavailable: unexpected prior queries')
        # Local PTR must not prime any root/TLD cache; both are separate one-shot cases.
        for tcp in (False, True):
            budget(2)
            row = query(SERVER, '20.65.95.100.in-addr.arpa.', 'PTR', source=SOURCE,
                        tcp=tcp, expected='NOERROR', expected_ptr='dns.vynalthai.com.',
                        timeout=2, scenario='private-server-identity')
            receipt['queries'].append(row)
            if not row['pass']:
                raise RuntimeError('Private PTR identity failed; no retry')
        for scenario, timeout in [('dnssec-cold', 15), ('dnssec-warm', 2),
                                  ('standard', 5), ('diagnostic-cd', 5)]:
            for name, kind, tcp, rcode, ad, cd in case_plan(scenario):
                budget(timeout)
                row = query(SERVER, name, kind, source=SOURCE, tcp=tcp, expected=rcode,
                            ad=ad, cd=cd, timeout=timeout, scenario=scenario,
                            cache_evidence=f"PID {before['unit']['MainPID']}; explicit sequential {scenario}")
                receipt['queries'].append(row)
                print(json.dumps(row), flush=True)
                if not row['pass']:
                    raise RuntimeError('Acceptance failed; no retry or subsequent scenario')
            if scenario == 'dnssec-cold':
                budget(8)
                cold_hits = float(inspect(args.ssh_key)['stats']['total.num.cachehits'])
            if scenario == 'dnssec-warm':
                budget(8)
                warm_hits = float(inspect(args.ssh_key)['stats']['total.num.cachehits'])
                receipt['warm_cache_hit_delta'] = warm_hits - cold_hits
                if warm_hits - cold_hits < 4:
                    raise RuntimeError('Four warm cache hits not observed')
        budget(8)
        after = receipt['after'] = inspect(args.ssh_key, True)
        validate_state(after, args.config_sha256)
        for field in ('nft_sha256', 'sshd_sha256'):
            if before[field] != after[field]:
                raise RuntimeError(f'Management baseline changed: {field}')
        for field in ('MainPID', 'NRestarts'):
            if before['unit'][field] != after['unit'][field]:
                raise RuntimeError(f'Unbound changed during acceptance: {field}')
        if len(after.get('local_refused', [])) != 2 or not all(row['pass'] for row in after['local_refused']):
            raise RuntimeError('Unapproved loopback ACL test failed')
        if clock() - started > args.deadline_seconds:
            raise RuntimeError('Acceptance deadline exceeded; never confirm')
        receipt['pass'] = True
    except Exception as exc:
        receipt['error'] = {'type': type(exc).__module__ + '.' + type(exc).__name__, 'message': str(exc)}
    receipt['elapsed_seconds'] = round(clock() - started, 6)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ssh-key', required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--authorized-target', action='store_true', required=True)
    parser.add_argument('--deadline-seconds', type=float, default=100)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[a-f0-9]{64}', args.config_sha256) or not 0 < args.deadline_seconds <= 100:
        parser.error('Require reviewed SHA256 and acceptance deadline <=100s')
    result = accept(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'pass': result['pass'], 'error': result['error'],
                      'elapsed_seconds': result['elapsed_seconds']}), flush=True)
    raise SystemExit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
