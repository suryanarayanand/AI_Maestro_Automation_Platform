from web.services.result_validation_service import excel_condition_verdict

from fix_needs_review_traceability import EVIDENCE, WORKBOOKS


for case_id in EVIDENCE:
    verdict = excel_condition_verdict(case_id, "PASS")
    print(case_id, verdict[0], verdict[1])
    assert verdict[0] == "PASS", verdict

for workbook in WORKBOOKS:
    assert workbook.exists() and workbook.stat().st_size > 0, workbook

print("Validation complete")
