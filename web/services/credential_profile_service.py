"""Local test-account profiles; secrets never enter YAML, suites, or portal DB."""

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CREDENTIAL_FILE = ROOT / "credentials.local.json"
SUPPORTED = ("SUBSCRIBER", "REGISTERED", "EXPIRED")
LOGIN_METHODS = ("EMAIL_PASSWORD", "GOOGLE", "APPLE")


def _read():
    if not CREDENTIAL_FILE.is_file():
        return {"profiles": {}}
    try:
        value = json.loads(CREDENTIAL_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}}
    if "profiles" not in value:
        # Preserve the existing account as the Subscriber profile.
        value = {"profiles": {"SUBSCRIBER": {
            "email": value.get("email", ""), "password": value.get("password", "")
        }}}
    return value


def profile_status(state):
    state = str(state or "").upper()
    item = _read().get("profiles", {}).get(state, {})
    return {
        "state": state, "email": str(item.get("email") or ""),
        "configured": bool(item.get("email") and item.get("password")),
        "password_mask": "********" if item.get("password") else "",
        "login_method": item.get("login_method", "EMAIL_PASSWORD"),
        "google_email": str(item.get("google_email") or ""),
        "apple_email": str(item.get("apple_email") or ""),
    }


def save_profile(state, email, password="", login_method="EMAIL_PASSWORD",
                 google_email="", apple_email=""):
    state = str(state or "").upper()
    if state not in SUPPORTED:
        raise ValueError("Unsupported credential profile")
    login_method = str(login_method or "EMAIL_PASSWORD").upper()
    if login_method not in LOGIN_METHODS:
        raise ValueError("Unsupported login method")
    email = str(email or "").strip()
    if not email or "@" not in email:
        raise ValueError("Enter a valid test-account email address")
    value = _read()
    profiles = value.setdefault("profiles", {})
    current = profiles.get(state, {})
    password = str(password or "")
    if not password and not current.get("password"):
        raise ValueError("Enter a password when configuring this profile for the first time")
    profiles[state] = {
        "email": email, "password": password or current.get("password", ""),
        "login_method": login_method,
        "google_email": str(google_email or "").strip(),
        "apple_email": str(apple_email or "").strip(),
    }
    temporary = CREDENTIAL_FILE.with_suffix(".local.json.tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, CREDENTIAL_FILE)
    return profile_status(state)


def execution_credentials(state):
    state = str(state or "SUBSCRIBER").upper()
    item = _read().get("profiles", {}).get(state, {})
    return {"TEST_EMAIL": item.get("email"), "TEST_PASSWORD": item.get("password")}
