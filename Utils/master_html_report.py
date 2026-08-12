import json
from pathlib import Path


def generate_master_dashboard(json_file, output_folder):

    print("=" * 80)
    print("GENERATING MASTER DASHBOARD")
    print("=" * 80)

    json_file = Path(json_file)
    output_folder = Path(output_folder)

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    framework = data["framework"]
    execution = data["execution"]
    visual = data["visual"]
    ai = data["ai"]
    executions = data["executions"]

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>Automation Framework Dashboard</title>

<style>

body{{
    font-family:Segoe UI,Arial,sans-serif;
    background:#eef3f8;
    margin:30px;
}}

h1{{
    color:#154c79;
}}

.summary{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:20px;
    margin-top:30px;
}}

.card{{
    background:white;
    border-radius:15px;
    padding:25px;
    text-align:center;
    box-shadow:0 5px 15px rgba(0,0,0,.12);
}}

.card h3{{
    color:#666;
}}

.card h2{{
    color:#154c79;
    font-size:40px;
}}

table{{
    width:80%;
    margin:25px auto;
    border-collapse:collapse;
    margin-top:30px;
    background:white;
}}

th{{
    width:80%;
    border-collapse:collapse;
    margin-top:25px;
    background:white;
    font-size:13px;
}}

td{{
    padding:13px;
    border-bottom:1px solid #ddd;
}}

tr:hover{{
    background:#f5f5f5;
}}

.pass{{
    color:green;
    font-weight:bold;
}}

.fail{{
    color:red;
    font-weight:bold;
}}

</style>

</head>

<body>

<h1>Automation Framework Dashboard</h1>

<p>
Overall Automation Execution Summary
</p>
"""

    html += f"""

<div class="summary">

<div class="card">
<h3>Total Runs</h3>
<h2>{framework["total_runs"]}</h2>
</div>

<div class="card">
<h3>Passed Runs</h3>
<h2 style="color:green;">
{execution["passed_runs"]}
</h2>
</div>

<div class="card">
<h3>Failed Runs</h3>
<h2 style="color:red;">
{execution["failed_runs"]}
</h2>
</div>

<div class="card">
<h3>Pass Rate</h3>
<h2>
{execution["pass_rate"]}%
</h2>
</div>

</div>
"""
    html += f"""

<h2>Suite Summary</h2>

<div class="summary">

<div class="card">
<h3>Smoke</h3>
<h2>{framework["smoke_runs"]}</h2>
</div>

<div class="card">
<h3>Sanity</h3>
<h2>{framework["sanity_runs"]}</h2>
</div>

<div class="card">
<h3>Regression</h3>
<h2>{framework["regression_runs"]}</h2>
</div>

</div>
"""
    
    html += f"""

<h2>Visual Testing</h2>

<div class="summary">

<div class="card">
<h3>Total Images</h3>
<h2>{visual["total_images"]}</h2>
</div>

<div class="card">
<h3>Passed Images</h3>
<h2 style="color:green;">
{visual["passed_images"]}
</h2>
</div>

<div class="card">
<h3>Failed Images</h3>
<h2 style="color:red;">
{visual["failed_images"]}
</h2>
</div>

<div class="card">
<h3>AI Issues</h3>
<h2>
{ai["issues"]}
</h2>
</div>

</div>
"""
    
    html += """

<h2>Execution History</h2>

<table>

<tr>

<th>Execution</th>

<th>Suite</th>

<th>Status</th>

<th>Images</th>

<th>AI Issues</th>

</tr>

"""

    for run in executions:

        status_class = "pass" if run["status"] == "PASS" else "fail"

        html += f"""

<tr>

<td>{run["folder"]}</td>

<td>{run["suite"]}</td>

<td class="{status_class}">
{run["status"]}
</td>

<td>{run["images"]}</td>

<td>{run["ai_issues"]}</td>

</tr>

"""
        
    html += """

</table>

</body>

</html>

"""
    output = output_folder / "Master_Dashboard.html"

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    print("Master Dashboard Generated")

    return output

# =====================================================
# Run from Command Line
# =====================================================

if __name__ == "__main__":

    REPORT_FOLDER = (
        Path(__file__).resolve().parent.parent /
        "Reports"
    )

    JSON_FILE = REPORT_FOLDER / "Master_Report.json"

    generate_master_dashboard(
        JSON_FILE,
        REPORT_FOLDER
    )