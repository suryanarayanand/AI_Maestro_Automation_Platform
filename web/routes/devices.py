from flask import Blueprint, render_template

from web.services.device_service import get_device_status

devices_bp = Blueprint("devices", __name__)


@devices_bp.route("/devices")
def devices():

    device = get_device_status()

    return render_template(
        "devices.html",
        device=device
    )