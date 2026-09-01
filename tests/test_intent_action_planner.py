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
from yaml_writer import YAMLWriter


class IntentActionPlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = IntentActionPlanner()

    def test_anonymous_ad_and_article_intents_use_validated_locators(self):
        self.assertEqual(
            self.planner.plan("Verify that inline ads are displayed."),
            [{"command": "assertVisible", "parameters": {"text": "ADVERTISEMENT"}}],
        )
        self.assertEqual(
            self.planner.plan("Verify that the bottom sticky ad is displayed."),
            [{"command": "assertVisible", "parameters": {"id": "aw0"}}],
        )
        self.assertEqual(
            self.planner.plan("Open any article from the Home page."),
            [{"command": "tapOn", "parameters": {"id": "article_card", "index": 0}}],
        )
        self.assertEqual(
            self.planner.plan("Verify that the interstitial ad is displayed."),
            [{"command": "assertVisible", "parameters": {"id": "ad_iframe"}}],
        )

    def test_subscriber_ad_intents_assert_absence(self):
        self.assertEqual(
            self.planner.plan("User should not see any inline ads."),
            [{"command": "assertNotVisible", "parameters": {"text": "ADVERTISEMENT"}}],
        )
        self.assertEqual(
            self.planner.plan("User should not see the bottom sticky ad."),
            [{"command": "assertNotVisible", "parameters": {"id": "aw0"}}],
        )

    def test_subscriber_home_bundle_uses_validated_identity_and_ad_locators(self):
        entitlement = self.planner.plan(
            "Subscribe, Advertisement, and the sticky advertisement container are not "
            "visible for the active subscriber.", "SUB_HOME_001"
        )
        self.assertEqual([item["command"] for item in entitlement], [
            "assertNotVisible", "assertNotVisible", "assertNotVisible",
        ])
        self.assertEqual(entitlement[-1]["parameters"], {"id": "aw0"})

        refreshed = self.planner.plan(
            "Home remains visible with The Hindu logo, hamburger menu, and at least one "
            "article card available.", "SUB_HOME_002"
        )
        self.assertEqual([item["command"] for item in refreshed], [
            "assertVisible", "assertVisible", "assertVisible", "assertVisible",
            "takeScreenshot",
        ])
        self.assertEqual(refreshed[1]["parameters"], {"id": "nav_menu"})
        self.assertEqual(refreshed[3]["parameters"], {"id": "article_card", "index": 0})

    def test_preserves_explicit_repeat_counts(self):
        home = self.planner.plan("Scroll down through the Home page five times.")
        articles = self.planner.plan("Swipe right to left through ten consecutive articles.")
        self.assertEqual(home[0]["command"], "repeat")
        self.assertEqual(home[0]["parameters"]["times"], 5)
        self.assertEqual([item["command"] for item in home], [
            "repeat", "tapOn", "waitForAnimationToEnd",
        ])
        self.assertEqual(articles[0]["parameters"]["times"], 10)

    def test_nested_parameterless_commands_use_maestro_short_form(self):
        yaml_text = YAMLWriter().write({
            "appId": "com.example",
            "tags": ["generated"],
            "steps": [{
                "command": "repeat",
                "parameters": {
                    "times": 2,
                    "commands": [
                        {"swipe": {"direction": "UP"}},
                        {"waitForAnimationToEnd": {}},
                    ],
                },
            }],
        })
        self.assertIn("      - waitForAnimationToEnd\n", yaml_text)
        self.assertNotIn("      - waitForAnimationToEnd:\n", yaml_text)

    def test_negative_verify_wins_over_positive_ad_keywords(self):
        self.assertEqual(
            self.planner.plan("Verify that inline advertisements are not visible."),
            [{"command": "assertNotVisible", "parameters": {"text": "ADVERTISEMENT"}}],
        )

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

    def test_games_language_never_relaunches_the_application(self):
        for step, flow in (
            ("Launch Mini Sudoku and verify page loads.", "SC_27_SUDOKU_MINI.yaml"),
            ("Launch Easy Sudoku and verify page loads.", "SC_27_SUDOKU_EASY.yaml"),
        ):
            with self.subTest(step=step):
                result = self.planner.plan(step, "TC_002_proto")
                self.assertEqual(result, [{
                    "command": "runFlow", "parameters": {"path": flow},
                }])

    def test_tc_002_uses_isolated_game_flows_without_duplicate_setup(self):
        yaml_text = YAMLGenerator().generate_yaml(["source rows"], case_id="TC_002")
        self.assertNotIn('LOGIN.yaml', yaml_text)
        self.assertNotIn('Anonymous_account_onboarding.yaml', yaml_text)
        self.assertNotIn('id: "nav_games"', yaml_text)
        self.assertIn('SC_27_CRYPTIC_CROSSWORD.yaml', yaml_text)
        self.assertIn('SC_27_NEWS_QUIZ.yaml', yaml_text)

    def test_games_navigation_return_and_visibility_are_deterministic(self):
        self.assertEqual(
            self.planner.plan("Navigate to the Games tab."),
            [{"command": "tapOn", "parameters": {"id": "nav_games"}}],
        )
        self.assertEqual(
            self.planner.plan("Return to Games page."),
            [{"command": "tapOn", "parameters": {"id": "nav_games"}}],
        )
        self.assertEqual(
            self.planner.plan("Verify Games landing page loads."),
            [{"command": "assertVisible", "parameters": {"id": "screen_games"}}],
        )

    def test_news_quiz_uses_observed_quiz_card_flow(self):
        self.assertEqual(
            self.planner.plan("Validate additional games including News Quiz."),
            [{"command": "runFlow", "parameters": {"path": "SC_27_NEWS_QUIZ.yaml"}}],
        )

    def test_navigation_does_not_invent_assertion(self):
        commands = self.planner.plan("Open hamburger menu", "TC_1")
        self.assertEqual(commands, [{"command": "tapOn", "parameters": {"id": "nav_menu"}}])

    def test_subscriber_login_sequence_is_deterministic(self):
        cases = {
            "Tap on User icon which is there at top right": ("tapOn", {"id": "nav_account"}),
            "Navigate to Home page": ("tapOn", {"id": "nav_home"}),
            "Verify Home page header": ("assertVisible", {"id": "screen_home"}),
        }
        for step, (command, parameters) in cases.items():
            with self.subTest(step=step):
                self.assertEqual(self.planner.plan(step, "TC_1"), [
                    {"command": command, "parameters": parameters}
                ])
        login_tap = self.planner.plan("Tap on login text", "TC_1")
        self.assertEqual(login_tap[0]["command"], "runFlow")
        self.assertEqual(login_tap[0]["parameters"]["when"], {"visible": {"id": "cta_login"}})
        credentials = self.planner.plan("Provide the valid credentials and login", "TC_1")
        self.assertEqual([item["command"] for item in credentials], ["runFlow", "extendedWaitUntil"])

    def test_subscriber_login_uses_complete_state_transition(self):
        self.assertEqual(
            self.planner.plan("Login as subscriber", "TC_1"),
            [{"command": "runFlow", "parameters": {
                "path": "../Common/OPEN_SUBSCRIBER_HOME.yaml"
            }}],
        )

    def test_post_article_sections_are_not_silently_dropped(self):
        end = self.planner.plan("Continue scrolling until reaching the end of the article.", "TC_1")
        self.assertEqual(end[0]["command"], "scrollUntilVisible")
        self.assertEqual(end[0]["parameters"]["element"], {"text": "Post a comment"})
        expected = {
            "Verify the Post Comment section after the article.": "Post a comment",
            "Verify the Related Topics section. (If available for the article)": "Related Topics",
        }
        for step, text in expected.items():
            with self.subTest(step=step):
                self.assertEqual(self.planner.plan(step, "TC_1"), [
                    {"command": "assertVisible", "parameters": {"text": text}}
                ])
        recommended = self.planner.plan("Verify the Recommended section.", "TC_1")
        self.assertEqual([item["command"] for item in recommended], ["runFlow"])
        headlines = self.planner.plan(
            "Verify the Headlines section. Scroll further through the post-article sections.", "TC_1"
        )
        self.assertEqual([item["command"] for item in headlines], [
            "runFlow", "swipe", "waitForAnimationToEnd"
        ])

    def test_premium_navigation_and_briefing_article_are_grounded(self):
        for step in ("Navigate to the Premium tab.", "Navigate to Premium Briefing"):
            with self.subTest(step=step):
                self.assertEqual(self.planner.plan(step, "TC_1"), [
                    {"command": "tapOn", "parameters": {"id": "nav_premium"}}
                ])
        briefing = self.planner.plan("Locate and tap on a Briefing article.", "TC_1")
        self.assertEqual([item["command"] for item in briefing], ["runFlow", "tapOn"])
        self.assertEqual(briefing[-1]["parameters"], {"text": "READ FULL ARTICLE"})
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
