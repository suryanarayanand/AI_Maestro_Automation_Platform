import json
import subprocess
from collections import deque
from pathlib import Path

from web.portal_db import connect

ROOT = Path(__file__).resolve().parents[2]
HEALTH_LOG = ROOT / "Reports" / "Long_Run_Health.jsonl"


def _run_adb(*args, timeout=8):
    return subprocess.run(["adb", *args], capture_output=True, text=True,
                          timeout=timeout, check=False)


def get_device_status():
    """Return current ADB status without blocking the portal."""
    try:
        result = _run_adb("devices", "-l")
        devices = []
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return {"connected": bool(devices), "count": len(devices),
                "device_id": devices[0] if devices else "",
                "status": "Connected" if devices else "Disconnected"}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"connected": False, "count": 0, "device_id": "",
                "status": f"ADB error: {exc}"}


def get_health_history(limit=24):
    """Read recent half-hour samples, tolerating a partial final line."""
    if not HEALTH_LOG.exists():
        return []
    records = deque(maxlen=limit)
    try:
        with HEALTH_LOG.open("r", encoding="utf-8-sig", errors="replace") as stream:
            for line in stream:
                try:
                    records.append(json.loads(line))
                except (TypeError, json.JSONDecodeError):
                    continue
    except OSError:
        return []
    return list(records)


def get_device_health():
    history = get_health_history()
    latest = history[-1] if history else {}
    latest.setdefault("alerts", [])
    try:
        with connect() as db:
            row = db.execute(
                "SELECT id,suite,status,current_case,completed,total FROM jobs "
                "WHERE status IN ('running','cancel_requested') "
                "ORDER BY CASE status WHEN 'running' THEN 0 ELSE 1 END,id LIMIT 1"
            ).fetchone()
        latest["job"] = dict(row) if row else {}
    except Exception:
        latest.setdefault("job", {})
    latest["history_available"] = bool(history)
    return latest, list(reversed(history))
