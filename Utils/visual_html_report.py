import json
from pathlib import Path


def _badge_class(status):
    return {
        "PASS": "status-pass",
        "FAIL": "status-fail",
        "NOT FOUND": "status-notfound"
    }.get(status, "status-fail")

print(__file__)
print("VISUAL HTML REPORT VERSION 2")

def generate_visual_html_report(json_file, output_folder):

    print("=" * 80)
    print("USING VISUAL HTML REPORT")
    print("=" * 80)
    print("Running file:", __file__)
    json_file = Path(json_file)
    output_folder = Path(output_folder)

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    suite = data["suite"]
    results = data["results"]
    reference_meta = data.get("reference", {})
    actual_meta = data.get("actual", {})

    def device_label(meta):
        return " | ".join(filter(None, [
            meta.get("role"), meta.get("manufacturer"), meta.get("model"),
            f'Android {meta.get("android")}' if meta.get("android") else "",
            f'App {meta.get("version_name")}' if meta.get("version_name") else "",
            meta.get("resolution"), meta.get("density"),
        ])) or "Device metadata unavailable"

    reference_label = device_label(reference_meta)
    actual_label = device_label(actual_meta)

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>Visual Regression Report</title>

<style>

/* =====================================================
   GLOBAL
===================================================== */

body{{
    font-family:Segoe UI,Arial,sans-serif;
    background:#eef3f8;
    margin:30px;
    color:#222;
}}

h1{{
    color:#154c79;
    margin-bottom:8px;
}}

h2{{
    color:#1f4e79;
}}

h3{{
    color:#285f8f;
}}

/* =====================================================
   SUMMARY
===================================================== */

.summary{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:25px;
    margin-top:25px;
    margin-bottom:40px;
}}

.card{{
    background:white;
    border-radius:15px;
    padding:25px;
    text-align:center;
    box-shadow:0 6px 18px rgba(0,0,0,.08);
    transition:.25s;
}}

.card:hover{{
    transform:translateY(-4px);
}}

.card h2{{
    margin-top:15px;
    font-size:42px;
    color:#154c79;
    font-weight:700;
}}

.card h3{{
    color:#777;
    font-size:18px;
    margin:0;
}}

/* =====================================================
   STATUS
===================================================== */

.status-pass{{
    background:#28a745;
    color:white;
    padding:7px 16px;
    border-radius:25px;
    font-weight:bold;
}}

.status-fail{{
    background:#dc3545;
    color:white;
    padding:7px 16px;
    border-radius:25px;
    font-weight:bold;
}}

.status-review{{
    background:#ff9800;
    color:white;
    padding:7px 16px;
    border-radius:25px;
    font-weight:bold;
}}

.status-notfound{{
    background:#6c757d;
    color:white;
    padding:7px 16px;
    border-radius:25px;
    font-weight:bold;
}}

/* =====================================================
   RESULT CARD
===================================================== */

.result-card{{
    background:white;
    margin-top:35px;
    border-radius:15px;
    padding:25px;
    box-shadow:0 5px 18px rgba(0,0,0,.08);
}}

/* =====================================================
   INFO GRID
===================================================== */

.info-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:18px;
    margin-top:20px;
}}

.info{{
    background:#f7f9fc;
    border-radius:10px;
    padding:15px;
}}

/* =====================================================
   AI
===================================================== */

.ai-card{{
    margin-top:25px;
    padding:20px;
    background:#f4f9ff;
    border-left:6px solid #0078d4;
    border-radius:10px;
}}

.ai-summary{{
    margin-top:15px;
    line-height:1.7;
}}

/* =====================================================
   ISSUE CARD
===================================================== */

.issue{{
    margin-top:15px;
    padding:18px;
    background:white;
    border-left:6px solid #dc3545;
    border-radius:8px;
    box-shadow:0 2px 8px rgba(0,0,0,.08);
}}

.issue:hover{{
    transform:translateY(-2px);
    transition:.2s;
}}

/* =====================================================
   IMAGES
===================================================== */

.images{{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:20px;
    margin-top:25px;
}}

.image-box{{
    text-align:center;
}}

.image-box img{{
    width:100%;
    height:auto;
    border-radius:10px;
    border:2px solid #ddd;
    cursor:pointer;
    transition:.25s;
    box-shadow:0 3px 12px rgba(0,0,0,.08);
}}

.image-box img:hover{{
    transform:scale(1.02);
}}

hr{{
    border:none;
    height:1px;
    background:#d9d9d9;
    margin:25px 0;
}}

