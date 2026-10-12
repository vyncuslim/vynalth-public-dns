import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render import render

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config.example.json').read_text())

    def test_default_closed(self):
        conf, nft = render(self.config)
        self.assertIn('access-control: 0.0.0.0/0 refuse', conf)
        self.assertNotIn('dport 53', nft)
        self.assertIn('policy drop', nft)

    def test_host_acl(self):
        self.config['clients'] = ['192.0.2.44/32']
        conf, nft = render(self.config)
        self.assertIn('access-control: 192.0.2.44/32 allow', conf)
        self.assertIn('udp dport 53 limit rate 20/second', nft)
        self.assertIn('tcp dport 53 limit rate 20/second', nft)

    def test_no_network_wide_recursion(self):
        for subnet in ['0.0.0.0/0', '::/0', '10.0.0.0/8', '192.0.2.1/24', '224.0.0.1/32']:
            with self.subTest(subnet=subnet):
                self.config['clients'] = [subnet]
                with self.assertRaises(ValueError):
                    render(self.config)

    def test_no_injection(self):
        self.config['listen'] = '127.0.0.1\nforward-zone:'
        with self.assertRaises(ValueError):
            render(self.config)

    def test_ipv6_opt_in(self):
        self.config['clients'] = ['2001:db8::1/128']
        with self.assertRaises(ValueError):
            render(self.config)
        self.config['ipv6'] = True
        self.assertIn('ip6 saddr', render(self.config)[1])

    def test_rate_bounds(self):
        for value in [0, -1, 101, True, '20']:
            cfg = copy.deepcopy(self.config)
            cfg['ip_ratelimit'] = value
            with self.assertRaises(ValueError):
                render(cfg)

    def test_independent_dns(self):
        conf, _ = render(self.config)
        self.assertNotIn('forward-zone:', conf)
        self.assertIn('validator iterator', conf)
        self.assertIn('log-queries: no', conf)
        self.assertIn('max-udp-size: 1232', conf)

if __name__ == '__main__':
    unittest.main()
