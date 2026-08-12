import json
import shutil
from pathlib import Path

import cv2

from Utils.image_compare import (
    prepare_images,
    compare_images
)
from Utils.visual_ai import ( 
    analyze_visual_difference
)
def analyze_visual_scenario(
    baseline_folder,
    actual_folder,
    execution_folder,
    test_id
):
    """
    Compare all screenshots of one scenario.
    """

    baseline_folder = Path(baseline_folder)
    actual_folder = Path(actual_folder)
    execution_folder = Path(execution_folder)

    comparison_folder = (
        execution_folder /
        "comparison" /
        test_id
    )

    comparison_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    details = []

    passed = 0
    failed = 0

    baseline_images = sorted(
        baseline_folder.rglob("*.png")
    )

    print(f"\nFound {len(baseline_images)} baseline images")

    for baseline_image in baseline_images:

        relative_path = baseline_image.relative_to(
            baseline_folder
        )

        actual_image = (
            actual_folder /
            relative_path
        )

        print("\nComparing")
        print("Baseline :", baseline_image)
        print("Actual   :", actual_image)

        if not actual_image.exists():

            print("Actual image not found.")

            details.append({
                "image": baseline_image.name,
                "status": "NOT FOUND",
                "similarity": 0,
                "threshold": 95.0,
                "difference_count": 0,
                "reference": str(baseline_image),
                "actual": "",
                "difference": "",
            })

            continue

        original_reference = cv2.imread(str(baseline_image))
        original_actual = cv2.imread(str(actual_image))
        reference_size = f"{original_reference.shape[1]}x{original_reference.shape[0]}"
        actual_size = f"{original_actual.shape[1]}x{original_actual.shape[0]}"
        normalized = original_reference.shape != original_actual.shape

        reference, actual = prepare_images(
            baseline_image,
            actual_image
        )

        result = compare_images(
            reference,
            actual
        )

        comparison_image_folder = (
            comparison_folder /
            relative_path.parent
        )

        comparison_image_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        reference_file = (
            comparison_image_folder /
            f"reference_{baseline_image.name}"
        )

        actual_file = (
           comparison_image_folder /
           f"actual_{baseline_image.name}"
        )

        diff_file = (
            comparison_image_folder /
            f"diff_{baseline_image.name}"
        )

        shutil.copy2(
            baseline_image,
            reference_file
        )

        shutil.copy2(
            actual_image,
            actual_file
        )


        cv2.imwrite(
            str(diff_file),
            result["comparison_image"]
        )
        relative_parent = relative_path.parent.as_posix()

        ai_result = analyze_visual_difference(
            reference_file,
            actual_file,
            diff_file,
            result["similarity"],
            result["difference_count"]
        )


        details.append({

            "image": baseline_image.name,

            "status": result["status"],

            "similarity": result["similarity"],

            "threshold": result["threshold"],

            "difference_count": result["difference_count"],

            "reference_size": reference_size,

            "actual_size": actual_size,

            "normalized": normalized,

            "reference":
                f"comparison/{test_id}/{relative_parent}/reference_{baseline_image.name}",

            "actual":
                f"comparison/{test_id}/{relative_parent}/actual_{baseline_image.name}",

            "difference":
                f"comparison/{test_id}/{relative_parent}/diff_{baseline_image.name}",

            "ai_analysis": ai_result

        })

        if result["status"] == "PASS":
            passed += 1
            print(f"PASS - {baseline_image.name}")
        else:
            failed += 1
            print(f"FAIL - {baseline_image.name}")

    return {

        "passed": passed,

        "failed": failed,

        "total": len(details),

        "details": details

    }


def save_visual_report(summary, execution_folder):
    """
    Save Visual_Report.json
    """

    execution_folder = Path(execution_folder)

    report_file = execution_folder / "Visual_Report.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(
            summary,
            f,
            indent=4,
            ensure_ascii=False
        )

    return report_file


def analyze_visual_execution(results, reference=None, actual=None):
    """
    Create suite level summary.
    """

    total = sum(r.get("total", 0) for r in results)

    passed = sum(r.get("passed", 0) for r in results)

    failed = sum(r.get("failed", 0) for r in results)

    pass_rate = round(
        (passed / total) * 100,
        2
    ) if total else 0

    return {

        "suite": {

            "total": total,

            "passed": passed,

            "failed": failed,

            "pass_rate": pass_rate

        },

        "reference": reference or {},

        "actual": actual or {},

        "results": results

    }
