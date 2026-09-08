"""CLI boundary checks without requiring Blender or a redistributable font."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import generate

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'scripts/nameplate.py'


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.font = self.root / 'assets/fonts/test.ttf'
        self.font.parent.mkdir(parents=True)
        self.font.write_bytes(b'fixture: no Blender conversion is performed')
        self.config = self.root / '.nameplate-local.json'
        self.config.write_text(json.dumps({'font': 'assets/fonts/test.ttf'}))
        for name, value in [('ROOT', self.root), ('LOCAL_CONFIG', self.config)]:
            patcher = patch.object(generate, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_two_rows_forwarded_as_literal_arguments(self):
        # Argument-like strings and shell syntax must remain text values.
        top = '--font=somewhere'
        bottom = "NAME'S $(touch unwanted); `command`"
        with patch.object(generate, 'run', return_value=0) as run:
            self.assertEqual(generate.main(['--', top, bottom]), 0)
        command = run.call_args.args[0]
        self.assertIn('--top=' + top, command)
        self.assertIn('--bottom=' + bottom, command)
        self.assertEqual(command[command.index('--font') + 1], str(self.font))

    def test_missing_font_explains_setup_before_launch(self):
        self.font.unlink()
        with patch.object(generate, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'setup-font'):
                generate.main(['PUT YOUR', 'NAME HERE'])
        run.assert_not_called()

    def test_output_names_do_not_collide(self):
        with patch.object(generate, 'datetime') as clock:
            clock.now.return_value.strftime.return_value = 'same-second'
            first = generate.next_output_directory()
            first.mkdir(parents=True)
            second = generate.next_output_directory()
        self.assertNotEqual(first, second)
        self.assertFalse(second.exists())

    def test_failed_preprocess_keeps_previous_default(self):
        other = self.root / 'another.ttf'
        other.write_bytes(b'new font fixture')
        before = self.config.read_bytes()
        with patch.object(generate, 'run', return_value=7):
            self.assertEqual(generate.setup_font([str(other)]), 7)
        self.assertEqual(self.config.read_bytes(), before)

    def test_successful_setup_records_portable_default(self):
        other = self.root / 'another.ttf'
        other.write_bytes(b'new font fixture')
        with patch.object(generate, 'run', return_value=0), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(generate.setup_font([str(other), '--chars=--AB']), 0)
        self.assertEqual(json.loads(self.config.read_text())['font'], 'assets/fonts/another.ttf')
        self.assertEqual(generate.resolve_default_font().read_bytes(), other.read_bytes())

    def test_setup_does_not_overwrite_different_same_named_font(self):
        other = self.root / 'test.ttf'
        other.write_bytes(b'different fixture')
        before = self.font.read_bytes()
        with patch.object(generate, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'different font already exists'):
                generate.setup_font([str(other)])
        self.assertEqual(self.font.read_bytes(), before)
        run.assert_not_called()


class LauncherValidationTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, str(LAUNCHER), 'build', *args],
                              capture_output=True, text=True, check=False)

    def test_nonempty_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / 'existing.stl'
            sentinel.write_bytes(b'keep this result')
            result = self.invoke('--top=A', '--bottom=B', '--output', folder)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not empty', result.stderr)
            self.assertEqual(sentinel.read_bytes(), b'keep this result')

    def test_invalid_jobs_stop_before_blender(self):
        cases = [
            ('--top=', '--bottom=B'),
            ('--top=A\nB', '--bottom=C'),
            ('--top=A', '--bottom=B', '--angle=90'),
            ('--top=A', '--bottom=B', '--length=nan'),
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.invoke(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Running Blender', result.stdout)
                self.assertNotIn('Traceback', result.stderr)

    def test_json_object_required(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / 'job.json'
            job.write_text('[]')
            result = self.invoke('--config', str(job))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must be a JSON object', result.stderr)


if __name__ == '__main__':
    unittest.main()
