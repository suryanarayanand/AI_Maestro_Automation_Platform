import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from maestro_agent import collect_changed_screenshots, screenshot_snapshot
from Utils.ai_report import analyze_scenario


class ScreenshotPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "Screenshots"
        self.report = self.root / "Reports" / "Job_1"
        (self.source / "SC_01" / "nested").mkdir(parents=True)
        self.unchanged = self.source / "SC_01" / "unchanged.png"
        self.changed = self.source / "SC_01" / "nested" / "checkpoint.png"
        self.unchanged.write_bytes(b"unchanged")
        self.changed.write_bytes(b"old")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_only_changed_screenshots_are_copied_to_case_report(self):
        before = screenshot_snapshot(self.source)
        self.changed.write_bytes(b"new-content")
        new_image = self.source / "SC_01" / "new.png"
        new_image.write_bytes(b"new")

        copied = collect_changed_screenshots(
            before, self.report, "CASE_01", self.source
        )

        relative = [path.relative_to(self.report).as_posix() for path in copied]
        self.assertEqual(relative, [
            "screenshots/CASE_01/nested/checkpoint.png",
            "screenshots/CASE_01/new.png",
        ])
        self.assertFalse(
            (self.report / "screenshots" / "CASE_01" / "unchanged.png").exists()
        )

    @patch("Utils.ai_report.analyze_image")
    def test_ai_analysis_accepts_images_already_in_report_folder(self, analyze_image):
        analyze_image.return_value = {
            "status": "PASS", "confidence": 100, "severity": "None",
            "reason": "Test", "issues": [],
        }
        case_folder = self.report / "screenshots" / "CASE_01" / "nested"
        case_folder.mkdir(parents=True)
        (case_folder / "checkpoint.png").write_bytes(b"image")

        result = analyze_scenario(
            self.report / "screenshots" / "CASE_01",
            self.report,
            "CASE_01",
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["passed"], 1)
        self.assertEqual(
            result["details"][0]["image_path"],
            "screenshots/CASE_01/nested/checkpoint.png",
        )


if __name__ == "__main__":
    unittest.main()
