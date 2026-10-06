import io
import runpy
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "agent-kpt.py"


class LauncherRuntimeTests(unittest.TestCase):
    def test_launcher_rejects_python_older_than_310_before_app_import(self):
        original = sys.version_info
        original_argv = sys.argv[:]
        stderr = io.StringIO()
        try:
            sys.version_info = (3, 9, 11)
            sys.argv = [str(LAUNCHER), "--help"]
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
                runpy.run_path(str(LAUNCHER), run_name="__main__")
            self.assertEqual(ctx.exception.code, 2)
        finally:
            sys.version_info = original
            sys.argv = original_argv

        message = stderr.getvalue()
        self.assertIn("requires Python 3.10+", message)
        self.assertIn("Python 3.9.11", message)
        self.assertIn("py -3.11", message)


if __name__ == "__main__":
    unittest.main()
