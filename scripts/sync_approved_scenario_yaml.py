import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
case_ids = sys.argv[1:]
if not case_ids:
    raise SystemExit("Usage: sync_approved_scenario_yaml.py CASE_ID [CASE_ID ...]")
with sqlite3.connect(ROOT / "portal.db") as db:
    for case_id in case_ids:
        path = ROOT / "Scenarios" / f"{case_id}.yaml"
        draft = db.execute(
            "SELECT id FROM drafts WHERE case_id=? AND status='approved' ORDER BY id DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        if not path.is_file() or not draft:
            raise SystemExit(f"Missing approved scenario or draft for {case_id}")
        db.execute("UPDATE drafts SET yaml=? WHERE id=?", (path.read_text(encoding="utf-8"), draft[0]))
        print(f"Synchronized {case_id} draft #{draft[0]}")
