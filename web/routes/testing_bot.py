from flask import Blueprint, Response, jsonify, render_template, request, session

from web.services.testing_bot_service import chat, clear_history, history

testing_bot_bp = Blueprint("testing_bot", __name__)

@testing_bot_bp.route("/testing-bot")
def index():
    return render_template("testing_bot.html", messages=history(session["username"]))

@testing_bot_bp.route("/api/testing-bot/ask", methods=["POST"])
def ask():
    try:
        return jsonify(chat(session["username"], (request.get_json() or {}).get("question", "")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

@testing_bot_bp.route("/api/testing-bot/history")
def api_history():
    return jsonify({"messages": history(session["username"], limit=30)})

@testing_bot_bp.route("/api/testing-bot/clear", methods=["POST"])
def clear():
    return jsonify({"cleared": True, "deleted": clear_history(session["username"])})

@testing_bot_bp.route("/testing-bot/export")
def export():
    messages = history(session["username"], limit=10000)
    lines = ["# Testing Bot Chat", "", f"User: {session['username']}", ""]
    for item in messages:
        role = "Tester" if item["role"] == "user" else "Testing Bot"
        lines.extend([f"## {role}", "", item["message"], ""])
    return Response("\n".join(lines), mimetype="text/markdown", headers={
        "Content-Disposition": "attachment; filename=testing_bot_chat.md"
    })
