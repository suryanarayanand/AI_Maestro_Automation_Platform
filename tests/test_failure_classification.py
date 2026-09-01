import unittest

from web.services.adaptive_test_agent import classify_execution_failure


class FailureClassificationTests(unittest.TestCase):
    def test_second_login_after_article_is_generation_order_defect(self):
        log = """Run ../Common/LOGIN.yaml...
Run ../Common/LOGIN.yaml... COMPLETED
Tap on \"READ FULL ARTICLE\"... COMPLETED
Run ../Common/LOGIN.yaml...
Assert that \"Email\" is visible... FAILED
Assertion is false: \"Email\" is visible
"""
        result = classify_execution_failure(log)
        self.assertEqual(result["classification"], "generation_order_defect")
        self.assertEqual(result["component"], "generated_scenario")

    def test_first_login_email_failure_remains_execution_failure(self):
        log = """Run ../Common/LOGIN.yaml...
Assert that \"Email\" is visible... FAILED
"""
        self.assertEqual(classify_execution_failure(log)["classification"], "execution_failure")


if __name__ == "__main__":
    unittest.main()
