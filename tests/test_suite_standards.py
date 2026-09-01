import unittest
from unittest.mock import patch
from pathlib import Path

from web.services import scenario_service


class SuiteStandardsTests(unittest.TestCase):
    def test_rejects_duplicate_ids_and_missing_files(self):
        with patch.object(scenario_service, "SCENARIO_FOLDER", Path("Z:/missing")):
            errors = scenario_service.validate_suite_definition({"tests": [
                {"id": "SC_27", "yaml": "one.yaml"},
                {"id": "SC_27", "yaml": "two.yaml"},
            ]})
        self.assertTrue(any("Duplicate case ID" in item for item in errors))
        self.assertTrue(any("Scenario file not found" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
