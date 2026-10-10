"""One-shot, fail-closed acceptance with explicit cache and latency evidence."""
import argparse
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import sys
import time
import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype


def response_shape(reply, kind):
    """Describe wire semantics, never infer existence from a random-looking name."""
    matching = any(rr.rdtype == dns.rdatatype.from_text(kind) for rr in reply.answer)
    soa = any(rr.rdtype == dns.rdatatype.SOA for rr in reply.authority)
    if reply.rcode() == dns.rcode.NXDOMAIN:
        return 'NXDOMAIN'
    if reply.rcode() != dns.rcode.NOERROR:
        return dns.rcode.to_text(reply.rcode())
    if matching:
        return 'ANSWER'
    if soa:
        return 'NODATA'
    if any(rr.rdtype == dns.rdatatype.NS for rr in reply.authority) and not reply.answer:
        return 'REFERRAL'
    return 'NOERROR_WITHOUT_MATCHING_RRSET'


def check_query(server, name, kind='A', *, port=53, source=None, tcp=False,
                expected='NOERROR', ad=False, cd=False, timeout,
                latency_limit=None, scenario='standard', cache_evidence='unknown', expected_ptr=None,
                expected_nodata=False):
    """Exactly one transmission; observation can outlast the acceptance threshold.

    A late correct response is still FAIL. No fallback, retry, cache flush or
    production control operation occurs here.
    """
    limit = timeout if latency_limit is None else latency_limit
    if not 0 < limit <= timeout <= 30:
        raise ValueError('Require 0 < latency limit <= observation timeout <= 30s')
    if expected_nodata and (expected != 'NOERROR' or expected_ptr is not None):
        raise ValueError('Explicit NODATA requires NOERROR and no positive PTR expectation')
    query = dns.message.make_query(name, kind, use_edns=True, payload=1232, want_dnssec=True)
    if cd:
        query.flags |= dns.flags.CD
    row = {'query': {'name': query.question[0].name.to_text(), 'type': kind,
                     'class': 'IN', 'id': query.id, 'DO': True, 'CD': cd},
           'server': server, 'port': port, 'source': source,
           'transport': 'TCP' if tcp else 'UDP', 'scenario': scenario,
           'cache_evidence': cache_evidence, 'expected_rcode': expected,
           'require_AD': ad, 'observation_timeout_seconds': timeout,
           'expected_nodata': expected_nodata,
           'latency_limit_seconds': limit,
           'started_utc': datetime.now(timezone.utc).isoformat(),
           'elapsed_seconds': None, 'response': None, 'error': None,
           'pass': False, 'outcome': None, 'attempts': 1}
    start = time.monotonic()
    try:
        reply = (dns.query.tcp if tcp else dns.query.udp)(query, server, port=port,
                                                        source=source, timeout=timeout)
        elapsed = time.monotonic() - start
        row['response'] = {'rcode': dns.rcode.to_text(reply.rcode()),
                           'AD': bool(reply.flags & dns.flags.AD),
                           'CD': bool(reply.flags & dns.flags.CD),
                           'TC': bool(reply.flags & dns.flags.TC),
                           'AA': bool(reply.flags & dns.flags.AA),
                           'RA': bool(reply.flags & dns.flags.RA),
                           'shape': response_shape(reply, kind),
                           'answers': [rrset.to_text() for rrset in reply.answer],
                           'authority': [rrset.to_text() for rrset in reply.authority],
                           'SOA_negative_ttls': [min(rrset.ttl, item.minimum) for rrset in reply.authority
                                                if rrset.rdtype == dns.rdatatype.SOA for item in rrset],
                           'ptr_targets': [item.target.to_text() for rrset in reply.answer
                                           if rrset.rdtype == dns.rdatatype.PTR for item in rrset],
                           'EDE': [str(o) for o in reply.options if int(o.otype) == 15]}
        if elapsed > limit:
            outcome = 'latency_exceeded'
        elif row['response']['rcode'] != expected:
            outcome = 'unexpected_rcode'
        elif ad and not row['response']['AD']:
            outcome = 'missing_AD'
        elif (cd or expected == 'SERVFAIL') and row['response']['AD']:
            outcome = 'unexpected_AD'
        elif cd and not row['response']['CD']:
            outcome = 'missing_CD'
        elif row['response']['TC']:
            outcome = 'truncated'
        elif expected_ptr is not None and [(rrset.name.to_text(), rrset.rdtype, item.target.to_text())
                for rrset in reply.answer if rrset.rdtype == dns.rdatatype.PTR for item in rrset] != [(query.question[0].name.to_text(), dns.rdatatype.PTR, expected_ptr)]:
            outcome = 'unexpected_PTR'
        elif expected_nodata and row['response']['shape'] != 'NODATA':
            outcome = 'expected_NODATA'
        elif not expected_nodata and expected == 'NOERROR' and kind in ('A', 'AAAA', 'PTR') and not any(
                rrset.rdtype == dns.rdatatype.from_text(kind) for rrset in reply.answer):
            outcome = 'missing_answer'
        else:
            outcome = 'pass'
        row['outcome'] = outcome
        row['pass'] = outcome == 'pass'
    except Exception as exc:
        elapsed = time.monotonic() - start
        row['outcome'] = 'timeout' if isinstance(exc, (dns.exception.Timeout, TimeoutError)) else 'transport_error'
        row['error'] = {'type': type(exc).__module__ + '.' + type(exc).__name__, 'message': str(exc)}
    row['elapsed_seconds'] = round(elapsed, 6)
    return row


