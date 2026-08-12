"""UTC storage and portal-local timestamp formatting helpers."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


PORTAL_TIMEZONE = ZoneInfo(os.getenv("PORTAL_TIMEZONE", "Asia/Kolkata"))


def utc_now_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def portal_time(value, format_string="%d %b %Y, %I:%M:%S %p"):
    """Interpret database values as UTC and render them in portal local time."""
    if not value:
        return "-"
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(PORTAL_TIMEZONE).strftime(format_string)
