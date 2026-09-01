import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
YAML = '''appId: com.mobstac.thehindu
tags: [generated, ordered, subscriber, home, refresh, header]
---
- runFlow: "../Common/OPEN_SUBSCRIBER_HOME.yaml"
- swipe: {start: "50%, 25%", end: "50%, 80%", duration: 800}
- waitForAnimationToEnd: {timeout: 8000}
- assertVisible: {id: "screen_home"}
- assertVisible: {id: "nav_menu"}
- assertVisible: {text: "The Hindu"}
- assertVisible: {id: "article_card", index: 0}
- assertNotVisible: {text: "SUBSCRIBE"}
- assertNotVisible: {text: "ADVERTISEMENT"}
- assertNotVisible: {id: "aw0"}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_002_home_after_refresh"
'''


with sqlite3.connect(ROOT / "portal.db") as db:
    latest = db.execute(
        "SELECT id FROM drafts WHERE case_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
        ("SUB_HOME_002",),
    ).fetchone()
    if not latest:
        raise SystemExit("No pending SUB_HOME_002 draft found")
    db.execute(
        """UPDATE drafts SET yaml=?,coverage_status='complete',
           generation_mode='reviewed-repository',ai_confidence=1.0,ai_assumptions=?
           WHERE id=?""",
        (YAML, json.dumps([
            "nav_menu is the validated Home hamburger locator; The Hindu is the "
            "observed Home-logo accessibility label; article_card proves content returned."
        ]), latest[0]),
    )
    print(f"Updated pending SUB_HOME_002 draft #{latest[0]}")
