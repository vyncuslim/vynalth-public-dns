import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('mobile', Path(__file__).resolve().parents[1] / 'scripts/mobile-acceptance.py')
mobile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mobile)


class MobileAcceptanceTests(unittest.TestCase):
    def test_full_mobile_plan_is_bounded_and_uses_android_source(self):
        query = Mock(return_value={'pass': True})
        result = mobile.accept(query=query, clock=lambda: 0)
        self.assertTrue(result['pass'])
        self.assertEqual(query.call_count, 10)
        self.assertTrue(all(call.kwargs['source'] == '100.75.232.110' for call in query.call_args_list))
        self.assertEqual(sum(case[5] for case in mobile.plan()), 32)
        self.assertEqual(result['system_wide_dns'], 'NOT TESTED')

    def test_failure_or_timeout_cannot_be_retried_or_passed(self):
        query = Mock(return_value={'pass': False, 'outcome': 'timeout'})
        result = mobile.accept(query=query, clock=lambda: 0)
        self.assertFalse(result['pass'])
        self.assertEqual(query.call_count, 1)

    def test_budget_exhaustion_sends_no_query(self):
        query = Mock()
        result = mobile.accept(deadline=1, query=query, clock=lambda: 0)
        self.assertFalse(result['pass'])
        query.assert_not_called()
        with self.assertRaises(ValueError):
            mobile.accept(deadline=46)

    def test_mobile_receipt_cannot_replace_windows_confirmation(self):
        spec = importlib.util.spec_from_file_location('confirm_mobile', Path(__file__).resolve().parents[1] / 'scripts/confirmation-check.py')
        check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check)
        from test_confirmation import receipt_fixture
        receipt = receipt_fixture()
        receipt['scope'] = 'android-post-windows-release-gate'
        with self.assertRaises(ValueError):
            check.validate(receipt, {'config_sha256': 'a'*64, 'started_monotonic': 0,
                           'global_deadline_monotonic': 140, 'boot_id': 'boot'}, 30, 'boot', 'a'*64, '984')
