import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generation"))

from generate_th_pilot import PILOT_CASES, render


class GenerateTHPilotTests(unittest.TestCase):
    def test_render_uses_source_metadata_and_validated_ids(self):
        case = {
            "id": "TH_1177",
            "module": "Bottom Tabs",
            "name": "Bottom Bar Sections / Bottom Tab",
            "validation_points": [{"description": "Verify tab navigation"}],
        }
        yaml = render(case, PILOT_CASES["TH_1177"])
        self.assertIn("# Excel source: TH_1177", yaml)
        self.assertIn('id: "nav_trending"', yaml)
        self.assertIn('id: "screen_trending"', yaml)
        self.assertIn("takeScreenshot", yaml)


if __name__ == "__main__":
    unittest.main()
