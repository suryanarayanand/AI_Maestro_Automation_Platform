import json
import tempfile
import unittest
from pathlib import Path

from web.services.source_locator_service import extract_source_locators, import_source_locators


class SourceLocatorTests(unittest.TestCase):
    def test_extracts_source_candidates_without_marking_them_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Screen.kt").write_text('''
                Modifier.testTag("article_card")
                Icon(contentDescription = "Open account")
                Text("News Quiz")
            ''', encoding="utf-8")
            records = extract_source_locators(root)
            by_value = {item["locator"]["value"]: item for item in records}
            self.assertEqual(by_value["article_card"]["locator"]["type"], "id")
            self.assertEqual(by_value["article_card"]["status"], "candidate")
            self.assertGreater(by_value["article_card"]["confidence"],
                               by_value["News Quiz"]["confidence"])

    def test_import_is_atomic_json_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "layout.xml").write_text(
                '<View android:id="@+id/nav_home" />', encoding="utf-8"
            )
            output = Path(directory) / "locators.json"
            result = import_source_locators(root, output)
            self.assertEqual(result["count"], 1)
            self.assertEqual(json.loads(output.read_text())[0]["locator"]["value"], "nav_home")

    def test_ignores_test_sources_and_numeric_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test = root / "commonTest"
            test.mkdir()
            (test / "Fake.kt").write_text('Text("Fake locator")', encoding="utf-8")
            (root / "Main.kt").write_text('Text("123")\nText("Real label")', encoding="utf-8")
            values = {item["locator"]["value"] for item in extract_source_locators(root)}
            self.assertEqual(values, {"Real label"})


if __name__ == "__main__":
    unittest.main()
