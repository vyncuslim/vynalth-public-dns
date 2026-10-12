"""Local structured counters; no query names or client histories."""
import json
import subprocess
import time

def main():
    proc = subprocess.run(['unbound-control', 'stats_noreset'], capture_output=True, text=True)
    stats = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            try:
                stats[k] = float(v)
            except ValueError:
                pass
    queries = stats.get('total.num.queries', 0)
    stats['cache_hit_ratio'] = stats.get('total.num.cachehits', 0) / queries if queries else 0
    memory = {}
    with open('/proc/meminfo') as handle:
        for line in handle:
            key, value = line.split(':', 1)
            if key in ('MemTotal', 'MemAvailable'):
                memory[key + '_kb'] = int(value.split()[0])
    result = {'timestamp': time.time(), 'healthy': proc.returncode == 0,
              'dns': stats, 'memory': memory,
              'load': open('/proc/loadavg').read().split()[:3],
              'restarts': subprocess.check_output(['systemctl', 'show', 'unbound', '-p', 'NRestarts', '--value'], text=True).strip()}
    print(json.dumps(result))
    raise SystemExit(0 if proc.returncode == 0 else 1)

if __name__ == '__main__':
    main()
