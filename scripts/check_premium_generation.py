import sqlite3

db = sqlite3.connect("portal.db")
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT id,case_id,name,status,coverage_status,generation_mode,"
    "round(ai_confidence,2) confidence,error,source_file,user_state,ai_assumptions,traceability "
    "FROM drafts WHERE upper(case_id) LIKE '%PREM%' OR lower(source_file) LIKE '%premium%' "
    "ORDER BY id"
).fetchall()
print("drafts", len(rows))
for row in rows:
    print(dict(row))
db.close()
