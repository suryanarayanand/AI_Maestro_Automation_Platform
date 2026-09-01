import sys

from web.portal_db import connect


pattern = sys.argv[1] if len(sys.argv) > 1 else "%"
with connect() as db:
    rows = db.execute(
        "SELECT s.name screen,e.name,e.locator_type,e.locator_value,e.confidence,e.source "
        "FROM app_memory_elements e JOIN app_memory_screens s ON s.id=e.screen_id "
        "WHERE s.name LIKE ? AND e.locator_type IN ('id','text','accessibilityText') "
        "ORDER BY s.name,e.confidence DESC", (pattern,)
    ).fetchall()
for row in rows:
    value = (row["locator_value"] or "").lower()
    if not any(noise in value for noise in (
        "status_bar", "notification_icon", "battery", "wifi", "clock", "container",
        "signal", "2:", "android system", "businessline notification",
    )):
        print(dict(row))
