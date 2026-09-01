import json
import sys
import tempfile
import unittest
from pathlib import Path


GENERATION = Path(__file__).resolve().parents[1] / "generation"
sys.path.insert(0, str(GENERATION))

from repository_search import RepositorySearch
from yaml_generator import YAMLGenerator


class RepositorySearchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.validated = root / "validated.json"
        self.candidates = root / "candidates.json"
        self.validated.write_text(
            json.dumps([
                {
                    "name": "nav_home",
                    "status": "validated",
                    "locator": {"type": "id", "value": "nav_home", "priority": 1},
                }
            ]),
            encoding="utf-8",
        )
        self.candidates.write_text(
            json.dumps([
                {
                    "name": "HOME",
                    "locator": {"type": "text", "value": "HOME", "priority": 3},
                },
                {
                    "name": "India",
                    "locator": {"type": "text", "value": "India", "priority": 3},
                },
            ]),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_search(self, allow_candidate_fallback=False):
        return RepositorySearch(
            self.validated,
            self.candidates,
            allow_candidate_fallback=allow_candidate_fallback,
        )

    def test_validated_locator_has_precedence(self):
        repository = self.make_search(allow_candidate_fallback=True)
        result = repository.search("HOME")
        self.assertEqual(result["locator"]["type"], "id")
        self.assertEqual(repository.last_match_source, "validated")

    def test_strict_mode_rejects_unvalidated_candidate(self):
        repository = self.make_search()
        self.assertIsNone(repository.search("India"))
        self.assertIsNone(repository.last_match_source)

    def test_candidate_fallback_must_be_explicit(self):
        repository = self.make_search(allow_candidate_fallback=True)
        result = repository.search("India")
        self.assertEqual(result["locator"]["value"], "India")
        self.assertEqual(repository.last_match_source, "candidate")

    def test_empty_target_is_not_matched(self):
        repository = self.make_search(allow_candidate_fallback=True)
        self.assertIsNone(repository.search("  "))

    def test_explicit_selector_requires_exact_type_and_value(self):
        repository = self.make_search(allow_candidate_fallback=True)
        self.assertIsNotNone(repository.validated_selector("id", "nav_home"))
        self.assertIsNone(repository.validated_selector("id", "HOME"))
        self.assertIsNone(repository.validated_selector("text", "nav_home"))


class YAMLGeneratorSelectionTests(unittest.TestCase):

    def test_explicit_assert_not_visible_intent_uses_validated_locator(self):
        yaml = YAMLGenerator().generate_yaml(
            ["ASSERT_NOT_VISIBLE(nav_home)"], case_id="TC_1"
        )
        self.assertIn("- assertNotVisible:", yaml)
        self.assertIn('id: "nav_home"', yaml)

    def test_explicit_text_assertion_uses_visible_label(self):
        yaml = YAMLGenerator().generate_yaml(
            ["ASSERT_NOT_VISIBLE_TEXT(Subscribe)"], case_id="TC_1"
        )
        self.assertIn("- assertNotVisible:", yaml)
        self.assertIn('text: "Subscribe"', yaml)

    def test_unknown_explicit_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not validated"):
            YAMLGenerator().generate_yaml(["ASSERT_VISIBLE(invented_selector)"])
    def setUp(self):
        self.generator = YAMLGenerator()

    def test_tap_prefers_navigation_id_over_screen_id(self):
        self.assertEqual(
            self.generator.generate_command("Tap Ebooks")["parameters"]["id"],
            "nav_ebooks",
        )
        self.assertEqual(
            self.generator.generate_command("Tap Games")["parameters"]["id"],
            "nav_games",
        )

    def test_tap_menu_does_not_select_close_control(self):
        self.assertEqual(
            self.generator.generate_command("Tap Menu")["parameters"]["id"],
            "nav_menu",
        )

    def test_take_screenshot_uses_scalar_path(self):
        yaml = self.generator.generate_yaml([
            "Take screenshot Screenshots/Generated/GEN_001_Home"
        ])
        self.assertIn(
            '- takeScreenshot: "Screenshots/Generated/GEN_001_Home"',
            yaml,
        )

    def test_complex_active_tab_reset_is_expanded(self):
        yaml = self.generator.generate_yaml([
            "Verify that if a user scrolls halfway down the HOME screen feed and "
            "taps the HOME tab icon again, the screen automatically scrolls smoothly "
            "back to the absolute top of the feed page."
        ], case_id="TH_1181")
        self.assertIn('- runFlow: "../Common/OPEN_HOME_FOR_LOCATOR_SMOKE.yaml"', yaml)
        self.assertEqual(yaml.count('direction: "UP"'), 2)
        self.assertEqual(yaml.count('id: "nav_home"'), 2)
        self.assertIn('TH_1181_scrolled', yaml)
        self.assertIn('TH_1181_reset_top', yaml)


if __name__ == "__main__":
    unittest.main()
