import json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from Utils.ai_html_report import generate_ai_html_report
from Utils.ai_report import analyze_execution, analyze_scenario, save_ai_report
from Utils.bug_summary import generate_bug_summary, save_bug_summary
from Utils.bug_summary_html import generate_bug_summary_html
from Utils.excel_report import generate_excel_report
from Utils.html_report import generate_html_report
from Utils.master_html_report import generate_master_dashboard
from Utils.master_report import generate_master_report
from Utils.report_utils import create_execution_folder, save_log
from Utils.visual_html_report import generate_visual_html_report
from Utils.visual_report import analyze_visual_execution, analyze_visual_scenario, save_visual_report
from Utils.baseline_reports import generate_baseline_reports

PORTAL = os.getenv("MAESTRO_PORTAL_URL", "http://127.0.0.1:5000").rstrip("/")
TOKEN = os.getenv("MAESTRO_AGENT_TOKEN", "change-me")
AGENT = os.getenv("MAESTRO_AGENT_NAME", socket.gethostname())
ROOT = Path(__file__).resolve().parent
SCREENSHOT_ROOT = ROOT / "Screenshots"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_credentials():
    credentials_path = ROOT / "credentials.local.json"
    credentials = {}
    if credentials_path.is_file():
        credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    return {
        "TEST_EMAIL": os.getenv("MAESTRO_TEST_EMAIL") or credentials.get("email"),
        "TEST_PASSWORD": os.getenv("MAESTRO_TEST_PASSWORD") or credentials.get("password"),
    }


