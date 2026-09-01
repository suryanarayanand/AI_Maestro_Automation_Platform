import sqlite3

db = sqlite3.connect("portal.db")
cursor = db.execute(
    "DELETE FROM drafts WHERE source_file IN (?, ?)",
    ("Anonymous_Premium_Generation_Batch_1.xlsx", "Anonymous_Premium_Generation_Batch_2.xlsx"),
)
db.commit()
print("temporary batch drafts removed", cursor.rowcount)
db.close()
