import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from generation.large_workbook_reader import LargeWorkbookReader


class LargeWorkbookReaderTests(unittest.TestCase):
    def test_groups_blank_scenario_rows_under_previous_case(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["S.No", "Component/Module", "Test Scenario", "Description"])
            sheet.append([1, "Home", "Home navigation", "Verify Home"])
            sheet.append([2, "Home", None, "Verify Trending"])
            sheet.append([3, "Account", "Open account", "Tap Account"])
            workbook.save(path)

            groups = LargeWorkbookReader().read_groups(path)

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["id"], "TH_0001")
        self.assertEqual(groups[0]["module"], "Home")
        self.assertEqual(len(groups[0]["validation_points"]), 2)
        self.assertEqual(groups[1]["id"], "TH_0003")
        self.assertEqual(groups[1]["module"], "Account")


if __name__ == "__main__":
    unittest.main()
