from pathlib import Path
from datetime import datetime


def generate_html_report(results, suite_name, execution_time, report_folder):

    report_folder = Path(report_folder)
    report_folder.mkdir(parents=True, exist_ok=True)

    total = len(results)
    passed = len([r for r in results if r["status"] == "PASS"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    not_found = len([r for r in results if r["status"] == "NOT FOUND"])

    pass_rate = 0

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

<p><b>Not Found :</b> {not_found}</p>

<p><b>Pass Rate :</b> {pass_rate}%</p>

<p><b>Execution Time :</b> {execution_time} sec</p>

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

    html += """

</table>

</div>

</body>

</html>

"""

    output = report_folder / "Dashboard.html"

    with open(output, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"\nHTML Report Generated : {output}")