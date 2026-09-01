from web.portal_db import connect


terms = ("game", "account", "hamburger", "login", "sudoku", "bookmark", "history", "appearance", "text size")
with connect() as db:
    screens = db.execute(
        "SELECT id,name,app_state,last_seen_at FROM app_memory_screens ORDER BY last_seen_at DESC"
    ).fetchall()
    elements = db.execute(
        "SELECT s.name screen,e.name,e.locator_type,e.locator_value,e.confidence,e.source "
        "FROM app_memory_elements e JOIN app_memory_screens s ON s.id=e.screen_id "
        "ORDER BY s.name,e.confidence DESC"
    ).fetchall()

for row in screens:
    if any(term in (row["name"] or "").lower() for term in terms):
        print("SCREEN", dict(row))
for row in elements:
    text = " ".join(str(row[key] or "") for key in row.keys()).lower()
    if any(term in text for term in terms):
        print("ELEMENT", dict(row))

print("FOCUSED GAMES:")
for row in elements:
    if row["screen"].startswith("games") and row["locator_type"] in {"id", "text", "accessibilityText"}:
        value = (row["locator_value"] or "").lower()
        if not any(noise in value for noise in ("status_bar", "notification", "battery", "wifi", "clock", "container")):
            print(dict(row))
