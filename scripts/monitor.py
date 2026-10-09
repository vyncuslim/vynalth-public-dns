"""Local service sampler and structured alerts. No external transmissions."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def alerts(current, previous):
    events = []
    if not current['healthy']:
        events.append('DNS_CONTROL_UNAVAILABLE')
    memory = current['memory']
    if memory['MemAvailable_kb'] < memory['MemTotal_kb'] * 0.15:
        events.append('LOW_MEMORY')
    if previous:
        if int(current['restarts'] or 0) > int(previous['restarts'] or 0):
            events.append('SERVICE_RESTART')
        now, old = current['dns'], previous['dns']
        queries = now.get('total.num.queries', 0) - old.get('total.num.queries', 0)
        failures = now.get('num.answer.rcode.SERVFAIL', 0) - old.get('num.answer.rcode.SERVFAIL', 0)
        if queries >= 20 and failures / queries > 0.05:
            events.append('HIGH_SERVFAIL_RATIO')
        if now.get('total.num.queries_ip_ratelimited', 0) > old.get('total.num.queries_ip_ratelimited', 0):
            events.append('CLIENT_RATE_LIMIT')
    return events

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', type=Path, default=Path('/var/lib/vynalth-dns/monitor.json'))
    a = p.parse_args()
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/metrics.py')], text=True, capture_output=True)
    if not proc.stdout:
        print(json.dumps({'alerts': ['METRICS_COLLECTION_FAILED']}))
        sys.exit(1)
    current = json.loads(proc.stdout)
    previous = json.loads(a.state.read_text()) if a.state.exists() else None
    events = alerts(current, previous)
    print(json.dumps({'metrics': current, 'alerts': events}))
    a.state.parent.mkdir(parents=True, exist_ok=True)
    temp = a.state.with_suffix('.tmp')
    temp.write_text(json.dumps(current))
    temp.replace(a.state)
    sys.exit(proc.returncode)

if __name__ == '__main__':
    main()
