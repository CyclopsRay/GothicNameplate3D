"""Opt-in actual Blender regression: supply NAMEPLATE_TEST_FONT locally."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('NAMEPLATE_TEST_FONT'),
                     'Set NAMEPLATE_TEST_FONT to run the real Blender build.')
class BlenderIntegrationTests(unittest.TestCase):
    def test_two_rows_keep_template_height_and_export_closed_stl(self):
        with tempfile.TemporaryDirectory(prefix='nameplate-integration-') as folder:
            output = Path(folder) / 'model'
            result = subprocess.run([
                sys.executable, str(ROOT / 'generate.py'), 'PUT YOUR', 'NAME HERE',
                '--font', os.environ['NAMEPLATE_TEST_FONT'],
                '--output', str(output), '--no-render',
            ], capture_output=True, text=True, timeout=600)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'PASS')
            self.assertEqual(report['rows'], ['PUT YOUR', 'NAME HERE'])
            rows = {row['text']: row for row in report['layout']}
            for text, height in [('PUT YOUR', 26), ('NAME HERE', 27)]:
                self.assertEqual(rows[text]['fit'], 'stretch')
                self.assertAlmostEqual(rows[text]['height_mm_at_150'], height)
            self.assertEqual(report['stl']['status'], 'PASS')
            self.assertEqual(report['stl']['connected_components'], 1)
            self.assertEqual(report['stl']['nonmanifold_edges'], 0)
            self.assertEqual(report['stl']['zero_area_triangles'], 0)
            self.assertEqual(report['glb']['status'], 'PASS')
            for filename in ['nameplate.stl', 'nameplate.blend', 'nameplate.glb']:
                self.assertGreater((output / filename).stat().st_size, 100)


if __name__ == '__main__':
    unittest.main()
