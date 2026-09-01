"""Manage the local Git repository identity and private pull credential."""

import json
import os
import subprocess
import base64
from pathlib import Path
from urllib.parse import urlparse

from web.portal_db import connect


ROOT = Path(__file__).resolve().parents[2]
CREDENTIAL_FILE = ROOT / "repository_credentials.local.json"
ENV_FILE = ROOT / ".env"


def _git(*args):
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=5
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def validate_repository_url(value):
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Repository URL must be a valid HTTP or HTTPS URL.")
    if parsed.username or parsed.password:
        raise ValueError("Do not include credentials in the repository URL.")
    return value


def save_repository_configuration(repository_url, token=""):
    repository_url = validate_repository_url(repository_url)
    existing = _git("remote", "get-url", "origin")
    command = ("remote", "set-url", "origin", repository_url) if existing else (
        "remote", "add", "origin", repository_url
    )
    result = subprocess.run(
        ["git", *command], cwd=ROOT, capture_output=True, text=True, timeout=10
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Unable to configure Git origin.")
    if token.strip():
        CREDENTIAL_FILE.write_text(
            json.dumps({"token": token.strip()}), encoding="utf-8"
        )
    return sync_repository_metadata()


def has_repository_token():
    try:
        return bool(json.loads(CREDENTIAL_FILE.read_text(encoding="utf-8")).get("token"))
    except (OSError, json.JSONDecodeError):
        return False


def pull_repository():
    repository_url = _git("remote", "get-url", "origin")
    if not repository_url:
        raise ValueError("Configure a repository URL before pulling.")
    branch = _git("branch", "--show-current")
    if not branch:
        raise ValueError("The local repository is not on a named branch.")
    token = ""
    if CREDENTIAL_FILE.is_file():
        try:
            token = json.loads(CREDENTIAL_FILE.read_text(encoding="utf-8")).get("token", "")
        except json.JSONDecodeError as exc:
            raise ValueError("The saved repository credential is invalid.") from exc
    environment = os.environ.copy()
    if token:
        environment.update({
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Bearer {token}",
        })
    result = subprocess.run(
        ["git", "pull", "--ff-only", "origin", branch],
        cwd=ROOT, capture_output=True, text=True, timeout=180, env=environment,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "Git pull failed."
        raise ValueError(message.replace(token, "***") if token else message)
    return result.stdout.strip() or "Repository is already up to date."


def sync_repository_metadata():
    metadata = {
        "repository_link": _git("remote", "get-url", "origin"),
        "repository_branch": _git("branch", "--show-current"),
        "repository_commit": _git("rev-parse", "--short", "HEAD"),
    }
    with connect() as db:
        for key, value in metadata.items():
            db.execute(
                """INSERT INTO portal_settings(key,value,updated_at)
                   VALUES(?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET
                     value=excluded.value,
                     updated_at=CASE WHEN value<>excluded.value THEN CURRENT_TIMESTAMP ELSE updated_at END""",
                (key, value),
            )
    return metadata


def _local_environment():
    """Read the local ignored .env without exposing values through portal settings."""
    values = {}
    if not ENV_FILE.is_file():
        return values
    for raw in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def save_application_repository_configuration(repository_url, destination, token=""):
    """Persist application-source Git settings in the local ignored .env file."""
    repository_url = validate_repository_url(repository_url)
    destination = str(destination or "").strip()
    if not destination:
        raise ValueError("Choose a local application repository destination.")
    destination_path = Path(destination).resolve()
    if destination_path == destination_path.anchor or len(destination_path.parts) < 3:
        raise ValueError("Choose a specific local repository folder, not a drive root.")
    values = _local_environment()
    values["APP_REPOSITORY_URL"] = repository_url
    values["APP_REPOSITORY_PATH"] = str(destination_path)
    if token.strip():
        values["APP_REPOSITORY_TOKEN"] = token.strip()
    elif not values.get("APP_REPOSITORY_TOKEN"):
        values["APP_REPOSITORY_TOKEN"] = "PASTE_NEW_REPLACEMENT_TOKEN_HERE"
    preferred = ("APP_REPOSITORY_URL", "APP_REPOSITORY_TOKEN", "APP_REPOSITORY_PATH")
    lines = [f"{key}={values.pop(key)}" for key in preferred]
    lines.extend(f"{key}={value}" for key, value in values.items())
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return application_repository_status()


def application_repository_status():
    values = _local_environment()
    repository_url = values.get("APP_REPOSITORY_URL", "")
    destination_text = values.get("APP_REPOSITORY_PATH", "")
    destination = Path(destination_text) if destination_text else None
    is_repository = bool(destination and (destination / ".git").is_dir())
    metadata = {
        "repository_url": repository_url,
        "destination": destination_text,
        "token_configured": bool(
            values.get("APP_REPOSITORY_TOKEN", "")
            and values.get("APP_REPOSITORY_TOKEN") != "PASTE_NEW_REPLACEMENT_TOKEN_HERE"
        ),
        "exists": bool(destination and destination.exists()),
        "is_repository": is_repository,
        "branch": "",
        "commit": "",
    }
    if is_repository:
        for key, args in (
            ("branch", ("branch", "--show-current")),
            ("commit", ("rev-parse", "--short", "HEAD")),
        ):
            result = subprocess.run(
                ["git", "-c", f"safe.directory={destination.as_posix()}", "-C", str(destination), *args],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                metadata[key] = result.stdout.strip()
    return metadata


def sync_application_repository():
    """Clone or fast-forward pull the separate application source repository."""
    values = _local_environment()
    repository_url = validate_repository_url(values.get("APP_REPOSITORY_URL", ""))
    token = values.get("APP_REPOSITORY_TOKEN", "")
    destination_text = values.get("APP_REPOSITORY_PATH", "")
    if not token or token == "PASTE_NEW_REPLACEMENT_TOKEN_HERE":
        raise ValueError("Configure APP_REPOSITORY_TOKEN in .env before syncing.")
    if not destination_text:
        raise ValueError("Configure APP_REPOSITORY_PATH in .env before syncing.")
    destination = Path(destination_text).resolve()
    if destination == destination.anchor or len(destination.parts) < 3:
        raise ValueError("APP_REPOSITORY_PATH must be a specific local repository folder.")
    if destination.exists() and not (destination / ".git").is_dir():
        raise ValueError("The application repository destination exists but is not a Git repository.")

    basic = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    git_auth = ["git", "-c", f"http.extraHeader=Authorization: Basic {basic}"]
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        command = [*git_auth, "clone", repository_url, str(destination)]
    else:
        branch_result = subprocess.run(
            ["git", "-c", f"safe.directory={destination.as_posix()}", "-C", str(destination),
             "branch", "--show-current"], capture_output=True, text=True, timeout=10,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
        if not branch:
            raise ValueError("The application repository is not on a named branch.")
        command = [*git_auth, "-c", f"safe.directory={destination.as_posix()}", "-C",
                   str(destination), "pull", "--ff-only", "origin", branch]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "Application repository sync failed."
        raise ValueError(message.replace(token, "***").replace(basic, "***"))
    return result.stdout.strip() or result.stderr.strip() or "Application repository is already up to date."
