import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
yaml = (ROOT / "Scenarios" / "SUB_HOME_006.yaml").read_text(encoding="utf-8")
with sqlite3.connect(ROOT / "portal.db") as db:
    draft = db.execute(
        "SELECT id FROM drafts WHERE case_id=? AND status='approved' ORDER BY id DESC LIMIT 1",
        ("SUB_HOME_006",),
    ).fetchone()
    if not draft:
        raise SystemExit("No approved SUB_HOME_006 draft found")
    db.execute("UPDATE drafts SET yaml=? WHERE id=?", (yaml, draft[0]))
    print(f"Synchronized approved SUB_HOME_006 draft #{draft[0]}")
