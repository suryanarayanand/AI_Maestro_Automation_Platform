@echo off
title AI Maestro Automation Portal
cd /d D:\AI_Maestro_Automation_Platform

echo.
echo ==========================================
echo       AI MAESTRO AUTOMATION PORTAL
echo ==========================================
echo.
echo Portal: http://127.0.0.1:5000
echo Press Ctrl+C to stop the portal.
echo.

echo Starting Maestro execution agent...
powershell -NoProfile -Command "$agent = Get-CimInstance Win32_Process ^| Where-Object { $_.CommandLine -match 'maestro_agent\.py' }; if (-not $agent) { Start-Process -FilePath 'py' -ArgumentList 'maestro_agent.py' -WorkingDirectory '%CD%' -WindowStyle Hidden -RedirectStandardOutput '%CD%\maestro_agent.log' -RedirectStandardError '%CD%\maestro_agent_error.log' }"

py app.py

if errorlevel 1 (
    echo.
    echo Portal failed to start. Install dependencies with:
    echo py -m pip install -r requirements.txt
    pause
)
