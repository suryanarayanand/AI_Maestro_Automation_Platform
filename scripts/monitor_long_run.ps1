param(
    [int]$IntervalSeconds = 1800,
    [string]$DeviceSerial = "R9ZY40T6PHN"
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$monitorLog = Join-Path $projectRoot "Reports\Long_Run_Health.jsonl"
$monitorPid = Join-Path $projectRoot ".runtime\long_run_monitor.pid"
$pythonExe = "C:\Users\12503\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$previousProgress = ""
$unchangedChecks = 0

New-Item -ItemType Directory -Path (Split-Path -Parent $monitorPid) -Force | Out-Null
Set-Content -LiteralPath $monitorPid -Value $PID -Encoding ascii

try {
    while ($true) {
        $timestamp = (Get-Date).ToString("o")
        $deviceState = ((& adb -s $DeviceSerial get-state 2>&1) -join " ").Trim()
        $battery = ((& adb -s $DeviceSerial shell dumpsys battery 2>&1) -join "`n")
        $level = if ($battery -match '(?m)^\s*level:\s*(\d+)') { [int]$Matches[1] } else { $null }
        $status = if ($battery -match '(?m)^\s*status:\s*(\d+)') { [int]$Matches[1] } else { $null }
        $temperature = if ($battery -match '(?m)^\s*temperature:\s*(\d+)') { [math]::Round(([int]$Matches[1]) / 10, 1) } else { $null }
        $acPowered = $battery -match '(?m)^\s*AC powered:\s*true'
        $usbPowered = $battery -match '(?m)^\s*USB powered:\s*true'
        $wirelessPowered = $battery -match '(?m)^\s*Wireless powered:\s*true'
        $internetOutput = ((& adb -s $DeviceSerial shell ping -c 1 -W 3 8.8.8.8 2>&1) -join "`n")
        $internetReachable = ($LASTEXITCODE -eq 0 -and $internetOutput -match '1 packets transmitted, 1 received|1 received')
        $agent = Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'python.exe' -and $_.CommandLine -match 'maestro_agent\.py'
        } | Select-Object -First 1
        $jobJson = & $pythonExe -c "import sqlite3,json; c=sqlite3.connect(r'$projectRoot\portal.db'); c.row_factory=sqlite3.Row; r=c.execute('''select id,suite,status,current_case,completed,total from jobs where status in ('running','queued') order by case status when 'running' then 0 else 1 end,id limit 1''').fetchone(); print(json.dumps(dict(r)) if r else '{}')"
        $job = $jobJson | ConvertFrom-Json
        $progress = "$($job.id)|$($job.status)|$($job.current_case)|$($job.completed)|$($job.total)"
        if ($job.status -eq 'running' -and $progress -eq $previousProgress) { $unchangedChecks++ } else { $unchangedChecks = 0 }
        $previousProgress = $progress

        $alerts = @()
        if ($deviceState -ne 'device') { $alerts += "DEVICE_OFFLINE" }
        if (-not $agent) { $alerts += "MAESTRO_AGENT_MISSING" }
        if ($null -ne $level -and $level -lt 25) { $alerts += "BATTERY_LOW" }
        if ($null -ne $temperature -and $temperature -ge 45) { $alerts += "DEVICE_HOT" }
        if ($unchangedChecks -ge 10) { $alerts += "JOB_PROGRESS_STALE_10_MIN" }
        if ($deviceState -eq 'device' -and -not $internetReachable) { $alerts += "DEVICE_INTERNET_OFFLINE" }

        [ordered]@{
            timestamp = $timestamp
            device_serial = $DeviceSerial
            device_state = $deviceState
            battery_level = $level
            battery_status = $status
            plugged = ($acPowered -or $usbPowered -or $wirelessPowered)
            ac_powered = $acPowered
            usb_powered = $usbPowered
            wireless_powered = $wirelessPowered
            internet_reachable = $internetReachable
            temperature_c = $temperature
            maestro_agent_pid = if ($agent) { $agent.ProcessId } else { $null }
            job = $job
            unchanged_checks = $unchangedChecks
            alerts = $alerts
        } | ConvertTo-Json -Depth 5 -Compress | Add-Content -LiteralPath $monitorLog -Encoding utf8

        Start-Sleep -Seconds $IntervalSeconds
    }
}
finally {
    Remove-Item -LiteralPath $monitorPid -Force -ErrorAction SilentlyContinue
}
