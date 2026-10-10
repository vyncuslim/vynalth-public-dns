"""Only unique harmless transient lab units; production timer is never touched."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
unit = 'vynalth-candidate-timer-' + str(os.getpid())
rows = []
with tempfile.TemporaryDirectory(prefix='vynalth-timer-', dir='/var/lib/unbound') as folder:
    try:
        for seconds in (180, 60):
            subprocess.run(['systemd-run', '--unit=' + unit, '--on-active=' + str(seconds) + 's',
                            '--timer-property=AccuracySec=1s', '/usr/bin/touch', folder + '/fired'], check=True)
            proc = subprocess.run(['python3', str(ROOT / 'scripts/check-rollback-timer.py'), '--unit', unit + '.timer'],
                                  text=True, capture_output=True, check=False)
            row = json.loads(proc.stdout)
            assert row['pass'] == (seconds == 180)
            rows.append(row)
            subprocess.run(['systemctl', 'stop', unit + '.timer'], check=True)
        proc = subprocess.run(['python3', str(ROOT / 'scripts/check-rollback-timer.py'), '--unit', unit + '.timer'],
                              text=True, capture_output=True)
        assert proc.returncode != 0
        rows.append(json.loads(proc.stdout))
        assert not Path(folder + '/fired').exists()
    finally:
        subprocess.run(['systemctl', 'stop', unit + '.timer', unit + '.service'], capture_output=True)
print(json.dumps({'pass': True, 'cases': rows}))