def case_plan(scenario):
    if scenario == 'dnssec-cold':
        # First query to each name. Shared root/TLD state may already be warm.
        return [('cloudflare.com.', 'A', False, 'NOERROR', True, False),
                ('dnssec-failed.org.', 'A', False, 'SERVFAIL', False, False)]
    if scenario == 'dnssec-warm':
        return [(name, 'A', tcp, rcode, ad, False)
                for name, rcode, ad in [('cloudflare.com.', 'NOERROR', True),
                                        ('dnssec-failed.org.', 'SERVFAIL', False)]
                for tcp in (False, True)]
    if scenario == 'diagnostic-cd':
        return [('dnssec-failed.org.', 'A', tcp, 'NOERROR', False, True) for tcp in (False, True)]
    if scenario == 'refused':
        return [('example.com.', 'A', tcp, 'REFUSED', False, False) for tcp in (False, True)]
    return [('example.com.', 'A', False, 'NOERROR', False, False),
            ('example.com.', 'AAAA', False, 'NOERROR', False, False),
            ('example.com.', 'A', True, 'NOERROR', False, False),
            ('cloudflare.com.', 'A', False, 'NOERROR', True, False),
            ('dnssec-failed.org.', 'A', False, 'SERVFAIL', False, False),
            # Built-in RFC6761 local denial is authoritative, not DNSSEC signed.
            ('vynalth-acceptance.invalid.', 'A', False, 'NXDOMAIN', False, False),
            ('.', 'DNSKEY', True, 'NOERROR', True, False)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--server', required=True)
    p.add_argument('--port', type=int, default=53)
    p.add_argument('--source')
    p.add_argument('--authorized-target', action='store_true', required=True)
    p.add_argument('--expect-refused', action='store_true', help='Alias for --scenario refused')
    p.add_argument('--scenario', choices=['standard', 'dnssec-cold', 'dnssec-warm', 'diagnostic-cd', 'refused'], default='standard')
    p.add_argument('--timeout', type=float, required=True, help='Explicit per-query observation limit, <=30 seconds')
    p.add_argument('--latency-limit', type=float, help='Defaults to timeout; late responses never pass')
    p.add_argument('--deadline-seconds', type=float, default=90)
    p.add_argument('--cache-evidence', default='unknown', help='Caller attestation; not a cache flush or measurement')
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    ipaddress.ip_address(a.server)
    if a.source:
        ipaddress.ip_address(a.source)
    limit = a.timeout if a.latency_limit is None else a.latency_limit
    if not 0 < limit <= a.timeout <= 30 or not 0 < a.deadline_seconds <= 140:
        p.error('Invalid observation, latency or overall deadline')
    if a.expect_refused:
        a.scenario = 'refused'
    if a.scenario.startswith('dnssec-') and a.cache_evidence == 'unknown':
        p.error('DNSSEC cache scenario needs explicit --cache-evidence; no cache state is inferred')
    rows = []
    start = time.monotonic()
    for name, kind, tcp, expected, ad, cd in case_plan(a.scenario):
        if a.deadline_seconds - (time.monotonic() - start) < a.timeout:
            rows.append({'pass': False, 'outcome': 'insufficient_deadline', 'query': {'name': name, 'type': kind},
                         'transport': 'TCP' if tcp else 'UDP', 'attempts': 0})
            print(json.dumps(rows[-1]), flush=True)
            break
        row = check_query(a.server, name, kind, port=a.port, source=a.source, tcp=tcp,
                          expected=expected, ad=ad, cd=cd, timeout=a.timeout,
                          latency_limit=limit, scenario=a.scenario, cache_evidence=a.cache_evidence)
        rows.append(row)
        print(json.dumps(row), flush=True)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(rows, indent=2), encoding='utf-8')
        if not row['pass']:
            break
    if a.out:
        a.out.write_text(json.dumps(rows, indent=2), encoding='utf-8')
    sys.exit(0 if rows and all(row['pass'] for row in rows) else 1)


if __name__ == '__main__':
    main()
