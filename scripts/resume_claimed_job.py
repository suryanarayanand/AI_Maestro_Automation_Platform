import argparse

from web.portal_db import connect


parser = argparse.ArgumentParser()
parser.add_argument("job_id", type=int)
args = parser.parse_args()
with connect() as db:
    row = db.execute("SELECT status,completed,total FROM jobs WHERE id=?", (args.job_id,)).fetchone()
    if not row:
        raise SystemExit("job not found")
    if row["status"] not in {"running", "cancel_requested"} or row["completed"]:
        raise SystemExit(f"job is not safely resumable: {dict(row)}")
    db.execute(
        "UPDATE jobs SET status='queued',current_case=NULL,started_at=NULL,agent=NULL WHERE id=?",
        (args.job_id,),
    )
print({"job_id": args.job_id, "status": "queued", "reason": "agent failed before first case"})
