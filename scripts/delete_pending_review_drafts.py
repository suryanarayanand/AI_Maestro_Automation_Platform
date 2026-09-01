import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "portal.db"


def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ROOT / ".runtime" / "review-cleanup" / stamp / "portal.db.backup"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB, backup)
    with sqlite3.connect(DB) as db:
        rows = db.execute(
            "SELECT source_file,COUNT(*) FROM drafts WHERE status='pending' GROUP BY source_file ORDER BY source_file"
        ).fetchall()
        total = sum(row[1] for row in rows)
        db.execute("DELETE FROM drafts WHERE status='pending'")
    print(f"deleted_pending={total}")
    for source, count in rows:
        print(f"{source}: {count}")
    print(f"backup={backup}")


if __name__ == "__main__":
    main()
