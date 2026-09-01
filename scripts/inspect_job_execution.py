import sqlite3
import sys

job_id = int(sys.argv[1])
db = sqlite3.connect("portal.db")
db.row_factory = sqlite3.Row
job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
print("JOB", dict(job) if job else None)
for row in db.execute(
    "SELECT case_id,status,execution_status,condition_status,duration,stdout,stderr "
    "FROM job_results WHERE job_id=? ORDER BY id", (job_id,)
):
    item = dict(row)
    item["stdout"] = item["stdout"][-2000:]
    item["stderr"] = item["stderr"][-2000:]
    print("RESULT", item)
db.close()
