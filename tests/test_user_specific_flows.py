import unittest

from web.services.yaml_editor_service import account_tag


class UserSpecificFlowClassificationTests(unittest.TestCase):
    def test_supported_account_states_are_distinct(self):
        samples = {
            "anonymous": "anonymous user sees an advertisement",
            "subscriber": "active subscriber opens premium content",
            "registered-user": "registered user / non-subscriber sees Subscribe",
            "expired-user": "user with expired subscription sees renewal",
        }
        for expected, content in samples.items():
            with self.subTest(expected=expected):
                self.assertEqual(account_tag("flow.yaml", content), expected)

    def test_non_subscriber_is_not_active_subscriber(self):
        self.assertEqual(
            account_tag("flow.yaml", "authenticated non-subscriber account"),
            "registered-user",
        )


if __name__ == "__main__":
    unittest.main()
