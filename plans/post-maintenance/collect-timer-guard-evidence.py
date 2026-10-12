from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

def run(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()

def fingerprint():
    return {'pid': run('systemctl', 'show', 'unbound', '-p', 'MainPID', '--value'),
            'invocation': run('systemctl', 'show', 'unbound', '-p', 'InvocationID', '--value'),
            'config': hashlib.sha256(Path('/etc/unbound/unbound.conf').read_bytes()).hexdigest(),
            'nft': hashlib.sha256(run('nft', '--stateless', 'list', 'ruleset').encode()).hexdigest(),
            'ssh': hashlib.sha256(run('sshd', '-T').encode()).hexdigest()}

result = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'before': fingerprint(), 'cases': []}
unit = 'vynalth-timer-guard-lab-' + str(os.getpid())
with tempfile.TemporaryDirectory(prefix='vynalth-guard-', dir='/var/lib/unbound') as folder:
    try:
        for seconds in [180, 60]:
            subprocess.run(['systemd-run', '--unit=' + unit, '--on-active=' + str(seconds) + 's',
                   '--timer-property=AccuracySec=1s', '/usr/bin/touch', folder + '/fired'], check=True)
            proc = subprocess.run(['.venv/bin/python', 'proposals/check-rollback-timer.py', '--unit', unit + '.timer'], text=True, capture_output=True, timeout=10)
            row = {'declared_seconds': seconds, 'exit_code': proc.returncode, 'diagnostics': json.loads(proc.stdout)}
            assert (proc.returncode == 0) == (seconds == 180), row
            result['cases'].append(row)
            # The never-started service may already be garbage collected after
            # canceling its timer; only the active lab timer needs stopping.
            subprocess.run(['systemctl', 'stop', unit + '.timer'], check=True)
        proc = subprocess.run(['.venv/bin/python', 'proposals/check-rollback-timer.py', '--unit', unit + '.timer'], text=True, capture_output=True, timeout=10)
        assert proc.returncode != 0
        result['cases'].append({'stopped_or_missing_timer': True, 'exit_code': proc.returncode, 'diagnostics': json.loads(proc.stdout)})
        assert not Path(folder + '/fired').exists(), 'Lab never needs to execute callback'
    finally:
        subprocess.run(['systemctl', 'stop', unit + '.timer', unit + '.service'], capture_output=True)
result['after'] = fingerprint()
assert result['after'] == result['before']
result['pass'] = True
Path('artifacts/post-maintenance-guard.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
