import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "generation"
if str(GENERATION) not in sys.path:
    sys.path.insert(0, str(GENERATION))

from excel_reader import ExcelReader
from intent_action_planner import IntentActionPlanner
from workbook_normalizer import WorkbookNormalizer
from yaml_generator import YAMLGenerator


class IntentActionPlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = IntentActionPlanner()

    def test_native_actions(self):
        self.assertEqual(
            self.planner.plan("Launch The Hindu application with a fresh app state.")[0],
            {"command": "launchApp", "parameters": {"clearState": True}},
        )
        self.assertEqual(
            self.planner.plan("Relaunch the application.")[0]["command"], "launchApp"
        )
        self.assertEqual(
            self.planner.plan("Skip the onboarding screens if they are displayed.")[0]["command"],
            "runFlow",
        )

    def test_navigation_is_repository_backed(self):
        commands = self.planner.plan("Navigate to the Editorial section using SEE MORE.")
        self.assertEqual(commands[0]["command"], "tapOn")
        self.assertEqual(commands, [{"command": "tapOn", "parameters": {"text": "Editorial"}}])

    def test_games_and_hamburger_foundations(self):
        games = self.planner.plan("Navigate to the Games section from the Home page.")
        self.assertEqual(games[0], {"command": "tapOn", "parameters": {"id": "nav_games"}})
        self.assertEqual(games, [{"command": "tapOn", "parameters": {"id": "nav_games"}}])

    def test_navigation_does_not_invent_assertion(self):
        commands = self.planner.plan("Open hamburger menu", "TC_1")
        self.assertEqual(commands, [{"command": "tapOn", "parameters": {"id": "nav_menu"}}])

    def test_header_verification_is_not_reduced_to_whole_home_screen(self):
        self.assertIsNone(self.planner.plan("Verify Home page header", "TC_1"))
        expand = self.planner.plan("Expand the India category.")
        self.assertEqual(expand, [{"command": "tapOn", "parameters": {"text": "India"}}])

    def test_existing_common_flow_intent(self):
        commands = self.planner.plan(
            "Execute the reusable flow OPEN_SUBSCRIBER_GAMES.yaml to reach the Games page."
        )
        self.assertEqual(commands, [{
            "command": "runFlow",
            "parameters": {"path": "../Common/OPEN_SUBSCRIBER_GAMES.yaml"},
        }])

    def test_sc_23_multiline_upload_generates_complete_yaml(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            normalized = WorkbookNormalizer().normalize(
                ROOT / "Uploads" / "portal_test.xlsx", Path(directory) / "normalized.xlsx"
            )
            case = next(
                item for item in ExcelReader().group_cases(normalized.canonical_path)
                if item["id"] == "SC_23_gen"
            )
            yaml_text = YAMLGenerator().generate_yaml(case["steps"], tags=["generated"], case_id=case["id"])
            self.assertIn("- launchApp:", yaml_text)
            self.assertIn('id: "screen_home"', yaml_text)
            self.assertIn('text: "Editorial"', yaml_text)
            self.assertIn("takeScreenshot", yaml_text)

    def test_sc_29_uses_deterministic_category_routes(self):
        yaml_text = YAMLGenerator().generate_yaml(
            ["source wording is handled by the complex planner"],
            tags=["generated"], case_id="SC_29_gen",
        )
        self.assertGreaterEqual(yaml_text.count("OPEN_HOME_FOR_LOCATOR_SMOKE.yaml"), 10)
        self.assertIn('text: "Other Sports"', yaml_text)
        self.assertIn('id: "screen_section"', yaml_text)
        self.assertIn("- retry:", yaml_text)
        self.assertIn("commands:\n      - tapOn:\n          id: \"nav_menu\"", yaml_text)

    def test_sc_29_split_flows_are_isolated(self):
        india = YAMLGenerator().generate_yaml(["split"], case_id="SC_29_INDIA")
        world = YAMLGenerator().generate_yaml(["split"], case_id="SC_29_WORLD")
        sport = YAMLGenerator().generate_yaml(["split"], case_id="SC_29_SPORT")
        self.assertIn('text: "India"', india)
        self.assertNotIn('text: "Cricket"', india)
        self.assertIn('text: "World"', world)
        self.assertNotIn('text: "Cricket"', world)
        self.assertIn('text: "Other Sports"', sport)


if __name__ == "__main__":
    unittest.main()
