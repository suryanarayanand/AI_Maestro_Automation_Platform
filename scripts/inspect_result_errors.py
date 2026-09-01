import sqlite3
import sys


job_id = int(sys.argv[1])
case_ids = sys.argv[2:]
connection = sqlite3.connect("portal.db")
connection.row_factory = sqlite3.Row
for case_id in case_ids:
    row = connection.execute(
        "SELECT stdout,stderr FROM job_results WHERE job_id=? AND case_id=? ORDER BY id DESC LIMIT 1",
        (job_id, case_id),
    ).fetchone()
    output = (row["stderr"] or row["stdout"] or "") if row else "missing"
    print(f"### {case_id}\n{output[-6000:]}")
