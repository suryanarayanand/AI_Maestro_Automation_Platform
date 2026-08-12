import unittest
from unittest.mock import patch

from Utils.bug_summary import generate_bug_summary


class CombinedBugSummaryTests(unittest.TestCase):
    @patch("Utils.bug_summary.synthesize_bug_report")
    def test_visual_and_ai_findings_create_bug_when_run_passes(self, synthesize):
        synthesize.return_value = {"executive_summary": "Review", "top_risks": []}
        results = [{
            "id": "LOC_TEST", "name": "Test", "module": "M", "status": "PASS",
            "duration": 1, "log_file": "LOC_TEST.log",
            "screenshots": ["screenshots/LOC_TEST/page.png"],
            "ai_details": [{"status": "FAIL", "severity": "HIGH", "reason": "Debug text", "issues": []}],
        }]
        visual = {
            "reference": {"model": "Pixel"}, "actual": {"model": "Samsung"},
            "results": [{"scenario": "LOC_TEST", "details": [{
                "status": "FAIL", "image": "page.png", "similarity": 80,
                "reference": "comparison/ref.png", "actual": "comparison/actual.png",
                "difference": "comparison/diff.png",
                "ai_analysis": {"summary": "Layout changed", "issues": []},
            }]}],
        }
        report = generate_bug_summary(results, {}, visual, "Suite", 1)
        self.assertEqual(report["summary"]["failed"], 1)
        self.assertEqual(report["summary"]["passed"], 0)
        self.assertEqual(report["bugs"][0]["execution_status"], "PASS")
        self.assertEqual(report["bugs"][0]["sources"], ["Screenshot AI", "Visual"])


if __name__ == "__main__":
    unittest.main()
