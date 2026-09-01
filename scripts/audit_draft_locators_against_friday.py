import re

from web.portal_db import connect


SOURCE = "Anonymous_Games_Hamburger_Account_Settings_Approved_Test_Cases.xlsx"
ID_PATTERN = re.compile(r'\bid:\s*"([^"]+)"')
TEXT_PATTERN = re.compile(r'\btext:\s*"([^"]+)"')

with connect() as db:
    drafts = db.execute(
        "SELECT case_id,yaml FROM drafts WHERE source_file=? ORDER BY id", (SOURCE,)
    ).fetchall()
    memory = db.execute(
        "SELECT locator_type,locator_value,MAX(confidence) confidence "
        "FROM app_memory_elements GROUP BY locator_type,locator_value"
    ).fetchall()

known_ids = {row["locator_value"] for row in memory if row["locator_type"] == "id"}
known_text = {row["locator_value"] for row in memory if row["locator_type"] in {"text", "accessibilityText"}}
missing_ids, unobserved_text = {}, {}
for draft in drafts:
    yaml = draft["yaml"] or ""
    ids = sorted(set(ID_PATTERN.findall(yaml)) - known_ids)
    texts = []
    for pattern in set(TEXT_PATTERN.findall(yaml)):
        try:
            if not any(re.fullmatch(pattern, value, re.IGNORECASE) for value in known_text):
                texts.append(pattern)
        except re.error:
            texts.append(pattern)
    if ids:
        missing_ids[draft["case_id"]] = ids
    if texts:
        unobserved_text[draft["case_id"]] = sorted(texts)

print("drafts", len(drafts))
print("missing_ids", missing_ids)
print("unobserved_text_patterns", unobserved_text)
