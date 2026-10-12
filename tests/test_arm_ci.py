import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('arm_service',ROOT/'tests/arm_service_recovery.py')
service=importlib.util.module_from_spec(spec); spec.loader.exec_module(service)


class ArmCITests(unittest.TestCase):
    def test_public_standard_runner_fail_closed_pipeline(self):
        jobs=yaml.safe_load((ROOT/'.github/workflows/validate.yml').read_text())['jobs']
        arm=jobs['gate-c-arm64']
        self.assertEqual(arm['runs-on'],'ubuntu-24.04-arm')
        self.assertEqual(arm['if'],'github.event.repository.private == false')
        self.assertEqual(arm['permissions'],{'contents':'read'})
        self.assertEqual(arm['defaults']['run']['shell'],'bash')
        self.assertLessEqual(arm['timeout-minutes'],20)
        self.assertFalse(any(s.get('continue-on-error') for s in arm['steps']))
        self.assertIn('validate',jobs)
        original='\n'.join(s.get('run','') for s in jobs['validate']['steps'])
        for expected in ('tests/private_transaction_lab.py','tests/local_runtime.py','tests/tailscale_firewall_lab.sh','terraform validate'):
            self.assertIn(expected,original)

    def test_enforcement_timer_and_evidence_steps_are_mandatory(self):
        steps=yaml.safe_load((ROOT/'.github/workflows/validate.yml').read_text())['jobs']['gate-c-arm64']['steps']
        commands='\n'.join(s.get('run','') for s in steps)
        for required in ('test "$(uname -m)" = aarch64','--require-apparmor','tests/arm_service_recovery.py','tests/gate_c_rollback_lab.py'):
            self.assertIn(required,commands)
        self.assertNotIn('aa-disable',commands)
        self.assertNotIn('tailscale up',commands)
        artifact=next(s for s in steps if s.get('uses','').startswith('actions/upload-artifact@'))
        self.assertEqual(artifact['if'],'always()')

    def test_service_fixture_preserves_security_and_two_clients(self):
        conf=service.fixture_config((ROOT/'plans/phase-b-unbound.conf').read_text(),Path('/var/lib/unbound/vynalth-arm-ci-test'))
        for line in ('access-control: 100.85.132.14/32 allow','access-control: 100.75.232.110/32 allow',
                     'access-control: 0.0.0.0/0 refuse','interface: 100.95.65.20','val-permissive-mode: no',
                     'module-config: "validator iterator"','PTR dns.vynalthai.com.'):
            self.assertIn(line,conf)
        self.assertNotIn('interface: 0.0.0.0',conf)
        self.assertNotIn('forward-zone:',conf)
        self.assertNotIn('auto-trust-anchor-file:',conf)  # offline fixture, not root-recursion proof
