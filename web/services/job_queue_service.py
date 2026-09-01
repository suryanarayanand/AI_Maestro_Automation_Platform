"""Create deterministic, sequential execution jobs in bounded batches."""

import math

from web.portal_db import connect


def configured_batch_size(db=None):
    owns_connection = db is None
    connection = db or connect()
    try:
        row = connection.execute(
            "SELECT value FROM portal_settings WHERE key='execution_batch_size'"
        ).fetchone()
        return max(1, min(100, int(row["value"] if row else 10)))
    finally:
        if owns_connection:
            connection.close()


def create_batched_jobs(suite, tests, mode="queue"):
    if mode not in {"queue", "run-now"}:
        raise ValueError("Invalid execution mode.")
    with connect() as db:
        batch_size = configured_batch_size(db)
        batch_count = max(1, math.ceil(len(tests) / batch_size))
        top_priority = db.execute(
            "SELECT COALESCE(MAX(priority), 0) FROM jobs WHERE status='queued'"
        ).fetchone()[0] + batch_count
        ids = []
        for index in range(batch_count):
            start = index * batch_size
            total = len(tests[start:start + batch_size])
            priority = top_priority - index if mode == "run-now" else 0
            cursor = db.execute(
                """INSERT INTO jobs(
                       suite,total,priority,request_mode,batch_start,batch_number,batch_count
                   ) VALUES(?,?,?,?,?,?,?)""",
                (suite, total, priority, "run_now" if mode == "run-now" else "queue",
                 start, index + 1, batch_count),
            )
            ids.append(cursor.lastrowid)
    return ids
