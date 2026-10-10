"""Fail-closed receipt/deadline check. Reads state only; never confirms/deploys."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from acceptance import case_plan


def validate(receipt, transaction, now, boot_id, config_hash, pid):
    if (receipt.get('pass') is not True or receipt.get('error') is not None
            or receipt.get('expected_config_sha256') != transaction['config_sha256']
            or config_hash != transaction['config_sha256'] or boot_id != transaction['boot_id']
            or not 0 <= now - transaction['started_monotonic'] < 140
            or not now < transaction['global_deadline_monotonic']
            or not 0 <= receipt['elapsed_seconds'] <= 100
            or not receipt.get('warm_cache_hit_delta', 0) >= 4):
        raise ValueError('Receipt, config, boot or transaction deadline invalid')
    expected = [('20.65.95.100.in-addr.arpa.', 'PTR', tcp, 'NOERROR', False, False,
                 'private-server-identity', 2) for tcp in (False, True)]
    for scenario, limit in [('dnssec-cold', 15), ('dnssec-warm', 2), ('standard', 5), ('diagnostic-cd', 5)]:
        expected += [(*case, scenario, limit) for case in case_plan(scenario)]
    rows = receipt['queries']
    if len(rows) != len(expected):
        raise ValueError('Incomplete acceptance query inventory')
    for row, (name, kind, tcp, rcode, ad, cd, scenario, limit) in zip(rows, expected):
        response = row['response']
        if (row.get('pass') is not True or row['attempts'] != 1 or row['error'] is not None
                or row['query']['name'] != name or row['query']['type'] != kind
                or row['transport'] != ('TCP' if tcp else 'UDP') or row['scenario'] != scenario
                or row['server'] != '100.95.65.20' or row['source'] != '100.85.132.14'
                or row['port'] != 53 or not 0 <= row['elapsed_seconds'] <= limit
                or row['latency_limit_seconds'] != limit or response['rcode'] != rcode
                or (ad and not response['AD']) or ((cd or rcode == 'SERVFAIL') and response['AD'])
                or response['TC'] or (cd and not response['CD'])):
            raise ValueError('Failed/mismatched acceptance query')
        if kind == 'PTR' and response.get('ptr_targets') != ['dns.vynalthai.com.']:
            raise ValueError('Incorrect private PTR identity')
    for state in (receipt['before'], receipt['after']):
        if state['unit']['MainPID'] != pid or state['config_sha256'] != config_hash:
            raise ValueError('Receipt process/config no longer matches')
    denied = receipt['after']['local_refused']
    if len(denied) != 2 or any(row.get('pass') is not True or row['response']['rcode'] != 'REFUSED'
                             or row['attempts'] != 1 for row in denied):
        raise ValueError('Missing unauthorized-client rejection')
    if {row['transport'] for row in denied} != {'UDP', 'TCP'}:
        raise ValueError('Incomplete ACL transport coverage')
    for field in ('nft_sha256', 'sshd_sha256'):
        if receipt['before'][field] != receipt['after'][field]:
            raise ValueError('Management state changed')
    if receipt['before']['unit']['NRestarts'] != receipt['after']['unit']['NRestarts']:
        raise ValueError('Unexpected restart')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('receipt', type=Path)
    parser.add_argument('ssh_connection')
    parser.add_argument('--deadline-only', action='store_true', help='Internal final recheck before atomic confirmation')
    args = parser.parse_args()
    transaction = json.loads(Path('/var/lib/vynalth-dns/rollback/transaction.json').read_text())
    receipt = json.loads(args.receipt.read_text())
    connection = args.ssh_connection.split()
    if len(connection) != 4 or connection[0] != '100.85.132.14' or connection[2] != '100.95.65.20':
        raise ValueError('Unexpected confirmation SSH path')
    pid = subprocess.check_output(['systemctl', 'show', 'unbound', '-p', 'MainPID', '--value'], text=True, timeout=5).strip()
    if not args.deadline_only:
        if hashlib.sha256(Path('/var/lib/vynalth-dns/rollback.sh').read_bytes()).digest() != hashlib.sha256((Path(__file__).resolve().parent / 'rollback.sh').read_bytes()).digest():
            raise ValueError('Installed rollback integrity changed')
        def read(*argv):
            return subprocess.check_output(argv, text=True, timeout=5).strip()
        for field, argv in [('nft_sha256', ['nft', '--stateless', 'list', 'ruleset']),
                            ('sshd_sha256', ['/usr/sbin/sshd', '-T'])]:
            if hashlib.sha256(read(*argv).encode()).hexdigest() != receipt['after'][field]:
                raise ValueError('Management drift before confirmation')
        if Path(f'/proc/{pid}/attr/current').read_text().strip() != 'unbound (enforce)':
            raise ValueError('Unbound AppArmor changed')
        props = dict(line.split('=', 1) for line in read('systemctl', 'show', 'unbound',
                     '-p', 'MemoryMax', '-p', 'TasksMax', '-p', 'LimitNOFILE', '-p', 'ActiveState').splitlines())
        if props != {'MemoryMax': '402653184', 'TasksMax': '64', 'LimitNOFILE': '1024', 'ActiveState': 'active'}:
            raise ValueError('Resource/service state changed')
        endpoints = {(line.split()[0], line.split()[4]) for line in read('ss', '-lntup').splitlines() if '"unbound"' in line}
        if endpoints != {(proto, ip + ':53') for proto in ('udp', 'tcp') for ip in ('127.0.0.1', '100.95.65.20')}:
            raise ValueError('DNS listeners changed')
        subprocess.run(['systemctl', 'is-active', '--quiet', 'tailscaled'], check=True, timeout=5)
    validate(receipt, transaction, time.monotonic(), Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
             hashlib.sha256(Path('/etc/unbound/unbound.conf').read_bytes()).hexdigest(), pid)
    print('PASS complete acceptance receipt and transaction <140s')


if __name__ == '__main__':
    main()
