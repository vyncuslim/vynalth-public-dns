import copy
import json
from pathlib import Path
import unittest
import sys
from unittest.mock import patch
import dns.message
import dns.rrset
from acceptance import check_query
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render import render


class IdentityTests(unittest.TestCase):
    def test_exact_rendered_bytes_and_narrow_owner(self):
        cfg = json.loads((ROOT / 'config.private.example.json').read_text())
        conf, _ = render(cfg)
        self.assertEqual(conf.encode(), (ROOT / 'plans/phase-b-unbound.conf').read_bytes())
        self.assertEqual([line for line in conf.splitlines() if 'local-zone:' in line],
                         ['    local-zone: "20.65.95.100.in-addr.arpa." static'])
        self.assertIn('3600 IN PTR dns.vynalthai.com.', conf)
        self.assertNotIn('IN A 100.95.65.20', conf)
        self.assertNotIn('interface: 0.0.0.0', conf)
        self.assertNotIn('forward-zone:', conf)
        self.assertIn('val-permissive-mode: no', conf)
        self.assertIn('discard-timeout: 15000', conf)

    def test_identity_mismatch_injection_or_public_listener_is_rejected(self):
        base = json.loads((ROOT / 'config.private.example.json').read_text())
        for field, value in [('address', '100.95.65.21'), ('hostname', 'evil.test.\nforward-zone:')]:
            cfg = copy.deepcopy(base)
            cfg['dns_identity'][field] = value
            with self.assertRaises(ValueError):
                render(cfg)
        base['listen'] = '134.185.94.152'
        with self.assertRaises(ValueError):
            render(base)

    def test_wrong_or_missing_ptr_cannot_pass(self):
        for target in (None, 'wrong.test.', 'dns.vynalthai.com.'):
            q = dns.message.make_query('20.65.95.100.in-addr.arpa.', 'PTR')
            response = dns.message.make_response(q)
            if target:
                response.answer.append(dns.rrset.from_text(q.question[0].name, 3600, 'IN', 'PTR', target))
            with patch('acceptance.dns.query.udp', return_value=response):
                row = check_query('127.0.0.1', q.question[0].name, 'PTR', timeout=2,
                                  expected_ptr='dns.vynalthai.com.')
            self.assertEqual(row['pass'], target == 'dns.vynalthai.com.')
