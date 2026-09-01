from pathlib import Path

from web.portal_db import connect


source = "Anonymous_Games_Hamburger_Account_Settings_Approved_Test_Cases.xlsx"
output = Path(".runtime/latest_generated_drafts.txt")
output.parent.mkdir(parents=True, exist_ok=True)
with connect() as db:
    rows = db.execute(
        "SELECT case_id,name,error,yaml FROM drafts WHERE source_file=? ORDER BY id",
        (source,),
    ).fetchall()
output.write_text("\n\n".join(
    f"### {row['case_id']} — {row['name']}\nERROR: {row['error']}\n{row['yaml']}"
    for row in rows
), encoding="utf-8")
print(output, len(rows))
