"""Only disposable lab units; production service calls in the lab are stubbed."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

def run(*args, allowed=(0,)):
    p = subprocess.run(args, text=True, capture_output=True, timeout=10)
    if p.returncode not in allowed:
        raise RuntimeError(p.stderr)
    return p.stdout.strip()

def fingerprint():
    return {'pid': run('systemctl', 'show', 'unbound', '-p', 'MainPID', '--value'),
      'invocation': run('systemctl', 'show', 'unbound', '-p', 'InvocationID', '--value'),
      'config': hashlib.sha256(Path('/etc/unbound/unbound.conf').read_bytes()).hexdigest(),
      'nft': hashlib.sha256(run('nft', '--stateless', 'list', 'ruleset').encode()).hexdigest(),
      'ssh': hashlib.sha256(run('sshd', '-T').encode()).hexdigest()}

out = Path('artifacts/post-maintenance-rollback.json')
before = fingerprint()
result = {'started_utc': datetime.now(timezone.utc).isoformat(), 'production_before': before,
          'production_after': None, 'canceled_timer': None, 'real_180s_lab': None}
# Recreate an independent benign timer name after early cancellation. Never
# inspect/stop/recreate the real vynalth-rollback production unit here.
unit = 'vynalth-transient-reuse-lab-' + str(__import__('os').getpid())
with tempfile.TemporaryDirectory(prefix='vynalth-transient-', dir='/var/lib/unbound') as folder:
    marker = str(Path(folder) / 'fired')
    try:
        armed = run('systemd-run', '--unit=' + unit, '--on-active=180s', '--timer-property=AccuracySec=1s', '/usr/bin/touch', marker)
        active = run('systemctl', 'show', unit + '.timer', '-p', 'ActiveState', '-p', 'NextElapseUSecMonotonic', '-p', 'FragmentPath')
        run('systemctl', 'stop', unit + '.timer')
        canceled = run('systemctl', 'show', unit + '.timer', '-p', 'ActiveState', '-p', 'LoadState', '-p', 'FragmentPath')
        assert not Path(marker).exists()
        rearmed = run('systemd-run', '--unit=' + unit, '--on-active=2s', '--timer-property=AccuracySec=1s', '/usr/bin/touch', marker)
        start = time.monotonic()
        while not Path(marker).exists() and time.monotonic() - start < 10:
            time.sleep(0.1)
        assert Path(marker).exists(), 'Same-name benign rearm failed'
        result['canceled_timer'] = {'unit': unit, 'armed': armed, 'active': active,
             'after_cancel': canceled, 'same_name_rearm': rearmed,
             'rearm_marker_observed': True,
             'journal': run('journalctl', '-u', unit + '.timer', '-u', unit + '.service', '--no-pager')}
    finally:
        run('systemctl', 'stop', unit + '.timer', unit + '.service', allowed=(0, 5))
start = time.monotonic()
proc = subprocess.Popen(['bash', 'tests/service_rollback_lab.sh'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
lines = []
labunit = None
for line in proc.stdout:
    lines.append(line)
    print(line, end='', flush=True)
    match = re.search(r'Waiting for isolated timer (vynalth-rollback-test-\d+)', line)
    if match:
        labunit = match.group(1)
        result['real_180s_lab'] = {'unit': labunit, 'active_properties': run('systemctl', 'show', labunit + '.timer',
             '-p', 'ActiveState', '-p', 'NextElapseUSecMonotonic', '-p', 'AccuracyUSec', '-p', 'TimersMonotonic')}
        out.write_text(json.dumps(result, indent=2))
code = proc.wait()
result['real_180s_lab'] = {**(result['real_180s_lab'] or {}), 'exit_code': code,
    'elapsed_seconds': round(time.monotonic() - start, 6), 'stdout': ''.join(lines),
    'journal': run('journalctl', '-u', labunit + '.timer', '-u', labunit + '.service', '--no-pager') if labunit else None}
result['production_after'] = fingerprint()
result['pass'] = code == 0 and before == result['production_after'] and result['canceled_timer']['rearm_marker_observed']
out.write_text(json.dumps(result, indent=2))
print(json.dumps({'pass': result['pass'], 'production_unchanged': before == result['production_after']}), flush=True)
raise SystemExit(0 if result['pass'] else 1)
