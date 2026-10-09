import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from monitor import alerts

class MonitorTests(unittest.TestCase):
    def test_failures_and_reset(self):
        current = {'healthy': False, 'memory': {'MemTotal_kb': 100, 'MemAvailable_kb': 5},
                   'restarts': '2', 'dns': {'total.num.queries': 100, 'num.answer.rcode.SERVFAIL': 20}}
        previous = {'restarts': '1', 'dns': {'total.num.queries': 50, 'num.answer.rcode.SERVFAIL': 0}}
        self.assertEqual(set(alerts(current, previous)), {'DNS_CONTROL_UNAVAILABLE', 'LOW_MEMORY', 'SERVICE_RESTART', 'HIGH_SERVFAIL_RATIO'})
        current['dns'] = {'total.num.queries': 0}
        self.assertNotIn('HIGH_SERVFAIL_RATIO', alerts(current, previous))
