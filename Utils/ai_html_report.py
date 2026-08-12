import json
from pathlib import Path


def _badge_class(status):
    return {
        "PASS": "status-pass",
        "FAIL": "status-fail",
        "NOT FOUND": "status-notfound",
        "ERROR": "status-error"
    }.get(status, "status-error")


def _esc(value):
    """Minimal HTML escaping for text pulled from the AI response."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate_ai_html_report(json_file, output_folder):
    """
    Generate the AI HTML report from AI_Report.json.

    Renders:
      1. Suite-level summary cards
      2. Scenario-level table (status + AI pass/fail counts)
      3. Detailed AI Findings — one card per analyzed screenshot, showing
         the image itself alongside status, confidence, severity, reason,
         issues, and Jira title/description. Includes a "failures only"
         toggle since a full suite run can produce many screenshots.
    """

    json_file = Path(json_file)
    output_folder = Path(output_folder)

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    suite = data["suite"]
    results = data["results"]

    total_ai_pass = sum(item.get("ai_pass", 0) for item in results)
    total_ai_fail = sum(item.get("ai_fail", 0) for item in results)
    total_ai_errors = sum(item.get("ai_errors", 0) for item in results)
    total_ai = total_ai_pass + total_ai_fail + total_ai_errors

    html = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<title>AI Automation Report</title>

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f6f9;
    margin: 30px;
}}

h1 {{
    color: #1f4e79;
}}

h2 {{
    color: #1f4e79;
    margin-top: 40px;
}}

.summary {{
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 30px;
}}

.card {{
    background: white;
    width: 180px;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
    text-align: center;
}}

.card h2 {{
    margin: 10px 0 0;
    font-size: 30px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
}}

th {{
    background: #1f4e79;
    color: white;
    padding: 12px;
}}

td {{
    padding: 10px;
    border-bottom: 1px solid #dddddd;
    text-align: center;
}}

tr:hover {{
    background: #f8f8f8;
}}

.scenario {{
    text-align: left;
    padding-left: 15px;
}}

.status-pass {{
    background: #28a745;
    color: white;
    padding: 5px 12px;
    border-radius: 5px;
    font-weight: bold;
}}

.status-fail {{
    background: #dc3545;
    color: white;
    padding: 5px 12px;
    border-radius: 5px;
    font-weight: bold;
}}

.status-notfound {{
    background: orange;
    color: white;
    padding: 5px 12px;
    border-radius: 5px;
    font-weight: bold;
}}

.status-error {{
    background: #6c757d;
    color: white;
    padding: 5px 12px;
    border-radius: 5px;
    font-weight: bold;
}}

.toolbar {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 15px 0;
}}

.toolbar label {{
    font-size: 15px;
    color: #333;
}}

.scenario-block {{
    margin-bottom: 25px;
}}

.scenario-block h3 {{
    color: #1f4e79;
    border-bottom: 2px solid #1f4e79;
    padding-bottom: 6px;
}}

.finding {{
    display: flex;
    gap: 20px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
    padding: 15px;
    margin-bottom: 15px;
}}

.finding-fail {{
    border-left: 6px solid #dc3545;
}}

.finding-pass {{
    border-left: 6px solid #28a745;
}}

.finding-error {{
    border-left: 6px solid #6c757d;
}}

.finding-image {{
    flex: 0 0 260px;
}}

.finding-image img {{
    width: 100%;
    border-radius: 6px;
    border: 1px solid #ddd;
    cursor: zoom-in;
}}

.finding-details {{
    flex: 1;
    min-width: 0;
}}

.finding-details p {{
    margin: 6px 0;
}}

.finding-details ul {{
    margin: 4px 0 10px 20px;
}}

.jira-box {{
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 8px;
}}

.footer {{
    margin-top: 30px;
    color: gray;
    text-align: center;
}}

#lightbox {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,.85);
    align-items: center;
    justify-content: center;
    z-index: 999;
    cursor: zoom-out;
}}

#lightbox img {{
    max-width: 90%;
    max-height: 90%;
    border-radius: 6px;
}}

</style>

</head>

<body>

<h1>Automation AI Report</h1>

<div class="summary">

<div class="card">
<h3>Total Tests</h3>
<h2>{suite["total"]}</h2>
</div>

<div class="card">
<h3>Passed</h3>
<h2 style="color:green;">{suite["passed"]}</h2>
</div>

<div class="card">
<h3>Failed</h3>
<h2 style="color:red;">{suite["failed"]}</h2>
</div>

<div class="card">
<h3>Not Found</h3>
<h2 style="color:orange;">{suite["not_found"]}</h2>
</div>

<div class="card">
<h3>Pass Rate</h3>
<h2>{suite["pass_rate"]}%</h2>
</div>

</div>

<h2>Scenario Results</h2>

<table>

<tr>

<th>Scenario ID</th>
<th>Module</th>
<th>Scenario</th>
<th>Status</th>
<th>Duration (sec)</th>
<th>AI Total</th>
<th>AI PASS</th>
<th>AI FAIL</th>

</tr>
"""

    for item in results:

        badge = "status-pass"

        if item["status"] == "FAIL":
            badge = "status-fail"

        elif item["status"] == "NOT FOUND":
            badge = "status-notfound"

        ai_total = item.get("ai_pass", 0) + item.get("ai_fail", 0) + item.get("ai_errors", 0)

        html += f"""
<tr>

<td>{_esc(item["id"])}</td>

<td>{_esc(item["module"])}</td>

<td class="scenario">{_esc(item["name"])}</td>

<td>
<span class="{badge}">
{item["status"]}
</span>
</td>

<td>{item["duration"]}</td>

<td>{ai_total}</td>

<td>{item.get("ai_pass",0)}</td>

<td>{item.get("ai_fail",0)}</td>

</tr>
"""

    html += """

</table>

<br>

<h2>AI Screenshot Summary</h2>

<div class="summary">
"""

    html += f"""
<div class="card">
<h3>Total Screenshots</h3>
<h2>{total_ai}</h2>
</div>

<div class="card">
<h3>AI PASS</h3>
<h2 style="color:green;">{total_ai_pass}</h2>
</div>

<div class="card">
<h3>AI FAIL</h3>
<h2 style="color:red;">{total_ai_fail}</h2>
</div>

<div class="card">
<h3>AI ERROR</h3>
<h2 style="color:#6c757d;">{total_ai_errors}</h2>
</div>

</div>
"""

    # =====================================================
    # Detailed AI Findings — image + reason for every screenshot
    # =====================================================

    html += """
<h2>Detailed AI Findings</h2>

<div class="toolbar">
    <input type="checkbox" id="failuresOnly" onchange="toggleFailuresOnly()">
    <label for="failuresOnly">Show failures only</label>
</div>
"""

    any_details = False

    for item in results:

        ai_details = item.get("ai_details", [])

        if not ai_details:
            continue

        any_details = True

        html += f'<div class="scenario-block"><h3>{_esc(item["id"])} &mdash; {_esc(item["name"])}</h3>'

        for shot in ai_details:

            status = shot.get("status", "ERROR")
            badge = _badge_class(status)
            row_class = {
                "PASS": "finding-pass",
                "FAIL": "finding-fail"
            }.get(status, "finding-error")

            issues = shot.get("issues", []) or []
            issues_html = "".join(f"<li>{_esc(i)}</li>" for i in issues)

            jira_title = shot.get("jira_title", "")
            jira_desc = shot.get("jira_description", "")
            jira_html = ""
            if jira_title and jira_title != "N/A":
                jira_html = f"""
                <div class="jira-box">
                    <p><strong>Jira Title:</strong> {_esc(jira_title)}</p>
                    <p><strong>Jira Description:</strong> {_esc(jira_desc)}</p>
                </div>
                """

            img_path = shot.get("image_path", "")

            html += f"""
<div class="finding {row_class}" data-status="{status}">
    <div class="finding-image">
        <img src="{img_path}" alt="{_esc(shot.get('image',''))}" onclick="openLightbox(this.src)">
    </div>
    <div class="finding-details">
        <span class="{badge}">{status}</span>
        <p><strong>Image:</strong> {_esc(shot.get("image", ""))}</p>
        <p><strong>Confidence:</strong> {_esc(shot.get("confidence", ""))}
           &nbsp;&nbsp; <strong>Severity:</strong> {_esc(shot.get("severity", ""))}</p>
        <p><strong>Reason:</strong> {_esc(shot.get("reason", ""))}</p>
        {"<p><strong>Issues:</strong></p><ul>" + issues_html + "</ul>" if issues_html else ""}
        {jira_html}
    </div>
</div>
"""

        html += "</div>"

    if not any_details:
        html += "<p>No screenshots were analyzed for this run.</p>"

    html += """
<div id="lightbox" onclick="this.style.display='none'">
    <img id="lightbox-img" src="">
</div>

<div class="footer">
Generated by Automation Framework with AI Visual Analysis
</div>

<script>
function toggleFailuresOnly() {
    var onlyFailures = document.getElementById('failuresOnly').checked;
    var findings = document.querySelectorAll('.finding');
    findings.forEach(function (el) {
        if (onlyFailures) {
            el.style.display = (el.getAttribute('data-status') === 'FAIL') ? 'flex' : 'none';
        } else {
            el.style.display = 'flex';
        }
    });
}

function openLightbox(src) {
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox').style.display = 'flex';
}
</script>

</body>

</html>
"""

    output_file = output_folder / "AI_Report.html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return output_file