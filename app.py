import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, redirect, request, session, url_for

from web.routes.dashboard import dashboard_bp
from web.routes.suite import suite_bp
from web.routes.devices import devices_bp
from web.routes.settings import settings_bp
from web.routes.report import report_bp
from web.routes.auth import auth_bp
from web.routes.generator import generator_bp
from web.routes.jobs import jobs_bp
from web.routes.yaml_editor import yaml_editor_bp
from web.routes.app_memory import app_memory_bp
from web.routes.flow_workspace import flow_workspace_bp
from web.routes.testing_bot import testing_bot_bp
from web.routes.flows import flows_bp
from web.routes.user_profiles import user_profiles_bp
from web.routes.article_library import article_library_bp
from web.portal_db import init_db
from web.services.behavior_matrix_service import import_behavior_matrix, DEFAULT_MATRIX
from web.services.generation_service import resume_friday_reviews
from web.time_utils import portal_time

app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static"
)


# Secret key for flash messages
app.secret_key = os.getenv("PORTAL_SECRET_KEY", "development-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.jinja_env.filters["portal_time"] = portal_time


def start_local_maestro_agent():
    """Start the local queue worker with the portal; its file lock prevents duplicates."""
    enabled = os.getenv("AUTO_START_MAESTRO_AGENT", "1").strip().casefold()
    if enabled in {"0", "false", "no", "off"}:
        return None
    root = Path(__file__).resolve().parent
    stdout_handle = (root / "maestro_agent.log").open("a", encoding="utf-8")
    stderr_handle = (root / "maestro_agent_error.log").open("a", encoding="utf-8")
    kwargs = {
        "cwd": str(root), "stdout": stdout_handle, "stderr": stderr_handle,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.Popen([sys.executable, str(root / "maestro_agent.py")], **kwargs)
    finally:
        stdout_handle.close()
        stderr_handle.close()


@app.before_request
def require_portal_login():
    if request.endpoint in {"auth.login", "static"} or request.path.startswith("/api/agent/"):
        return None
    if not session.get("username"):
        return redirect(url_for("auth.login", next=request.path))

# Register Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(suite_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(report_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(generator_bp)
app.register_blueprint(jobs_bp)
app.register_blueprint(yaml_editor_bp)
app.register_blueprint(app_memory_bp)
app.register_blueprint(flow_workspace_bp)
app.register_blueprint(testing_bot_bp)
app.register_blueprint(flows_bp)
app.register_blueprint(user_profiles_bp)
app.register_blueprint(article_library_bp)
init_db()
if DEFAULT_MATRIX.is_file():
    import_behavior_matrix(DEFAULT_MATRIX)


@app.context_processor
def portal_preferences():
    theme = "light"
    username = session.get("username")
    if username:
        with __import__("web.portal_db", fromlist=["connect"]).connect() as db:
            row = db.execute(
                "SELECT value FROM portal_settings WHERE key=?",
                (f"portal_theme:{username}",),
            ).fetchone()
        if row and row["value"] in {"light", "dark"}:
            theme = row["value"]
    return {"portal_theme": theme}

if __name__ == "__main__":
    resume_friday_reviews()
    start_local_maestro_agent()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
