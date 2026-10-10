"""Read-only exact approved-baseline gate; never updates the baseline."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness', ROOT / 'scripts/post-maintenance-readiness.py')
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)

if __name__ == '__main__':
    path = ROOT / 'plans/post-boot-baseline.json'
    if len(sys.argv) != 3 or hashlib.sha256(path.read_bytes()).hexdigest() != sys.argv[1]:
        raise SystemExit('Exact human-reviewed baseline SHA256 required')
    baseline = json.loads(path.read_text())
    os.chdir(ROOT)  # Manifest entries are repository-relative, regardless of caller cwd.
    row = readiness.sample(sys.argv[2])
    if (row['fingerprint'] != baseline['fingerprint'] or row['operational_failures']
            or row['reboot_required'] or row['time_sync'] != 'yes'):
        print(json.dumps({'operational_failures': row['operational_failures'],
              'reboot_required': row['reboot_required'], 'time_sync': row['time_sync'],
              'drift_fields': [key for key, value in row['fingerprint'].items()
                               if baseline['fingerprint'].get(key) != value]}))
        raise SystemExit('Baseline drift, maintenance, pending reboot or clock failure')
    print('PASS pinned post-boot baseline (no refresh); deployment requires separate authorization')
