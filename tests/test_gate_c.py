import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('gate_c',Path(__file__).resolve().parents[1]/'scripts/gate-c-preflight.py')
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


class GateCTests(unittest.TestCase):
    def row(self):
        return {'hostname':'independent-lab','architecture':'aarch64','ubuntu24':True,
                'systemd':True,'apparmor_enabled':True,'unbound_available':True}

    def test_capability_contract_only_not_authorization(self):
        result=gate.evaluate(self.row())
        self.assertTrue(result['pass'])
        self.assertIn('never approves Oracle',result['authorization'])

    def test_missing_arch_enforcement_or_package_fails_closed(self):
        for key,value in [('architecture','x86_64'),('apparmor_enabled',False),('unbound_available',False),
                          ('ubuntu24',False),('systemd',False),('hostname','vynalthai-dns')]:
            row=self.row(); row[key]=value
            self.assertFalse(gate.evaluate(row)['pass'])
