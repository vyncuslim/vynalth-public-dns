from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('readiness', Path(__file__).resolve().parents[1] / 'scripts/post-maintenance-readiness.py')
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)
guard_spec = importlib.util.spec_from_file_location('timer_guard', Path(__file__).resolve().parents[1] / 'scripts/check-rollback-timer.py')
guard = importlib.util.module_from_spec(guard_spec)
guard_spec.loader.exec_module(guard)


class MaintenanceReadinessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, 7, tzinfo=timezone.utc).timestamp()
        self.services = {'apt-daily-upgrade.service': {'ActiveState': 'inactive', 'SubState': 'dead'}}
        self.timers = {'apt-daily.timer': {'NextElapseUSecRealtime': 'Sat 2026-10-10 12:39:38 UTC'}}

    def test_shutdown_helper_is_distinct_from_upgrade(self):
        self.assertFalse(readiness.is_upgrade_process(['/usr/bin/python3', '/usr/share/unattended-upgrades/unattended-upgrade-shutdown', '--wait-for-signal']))
        self.assertTrue(readiness.is_upgrade_process(['/usr/bin/python3', '/usr/bin/unattended-upgrade']))
        self.assertTrue(readiness.is_upgrade_process(['/usr/bin/perl', '/usr/sbin/needrestart']))

    def test_inactive_service_does_not_hide_package_process(self):
        failures = readiness.idle_failures(self.services, [{'pid': '42'}], {'lock': ''}, self.timers, self.now)
        self.assertIn('Package/needrestart process running', failures)

    def test_empty_process_list_does_not_hide_occupied_lock(self):
        failures = readiness.idle_failures(self.services, [], {'lock': '123'}, self.timers, self.now)
        self.assertIn('Package lock occupied', failures)

    def test_active_upgrade_service_blocks(self):
        self.services['apt-daily-upgrade.service'] = {'ActiveState': 'activating', 'SubState': 'start'}
        self.assertTrue(readiness.idle_failures(self.services, [], {}, self.timers, self.now))

    def test_unknown_or_near_timer_fails_closed(self):
        for text in ('', 'Sat 2026-10-10 07:10:00 UTC'):
            self.timers['apt-daily.timer']['NextElapseUSecRealtime'] = text
            self.assertTrue(readiness.idle_failures(self.services, [], {}, self.timers, self.now))

    def test_idle_scheduled_window_passes_operational_gate(self):
        self.assertEqual(readiness.idle_failures(self.services, [], {'lock': ''}, self.timers, self.now), [])

    def test_busctl_scalar_property_and_wrapped_method_results(self):
        fixtures = [('180000000', 180000000), ('"active"', 'active'), ('["/unit/path"]', '/unit/path')]
        for data, expected in fixtures:
            with patch.object(guard.subprocess, 'run', return_value=SimpleNamespace(stdout='{"data":' + data + '}')):
                self.assertEqual(guard.call('get-property'), expected)
