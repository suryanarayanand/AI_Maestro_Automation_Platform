import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Utils.baseline_reports import generate_baseline_reports


class BaselineReportTests(unittest.TestCase):
    def test_generates_only_execution_and_screenshot_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            image = folder / "screenshots" / "CASE_1" / "home.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"png")
            results = [{
                "id": "CASE_1", "name": "Home", "status": "PASS",
                "duration": 1.2, "screenshots": ["screenshots/CASE_1/home.png"],
            }]
            generate_baseline_reports(results, "Baseline", 1.2, folder, folder / "baselines")
            self.assertTrue((folder / "Execution_Report.html").is_file())
            self.assertTrue((folder / "Screenshot_Report.html").is_file())
            data = json.loads((folder / "Screenshot_Report.json").read_text())
            self.assertEqual(data["captured"], 1)
            self.assertTrue((folder / "baselines" / "CASE_1" / "home.png").is_file())

    def test_failed_case_screenshot_is_not_promoted_to_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            image = folder / "screenshots" / "CASE_BAD" / "failure.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"png")
            results = [{
                "id": "CASE_BAD", "name": "Failed", "status": "FAIL",
                "duration": 1.0,
                "screenshots": ["screenshots/CASE_BAD/failure.png"],
            }]
            generate_baseline_reports(results, "Baseline", 1.0, folder, folder / "baselines")
            data = json.loads((folder / "Screenshot_Report.json").read_text())
            self.assertEqual(data["not_saved_failed"], 1)
            self.assertEqual(data["tests"][0]["status"], "NOT_SAVED_FAILED")
            self.assertFalse((folder / "baselines" / "CASE_BAD" / "failure.png").exists())


if __name__ == "__main__":
    unittest.main()
