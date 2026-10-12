"""Historical proposal; canonical integrated gate is scripts/check-rollback-timer.py.

Check the actual independent monotonic timer before any active file write.
Only systemd property reads; no arming, stopping, cleanup or service changes.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time


def call(*args):
    proc = subprocess.run(['busctl', '--json=short', *args], text=True,
                          capture_output=True, timeout=5, check=True)
    data = json.loads(proc.stdout)['data']
    # busctl method results wrap arguments; scalar properties are unwrapped.
    return data[0] if isinstance(data, list) and len(data) == 1 else data


def check(unit):
    path = call('call', 'org.freedesktop.systemd1', '/org/freedesktop/systemd1',
                'org.freedesktop.systemd1.Manager', 'GetUnit', 's', unit)
    def prop(interface, name):
        return call('get-property', 'org.freedesktop.systemd1', path,
                    'org.freedesktop.systemd1.' + interface, name)
    result = {'unit': unit, 'pass': False,
              'active': prop('Unit', 'ActiveState'), 'substate': prop('Unit', 'SubState'),
              'fragment': prop('Unit', 'FragmentPath'),
              'entered_usec': prop('Unit', 'ActiveEnterTimestampMonotonic'),
              'next_usec': prop('Timer', 'NextElapseUSecMonotonic'),
              'accuracy_usec': prop('Timer', 'AccuracyUSec')}
    result['configured_interval_usec'] = result['next_usec'] - result['entered_usec']
    result['remaining_seconds'] = round(result['next_usec'] / 1e6 - time.monotonic(), 6)
    result['pass'] = (result['active'] == 'active' and result['substate'] == 'waiting'
        and result['fragment'] == '/run/systemd/transient/' + unit
        and Path(result['fragment']).is_file() and result['accuracy_usec'] == 1000000
        and abs(result['configured_interval_usec'] - 180000000) <= 1000000
        and 170 <= result['remaining_seconds'] <= 181)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--unit', default='vynalth-rollback.timer')
    args = parser.parse_args()
    try:
        result = check(args.unit)
    except Exception as exc:
        result = {'unit': args.unit, 'pass': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    print(json.dumps(result))
    raise SystemExit(0 if result['pass'] else 1)
