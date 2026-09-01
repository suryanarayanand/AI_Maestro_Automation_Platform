import unittest

from web.services.scenario_service import _display_module


class ScenarioModuleClassificationTests(unittest.TestCase):
    def test_explicit_home_module_wins_over_premium_keywords(self):
        test = {
            "id": "SUB_HOME_006", "module": "Home", "section": "Home",
            "name": "Subscriber premium article access", "yaml": "SUB_HOME_006.yaml",
        }
        self.assertEqual(_display_module(test), "Home")


if __name__ == "__main__":
    unittest.main()
