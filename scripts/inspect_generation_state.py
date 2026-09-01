from collections import Counter

from web.portal_db import connect


with connect() as db:
    rows = db.execute(
        "SELECT id, case_id, source_file, status, error, created_at "
        "FROM drafts ORDER BY id DESC LIMIT 5000"
    ).fetchall()

sources = {}
for row in rows:
    sources.setdefault(row["source_file"], []).append(row)

for source, items in list(sources.items())[:8]:
    statuses = Counter(item["status"] for item in items)
    errors = sum(bool(item["error"]) for item in items)
    print(source, len(items), dict(statuses), "errors=", errors,
          "latest=", items[0]["created_at"], "last_id=", items[0]["id"])

latest_source = next(iter(sources), None)
if latest_source:
    print("ERROR DETAILS:")
    for item in reversed(sources[latest_source]):
        if item["error"]:
            print(item["case_id"], "::", item["error"].replace("\n", " ")[:500])
