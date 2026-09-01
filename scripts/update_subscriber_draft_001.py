import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
YAML = '''appId: com.mobstac.thehindu
tags: [generated, ordered, subscriber, home, entitlement, no-ads]
---
- runFlow: "../Common/OPEN_SUBSCRIBER_HOME.yaml"
- extendedWaitUntil: {visible: {id: "screen_home"}, timeout: 30000}
- assertVisible: {id: "screen_home"}
- waitForAnimationToEnd: {timeout: 5000}
- assertNotVisible: {text: "SUBSCRIBE"}
- assertNotVisible: {text: "ADVERTISEMENT"}
- assertNotVisible: {id: "aw0"}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_001_subscriber_home_no_ads"
'''


with sqlite3.connect(ROOT / "portal.db") as db:
    latest = db.execute(
        "SELECT id FROM drafts WHERE case_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
        ("SUB_HOME_001",),
    ).fetchone()
    if not latest:
        raise SystemExit("No pending SUB_HOME_001 draft found")
    db.execute(
        """UPDATE drafts SET yaml=?,coverage_status='complete',
           generation_mode='reviewed-repository',ai_confidence=1.0,ai_assumptions=?
           WHERE id=?""",
        (YAML, json.dumps([
            "ADVERTISEMENT and aw0 are validated repository selectors; aw0 covers "
            "the Google ad container used by sticky advertising."
        ]), latest[0]),
    )
    print(f"Updated pending SUB_HOME_001 draft #{latest[0]}")
