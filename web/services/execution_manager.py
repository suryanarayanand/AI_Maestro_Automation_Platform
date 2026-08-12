from datetime import datetime


execution = {
    "running": False,
    "suite": None,
    "start_time": None,
    "logs": []
}

def start_execution(suite_name):
    execution["running"] = True
    execution["suite"] = suite_name
    execution["start_time"] = datetime.now()
    execution["logs"] = []


def finish_execution():
    execution["running"] = False
    execution["suite"] = None
    execution["start_time"] = None


def get_execution():
    return execution

def add_log(message):

    execution["logs"].append(message)

    # Keep only the latest 200 lines
    execution["logs"] = execution["logs"][-200:]


def get_logs():
    return execution["logs"]