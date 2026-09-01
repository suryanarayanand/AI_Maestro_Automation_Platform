import sqlite3
import sys


job_id = int(sys.argv[1])
connection = sqlite3.connect("portal.db")
connection.row_factory = sqlite3.Row

job = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
print({key: job[key] for key in job.keys() if key in {
    "id", "status", "current_case", "completed", "total", "suite",
    "report_folder", "started_at", "finished_at"
}})

rows = connection.execute(
    "SELECT case_id, status, stdout, stderr FROM job_results "
    "WHERE job_id = ? AND status != 'PASS' ORDER BY case_id",
    (job_id,),
).fetchall()
for row in rows:
    output = (row["stderr"] or row["stdout"] or "").strip().splitlines()
    print(row["case_id"], row["status"], " | ".join(output[-6:]))
