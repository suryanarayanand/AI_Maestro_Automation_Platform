import subprocess


def get_device_status():
    """
    Returns the current Android device status.
    """

    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )

        print(result.stdout)
        
        lines = result.stdout.strip().splitlines()

        devices = []

        for line in lines[1:]:
            if "\tdevice" in line:
                device_id = line.split("\t")[0]
                devices.append(device_id)

        if devices:
            return {
                "connected": True,
                "count": len(devices),
                "device_id": devices[0],
                "status": "Connected"
            }

        return {
            "connected": False,
            "count": 0,
            "device_id": "",
            "status": "Disconnected"
        }

    except Exception as e:

        return {
            "connected": False,
            "count": 0,
            "device_id": "",
            "status": f"Error : {e}"
        }