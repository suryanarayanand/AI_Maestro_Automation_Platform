import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from web.portal_db import connect

parser = argparse.ArgumentParser()
parser.add_argument("source")
arguments = parser.parse_args()

with connect() as database:
    rows = database.execute(
        "SELECT id,case_id,status,generation_mode,coverage_status,error "
        "FROM drafts WHERE source_file=? ORDER BY id",
        (arguments.source,),
    ).fetchall()
for row in rows:
    print(dict(row))
