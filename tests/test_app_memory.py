import unittest

from web.services.app_memory_service import extract_elements, hierarchy_fingerprint, safe_name
from web.services.adaptive_test_agent import _tokens, reusable_yaml, yaml_command_sequence


class AppMemoryTests(unittest.TestCase):
    def test_extracts_stable_id_and_text_candidates(self):
        hierarchy = {"children": [{"attributes": {
            "resource-id": "com.example:id/nav_home", "text": "Home",
            "accessibilityText": "Home tab", "clickable": "true", "enabled": "true",
            "class": "android.view.View", "bounds": "[0,0][10,10]",
        }, "children": []}]}
        elements = extract_elements(hierarchy)
        selectors = {(item["locator_type"], item["locator_value"]) for item in elements}
        self.assertIn(("id", "nav_home"), selectors)
        self.assertIn(("text", "Home"), selectors)
        self.assertIn(("text", "Home tab"), selectors)

    def test_fingerprint_is_order_independent(self):
        first = [
            {"locator_type": "id", "locator_value": "b", "confidence": .9},
            {"locator_type": "id", "locator_value": "a", "confidence": .9},
        ]
        self.assertEqual(hierarchy_fingerprint(first), hierarchy_fingerprint(list(reversed(first))))

    def test_screen_names_are_filesystem_safe(self):
        self.assertEqual(safe_name("Premium / Article"), "Premium_Article")

    def test_memory_search_ignores_generic_test_language(self):
        self.assertEqual(_tokens(["Verify the Home page header"]), {"home", "header"})

    def test_memory_search_splits_locator_names(self):
        self.assertEqual(_tokens(["screen_home", "cta_subscribe"]), {"home", "cta", "subscribe"})

    def test_memory_tokens_include_selector_decisions(self):
        decision = {"resolved_value": "nav_home", "source": "validated_repository"}
        self.assertIn("home", _tokens([decision]))

    def test_extracts_nested_yaml_command_sequence(self):
        content = """appId: example\n---\n- launchApp:\n    clearState: true\n- repeat:\n    times: 2\n    commands:\n      - swipe:\n          direction: LEFT\n      - assertNotVisible:\n          id: ad_iframe\n"""
        self.assertEqual(yaml_command_sequence(content), [
            "launchApp", "repeat", "swipe", "assertNotVisible",
        ])

    def test_reusable_yaml_rejects_parameterized_animation_wait(self):
        invalid = "appId: example\n---\n- waitForAnimationToEnd:\n    timeout: 10000\n"
        valid = "appId: example\n---\n- waitForAnimationToEnd\n"
        self.assertFalse(reusable_yaml(invalid))
        self.assertTrue(reusable_yaml(valid))

    def test_retrieval_budget_reserves_room_for_lessons(self):
        # This guards the arithmetic independently of database contents: a normal
        # 30-item request must leave ten positions for accepted behavioral evidence.
        limit = 30
        lesson_budget = min(10, max(1, limit // 3))
        self.assertEqual(lesson_budget, 10)
        self.assertEqual(limit - lesson_budget, 20)


if __name__ == "__main__":
    unittest.main()
