import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('private_acceptance', Path(__file__).resolve().parents[1] / 'scripts/private-acceptance.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PrivateAcceptanceTests(unittest.TestCase):
    def test_missing_acl_records_never_produce_complete_pass(self):
        states = [copy.deepcopy(self.state()) for _ in range(4)]
        states[2]['stats']['total.num.cachehits'] = '4'
        states[3]['local_refused'] = []
        with patch('builtins.print'):
            result = runner.accept(self.args(), Mock(side_effect=states), Mock(return_value={'pass': True}), lambda: 0)
        self.assertFalse(result['pass'])

    def test_cold_failure_after_ptr_never_runs_warm(self):
        query = Mock(side_effect=[{'pass': True}, {'pass': True}, {'pass': False, 'outcome': 'timeout'}])
        with patch('builtins.print'):
            result = runner.accept(self.args(), Mock(return_value=self.state()), query, lambda: 0)
        self.assertFalse(result['pass'])
        self.assertEqual(query.call_count, 3)
        self.assertEqual(query.call_args.kwargs['scenario'], 'dnssec-cold')

    def args(self, deadline=100):
        return SimpleNamespace(ssh_key='filename-only.key', config_sha256='a' * 64,
                               deadline_seconds=deadline)

    def state(self):
        return {'ssh_connection': '100.85.132.14 40000 100.95.65.20 22',
                'hostname': 'vynalthai-dns', 'unit': {'MainPID': '100', 'NRestarts': '0',
                  'ActiveState': 'active', 'MemoryMax': '402653184', 'TasksMax': '64', 'LimitNOFILE': '1024'},
                'apparmor': 'unbound (enforce)', 'config_sha256': 'a' * 64,
                'discard_timeout_ms': '15000', 'forwards': '', 'tailscale_ipv4': runner.SERVER,
                'tailscaled_active': 'active', 'rollback_timer_active': True,
                'rollback_snapshot_pending': True, 'nft_sha256': 'net', 'sshd_sha256': 'ssh',
                'listeners': '\n'.join(f'{proto} LISTEN 0 0 {ip}:53 *:* users:(("unbound",pid=100,fd=4))'
                    for proto in ('udp', 'tcp') for ip in ('127.0.0.1', runner.SERVER)),
                'stats': {'total.num.queries': '1', 'total.num.cachehits': '0'}}

    def test_first_failure_prevents_warm_query_and_confirmation(self):
        inspect = Mock(return_value=self.state())
        query = Mock(return_value={'pass': False, 'outcome': 'timeout'})
        with patch('builtins.print'):
            result = runner.accept(self.args(), inspect, query, lambda: 0)
        self.assertFalse(result['pass'])
        self.assertEqual(query.call_count, 1)
        self.assertEqual(inspect.call_count, 1)
        self.assertEqual(result['queries'][0]['outcome'], 'timeout')

    def test_missing_deadline_sends_no_dns_query(self):
        query = Mock()
        result = runner.accept(self.args(10), Mock(return_value=self.state()), query, lambda: 0)
        self.assertFalse(result['pass'])
        query.assert_not_called()

    def test_warm_cache_claim_requires_measured_hits(self):
        states = [copy.deepcopy(self.state()) for _ in range(3)]
        inspect = Mock(side_effect=states)
        query = Mock(return_value={'pass': True})
        with patch('builtins.print'):
            result = runner.accept(self.args(), inspect, query, lambda: 0)
        self.assertFalse(result['pass'])
        self.assertEqual(query.call_count, 8)
        self.assertEqual(result['warm_cache_hit_delta'], 0)

    def test_complete_receipt_needs_cache_and_acl_evidence(self):
        states = [copy.deepcopy(self.state()) for _ in range(4)]
        states[2]['stats']['total.num.cachehits'] = '4'
        states[3]['local_refused'] = [{'pass': True}, {'pass': True}]
        inspect = Mock(side_effect=states)
        query = Mock(return_value={'pass': True})
        with patch('builtins.print'):
            result = runner.accept(self.args(), inspect, query, lambda: 0)
        self.assertTrue(result['pass'])
        self.assertEqual(query.call_count, 17)
        self.assertEqual(result['warm_cache_hit_delta'], 4)
        inspect.assert_called_with('filename-only.key', True)

    def test_public_listener_or_wrong_ssh_source_fails_before_dns(self):
        for field, value in [('ssh_connection', '100.0.0.1 40000 100.95.65.20 22'),
                             ('listeners', 'udp LISTEN 0 0 0.0.0.0:53 *:* users:(("unbound"))')]:
            state = self.state()
            state[field] = value
            query = Mock()
            result = runner.accept(self.args(), Mock(return_value=state), query, lambda: 0)
            self.assertFalse(result['pass'])
            query.assert_not_called()
