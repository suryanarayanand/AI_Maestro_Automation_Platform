import json
import tempfile
import unittest
from pathlib import Path

from Utils.unique_bug_summary import generate_unique_bug_summary


class UniqueBugSummaryTests(unittest.TestCase):
    def _write_report(self, root, name, bugs):
        folder = root / name
        folder.mkdir()
        (folder / "Bug_Summary.json").write_text(
            json.dumps({"bugs": bugs}), encoding="utf-8"
        )

    def test_groups_repeated_and_similarly_worded_bugs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_report(root, "Run_1", [{
                "scenario_id": "A", "scenario_name": "Game", "severity": "Major",
                "reason": "Evidence detected by Screenshot AI", "sources": ["Screenshot AI"],
                "ai_findings": [{"reason": "Sudoko is misspelled and coumns should be columns", "issues": []}],
            }])
            self._write_report(root, "Run_2", [{
                "scenario_id": "B", "scenario_name": "Game copy", "severity": "Critical",
                "reason": "Evidence detected by Screenshot AI", "sources": ["Screenshot AI"],
                "ai_findings": [{"reason": "Misspelled Sudoko heading; coumns must read columns", "issues": []}],
            }])

            result = generate_unique_bug_summary(root, similarity_threshold=0.35)

            self.assertEqual(result["summary"]["source_bugs"], 2)
            self.assertEqual(result["summary"]["unique_bugs"], 1)
            self.assertEqual(result["summary"]["duplicates_removed"], 1)
            self.assertEqual(result["bugs"][0]["occurrence_count"], 2)
            self.assertEqual(result["bugs"][0]["severity"], "Critical")
            self.assertIn("generated_at", result)
            self.assertIn("generated_at_display", result)

    def test_generic_run_failures_are_excluded_from_product_bug_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in (1, 2):
                self._write_report(root, f"Run_{index}", [{
                    "scenario_id": f"CASE_{index}", "scenario_name": f"Case {index}",
                    "severity": "Critical", "reason": "Evidence detected by Run",
                    "sources": ["Run"], "ai_findings": [], "visual_findings": [],
                }])

            result = generate_unique_bug_summary(root)

            self.assertEqual(result["summary"]["source_bugs"], 0)
            self.assertEqual(result["summary"]["unique_bugs"], 0)

    def test_declared_non_bug_visual_finding_is_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_report(root, "Run_1", [{
                "scenario_id": "A", "scenario_name": "Page", "severity": "Minor",
                "execution_status": "PASS", "reason": "Evidence detected by Visual",
                "sources": ["Visual"], "visual_findings": [{
                    "summary": "No genuine UI defects detected; differences are dynamic content.",
                    "issues": [],
                }],
            }])

            result = generate_unique_bug_summary(root)

            self.assertEqual(result["summary"]["source_bugs"], 0)
            self.assertEqual(result["summary"]["unique_bugs"], 0)


if __name__ == "__main__":
    unittest.main()
