import unittest

from web.services.atomic_flow_composer import compose_atomic_flow
from web.services.atomic_flow_service import proposal_readiness
from web.services.yaml_editor_service import validate_maestro_yaml


class AtomicFlowComposerTests(unittest.TestCase):
    def step(self, action, state="ANONYMOUS", tags=None):
        return {
            "scenario": "Composer test", "source_text": f"User State: {state.title()}. Action: {action}",
            "user_state": state, "tags_list": tags or [state.casefold(), "functional"],
        }

    def test_photos_navigation_is_a_complete_grounded_flow(self):
        result = compose_atomic_flow(self.step("Verify selecting the Photos tab loads the photo gallery page"))
        self.assertTrue(validate_maestro_yaml(result))
        self.assertIn("OPEN_ANONYMOUS_HOME.yaml", result)
        self.assertIn('text: "Photos"', result)
        self.assertIn('text: "ADVERTISEMENT"', result)
        self.assertIn('text: "SUBSCRIBE"', result)
        self.assertIn("extendedWaitUntil:", result)
        self.assertIn("assertVisible:", result)
        self.assertGreaterEqual(result.count("\n- "), 5)

    def test_subscriber_ai_summary_includes_login_state_and_assertions(self):
        result = compose_atomic_flow(self.step("Verify AI Summary and Article FAQs", "SUBSCRIBER"))
        self.assertTrue(validate_maestro_yaml(result))
        self.assertIn("OPEN_SUBSCRIBER_HOME.yaml", result)
        self.assertNotIn("TEST_PIANO_SUB_EMAIL", result)
        self.assertIn("OPEN_SUBSCRIBER_HOME.yaml", result)
        self.assertIn('text: "Article FAQs"', result)
        self.assertIn("assertNotVisible:", result)
        self.assertNotIn('assertVisible:\n    text: "ADVERTISEMENT"', result)
        self.assertGreaterEqual(result.count("\n- "), 9)

    def test_external_requirement_is_not_turned_into_placeholder_yaml(self):
        with self.assertRaisesRegex(ValueError, "external test data"):
            compose_atomic_flow(self.step("Verify installation from Play Store"))

    def test_article_subscribe_login_returns_to_article(self):
        result = compose_atomic_flow(self.step(
            "Verify anonymous user signs in from the article Subscribe button and returns to the same article"
        ))
        self.assertIn("LOGIN_FROM_ARTICLE_SUBSCRIBE.yaml", result)
        self.assertIn('id: "screen_article_detail"', result)
        self.assertTrue(validate_maestro_yaml(result))

    def test_generated_anonymous_flow_is_publish_ready(self):
        step = self.step("Verify selecting the Photos tab loads the photo gallery page")
        result = compose_atomic_flow(step)
        readiness = proposal_readiness(step, result)
        self.assertTrue(readiness["ready"], readiness["checks"])

    def test_readiness_rejects_wrong_subscriber_entitlement(self):
        step = self.step("Verify selecting the Photos tab loads the photo gallery page", "SUBSCRIBER")
        result = compose_atomic_flow(step).replace("assertNotVisible:", "assertVisible:")
        readiness = proposal_readiness(step, result)
        self.assertFalse(readiness["ready"])
        failed = {item["name"] for item in readiness["checks"] if not item["passed"]}
        self.assertIn("User-state contract", failed)


if __name__ == "__main__":
    unittest.main()