def device_metadata(build_role):
    """Collect reproducible evidence about the device/build used by a report."""
    def adb(*args):
        try:
            return subprocess.run(
                ["adb", *args], capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except Exception:
            return ""

    serials = [
        line.split()[0] for line in adb("devices").splitlines()[1:]
        if line.strip().endswith("device")
    ]
    serial = serials[0] if len(serials) == 1 else ""
    prefix = ["-s", serial] if serial else []
    prop = lambda name: adb(*prefix, "shell", "getprop", name)
    package = "com.mobstac.thehindu"
    version = adb(*prefix, "shell", "dumpsys", "package", package)
    version_name = ""
    version_code = ""
    for line in version.splitlines():
        value = line.strip()
        if value.startswith("versionName=") and not version_name:
            version_name = value.split("=", 1)[1]
        if value.startswith("versionCode=") and not version_code:
            version_code = value.split("=", 1)[1].split()[0]
    return {
        "role": build_role,
        "serial": serial or "multiple-or-unavailable",
        "manufacturer": prop("ro.product.manufacturer"),
        "model": prop("ro.product.model"),
        "android": prop("ro.build.version.release"),
        "resolution": adb(*prefix, "shell", "wm", "size").replace("\n", "; "),
        "density": adb(*prefix, "shell", "wm", "density").replace("\n", "; "),
        "package": package,
        "version_name": version_name,
        "version_code": version_code,
    }


def maestro_command(yaml_path):
    executable = shutil.which("maestro.bat" if os.name == "nt" else "maestro")
    if not executable:
        raise FileNotFoundError("Maestro executable was not found on PATH")
    command = [executable, "test"]
    for maestro_name, value in test_credentials().items():
        if value:
            command.extend(["-e", f"{maestro_name}={value}"])
    command.append(str(yaml_path))
    return command


def screenshot_snapshot(folder=SCREENSHOT_ROOT):
    """Return a stable inventory used to identify images changed by one case."""
    folder = Path(folder)
    if not folder.exists():
        return {}
    return {
        path.relative_to(folder).as_posix(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in folder.rglob("*.png")
        if path.is_file()
    }


def collect_changed_screenshots(
    before,
    execution_folder,
    case_id,
    screenshot_root=SCREENSHOT_ROOT,
):
    """Copy screenshots created or overwritten during a case into its report."""
    screenshot_root = Path(screenshot_root)
    execution_folder = Path(execution_folder)
    destination = execution_folder / "screenshots" / case_id
    copied = []

    for relative, fingerprint in screenshot_snapshot(screenshot_root).items():
        if before.get(relative) == fingerprint:
            continue
        source = screenshot_root / Path(relative)
        source_relative = Path(relative)
        checkpoint = (
            Path(*source_relative.parts[1:])
            if len(source_relative.parts) > 1
            else source_relative
        )
        target = destination / checkpoint
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)

    return sorted(copied)


def api(path, method="GET", payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(PORTAL + path, data=body, method=method, headers={"X-Agent-Token": TOKEN, "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
            return json.loads(content) if content else None
    except HTTPError as exc:
        if exc.code == 204:
            return None
        raise


def generate_job_reports(job, results, execution_time, execution_folder):
    suite_name = job["suite"].title()
    baseline_root = ROOT / ".maestro" / "screenshots" / "Baselines" / "Screenshots"
    if job["suite"].lower() == "baseline":
        generate_baseline_reports(
            results,
            suite_name,
            execution_time,
            execution_folder,
            baseline_root,
            device_metadata("Production reference"),
        )
        return

    generate_excel_report(results, suite_name, execution_time, execution_folder)
    generate_html_report(results, suite_name, execution_time, execution_folder)

    ai_summary = analyze_execution(results)
    ai_file = save_ai_report(ai_summary, execution_folder)
    generate_ai_html_report(ai_file, execution_folder)

    visual_results = []
    for result in results:
        comparison = analyze_visual_scenario(
            baseline_root / result["id"],
            execution_folder / "screenshots" / result["id"],
            execution_folder,
            result["id"],
        )
        comparison["scenario"] = result["id"]
        visual_results.append(comparison)
    reference_metadata = {}
    metadata_file = baseline_root / "baseline_metadata.json"
    if metadata_file.is_file():
        reference_metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    visual_summary = analyze_visual_execution(
        visual_results, reference_metadata, device_metadata("Internal test actual")
    )
    visual_file = save_visual_report(visual_summary, execution_folder)
    generate_visual_html_report(visual_file, execution_folder)

    bug_summary = generate_bug_summary(
        results, ai_summary, visual_summary, suite_name, execution_time
    )
    bug_file = save_bug_summary(bug_summary, execution_folder)
    generate_bug_summary_html(bug_file, execution_folder)

    master_file = generate_master_report(ROOT / "Reports")
    generate_master_dashboard(master_file, ROOT / "Reports")


def stop_process_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def execute(job):
    completed, failed, cancelled, logs, results = 0, False, False, [], []
    job_started = time.monotonic()
    execution_folder = create_execution_folder(
        ROOT / "Reports", f"{job['suite'].title()}_Job_{job['id']}"
    )
    with tempfile.TemporaryDirectory(prefix="maestro-agent-") as temp:
        temp_root = Path(temp)
        scenario_dir = temp_root / "Scenarios"
        common_dir = temp_root / "Common"
        scenario_dir.mkdir()
        common_dir.mkdir()
        for name, content in job.get("common_flows", {}).items():
            (common_dir / Path(name).name).write_text(content, encoding="utf-8")
        for test in job["tests"]:
            api(f"/api/agent/jobs/{job['id']}", "PATCH", {"current_case": test["id"], "completed": completed})
            yaml_path = scenario_dir / Path(test["yaml"]).name
            yaml_path.write_text(test["yaml_content"], encoding="utf-8")
            started = time.monotonic()
            stdout_path = temp_root / f"{test['id']}.stdout.log"
            stderr_path = temp_root / f"{test['id']}.stderr.log"
            screenshots_before = screenshot_snapshot()
            timed_out = False
            case_timeout = max(30, int(job.get("case_timeout_seconds", 300)))
            with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
                process = subprocess.Popen(
                    maestro_command(yaml_path), stdout=stdout_file, stderr=stderr_file, text=True
                )
                while process.poll() is None:
                    time.sleep(1)
                    if time.monotonic() - started >= case_timeout:
                        stop_process_tree(process)
                        timed_out = True
                        break
                    state = api(f"/api/agent/jobs/{job['id']}/status")
                    if state and state.get("status") == "cancel_requested":
                        stop_process_tree(process)
                        cancelled = True
                        break
                process.wait()
            stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
            stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
            if timed_out:
                stderr = f"{stderr}\nCase exceeded the configured {case_timeout}-second timeout.\n"
            duration = round(time.monotonic() - started, 2)
            status = "CANCELLED" if cancelled else ("PASS" if process.returncode == 0 and not timed_out else "FAIL")
            failed = failed or status == "FAIL"
            logs.append(f"[{test['id']}] {status}\n{stdout}\n{stderr}")
            log_file = save_log(
                execution_folder, test["id"], stdout, stderr
            )
            captured = collect_changed_screenshots(
                screenshots_before, execution_folder, test["id"]
            )
            ai_result = analyze_scenario(
                execution_folder / "screenshots" / test["id"],
                execution_folder,
                test["id"],
            ) if captured else {
                "total": 0, "passed": 0, "failed": 0, "errors": 0, "details": []
            }
            results.append({
                "id": test["id"],
                "module": test.get("module", "Portal"),
                "name": test.get("name") or test["id"],
                "status": status,
                "duration": duration,
                "log_file": str(log_file),
                "screenshots": [
                    path.relative_to(execution_folder).as_posix()
                    for path in captured
                ],
                "ai_pass": ai_result["passed"],
                "ai_fail": ai_result["failed"],
                "ai_errors": ai_result["errors"],
                "ai_details": ai_result["details"],
            })
            api(f"/api/agent/jobs/{job['id']}/results", "POST", {"case_id": test["id"], "name": test.get("name"), "status": status, "duration": duration, "stdout": stdout, "stderr": stderr})
            completed += 1
            api(f"/api/agent/jobs/{job['id']}", "PATCH", {"completed": completed, "logs": "\n".join(logs)})
            if cancelled:
                break
    execution_time = round(time.monotonic() - job_started, 2)
    try:
        generate_job_reports(job, results, execution_time, execution_folder)
    except Exception as exc:
        logs.append(f"[REPORT GENERATION] FAIL\n{type(exc).__name__}: {exc}")
    api(f"/api/agent/jobs/{job['id']}", "PATCH", {
        "status": "cancelled" if cancelled else ("failed" if failed else "passed"),
        "current_case": None,
        "completed": completed,
        "logs": "\n".join(logs),
        "report_folder": execution_folder.name,
    })


def main():
    print(f"Agent {AGENT} polling {PORTAL}")
    while True:
        job = api("/api/agent/jobs/claim", "POST", {"agent": AGENT})
        execute(job) if job else time.sleep(5)


if __name__ == "__main__": main()
