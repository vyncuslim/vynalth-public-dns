"""Strict private-mount fixture commands; refuses use in the host mount namespace."""
import json
import os
from pathlib import Path
import sys
import time

lab = Path('/tmp/vynalth-transaction')
assert (lab / 'marker').is_file()
assert Path('/proc/self/ns/mnt').readlink().as_posix() != (lab / 'host-mount').read_text()
command, args = sys.argv[1], sys.argv[2:]
timer = Path('/run/systemd/transient/vynalth-rollback.timer')
if command == 'systemd-run':
    assert args == ['--unit=vynalth-rollback', '--on-active=180s', '--timer-property=AccuracySec=1s', '/bin/bash', '/var/lib/vynalth-dns/rollback.sh', '--service-only']
    assert Path('/etc/unbound/unbound.conf').read_bytes() == (lab / 'original.conf').read_bytes(), 'Writes preceded timer'
    timer.write_text(json.dumps({'entered': int(time.monotonic() * 1e6)}))
elif command == 'systemctl':
    if args[:2] == ['show', 'unbound'] and args[-1] == '--value':
        print((lab / 'production-pid').read_text().strip() if 'MainPID' in args else '')
    elif args == ['show', 'unbound', '-p', 'MemoryMax', '-p', 'TasksMax', '-p', 'LimitNOFILE', '-p', 'ActiveState']:
        print('MemoryMax=402653184\nTasksMax=64\nLimitNOFILE=1024\nActiveState=active')
    elif args[:2] == ['is-active', '--quiet']:
        if args[-1] == 'vynalth-rollback.timer' and not timer.exists():
            raise SystemExit(1)
        assert args[-1] in ('unbound', 'tailscaled', 'vynalth-rollback.timer')
    elif args == ['stop', 'vynalth-rollback.timer']:
        timer.unlink()
    elif args not in (['daemon-reload'], ['restart', 'unbound']):
        raise SystemExit('Unexpected lab systemctl: ' + repr(args))
elif command == 'busctl':
    assert timer.is_file()
    entered = json.loads(timer.read_text())['entered']
    if 'GetUnit' in args:
        data = ['/unit/lab']
    else:
        data = {'ActiveState': 'active', 'SubState': 'waiting', 'FragmentPath': str(timer),
                'ActiveEnterTimestampMonotonic': entered, 'AccuracyUSec': 1000000,
                'NextElapseUSecMonotonic': entered + (60000000 if os.environ['VYNALTH_LAB_MODE'] == 'bad-timer' else 180000000)}[args[-1]]
    print(json.dumps({'data': data}))
elif command == 'ip':
    assert args == ['-4', 'addr', 'show', 'dev', 'tailscale0']
    print('inet 100.95.65.20/32')
elif command == 'dig':
    assert args == ['@127.0.0.1', 'localhost', '+time=2', '+tries=1']
    print('status: NOERROR')
elif command == 'nft' and args == ['--stateless', 'list', 'ruleset']:
    print('LAB rules')
elif command == 'ss' and args == ['-lntup']:
    for proto in ('udp', 'tcp'):
        for addr in ('127.0.0.1', '100.95.65.20'):
            print(f'{proto} LISTEN 0 0 {addr}:53 *:* users:(("unbound"))')
else:
    raise SystemExit('Prohibited/unexpected command in lab: ' + command)
