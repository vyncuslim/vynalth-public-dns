"""Future authorized OPPO DNS-only release gate, NEVER a second deployment.

Run on the actual phone AFTER protected Windows confirmation. No SSH, service,
timer, Tailscale-admin, OS-DNS or deployment operations; no retry/cache flush.
PASS is query-path evidence only, not proof of system-wide Android DNS usage.
"""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from acceptance import check_query

SERVER = '100.95.65.20'
SOURCE = '100.75.232.110'


def plan():
    cases = [('example.com.', kind, tcp, 'NOERROR', False, 2, None)
             for tcp in (False, True) for kind in ('A', 'AAAA')]
    cases += [('20.65.95.100.in-addr.arpa.', 'PTR', tcp, 'NOERROR', False, 2, 'dns.vynalthai.com.')
              for tcp in (False, True)]
    cases += [(name, 'A', tcp, code, ad, 5, None)
              for tcp in (False, True) for name, code, ad in
              [('cloudflare.com.', 'NOERROR', True), ('dnssec-failed.org.', 'SERVFAIL', False)]]
    return cases


def accept(deadline=45, query=check_query, clock=time.monotonic):
    if not 0 < deadline <= 45:
        raise ValueError('Mobile gate is bounded to45s; cannot extend Windows transaction')
    started = clock()
    result = {'pass': False, 'scope': 'android-post-windows-release-gate',
              'system_wide_dns': 'NOT TESTED', 'cache_state': 'unknown/may be warm; no cold/cache-hit assertion',
              'queries': [], 'error': None}
    try:
        for name, kind, tcp, expected, ad, timeout, ptr in plan():
            if deadline - (clock()-started) < timeout:
                raise TimeoutError('Mobile deadline insufficient; no next query/retry')
            kwargs = {'source': SOURCE, 'tcp': tcp, 'expected': expected, 'ad': ad,
                      'timeout': timeout, 'scenario': 'android-post-windows',
                      'cache_evidence': result['cache_state']}
            if ptr:
                kwargs['expected_ptr'] = ptr
            row = query(SERVER, name, kind, **kwargs)
            result['queries'].append(row)
            if not row['pass']:
                raise RuntimeError('Mobile DNS gate failed; no subsequent test or retry')
        if clock()-started >= deadline:
            raise TimeoutError('Mobile deadline exceeded')
        result['pass'] = True
    except Exception as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['elapsed_seconds'] = round(clock()-started, 6)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorized-post-confirmation-test', action='store_true', required=True)
    parser.add_argument('--deadline-seconds', type=float, default=45)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = accept(args.deadline_seconds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    raise SystemExit(0 if result['pass'] else 1)
