import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generation"))

from build_optimized_locator_suite import PAGES, render


class OptimizedLocatorSuiteTests(unittest.TestCase):
    def test_all_requested_pages_are_present(self):
        self.assertEqual(len(PAGES), 14)

    def test_dedicated_page_uses_validated_container(self):
        yaml = render("Sci-Tech", "screen_section", "child", ("Science", False))
        self.assertIn('id: "screen_section"', yaml)
        self.assertIn('text: "Sci-Tech"', yaml)

    def test_duplicate_child_uses_second_match(self):
        yaml = render("Books", "screen_section", "child", ("Books", True))
        self.assertIn("index: 1", yaml)


if __name__ == "__main__":
    unittest.main()
