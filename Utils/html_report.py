from pathlib import Path
from datetime import datetime
import html
import re
import subprocess


def _app_metadata():
    data = {"app": "The Hindu", "package": "com.mobstac.thehindu"}
    try:
        device = subprocess.run(["adb", "devices"], capture_output=True, text=True,
                                timeout=5).stdout.splitlines()[1].split()[0]
        def adb(*args):
            return subprocess.run(["adb", "-s", device, *args], capture_output=True,
                                  text=True, timeout=8).stdout.strip()
        package = adb("shell", "dumpsys", "package", data["package"])
        data.update({"device": device, "model": adb("shell", "getprop", "ro.product.model"),
                     "android": adb("shell", "getprop", "ro.build.version.release"),
                     "version": (re.search(r"versionName=([^\s]+)", package) or [None, "Unknown"])[1],
                     "code": (re.search(r"versionCode=(\d+)", package) or [None, "Unknown"])[1]})
    except Exception:
        data.update({"device": "Unavailable", "model": "Unavailable", "android": "Unavailable",
                     "version": "Unknown", "code": "Unknown"})
    return data


def _execution_steps(result):
    text = "\n".join((result.get("stdout", ""), result.get("stderr", "")))
    pattern = re.compile(r"^\s*(.+?)\.\.\.\s*(COMPLETED|FAILED|SKIPPED)\s*$")
    return [(match.group(1).strip(), match.group(2)) for line in text.splitlines()
            if (match := pattern.match(line))]


def generate_html_report(results, suite_name, execution_time, report_folder):

    report_folder = Path(report_folder)
    report_folder.mkdir(parents=True, exist_ok=True)

    total = len(results)
    passed = len([r for r in results if r["status"] == "PASS"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    needs_review = len([r for r in results if r["status"] == "NEEDS_REVIEW"])
    needs_review = len([r for r in results if r["status"] == "NEEDS_REVIEW"])
    not_found = len([r for r in results if r["status"] == "NOT FOUND"])

    pass_rate = 0
    metadata = _app_metadata()

    if total > 0:
        pass_rate = round((passed / total) * 100, 2)

    html = f"""
<!DOCTYPE html>
<html>

<head>

<title>Automation Report</title>

<style>

body {{
    font-family: Arial;
    background:#f5f5f5;
    margin:40px;
}}

.container{{
    background:white;
    padding:30px;
    border-radius:10px;
}}

h1{{
    color:#0b5394;
}}

table{{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}}

th,td{{
    border:1px solid #ccc;
    padding:10px;
    text-align:left;
}}

th{{
    background:#0b5394;
    color:white;
}}

.pass{{
    color:green;
    font-weight:bold;
}}

.fail{{
    color:red;
    font-weight:bold;
}}

.notfound{{
    color:orange;
    font-weight:bold;
}}

.review{{
    color:#6847bd;
    font-weight:bold;
}}

.review{{
    color:#6847bd;
    font-weight:bold;
}}

.summary{{
    margin-top:20px;
    padding:15px;
    background:#eef5ff;
    border-radius:8px;
}}

</style>

</head>

<body>

<div class="container">

<h1>Automation Framework Report</h1>

<h2>{suite_name} Suite</h2>

<div class="summary">

<p><b>Date :</b> {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}</p>

<p><b>Total Tests :</b> {total}</p>

<p><b>Passed :</b> {passed}</p>

<p><b>Failed :</b> {failed}</p>

<p><b>Needs Review :</b> {needs_review}</p>

<p><b>Needs Review :</b> {needs_review}</p>

<p><b>Not Found :</b> {not_found}</p>

<p><b>Pass Rate :</b> {pass_rate}%</p>

<p><b>Execution Time :</b> {execution_time} sec</p>
<p><b>Application :</b> {metadata['app']} ({metadata['package']})</p>
<p><b>App Version :</b> {metadata['version']} / {metadata['code']}</p>
<p><b>Device :</b> {metadata['model']} · {metadata['device']} · Android {metadata['android']}</p>

</div>

<table>

<tr>

<th>ID</th>

<th>Module</th>

<th>Scenario</th>

<th>Status</th>

<th>Duration (sec)</th>

</tr>

"""

    for r in results:

        css = "pass"

        if r["status"] == "FAIL":
            css = "fail"

        elif r["status"] == "NEEDS_REVIEW":
            css = "review"

        elif r["status"] == "NEEDS_REVIEW":
            css = "review"

        elif r["status"] == "NOT FOUND":
            css = "notfound"

        html += f"""

<tr>

<td>{r['id']}</td>

<td>{r['module']}</td>

<td>{r['name']}</td>

<td class="{css}">{r['status']}</td>

<td>{r['duration']}</td>

</tr>

"""

    html += "</table><h2>Execution Steps</h2>"
    for r in results:
        # Keep every case compact by default; expand only on reviewer click.
        open_attr = ""
        summary_css = "pass" if r["status"] == "PASS" else "review" if r["status"] == "NEEDS_REVIEW" else "fail"
        html += f'<details{open_attr}><summary><b>{html_escape(r["id"])}</b> — {html_escape(r["name"])} — <span class="{summary_css}">{r["status"]}</span></summary>'
        html += '<table><tr><th>#</th><th>Execution step</th><th>Status</th></tr>'
        for number, (command, status) in enumerate(_execution_steps(r), 1):
            css = "pass" if status == "COMPLETED" else "fail" if status == "FAILED" else "notfound"
            html += f'<tr><td>{number}</td><td>{html_escape(command)}</td><td class="{css}">{status}</td></tr>'
        html += '</table></details>'

    html += """

</div>

</body>

</html>

"""

    output = report_folder / "Dashboard.html"

    with open(output, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"\nHTML Report Generated : {output}")


def html_escape(value):
    return html.escape(str(value or ""))
