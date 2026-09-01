from collections import Counter

from web.portal_db import connect


modules = {
    "ANON_GAMES_": "Games",
    "ANON_HAM_": "Hamburger Menu",
    "ANON_ACCOUNT_": "Account Settings",
}
with connect() as db:
    rows = db.execute(
        """WITH ranked AS (
               SELECT case_id,status,job_id,
                      ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY id DESC) position
               FROM job_results
           ) SELECT case_id,status,job_id FROM ranked WHERE position=1"""
    ).fetchall()
for prefix, module in modules.items():
    selected = [row for row in rows if row["case_id"].startswith(prefix)]
    print(module, len(selected), dict(Counter(row["status"] for row in selected)),
          "latest_jobs", sorted({row["job_id"] for row in selected}))
