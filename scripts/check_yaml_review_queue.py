import sqlite3

db = sqlite3.connect("portal.db")
db.row_factory = sqlite3.Row
print("SUMMARY")
for row in db.execute(
    "SELECT source_file,status,coverage_status,COUNT(*) count "
    "FROM drafts GROUP BY source_file,status,coverage_status "
    "ORDER BY MAX(id) DESC"
):
    print(dict(row))
print("LATEST")
for row in db.execute(
    "SELECT id,case_id,name,status,coverage_status,generation_mode,"
    "round(ai_confidence,2) confidence,error,source_file "
    "FROM drafts ORDER BY id DESC LIMIT 60"
):
    print(dict(row))
print("PREMIUM QUALITY")
row = db.execute(
    "SELECT COUNT(*) total,COUNT(DISTINCT case_id) cases,"
    "SUM(CASE WHEN error IS NOT NULL AND error!='' THEN 1 ELSE 0 END) errors,"
    "SUM(CASE WHEN yaml IS NOT NULL AND trim(yaml)!='' THEN 1 ELSE 0 END) with_yaml,"
    "SUM(CASE WHEN coverage_status='complete' THEN 1 ELSE 0 END) complete "
    "FROM drafts WHERE source_file='Anonymous_Premium_Approved_Test_Cases.xlsx'"
).fetchone()
print(dict(row))
db.close()
