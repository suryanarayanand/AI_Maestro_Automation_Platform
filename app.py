import os
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
from web.portal_db import init_db
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
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
