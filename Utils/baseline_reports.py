import html
import json
import shutil
from pathlib import Path


def generate_baseline_reports(results, suite_name, execution_time, execution_folder, baseline_root, metadata=None):
    execution_folder = Path(execution_folder)
    baseline_root = Path(baseline_root)
    baseline_root.mkdir(parents=True, exist_ok=True)
    if metadata:
        (baseline_root / "baseline_metadata.json").write_text(
            json.dumps(metadata, indent=4), encoding="utf-8"
        )

    execution_rows = []
    screenshot_rows = []
    for result in results:
        execution_rows.append({
            "id": result["id"],
            "name": result["name"],
            "status": result["status"],
            "duration": result["duration"],
        })

        saved = []
        if result["status"] == "PASS":
            for relative in result.get("screenshots", []):
                source = execution_folder / relative
                if not source.is_file():
                    continue
                destination = baseline_root / result["id"] / source.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                saved.append(destination.name)
        screenshot_status = (
            "NOT_SAVED_FAILED"
            if result["status"] != "PASS"
            else ("CAPTURED" if saved else "MISSING")
        )
        screenshot_rows.append({
            "id": result["id"],
            "name": result["name"],
            "status": screenshot_status,
            "count": len(saved),
            "files": saved,
        })

    execution_data = {
        "suite": suite_name,
        "execution_time": execution_time,
        "passed": sum(row["status"] == "PASS" for row in execution_rows),
        "failed": sum(row["status"] != "PASS" for row in execution_rows),
        "tests": execution_rows,
    }
    screenshot_data = {
        "suite": suite_name,
        "captured": sum(row["status"] == "CAPTURED" for row in screenshot_rows),
        "missing": sum(row["status"] == "MISSING" for row in screenshot_rows),
        "not_saved_failed": sum(
            row["status"] == "NOT_SAVED_FAILED" for row in screenshot_rows
        ),
        "tests": screenshot_rows,
    }

    _write_report(execution_folder, "Execution_Report", "YAML Execution Report", execution_data, execution_rows)
    _write_report(execution_folder, "Screenshot_Report", "Baseline Screenshot Report", screenshot_data, screenshot_rows)


def _write_report(folder, stem, title, data, rows):
    (folder / f"{stem}.json").write_text(json.dumps(data, indent=4), encoding="utf-8")
    body = []
    for row in rows:
        status = row["status"]
        detail = (
            f'{row.get("duration", 0)} sec'
            if "duration" in row
            else f'{row.get("count", 0)} screenshot(s)'
        )
        body.append(
            "<tr>"
            f'<td>{html.escape(str(row["id"]))}</td>'
            f'<td>{html.escape(str(row["name"]))}</td>'
            f'<td class="{status.lower()}">{html.escape(status)}</td>'
            f'<td>{html.escape(detail)}</td>'
            "</tr>"
        )
    document = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:Segoe UI,Arial;background:#f4f6fa;padding:30px}}main{{background:white;padding:24px;border-radius:12px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}.pass,.captured{{color:#16803c;font-weight:bold}}.fail,.cancelled,.missing{{color:#c62828;font-weight:bold}}</style>
</head><body><main><h1>{title}</h1><p>Suite: {html.escape(str(data['suite']))}</p>
<table><thead><tr><th>Case</th><th>Name</th><th>Status</th><th>Details</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></main></body></html>"""
    (folder / f"{stem}.html").write_text(document, encoding="utf-8")
