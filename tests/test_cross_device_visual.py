import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from Utils.image_compare import prepare_images
from Utils.visual_report import analyze_visual_execution, analyze_visual_scenario


class CrossDeviceVisualTests(unittest.TestCase):
    def test_prepare_images_normalizes_actual_to_reference_size(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            reference = np.zeros((100, 50, 3), dtype=np.uint8)
            actual = np.zeros((200, 120, 3), dtype=np.uint8)
            cv2.imwrite(str(root / "reference.png"), reference)
            cv2.imwrite(str(root / "actual.png"), actual)

            prepared_reference, prepared_actual = prepare_images(
                root / "reference.png", root / "actual.png"
            )

            self.assertEqual(prepared_reference.shape, (100, 50, 3))
            self.assertEqual(prepared_actual.shape, (100, 50, 3))

    @patch("Utils.visual_report.analyze_visual_difference")
    def test_report_records_original_sizes_and_normalization(self, ai):
        ai.return_value = {"overall_status": "PASS", "issue_count": 0, "issues": []}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = root / "baseline"
            actual = root / "actual"
            baseline.mkdir()
            actual.mkdir()
            cv2.imwrite(str(baseline / "page.png"), np.zeros((100, 50, 3), dtype=np.uint8))
            cv2.imwrite(str(actual / "page.png"), np.zeros((200, 120, 3), dtype=np.uint8))

            result = analyze_visual_scenario(baseline, actual, root / "report", "LOC_TEST")

            detail = result["details"][0]
            self.assertEqual(detail["reference_size"], "50x100")
            self.assertEqual(detail["actual_size"], "120x200")
            self.assertTrue(detail["normalized"])

    def test_suite_summary_counts_image_results(self):
        summary = analyze_visual_execution(
            [{"scenario": "A", "total": 2, "passed": 1, "failed": 1}],
            {"model": "Pixel"}, {"model": "Samsung"},
        )
        self.assertEqual(summary["suite"], {"total": 2, "passed": 1, "failed": 1, "pass_rate": 50.0})
        self.assertEqual(summary["reference"]["model"], "Pixel")
        self.assertEqual(summary["actual"]["model"], "Samsung")


if __name__ == "__main__":
    unittest.main()
