import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from render import render

class TailscalePolicyTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / 'config.private.example.json').read_text())

    def test_private_identity_and_transport(self):
        conf, nft = render(self.cfg)
        self.assertIn('interface: 127.0.0.1', conf)
        self.assertIn('interface: 100.95.65.20', conf)
        self.assertIn('access-control: 100.85.132.14/32 allow', conf)
        self.assertIn('access-control: 100.75.232.110/32 allow', conf)
        self.assertNotIn('100.75.232.110', '\n'.join(line for line in nft.splitlines() if 'dport 22' in line))
        self.assertNotIn('access-control: 100.64.0.0/10 allow', conf)
        self.assertIn('iifname "tailscale0" ip saddr 100.85.132.14/32 ip daddr 100.95.65.20 udp dport 53', nft)
        self.assertIn('iifname != "tailscale0" udp dport 41641 accept', nft)
        self.assertIn('udp sport 67 udp dport 68 accept', nft)
        self.assertNotIn('iifname "tailscale0" accept', nft)
        self.assertIn('iifname != "tailscale0" tcp dport 22', nft)

    def test_public_listener_or_client_rejected(self):
        for key, value in [('listen', '134.185.94.152'), ('clients', ['192.0.2.1/32'])]:
            cfg = copy.deepcopy(self.cfg)
            cfg[key] = value
            with self.assertRaises(ValueError):
                render(cfg)

    def test_missing_extra_or_duplicate_private_device_is_rejected(self):
        for clients in (['100.85.132.14/32'], ['100.75.232.110/32'],
                        self.cfg['clients']+['100.75.232.111/32'], self.cfg['clients']+['100.75.232.110/32']):
            cfg = copy.deepcopy(self.cfg)
            cfg['clients'] = clients
            with self.assertRaises(ValueError):
                render(cfg)

    def test_unsafe_interface_port_rejected(self):
        for key, value in [('interface', 'tailscale0" accept'), ('udp_port', 53)]:
            cfg = copy.deepcopy(self.cfg)
            cfg['tailscale'][key] = value
            with self.assertRaises(ValueError):
                render(cfg)
