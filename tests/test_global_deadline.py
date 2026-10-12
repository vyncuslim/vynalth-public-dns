import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import json
import subprocess

spec = importlib.util.spec_from_file_location('transaction', Path(__file__).resolve().parents[1] / 'scripts/private-transaction.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class GlobalDeadlineTests(unittest.TestCase):
    def scenario(self, costs, fail_at=None):
        now = [0]
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            index = len(calls) - 1
            now[0] += costs[index] if index < len(costs) else 0
            if index == fail_at:
                raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
            if argv[:2] == ['git', 'rev-parse']:
                output = 'a'*40
            elif argv[:2] == ['git', 'ls-remote']:
                output = 'a'*40 + ' refs/heads/codex/phase-a-dns'
            elif 'clock-probe.py' in argv[-1]:
                output = json.dumps({'monotonic': 1000, 'boot_id': '06c41b28-e22e-4540-8bd7-61b91fcaf465'})
            else:
                output = ''
            return SimpleNamespace(stdout=output)
        with patch.object(runner.Path, 'read_text', return_value='{"pass":true}'):
            result = runner.execute(self.args(), run, lambda: now[0])
        return result, calls

    def test_complete_mock_trial_includes_all_command_and_network_time(self):
        result, calls = self.scenario([1, 1, 1, 3, 60, 10, 20, 2, 2, 10])
        self.assertTrue(result['pass'])
        self.assertEqual(result['elapsed_global_seconds'], 110)
        self.assertEqual(result['server_global_deadline_monotonic'], 1133)
        self.assertEqual(len(calls), 10)

    def test_long_verification_prevents_deployment(self):
        result, calls = self.scenario([1, 1, 1, 3, 120])
        self.assertFalse(result['pass'])
        self.assertFalse(result['deployment_command_started'])
        self.assertFalse(result['confirmation_command_started'])
        self.assertEqual(len(calls), 5)

    def test_acceptance_or_transfer_delay_prevents_confirmation_and_recovers_once(self):
        for costs in ([1, 1, 1, 3, 60, 10, 70], [1, 1, 1, 3, 60, 10, 20, 2, 25]):
            result, calls = self.scenario(costs)
            self.assertFalse(result['pass'])
            self.assertFalse(result['confirmation_command_started'])
            self.assertEqual(sum('rollback.sh --service-only' in call[0][-1] for call in calls), 1)

    def test_lost_confirmation_reply_is_unknown_never_retried(self):
        result, calls = self.scenario([1, 1, 1, 3, 60, 10, 20, 2, 2, 1], fail_at=9)
        self.assertFalse(result['pass'])
        self.assertIn('UNKNOWN', result['confirmation_outcome'])
        self.assertEqual(sum('scripts/confirm.sh' in call[0][-1] for call in calls), 1)

    def args(self):
        return SimpleNamespace(commit='a'*40, config_sha256='b'*64, baseline_sha256='c'*64, ssh_key='filename-only.key')

    def test_network_reply_delay_makes_server_deadline_earlier(self):
        self.assertEqual(runner.mapped_deadline(1000, 10, 0), 1129)
        # Real probe emission could have been at client5. Earliest safe bound
        # is still1129, not1134 or a new1140-second server-local window.
        self.assertLess(runner.mapped_deadline(1000, 10, 0), 1000+140)

    def test_no_budget_or_nan_probe_is_rejected(self):
        for mono, received in ((1000, 120), (float('nan'), 2), (float('inf'), 2)):
            with self.assertRaises(ValueError):
                runner.mapped_deadline(mono, received, 0)

    def test_command_latency_consumes_global_deadline_and_sends_no_deploy(self):
        times = iter((0, 1, 140, 140, 140))
        run = Mock(return_value=SimpleNamespace(stdout='a'*40))
        result = runner.execute(self.args(), run, lambda: next(times))
        self.assertFalse(result['pass'])
        self.assertFalse(result['deployment_command_started'])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs['timeout'], 5)

    def test_timeout_during_verification_never_starts_confirmation(self):
        run = Mock(side_effect=subprocess.TimeoutExpired('git', 5))
        result = runner.execute(self.args(), run, lambda: 0)
        self.assertFalse(result['pass'])
        self.assertFalse(result['confirmation_command_started'])
        self.assertEqual(run.call_count, 1)
