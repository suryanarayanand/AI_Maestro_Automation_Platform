import subprocess
from pathlib import Path
import threading

from web.services.execution_manager import (
    start_execution,
    finish_execution
)
ROOT = Path(__file__).resolve().parents[2]

# Stores the currently running process
running_process = None

def monitor_process(process):
    """
    Wait until the automation finishes.
    """
    process.wait()
    finish_execution()

def run_suite(suite_name):
    """
    Starts a suite in the background.
    """

    global running_process

    # Prevent starting another suite if one is already running
    if running_process and running_process.poll() is None:
        return False

    command = [
        "py",
        "run_suite.py",
        suite_name
    ]
    start_execution(suite_name)

    running_process = subprocess.Popen(
    command,
    cwd=ROOT,
    text=True
    )
    # Start monitoring the process in the background
    threading.Thread(
        target=monitor_process,
        args=(running_process,),
        daemon=True
    ).start()

    return True
