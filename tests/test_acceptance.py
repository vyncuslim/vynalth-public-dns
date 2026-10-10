import unittest
from unittest.mock import patch
import dns.exception
import dns.flags
import dns.message
import dns.rcode
import dns.rrset
from acceptance import check_query, case_plan


class AcceptanceTests(unittest.TestCase):
    def response(self, cd=False, ad=True, rcode='NOERROR'):
        q = dns.message.make_query('example.com.', 'A')
        r = dns.message.make_response(q)
        if ad:
            r.flags |= dns.flags.AD
        if cd:
            r.flags |= dns.flags.CD
        r.set_rcode(dns.rcode.from_text(rcode))
        if rcode == 'NOERROR':
            r.answer.append(dns.rrset.from_text('example.com.', 300, 'IN', 'A', '203.0.113.1'))
        return r

    def test_tcp_timeout_keeps_exact_context_and_one_attempt(self):
        with patch('acceptance.dns.query.tcp', side_effect=dns.exception.Timeout) as send, patch('acceptance.time.monotonic', side_effect=[10, 15]):
            r = check_query('127.0.0.1', 'dnssec-failed.org.', tcp=True, expected='SERVFAIL', timeout=5)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(r['transport'], 'TCP')
        self.assertEqual(r['query']['name'], 'dnssec-failed.org.')
        self.assertEqual(r['elapsed_seconds'], 5)
        self.assertEqual(r['error']['type'], 'dns.exception.Timeout')
        self.assertIsNone(r['response'])
        self.assertFalse(r['pass'])

    def test_late_correct_response_stays_failed(self):
        with patch('acceptance.dns.query.udp', return_value=self.response()) as send, patch('acceptance.time.monotonic', side_effect=[1, 7]):
            r = check_query('127.0.0.1', 'example.com.', ad=True, timeout=20, latency_limit=5)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(r['response']['rcode'], 'NOERROR')
        self.assertEqual(r['outcome'], 'latency_exceeded')
        self.assertFalse(r['pass'])

    def test_valid_requires_ad(self):
        with patch('acceptance.dns.query.udp', return_value=self.response(ad=False)):
            self.assertEqual(check_query('127.0.0.1', 'example.com.', ad=True, timeout=5)['outcome'], 'missing_AD')

    def test_cd_diagnostic_cannot_count_as_validation(self):
        with patch('acceptance.dns.query.udp', return_value=self.response(cd=True, ad=False)):
            r = check_query('127.0.0.1', 'example.com.', cd=True, timeout=5)
        self.assertTrue(r['pass'])
        self.assertTrue(r['query']['CD'])
        self.assertFalse(r['response']['AD'])

    def test_bogus_cannot_return_success_or_ad(self):
        with patch('acceptance.dns.query.udp', return_value=self.response()):
            self.assertFalse(check_query('127.0.0.1', 'example.com.', expected='SERVFAIL', timeout=5)['pass'])
        with patch('acceptance.dns.query.udp', return_value=self.response(rcode='SERVFAIL')):
            self.assertEqual(check_query('127.0.0.1', 'example.com.', expected='SERVFAIL', timeout=5)['outcome'], 'unexpected_AD')

    def test_scenarios_preserve_tests_and_transport(self):
        self.assertEqual(len(case_plan('standard')), 7)
        self.assertEqual(len(case_plan('dnssec-cold')), 2)
        self.assertEqual(len(case_plan('dnssec-warm')), 4)
        self.assertEqual([c[2] for c in case_plan('dnssec-warm')], [False, True, False, True])

    def test_observation_must_cover_explicit_latency_budget(self):
        with self.assertRaises(ValueError):
            check_query('127.0.0.1', 'example.com.', timeout=2, latency_limit=15)