table{{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}}

th{{
    background:#154c79;
    color:white;
    padding:12px;
}}

td{{
    padding:12px;
    border-bottom:1px solid #ddd;
}}

tr:hover{{
    background:#f5f5f5;
}}

/* =====================================================
   LIGHTBOX
===================================================== */

#lightbox{{
    display:none;
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:rgba(0,0,0,.9);
    justify-content:center;
    align-items:center;
    z-index:9999;
}}

#lightbox img{{
    max-width:92%;
    max-height:92%;
}}

/* =====================================================
   FOOTER
===================================================== */

.footer{{
    margin-top:50px;
    text-align:center;
    color:#777;
}}

</style>


</head>

<body>

<h1>Visual Regression Report</h1>

<p style="color:#666;font-size:18px;">
AI Powered Visual Regression Dashboard
</p>

<div class="info-grid">
<div class="info"><strong>Reference</strong><br>{reference_label}</div>
<div class="info"><strong>Actual</strong><br>{actual_label}</div>
</div>

<div class="summary">

<div class="card">
<h3>Total</h3>
<h2>{suite["total"]}</h2>
</div>

<div class="card">
<h3>Passed</h3>
<h2 style="color:green">{suite["passed"]}</h2>
</div>

<div class="card">
<h3>Failed</h3>
<h2 style="color:red">{suite["failed"]}</h2>
</div>

<div class="card">
<h3>Pass Rate</h3>
<h2>{suite["pass_rate"]}%</h2>
</div>

</div>

<h2>Comparison Details</h2>
"""
    for scenario in results:

        html += f"""
<h2>{scenario["scenario"]}</h2>
"""

        for detail in scenario["details"]:

            badge = _badge_class(detail["status"])
            ai = detail.get("ai_analysis", {})

            overall_status = ai.get("overall_status", "N/A")
            issue_count = ai.get("issue_count", 0)
            summary = ai.get("summary", "No AI analysis available.")
            issues = ai.get("issues", [])
            html += f"""

<div class="result-card">

<p><strong>Image :</strong> {detail["image"]}</p>

<p>
<strong>Status :</strong>
<span class="{badge}">
{detail["status"]}
</span>
</p>

<p><strong>Similarity :</strong> {detail["similarity"]}%</p>

<p><strong>Threshold :</strong> {detail["threshold"]}%</p>


<p><strong>Difference Count :</strong> {detail["difference_count"]}</p>

<p><strong>Image Size :</strong> Reference {detail.get("reference_size", "N/A")} | Actual {detail.get("actual_size", "N/A")}</p>

<p><strong>Cross-device Normalization :</strong> {"Applied" if detail.get("normalized") else "Not required"}</p>

<hr>

<h3>🤖 AI Visual Analysis</h3>

<p>
<strong>Overall Status :</strong>
<b>{overall_status}</b>
</p>

<p>
<strong>Issues Found :</strong>
{issue_count}
</p>

<p>
<strong>Summary :</strong><br>
{summary}
</p>

"""

            for issue in issues:

                html += f"""

<div style="background:#f8f9fa;
padding:15px;
margin-bottom:15px;
border-left:5px solid #dc3545;
border-radius:6px;">

<h4>{issue["title"]}</h4>

<p>
<b>Severity :</b>
{issue["severity"]}
</p>

<p>
<b>Component :</b>
{issue["component"]}
</p>

<p>
<b>Description :</b><br>
{issue["description"]}
</p>

<p>
<b>Recommendation :</b><br>
{issue["recommendation"]}
</p>

</div>

"""

            html += f"""

<div class="images">

<div class="image-box">
<h3>Production Reference</h3>
<img src="{detail['reference']}" onclick="openImage(this.src)">
</div>

<div class="image-box">
<h3>Internal Test Actual</h3>
<img src="{detail['actual']}" onclick="openImage(this.src)">
</div>

<div class="image-box">
<h3>Visual Difference</h3>
<img src="{detail['difference']}" onclick="openImage(this.src)">
</div>

</div>

</div>

"""

    html += """
<div id="lightbox" onclick="closeImage()">
    <img id="lightbox-image">
</div>

<div class="footer">
Generated by Automation Framework - Visual Regression
</div>

<script>

function openImage(src){

    document.getElementById("lightbox-image").src = src;
    document.getElementById("lightbox").style.display = "flex";

}

function closeImage(){

    document.getElementById("lightbox").style.display = "none";

}

</script>

</body>

</html>
"""


    output_file = output_folder / "Visual_Report.html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return output_file
