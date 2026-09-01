import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
db = sqlite3.connect(ROOT / "portal.db")
db.row_factory = sqlite3.Row

for source, expected, prefix in (
    ("Anonymous_Premium_Approved_Test_Cases.xlsx", 30, "ANON_PREM_"),
    ("Anonymous_EBooks_Approved_Test_Cases.xlsx", 20, "ANON_EBOOK_"),
):
    rows = db.execute(
        "SELECT case_id,yaml,coverage_status,error FROM drafts "
        "WHERE source_file=? AND status='pending' ORDER BY case_id", (source,)
    ).fetchall()
    assert len(rows) == expected, (source, len(rows))
    assert len({row["case_id"] for row in rows}) == expected
    for row in rows:
        text = row["yaml"] or ""
        assert row["case_id"].startswith(prefix)
        assert row["coverage_status"] == "complete" and not row["error"]
        assert text.startswith("appId: com.mobstac.thehindu")
        assert "\n---\n" in text
        assert "runFlow" in text and "takeScreenshot" in text
        for reference in re.findall(r'runFlow:\s*"([^\"]+)"', text):
            target = (ROOT / "Scenarios" / reference).resolve()
            assert target.is_file(), (row["case_id"], reference, target)
    print(source, "verified", len(rows))
db.close()
