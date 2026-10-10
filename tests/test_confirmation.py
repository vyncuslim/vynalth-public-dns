import copy
import importlib.util
from pathlib import Path
import unittest
from acceptance import case_plan

spec = importlib.util.spec_from_file_location('confirmation', Path(__file__).resolve().parents[1] / 'scripts/confirmation-check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def receipt_fixture():
    cases = [('20.65.95.100.in-addr.arpa.', 'PTR', tcp, 'NOERROR', False, False,
              'private-server-identity', 2) for tcp in (False, True)]
    for scenario, limit in [('dnssec-cold', 15), ('dnssec-warm', 2), ('standard', 5), ('diagnostic-cd', 5)]:
        cases += [(*case, scenario, limit) for case in case_plan(scenario)]
    rows = [{'pass': True, 'attempts': 1, 'error': None, 'query': {'name': name, 'type': kind},
             'transport': 'TCP' if tcp else 'UDP', 'scenario': scenario, 'server': '100.95.65.20',
             'source': '100.85.132.14', 'port': 53, 'elapsed_seconds': .1,
             'latency_limit_seconds': limit, 'response': {'rcode': code, 'AD': ad, 'CD': cd,
                 'TC': False, 'ptr_targets': ['dns.vynalthai.com.'] if kind == 'PTR' else []}}
            for name, kind, tcp, code, ad, cd, scenario, limit in cases]
    state = {'unit': {'MainPID': '984', 'NRestarts': '0'}, 'config_sha256': 'a'*64,
             'nft_sha256': 'network', 'sshd_sha256': 'ssh'}
    after = copy.deepcopy(state)
    after['local_refused'] = [{'pass': True, 'response': {'rcode': 'REFUSED'}, 'attempts': 1,
                              'transport': transport} for transport in ('UDP', 'TCP')]
    return {'pass': True, 'error': None, 'scope': 'windows-protected-transaction', 'expected_config_sha256': 'a'*64,
            'elapsed_seconds': 30, 'warm_cache_hit_delta': 4, 'queries': rows,
            'before': state, 'after': after}


class ConfirmationTests(unittest.TestCase):
    def check(self, receipt, now=139.9, boot='boot', pid='984'):
        checker.validate(receipt, {'config_sha256': 'a'*64, 'started_monotonic': 0, 'global_deadline_monotonic': 140, 'boot_id': 'boot'},
                         now, boot, 'a'*64, pid)

    def test_complete_receipt_before_140_passes(self):
        self.check(receipt_fixture())

    def test_at_140_or_changed_boot_pid_blocks(self):
        for kwargs in ({'now': 140}, {'now': 180}, {'boot': 'other'}, {'pid': '985'}):
            with self.assertRaises(ValueError):
                self.check(receipt_fixture(), **kwargs)

    def test_global_budget_cannot_restart_after_remote_preflight(self):
        with self.assertRaises(ValueError):
            checker.validate(receipt_fixture(), {'config_sha256': 'a'*64, 'started_monotonic': 90,
                             'global_deadline_monotonic': 140, 'boot_id': 'boot'}, 141, 'boot', 'a'*64, '984')

    def test_missing_global_deadline_fails_closed(self):
        with self.assertRaises(KeyError):
            checker.validate(receipt_fixture(), {'config_sha256': 'a'*64, 'started_monotonic': 90,
                             'boot_id': 'boot'}, 100, 'boot', 'a'*64, '984')

    def test_missing_failed_timed_out_or_wrong_ptr_blocks(self):
        mutations = [lambda r: r['queries'].pop(),
                     lambda r: r['queries'][0].update({'expected_nodata': True}),
                     lambda r: r['queries'][0].update({'pass': False, 'response': None}),
                     lambda r: r['queries'][0]['response'].update({'ptr_targets': ['wrong.test.']}),
                     lambda r: r['after']['local_refused'].pop(),
                     lambda r: r.update({'warm_cache_hit_delta': 0}),
                     lambda r: r.update({'expected_config_sha256': 'b'*64}),
                     lambda r: r['after'].update({'nft_sha256': 'changed'})]
        for mutate in mutations:
            r = receipt_fixture()
            mutate(r)
            with self.assertRaises((ValueError, KeyError, TypeError)):
                self.check(r)
