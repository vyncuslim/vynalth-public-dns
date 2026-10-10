"""Read-only receipt for the approved private service; never changes service state."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from acceptance import check_query


def run(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def inspect(connection, local_refused=False):
    unit = dict(line.split('=', 1) for line in run('systemctl', 'show', 'unbound',
                '-p', 'MainPID', '-p', 'NRestarts', '-p', 'MemoryMax', '-p', 'TasksMax',
                '-p', 'LimitNOFILE', '-p', 'ActiveState').splitlines())
    pid = int(unit['MainPID'])
    if pid <= 0:
        raise RuntimeError('No active Unbound PID')
    control = ('unbound-control', '-s', '/run/unbound.ctl')
    stats = dict(line.split('=', 1) for line in run(*control, 'stats_noreset').splitlines())
    result = {
        'ssh_connection': connection, 'hostname': run('hostname'), 'unit': unit,
        'apparmor': Path(f'/proc/{pid}/attr/current').read_text().strip(),
        'config_sha256': hashlib.sha256(Path('/etc/unbound/unbound.conf').read_bytes()).hexdigest(),
        'nft_sha256': hashlib.sha256(run('nft', '--stateless', 'list', 'ruleset').encode()).hexdigest(),
        'sshd_sha256': hashlib.sha256(run('/usr/sbin/sshd', '-T').encode()).hexdigest(),
        'tailscale_ipv4': run('tailscale', 'ip', '-4'),
        'tailscaled_active': run('systemctl', 'is-active', 'tailscaled'),
        'listeners': run('ss', '-lntup'),
        'rollback_timer_active': subprocess.run(['systemctl', 'is-active', '--quiet',
                                                  'vynalth-rollback.timer']).returncode == 0,
        'rollback_snapshot_pending': Path('/var/lib/vynalth-dns/rollback/service-only').is_file(),
        'discard_timeout_ms': run(*control, 'get_option', 'discard-timeout'),
        'forwards': run(*control, 'list_forwards'),
        'stats': {k: v for k, v in stats.items() if k.startswith('total.')},
    }
    if local_refused:
        result['local_refused'] = [check_query('127.0.0.1', 'example.com.', source='127.0.0.2',
                                      tcp=tcp, expected='REFUSED', timeout=2,
                                      scenario='unapproved-loopback-client') for tcp in (False, True)]
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ssh-connection', required=True)
    parser.add_argument('--local-refused', action='store_true')
    args = parser.parse_args()
    print(json.dumps(inspect(args.ssh_connection, args.local_refused)))
