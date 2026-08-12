import json
from pathlib import Path


def generate_bug_summary_html(json_file, output_folder):

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = f"""
<!DOCTYPE html>
<html>
{build_head()}
<body>

<div class="container">

    {build_header(data)}

    {build_summary_cards(data)}

    {build_ai_synthesis(data)}

    {build_bug_cards(data)}

</div>

</body>
</html>
"""

    output = Path(output_folder) / "Bug_Summary.html"

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    return output
def build_head():

    return """
<head>

<title>Bug Investigation Dashboard</title>

<style>
.bug-card{

    background:white;

    margin-top:25px;

    border-radius:12px;

    padding:25px;

    box-shadow:0 5px 15px rgba(0,0,0,.1);

}

.bug-header{

    display:flex;

    justify-content:space-between;

    align-items:center;

}

.bug-body{

    display:flex;

    gap:30px;

    margin-top:20px;

    margin-bottom:20px;

}

.info{

    min-width:140px;

}

.severity{

    padding:10px 18px;

    border-radius:30px;

    color:white;

    font-weight:bold;

}

.major{

    background:#f59e0b;

}

.critical{

    background:#dc2626;

}

.minor{

    background:#16a34a;

}
.screenshot-section{

    margin-top:25px;

}

.bug-image{

    width:350px;

    max-width:100%;

    border-radius:10px;

    border:1px solid #ddd;

    cursor:pointer;

    transition:.3s;

}

.bug-image:hover{

    transform:scale(1.02);

    box-shadow:0 5px 20px rgba(0,0,0,.2);

}

.gallery{

    display:flex;

    flex-wrap:wrap;

    gap:12px;

    margin-top:15px;

}

.gallery-image{

    width:180px;

    border-radius:8px;

    border:1px solid #ddd;

    cursor:pointer;

    transition:.3s;

}

.gallery-image:hover{

    transform:scale(1.05);

}
body{
    margin:0;
    padding:0;
    background:#f5f7fb;
    font-family:Segoe UI,Arial,sans-serif;
}

.container{
    width:95%;
    margin:auto;
    padding:20px;
}

.header{
    background:#1f2937;
    color:white;
    padding:20px;
    border-radius:10px;
    margin-bottom:20px;
}

.cards{
    display:flex;
    gap:20px;
    flex-wrap:wrap;
    margin-bottom:30px;
}

.card{
    background:white;
    width:180px;
    padding:20px;
    border-radius:10px;
    box-shadow:0 2px 10px rgba(0,0,0,0.1);
    text-align:center;
}

.card h2{
    margin:0;
    font-size:36px;
}

.card p{
    color:#666;
}

</style>

</head>
"""

def build_header(data):

    return f"""
<div class="header">

<h1>🐞 Bug Investigation Dashboard</h1>

<p>

<b>Suite:</b> {data["suite"]}

&nbsp;&nbsp;&nbsp;

<b>Execution:</b> {data["execution_time"]:.2f} sec

</p>

</div>
"""

def build_summary_cards(data):

    summary = data["summary"]

    return f"""
<div class="cards">

<div class="card">
<h2>{summary["total"]}</h2>
<p>Total</p>
</div>

<div class="card">
<h2>{summary["failed"]}</h2>
<p>Failed</p>
</div>

<div class="card">
<h2>{summary["critical"]}</h2>
<p>Critical</p>
</div>

<div class="card">
<h2>{summary["major"]}</h2>
<p>Major</p>
</div>

<div class="card">
<h2>{summary["minor"]}</h2>
<p>Minor</p>
</div>

</div>
"""


def build_ai_synthesis(data):
    synthesis = data.get("ai_synthesis", {})
    risks = "".join(f"<li>{risk}</li>" for risk in synthesis.get("top_risks", []))
    devices = data.get("device_comparison", {})
    reference = devices.get("reference", {})
    actual = devices.get("actual", {})
    return f"""
<div class="bug-card">
<h2>Combined AI Assessment</h2>
<p><b>Executive summary</b><br>{synthesis.get('executive_summary', 'Unavailable')}</p>
<p><b>Release recommendation</b><br>{synthesis.get('release_recommendation', 'Review required')}</p>
<ul>{risks}</ul><hr>
<p><b>Reference:</b> {reference.get('manufacturer', '')} {reference.get('model', '')} — App {reference.get('version_name', 'unknown')}</p>
<p><b>Actual:</b> {actual.get('manufacturer', '')} {actual.get('model', '')} — App {actual.get('version_name', 'unknown')}</p>
</div>
"""


def build_bug_cards(data):

    html = "<h2>Combined Findings</h2>"

    for bug in data["bugs"]:

        severity_class = bug["severity"].lower()

        html += f"""

<div class="bug-card">

    <div class="bug-header">

        <div>

            <h2>{bug["bug_id"]}</h2>

            <h3>{bug["scenario_id"]}</h3>

            <p>{bug["scenario_name"]}</p>

        </div>

        <div class="severity {severity_class}">
            {bug["severity"]}
        </div>

    </div>

    <div class="bug-body">

        <div class="info">

            <b>Status</b><br>
            {bug["status"]}
            <br><small>Run: {bug.get("execution_status", "N/A")}</small>

        </div>

        <div class="info">

            <b>Type</b><br>
            {bug["bug_type"]}

        </div>

        <div class="info">

            <b>Confidence</b><br>
            {bug["confidence"]}%

        </div>

        <div class="info">

            <b>Execution</b><br>
            {bug["execution_time"]} sec

        </div>

    </div>

    <hr>

    <p>

    <b>Reason</b><br>

    {bug["reason"]}

    </p>

    <p>

    <b>Recommendation</b><br>

    {bug["recommendation"]}

    </p>

    <p><b>Evidence sources</b><br>{', '.join(bug.get('sources', []))}</p>

    <p><b>Screenshot AI findings</b><br>{'<br>'.join(item.get('reason', '') for item in bug.get('ai_findings', [])) or 'None'}</p>

    <p><b>Visual findings</b><br>{'<br>'.join(item.get('summary', '') for item in bug.get('visual_findings', [])) or 'None'}</p>


"""


        # Screenshot Section
        if bug.get("screenshots"):

            html += """
<div class="screenshot-section">

<h3>📷 Screenshots</h3>

<div class="gallery">
"""

            for image in bug.get("screenshots", []):

                html += f"""
<img
    src="{image}"
    class="gallery-image"
    onclick="window.open('{image}','_blank')">
"""

            html += """
</div>
</div>
"""
        else:
            html += """
<div class="screenshot-section">
<h3>Screenshot evidence</h3>
<p>No screenshot was captured before this failure.</p>
</div>
"""

        if bug.get("comparison_images"):
            html += '<div class="screenshot-section"><h3>Reference / Actual / Difference</h3><div class="gallery">'
            for image in bug["comparison_images"]:
                html += f'<img src="{image}" class="gallery-image" onclick="window.open(\'{image}\',\'_blank\')">'
            html += "</div></div>"

        # Close the bug card
        html += """
</div>
"""

    return html      

  


