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

    def test_existing_capture_is_preserved_before_any_host_read(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'capture.json'; out.write_bytes(b'original evidence\n')
            argv=['readiness','--capture','--interval','60','--ssh-connection','test','--out',str(out)]
            with patch('sys.argv',argv),patch.object(capture,'sample') as sample:
                with self.assertRaises(SystemExit) as status: capture.main()
                self.assertEqual(status.exception.code,2)
                sample.assert_not_called()
            self.assertEqual(out.read_bytes(),b'original evidence\n')

    def test_capture_does_not_create_unapproved_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=Path(directory)/'not-approved'; out=parent/'capture.json'
            argv=['readiness','--capture','--ssh-connection','test','--out',str(out)]
            with patch('sys.argv',argv),patch.object(capture,'sample') as sample:
                with self.assertRaises(SystemExit) as status: capture.main()
                self.assertEqual(status.exception.code,2); sample.assert_not_called()
            self.assertFalse(parent.exists())

    def test_first_sample_failure_never_sleeps_or_reads_again(self):
        for reason in ('operational', 'ntp', 'reboot'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                out = Path(directory) / 'capture.json'
                first = {'fingerprint': {'unit': {'MainPID': '1'}},
                         'operational_failures': [], 'time_sync': 'yes',
                         'reboot_required': False}
                if reason == 'operational':
                    first['operational_failures'] = ['Maintenance service not idle']
                elif reason == 'ntp':
                    first['time_sync'] = 'no'
                else:
                    first['reboot_required'] = True
                argv = ['readiness', '--capture', '--interval', '60',
                        '--ssh-connection', 'test-fixture', '--out', str(out)]
                with patch('sys.argv', argv), patch.object(
                        capture, 'sample',
                        side_effect=[first, AssertionError('unapproved second sample')]) as sample, patch.object(
                        capture.time, 'sleep') as sleep:
                    with self.assertRaises(SystemExit) as status:
                        capture.main()
                self.assertEqual(status.exception.code, 1)
                sample.assert_called_once_with('test-fixture')
                sleep.assert_not_called()
                result = json.loads(out.read_text())
                self.assertEqual(len(result['samples']), 1)
                self.assertTrue(result['failures'])
                self.assertFalse(result['capture_complete'])
                self.assertFalse(result['deployment_ready'])

    def test_pinned_baseline_mismatch_stops_before_sleep(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'capture.json'
            baseline = Path(directory) / 'baseline.json'
            baseline.write_text(json.dumps({'fingerprint': {'unit': {'MainPID': 'old'}}}))
            first = {'fingerprint': {'unit': {'MainPID': 'new'}},
                     'operational_failures': [], 'time_sync': 'yes',
                     'reboot_required': False}
            argv = ['readiness', '--baseline', str(baseline), '--interval', '60',
                    '--ssh-connection', 'test-fixture', '--out', str(out)]
            with patch('sys.argv', argv), patch.object(
                    capture, 'sample',
                    side_effect=[first, AssertionError('unapproved second sample')]) as sample, patch.object(
                    capture.time, 'sleep') as sleep:
                with self.assertRaises(SystemExit) as status:
                    capture.main()
            self.assertEqual(status.exception.code, 1)
            sample.assert_called_once()
            sleep.assert_not_called()
            result = json.loads(out.read_text())
            self.assertEqual(len(result['samples']), 1)
            self.assertIn('Pinned baseline drift: new review required, never auto-refresh', result['failures'])
            self.assertFalse(result['deployment_ready'])

    def test_first_sample_exception_does_not_retry_or_sleep(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'capture.json'
            argv = ['readiness', '--capture', '--interval', '60',
                    '--ssh-connection', 'test-fixture', '--out', str(out)]
            with patch('sys.argv', argv), patch.object(
                    capture, 'sample', side_effect=RuntimeError('first sample failed')) as sample, patch.object(
                    capture.time, 'sleep') as sleep:
                with self.assertRaises(SystemExit) as status:
                    capture.main()
            self.assertEqual(status.exception.code, 1)
            sample.assert_called_once()
            sleep.assert_not_called()
            result = json.loads(out.read_text())
            self.assertEqual(len(result['samples']), 0)
            self.assertIn('RuntimeError: first sample failed', result['failures'])
            self.assertFalse(result['capture_complete'])
            self.assertFalse(result['deployment_ready'])

    def test_second_sample_failure_is_not_a_success(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'capture.json'
            first = {'fingerprint': {'unit': {'MainPID': '1'}},
                     'operational_failures': [], 'time_sync': 'yes',
                     'reboot_required': False}
            second = {**first, 'operational_failures': ['Package lock occupied']}
            argv = ['readiness', '--capture', '--interval', '60',
                    '--ssh-connection', 'test-fixture', '--out', str(out)]
            with patch('sys.argv', argv), patch.object(
                    capture, 'sample', side_effect=[first, second]) as sample, patch.object(
                    capture.time, 'sleep') as sleep:
                with self.assertRaises(SystemExit) as status:
                    capture.main()
            self.assertEqual(status.exception.code, 1)
            self.assertEqual(sample.call_count, 2)
            sleep.assert_called_once_with(60)
            result = json.loads(out.read_text())
            self.assertEqual(len(result['samples']), 2)
            self.assertFalse(result['capture_complete'])
            self.assertFalse(result['deployment_ready'])
