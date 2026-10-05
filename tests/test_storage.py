import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_kpt.storage import project_paths


class StoragePathTests(unittest.TestCase):
    def test_default_reports_and_work_stay_outside_target_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            state = base / "state"
            project.mkdir()
            with patch.dict(
                os.environ,
                {"AGENT_KPT_HOME": str(state)},
                clear=False,
            ):
                paths = project_paths(project)
            self.assertTrue(Path(paths["state_dir"]).is_relative_to(state))
            self.assertTrue(Path(paths["work_dir"]).is_relative_to(state))
            self.assertTrue(Path(paths["report_dir"]).is_relative_to(state))
            self.assertFalse(Path(paths["report_dir"]).is_relative_to(project))
            self.assertTrue(Path(paths["work_dir"]).exists())
            self.assertTrue(Path(paths["report_dir"]).exists())

    def test_report_dir_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            state = base / "state"
            reports = base / "custom-reports"
            project.mkdir()
            with patch.dict(
                os.environ,
                {
                    "AGENT_KPT_HOME": str(state),
                    "AGENT_KPT_REPORT_DIR": str(reports),
                },
                clear=False,
            ):
                paths = project_paths(project)
            self.assertEqual(Path(paths["report_dir"]), reports.resolve())
            self.assertTrue(reports.exists())


if __name__ == "__main__":
    unittest.main()
