"""Isolated loopback Unbound process, no host service/firewall changes.

Uses local data only; public recursion is tested separately by acceptance.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import socket
import threading
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.exception
import dns.rrset
import dns.dnssec
import dns.rdatatype
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render import render

class Authority:
    """Private fixture only. Never sends network queries."""
    def __init__(self):
        self.count = 0
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.dnskey = dns.dnssec.make_dnskey(self.key.public_key(), 'ECDSAP256SHA256', flags=257)
        self.keys = dns.rrset.from_rdata('signed-fixture.test.', 300, self.dnskey)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', 15354))
        self.sock.settimeout(0.1)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                wire, peer = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            request = dns.message.from_wire(wire)
            response = dns.message.make_response(request)
            response.flags |= dns.flags.AA
            name = request.question[0].name.to_text()
            kind = request.question[0].rdtype
            self.count += 1
            signed = name.endswith('.signed-fixture.test.') or name == 'signed-fixture.test.'
            rrset = None
            if signed and kind == dns.rdatatype.DNSKEY:
                rrset = self.keys
            elif signed and kind == dns.rdatatype.A:
                rrset = dns.rrset.from_text(name, 300, 'IN', 'A', '203.0.113.9')
            if rrset is not None:
                sig = dns.dnssec.sign(rrset, self.key, 'signed-fixture.test.', self.dnskey,
                                      inception=int(time.time()) - 3600, expiration=int(time.time()) + 86400)
                if name.startswith('bogus.'):
                    rrset = dns.rrset.from_text(name, 300, 'IN', 'A', '203.0.113.10')
                response.answer.extend([rrset, dns.rrset.from_rdata(name, 300, sig)])
                self.sock.sendto(response.to_wire(), peer)
                continue
            if kind == 1:
                addr = '10.1.2.3' if name.startswith('private.') else '203.0.113.9'
                response.answer.append(dns.rrset.from_text(name, 300, 'IN', 'A', addr))
            elif kind == 28:
                response.answer.append(dns.rrset.from_text(name, 300, 'IN', 'AAAA', 'fd00::7'))
            self.sock.sendto(response.to_wire(), peer)

    def close(self):
        self.stop.set()
        self.thread.join(timeout=1)
        self.sock.close()

def main():
    cfg = json.loads((ROOT / 'config.example.json').read_text())
    conf, _ = render(cfg)
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        # Preserve security settings; substitute writable paths and high loopback port.
        conf = conf.replace('username: "unbound"', 'username: ""')
        conf = conf.replace('directory: "/etc/unbound"', f'directory: "{folder}"')
        conf = conf.replace('port: 53', 'port: 15353')
        data_dir = Path(os.environ.get('DNS_ROOT_DATA', '/usr/share/dns'))
        conf = conf.replace('/usr/share/dns/root.hints', str(data_dir / 'root.hints'))
        conf = conf.replace('/var/lib/unbound/root.key', str(base / 'root.key'))
        conf = conf.replace('/run/unbound/control.sock', str(base / 'control.sock'))
        conf += '\nserver:\n    pidfile: "' + str(base / 'unbound.pid') + '"\n'
        conf += '    use-syslog: no\n    ip-ratelimit: 0\n'
        conf += '    local-zone: "fixture.test." static\n'
        conf += '    local-data: "a.fixture.test. 300 IN A 203.0.113.7"\n'
        conf += '    local-data: "a.fixture.test. 300 IN AAAA 2001:db8::7"\n'
        conf += '    local-zone: "blocked.fixture.test." refuse\n'
        conf += '    do-not-query-localhost: no\n'
        conf += '    domain-insecure: "authority.test."\n'
        conf += '    local-zone: "test." nodefault\n'
        conf += '    local-zone: "authority.test." nodefault\n'
        conf += '    trust-anchor-file: "' + str(base / 'fixture.key') + '"\n'
        for n in range(30):
            conf += f'    local-data: \'large.fixture.test. 300 IN TXT "{n:02d}' + 'x' * 180 + '"\'\n'
        conf += 'stub-zone:\n    name: "authority.test."\n    stub-addr: 127.0.0.1@15354\n    stub-first: no\n'
        conf += 'stub-zone:\n    name: "signed-fixture.test."\n    stub-addr: 127.0.0.1@15354\n    stub-first: no\n'
        (base / 'root.key').write_bytes((data_dir / 'root.key').read_bytes())
        path = base / 'unbound.conf'
        path.write_text(conf)
        def start():
            log = open(base / 'unbound.log', 'a')
            proc = subprocess.Popen(['unbound', '-d', '-c', str(path)], stdout=log, stderr=log)
            for _ in range(50):
                if proc.poll() is not None:
                    raise RuntimeError((base / 'unbound.log').read_text())
                try:
                    query('a.fixture.test.', 'A')
                    return proc, log
                except (OSError, dns.exception.Timeout):
                    time.sleep(0.1)
            proc.terminate()
            proc.wait()
            raise RuntimeError('Resolver did not become ready')
        def query(name, kind, tcp=False, payload=1232):
            q = dns.message.make_query(name, kind, use_edns=True, payload=payload, want_dnssec=True)
            return (dns.query.tcp if tcp else dns.query.udp)(q, '127.0.0.1', port=15353, timeout=0.3)
        authority = Authority()
        (base / 'fixture.key').write_text(authority.keys.to_text() + '\n')
        subprocess.run(['unbound-checkconf', str(path)], check=True)
        proc, log = start()
        try:
            for tcp in (False, True):
                for kind in ('A', 'AAAA'):
                    r = query('a.fixture.test.', kind, tcp)
                    assert r.rcode() == 0 and r.answer
            assert query('missing.fixture.test.', 'A').rcode() == dns.rcode.NXDOMAIN
            assert query('blocked.fixture.test.', 'A').rcode() == dns.rcode.REFUSED
            r = query('large.fixture.test.', 'TXT', payload=512)
            assert r.flags & dns.flags.TC
            assert query('large.fixture.test.', 'TXT', tcp=True).answer
            for tcp in (False, True):
                request = dns.message.make_query('a.fixture.test.', 'A')
                response = (dns.query.tcp if tcp else dns.query.udp)(request, '127.0.0.1', port=15353, source='127.0.0.2', timeout=1)
                assert response.rcode() == dns.rcode.REFUSED
            response = query('cached.authority.test.', 'A')
            assert response.answer, response.to_text() + f' authority_requests={authority.count}'
            first = authority.count
            assert query('cached.authority.test.', 'A').answer
            assert authority.count == first, 'Cache miss unexpectedly queried local authority again'
            assert not query('private.authority.test.', 'A').answer
            assert not query('private.authority.test.', 'AAAA').answer
            signed = query('valid.signed-fixture.test.', 'A')
            assert signed.answer and signed.flags & dns.flags.AD, signed.to_text()
            assert query('bogus.signed-fixture.test.', 'A').rcode() == dns.rcode.SERVFAIL
            authority.close()
            # Uncached name against unavailable local authority must not return NOERROR answer.
            try:
                response = query('outage.authority.test.', 'A')
                assert response.rcode() == dns.rcode.SERVFAIL
            except dns.exception.Timeout:
                pass  # bounded fixture outage yields timeout; not a successful answer
            authority = Authority()
            assert query('recovered.authority.test.', 'A').answer
            proc.terminate()
            proc.wait(timeout=5)
            log.close()
            proc, log = start()
            assert query('a.fixture.test.', 'A').answer
            # Rate simulation is bounded to loopback, 40 packets; no third-party queries.
            proc.terminate()
            proc.wait(timeout=5)
            log.close()
            path.write_text(conf.replace('ip-ratelimit: 0', 'ip-ratelimit: 5'))
            proc, log = start()
            request = dns.message.make_query('a.fixture.test.', 'A').to_wire()
            dropped = 0
            for _ in range(40):
                try:
                    dns.query.udp(dns.message.from_wire(request), '127.0.0.1', port=15353, timeout=0.01)
                except dns.exception.Timeout:
                    dropped += 1
            assert dropped > 0, 'Per-client rate limit did not drop any excess packet'
            print('PASS: isolated UDP/TCP A/AAAA, DNSSEC valid/bogus, NXDOMAIN, ACL, truncation/TCP fallback, cache, rebinding, local authority outage/recovery, restart, bounded rate limit')
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            log.close()
            authority.close()

if __name__ == '__main__':
    main()
