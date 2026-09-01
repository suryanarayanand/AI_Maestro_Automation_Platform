import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.portal_db import connect


parser = argparse.ArgumentParser()
parser.add_argument("source", nargs="?", default="TH_App_Normalized_1397_Cases.xlsx")
SOURCE = parser.parse_args().source

with connect() as database:
    row = database.execute(
        "SELECT count(1) AS total, min(id) AS first_id, max(id) AS last_id "
        "FROM drafts WHERE source_file=? AND status='pending'",
        (SOURCE,),
    ).fetchone()
    print(dict(row))
    database.execute(
        "DELETE FROM drafts WHERE source_file=? AND status='pending'",
        (SOURCE,),
    )
    print("Removed partial pending drafts from the stopped oversized request.")
