import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web.services import yaml_editor_service


class YAMLDeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.scenarios = self.root / "Scenarios"
        self.suites = self.root / "Suites"
        self.backups = self.root / "Backups" / "YAML"
        self.scenarios.mkdir()
        self.suites.mkdir()
        self.patches = [
            patch.object(yaml_editor_service, "ROOT", self.root),
            patch.object(yaml_editor_service, "SCENARIOS", self.scenarios),
            patch.object(yaml_editor_service, "SUITES", self.suites),
            patch.object(yaml_editor_service, "BACKUPS", self.backups),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_delete_preserves_recovery_backup(self):
        scenario = self.scenarios / "unused.yaml"
        scenario.write_text("appId: example\n---\n- launchApp\n", encoding="utf-8")

        backup = yaml_editor_service.delete_scenario("unused.yaml")

        self.assertFalse(scenario.exists())
        self.assertTrue((self.root / backup).is_file())
        self.assertIn("Backups/YAML/Deleted", backup)

    def test_delete_refuses_suite_referenced_yaml(self):
        scenario = self.scenarios / "used.yaml"
        scenario.write_text("appId: example\n---\n- launchApp\n", encoding="utf-8")
        (self.suites / "smoke.json").write_text(
            json.dumps({"tests": [{"id": "USED", "yaml": "used.yaml"}]}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "referenced by suite.*smoke"):
            yaml_editor_service.delete_scenario("used.yaml")

        self.assertTrue(scenario.is_file())

    def test_list_scenarios_extracts_and_filters_account_tags(self):
        (self.scenarios / "anonymous.yaml").write_text(
            "appId: example\ntags:\n  - smoke\n  - anonymous\n---\n- launchApp\n",
            encoding="utf-8",
        )
        (self.scenarios / "subscriber.yaml").write_text(
            "appId: example\ntags: [regression, subscriber]\n---\n- launchApp\n",
            encoding="utf-8",
        )

        anonymous = yaml_editor_service.list_scenarios(tag="anonymous")

        self.assertEqual([item["name"] for item in anonymous], ["anonymous.yaml"])
        self.assertIn("smoke", anonymous[0]["tags"])
        self.assertIn("anonymous", yaml_editor_service.list_available_tags())


if __name__ == "__main__":
    unittest.main()
