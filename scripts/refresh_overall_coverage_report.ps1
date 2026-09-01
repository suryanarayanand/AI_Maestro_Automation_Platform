$ErrorActionPreference = "Stop"
Set-Location -LiteralPath "D:\AI_Maestro_Automation_Platform"
& "C:\Users\12503\AppData\Local\Python\pythoncore-3.14-64\python.exe" "scripts\generate_overall_coverage_report.py" --pdf
if ($LASTEXITCODE -ne 0) {
    throw "Overall coverage PDF generation failed with exit code $LASTEXITCODE"
}
