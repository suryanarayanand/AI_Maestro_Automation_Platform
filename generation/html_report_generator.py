from html import escape
from pathlib import Path


class HTMLReportGenerator:
    def generate(self, report, output_file):
        rows = "".join(f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in report.items())
        document = f"<!doctype html><html><head><meta charset='utf-8'><title>QA Report</title></head><body><h1>QA Report</h1><table>{rows}</table></body></html>"
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document, encoding="utf-8")
        return path
