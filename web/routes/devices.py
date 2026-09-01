from flask import Blueprint, render_template

from web.services.device_service import get_device_health, get_device_status

devices_bp = Blueprint("devices", __name__)


@devices_bp.route("/devices")
def devices():
    device = get_device_status()
    health, health_history = get_device_health()
    return render_template(
        "devices.html", device=device, health=health, health_history=health_history
    )
