"""Low-volume approved-client acceptance. Explicit target; no load tests."""
import argparse
import ipaddress
import json
import sys
import dns.flags
import dns.message
import dns.query
import dns.rcode

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--server', required=True)
    p.add_argument('--port', type=int, default=53)
    p.add_argument('--authorized-target', action='store_true', required=True)
    p.add_argument('--expect-refused', action='store_true')
    a = p.parse_args()
    ipaddress.ip_address(a.server)
    results = []
    def check(name, kind, tcp=False, expected='NOERROR', ad=False):
        query = dns.message.make_query(name, kind, want_dnssec=True)
        try:
            response = (dns.query.tcp if tcp else dns.query.udp)(query, a.server, port=a.port, timeout=5)
            ok = dns.rcode.to_text(response.rcode()) == expected and (not ad or bool(response.flags & dns.flags.AD))
            if expected == 'NOERROR' and kind in ('A', 'AAAA'):
                ok = ok and bool(response.answer)
            results.append({'case': name + '/' + kind + ('/TCP' if tcp else '/UDP'), 'pass': ok,
                            'rcode': dns.rcode.to_text(response.rcode())})
        except Exception as exc:
            results.append({'case': name + '/' + kind, 'pass': False, 'error': type(exc).__name__})
    if a.expect_refused:
        check('example.com', 'A', expected='REFUSED')
        check('example.com', 'A', tcp=True, expected='REFUSED')
    else:
        check('example.com', 'A')
        check('example.com', 'AAAA')
        check('example.com', 'A', tcp=True)
        check('cloudflare.com', 'A', ad=True)
        check('dnssec-failed.org', 'A', expected='SERVFAIL')
        check('vynalth-acceptance.invalid', 'A', expected='NXDOMAIN')
        check('.', 'DNSKEY', tcp=True, ad=True)
    print(json.dumps(results, indent=2))
    sys.exit(0 if all(x['pass'] for x in results) else 1)

if __name__ == '__main__':
    main()
