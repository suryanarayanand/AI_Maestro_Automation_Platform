import unittest
from unittest.mock import patch

from web.services import testing_bot_service


class TestingBotSafetyTests(unittest.TestCase):
    def test_uncovered_requirements_are_reported(self):
        traceability = [
            {"requirement": "Open Videos", "status": "covered"},
            {"requirement": "Verify selected tab", "status": "missing"},
        ]
        self.assertEqual(
            testing_bot_service._uncovered(traceability),
            ["Verify selected tab"],
        )

    @patch.object(testing_bot_service, "_latest_proposal")
    def test_incomplete_suggestion_cannot_be_applied(self, latest):
        latest.return_value = {
            "case_id": "ANON_VIDEO_001", "coverage": 0.5,
            "coverage_status": "incomplete", "uncovered": ["Tap Videos"],
        }
        with self.assertRaisesRegex(ValueError, "covers only 50%"):
            testing_bot_service._apply_proposal("admin")


if __name__ == "__main__":
    unittest.main()
