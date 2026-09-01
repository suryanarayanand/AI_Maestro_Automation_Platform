import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LoginFlowContractTests(unittest.TestCase):
    def test_login_finishes_on_authenticated_account_drawer(self):
        yaml = (ROOT / "Common" / "LOGIN.yaml").read_text(encoding="utf-8")
        self.assertIn('visible: "^Account$"', yaml)
        self.assertIn('id: "cta_menu_close"', yaml)
        self.assertIn('id: "screen_home"', yaml)
        self.assertIn('id: "cta_login"', yaml)
        self.assertNotIn('visible: "Home"', yaml)


if __name__ == "__main__":
    unittest.main()
