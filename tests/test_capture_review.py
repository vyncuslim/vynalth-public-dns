import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('capture',Path(__file__).resolve().parents[1]/'scripts/post-maintenance-readiness.py')
capture=importlib.util.module_from_spec(spec); spec.loader.exec_module(capture)


class CaptureTests(unittest.TestCase):
    def run_capture(self,drift=False):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'capture.json'
            rows=[{'fingerprint':{'unit':{'MainPID':'1'}},'operational_failures':[],'time_sync':'yes','reboot_required':False},
                  {'fingerprint':{'unit':{'MainPID':'2' if drift else '1'}},'operational_failures':[],'time_sync':'yes','reboot_required':False}]
            argv=['readiness','--capture','--interval','60','--ssh-connection','test-fixture','--out',str(out)]
            with patch('sys.argv',argv),patch.object(capture,'sample',side_effect=rows),patch.object(capture.time,'sleep') as sleep:
                with self.assertRaises(SystemExit) as status: capture.main()
                sleep.assert_called_once_with(60)
            return status.exception.code,json.loads(out.read_text())

    def test_successful_review_capture_never_authorizes_deployment(self):
        code,result=self.run_capture()
        self.assertEqual(code,0)
        self.assertTrue(result['capture_complete'])
        self.assertFalse(result['deployment_ready'])

    def test_drift_blocks_capture(self):
        code,result=self.run_capture(True)
        self.assertEqual(code,1)
        self.assertFalse(result['capture_complete'])
        self.assertFalse(result['deployment_ready'])
