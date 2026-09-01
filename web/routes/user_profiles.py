from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from web.services.scenario_service import get_suite_editor
from web.services.credential_profile_service import profile_status, save_profile

user_profiles_bp = Blueprint("user_profiles", __name__)

PROFILE_DEFINITIONS = [
    {"key":"ANONYMOUS","suite_key":"user_anonymous","name":"Anonymous","icon":"A","tone":"anonymous","description":"Ads, Subscribe prompts, and login gates are expected.","setup":"Ready"},
    {"key":"SUBSCRIBER","suite_key":"user_subscriber","name":"Active Subscriber","icon":"S","tone":"subscriber","description":"Premium access, entitled AI Summary, Bookmark, and Comment flows.","setup":"Config credentials"},
    {"key":"REGISTERED","suite_key":"user_registered","name":"Registered Free User","icon":"R","tone":"registered","description":"Signed-in free access with paywalls and account-enabled interactions.","setup":"Waiting for credentials"},
    {"key":"EXPIRED","suite_key":"user_expired","name":"Expired Subscriber","icon":"E","tone":"expired","description":"Renewal prompts and restricted Premium access after entitlement expiry.","setup":"Not configured"},
]

@user_profiles_bp.route("/user-profiles")
def index():
    profiles = []
    for definition in PROFILE_DEFINITIONS:
        item = dict(definition)
        suite = get_suite_editor(item["suite_key"])
        item["case_count"] = len(suite["tests"]) if suite else 0
        item["modules"] = [{"name": module, "count": suite["module_counts"].get(module, 0)} for module in ("Home", "Premium", "Login", "Trending", "eBooks", "Games")] if suite else []
        item["credentials"] = profile_status(item["key"]) if item["key"] != "ANONYMOUS" else None
        profiles.append(item)
    return render_template("user_profiles.html", profiles=profiles)


@user_profiles_bp.route("/user-profiles/<state>")
def detail(state):
    state = str(state or "").upper()
    definition = next((item for item in PROFILE_DEFINITIONS if item["key"] == state), None)
    if not definition:
        abort(404)
    profile = dict(definition)
    profile["credentials"] = profile_status(state) if state != "ANONYMOUS" else None
    return render_template("user_profile_detail.html", profile=profile)


@user_profiles_bp.route("/user-profiles/<state>/credentials", methods=["POST"])
def credentials(state):
    try:
        save_profile(
            state, request.form.get("email"), request.form.get("password"),
            request.form.get("login_method"), request.form.get("google_email"),
            request.form.get("apple_email"),
        )
        flash(f"{state.title()} test credentials saved locally. The password remains masked.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("user_profiles.detail", state=state.upper()))
