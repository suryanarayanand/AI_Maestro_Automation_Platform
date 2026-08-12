import json
from pathlib import Path


def generate_master_report(report_root):
    """
    Reads every execution folder inside Reports/
    and creates Master_Report.json
    """

    report_root = Path(report_root)

    executions = []

    total_runs = 0
    smoke_runs = 0
    sanity_runs = 0
    regression_runs = 0

    passed_runs = 0
    failed_runs = 0

    total_images = 0
    passed_images = 0
    failed_images = 0

    total_ai_issues = 0

    # ---------------------------------------------
    # Scan every execution folder
    # ---------------------------------------------

    for folder in sorted(report_root.iterdir()):
        print(f"Checking: {folder.name}")
        if not folder.is_dir():
            continue
        print("Directory Found")

        ai_json = folder / "AI_Report.json"
        visual_json = folder / "Visual_Report.json"

        if not ai_json.exists():
            continue

        if not visual_json.exists():
            continue
        print("✓ Valid Execution Folder")

        total_runs += 1

        # -----------------------------------------
        # Read AI Report
        # -----------------------------------------

        with open(ai_json, "r", encoding="utf-8") as f:
            ai = json.load(f)

        # -----------------------------------------
        # Read Visual Report
        # -----------------------------------------

        with open(visual_json, "r", encoding="utf-8") as f:
            visual = json.load(f)

        suite_name = folder.name.split("_")[0]

        if suite_name.lower() == "smoke":
            smoke_runs += 1

        elif suite_name.lower() == "sanity":
            sanity_runs += 1

        elif suite_name.lower() == "regression":
            regression_runs += 1

        visual_pass = visual["suite"]["passed"]
        visual_fail = visual["suite"]["failed"]

        total_images += visual_pass + visual_fail
        passed_images += visual_pass
        failed_images += visual_fail

        ai_issues = 0

        for scenario in visual["results"]:

            for detail in scenario["details"]:

                ai_result = detail.get(
                    "ai_analysis",
                    {}
                )

                ai_issues += ai_result.get(
                    "issue_count",
                    0
                )

        total_ai_issues += ai_issues

        execution_status = "PASS" if ai["suite"]["failed"] == 0 else "FAIL"

        if execution_status == "PASS":
            passed_runs += 1
        else:
            failed_runs += 1

        executions.append({

            "folder": folder.name,

            "suite": suite_name,

            "status": execution_status,

            "images": visual_pass + visual_fail,

            "passed_images": visual_pass,

            "failed_images": visual_fail,

            "ai_issues": ai_issues

        })

    pass_rate = round(
        (passed_runs / total_runs) * 100,
        2
    ) if total_runs else 0

    summary = {

        "framework": {

            "total_runs": total_runs,

            "smoke_runs": smoke_runs,

            "sanity_runs": sanity_runs,

            "regression_runs": regression_runs

        },

        "execution": {

            "passed_runs": passed_runs,

            "failed_runs": failed_runs,

            "pass_rate": pass_rate

        },

        "visual": {

            "total_images": total_images,

            "passed_images": passed_images,

            "failed_images": failed_images

        },

        "ai": {

            "issues": total_ai_issues

        },

        "executions": executions

    }

    output = report_root / "Master_Report.json"

    with open(
        output,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\nMaster Report Generated")

    print(output)

    return output
# =====================================================
# Run from Command Line
# =====================================================



if __name__ == "__main__":

    REPORT_FOLDER = (
        Path(__file__).resolve().parent.parent /
        "Reports"
    )

    print("=" * 70)
    print("MASTER REPORT GENERATOR")
    print("=" * 70)
    print("Scanning:", REPORT_FOLDER)
    print()

    generate_master_report(REPORT_FOLDER)
