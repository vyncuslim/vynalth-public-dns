"""Real Unbound in a LOCAL/CI network namespace, never an Oracle test.

Synthetic source IPs match both devices. No Tailscale process, real phone or
public recursion. Namespace has only loopback/no default route. AppArmor status
is reported honestly; --require-apparmor is mandatory in enforcing CI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import dns.flags
import dns.message
import dns.query
import dns.rcode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render import render
from local_runtime import Authority

SERVER = '100.95.65.20'
CLIENTS = {'windows': '100.85.132.14', 'oppo_android': '100.75.232.110'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inside', action='store_true')
    parser.add_argument('--require-apparmor', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.inside:
        argv = [sys.executable, str(Path(__file__).resolve()), '--inside', '--out', str(args.out.resolve())]
        if args.require_apparmor:
            argv.append('--require-apparmor')
        raise SystemExit(subprocess.run(['unshare', '--net', *argv]).returncode)
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
    for address in [SERVER, *CLIENTS.values(), '100.75.232.111', '198.51.100.44']:
        subprocess.run(['ip', 'addr', 'add', address+'/32', 'dev', 'lo'], check=True)
    assert not subprocess.check_output(['ip', 'route', 'show', 'default'], text=True).strip()
    conf, _ = render(json.loads((ROOT / 'config.private.example.json').read_text()))
    assert conf.encode() == (ROOT / 'plans/phase-b-unbound.conf').read_bytes()
    parent = '/var/lib/unbound' if Path('/etc/apparmor.d/usr.sbin.unbound').exists() else None
    result = {'pass': False, 'scope': 'local/CI network namespace; synthetic client IPs',
              'config_sha256': hashlib.sha256(conf.encode()).hexdigest(), 'clients': {},
              'denied': [], 'live_android': 'PENDING LIVE ACCEPTANCE', 'app_armor': None}
    with tempfile.TemporaryDirectory(prefix='vynalth-two-clients-', dir=parent) as folder:
        base = Path(folder)
        authority = Authority()
        proc = None
        try:
            (base / 'fixture.key').write_text(authority.keys.to_text()+'\n')
            conf = conf.replace('username: "unbound"', 'username: ""')
            conf = conf.replace('directory: "/etc/unbound"', f'directory: "{folder}"')
            conf = conf.replace('port: 53', 'port: 15357')
            conf = conf.replace('/usr/share/dns/root.hints', str(Path(os.environ.get('DNS_ROOT_DATA', '/usr/share/dns')) / 'root.hints'))
            conf = '\n'.join(line for line in conf.splitlines() if 'auto-trust-anchor-file:' not in line)+'\n'
            conf = conf.replace('/run/unbound.ctl', str(base / 'control.sock'))
            conf += (f'\nserver:\n    pidfile: "{base}/unbound.pid"\n    use-syslog: no\n'
                     f'    trust-anchor-file: "{base}/fixture.key"\n    do-not-query-localhost: no\n'
                     '    local-zone: "fixture.test." static\n'
                     '    local-data: "a.fixture.test. 300 IN A 203.0.113.7"\n'
                     '    local-data: "a.fixture.test. 300 IN AAAA 2001:db8::7"\n'
                     '    local-zone: "test." nodefault\n'
                     'stub-zone:\n    name: "signed-fixture.test."\n    stub-addr: 127.0.0.1@15354\n    stub-first: no\n')
            path = base / 'unbound.conf'
            path.write_text(conf)
            subprocess.run(['unbound-checkconf', str(path)], check=True)
            def limits():
                resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
            with (base / 'log').open('w') as log:
                proc = subprocess.Popen(['unbound', '-d', '-c', str(path)], stdout=log, stderr=log, preexec_fn=limits)
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError((base / 'log').read_text())
                    if (base / 'control.sock').exists():
                        break
                    time.sleep(.05)
                else:
                    raise RuntimeError('Isolated socket readiness failed')
                result['app_armor'] = Path(f'/proc/{proc.pid}/attr/current').read_text().strip().rstrip('\0')
                if args.require_apparmor and result['app_armor'] != 'unbound (enforce)':
                    raise RuntimeError('Required enforcing AppArmor unavailable')
                result['app_armor_test'] = 'PASS' if result['app_armor'] == 'unbound (enforce)' else 'NOT TESTED: enforcing profile unavailable; never disabled'
                def query(source, name, kind='A', tcp=False, cd=False):
                    q = dns.message.make_query(name, kind, want_dnssec=True)
                    if cd:
                        q.flags |= dns.flags.CD
                    start = time.monotonic()
                    reply = (dns.query.tcp if tcp else dns.query.udp)(q, SERVER, port=15357, source=source, timeout=2)
                    return reply, time.monotonic()-start
                control = ['unbound-control', '-c', str(path)]
                assert not subprocess.check_output(control+['list_forwards'], text=True).strip()
                result['forwarders'] = []
                def hits():
                    stats = dict(line.split('=', 1) for line in subprocess.check_output(control+['stats_noreset'], text=True).splitlines())
                    return float(stats['total.num.cachehits'])
                for client, source in CLIENTS.items():
                    rows = []
                    for tcp in (False, True):
                        for kind in ('A', 'AAAA'):
                            r, elapsed = query(source, 'a.fixture.test.', kind, tcp)
                            assert r.rcode() == dns.rcode.NOERROR and r.answer
                            rows.append({'type': kind, 'tcp': tcp, 'rcode': 'NOERROR', 'elapsed_seconds': elapsed})
                        r, _ = query(source, '20.65.95.100.in-addr.arpa.', 'PTR', tcp)
                        assert r.rcode() == dns.rcode.NOERROR and len(r.answer) == 1
                        assert len(r.answer[0]) == 1 and r.answer[0][0].target.to_text() == 'dns.vynalthai.com.'
                        r, _ = query(source, '21.65.95.100.in-addr.arpa.', 'PTR', tcp)
                        assert r.rcode() == dns.rcode.NXDOMAIN and not r.answer
                        for name, expected, ad in [('valid.signed-fixture.test.', dns.rcode.NOERROR, True),
                                                   ('bogus.signed-fixture.test.', dns.rcode.SERVFAIL, False)]:
                            r, elapsed = query(source, name, tcp=tcp)
                            assert r.rcode() == expected and bool(r.flags & dns.flags.AD) == ad
                            rows.append({'name': name, 'tcp': tcp, 'rcode': dns.rcode.to_text(r.rcode()), 'AD': ad, 'elapsed_seconds': elapsed})
                        r, _ = query(source, 'bogus.signed-fixture.test.', tcp=tcp, cd=True)
                        assert r.rcode() == dns.rcode.NOERROR and r.flags & dns.flags.CD and not r.flags & dns.flags.AD
                    result['clients'][client] = {'source': source, 'pass': True, 'ptr': 'dns.vynalthai.com.', 'unrelated_reverse': 'NXDOMAIN unchanged', 'queries': rows}
                    before = hits()
                    for tcp in (False, True):
                        r, _ = query(source, 'valid.signed-fixture.test.', tcp=tcp)
                        assert r.rcode() == dns.rcode.NOERROR and r.flags & dns.flags.AD
                    delta = hits()-before
                    assert delta >= 2
                    result['clients'][client]['warm_cache_hit_delta'] = delta
                for source in ('100.75.232.111', '198.51.100.44'):
                    for tcp in (False, True):
                        for name, kind in [('a.fixture.test.', 'A'), ('20.65.95.100.in-addr.arpa.', 'PTR')]:
                            r, _ = query(source, name, kind, tcp)
                            assert r.rcode() == dns.rcode.REFUSED
                            result['denied'].append({'source': source, 'tcp': tcp, 'type': kind, 'rcode': 'REFUSED'})
                result['pass'] = True
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            authority.close()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
