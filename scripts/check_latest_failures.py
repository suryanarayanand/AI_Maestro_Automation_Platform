import sqlite3

db = sqlite3.connect("portal.db")
db.row_factory = sqlite3.Row
print("JOBS")
for row in db.execute(
    "select id,status,current_case,completed,total "
    "from jobs where id in (269,271) order by id"
):
    print(dict(row))
print("LATEST")
for row in db.execute(
    "select id,suite,status,current_case,completed,total from jobs "
    "where id>=269 order by id desc limit 10"
):
    print(dict(row))
print("TRENDING FAILURES")
for row in db.execute(
    "select r.job_id,r.case_id,r.status,r.execution_status,r.condition_status "
    "from job_results r join jobs j on j.id=r.job_id "
    "where r.case_id like 'ANON_TREND_%' and r.status in ('FAIL','CANCELLED') "
    "order by r.id desc limit 30"
):
    print(dict(row))
print("NONPASS")
for row in db.execute(
    "select job_id,case_id,status,execution_status,condition_status,"
    "round(duration,1) duration from job_results "
    "where job_id in (269,271) and upper(coalesce(status,'')) != 'PASS' "
    "order by job_id,id"
):
    print(dict(row))
