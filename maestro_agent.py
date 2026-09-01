import json, os, re, shutil, socket, subprocess, sys, tempfile, time
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
RUNTIME_ROOT = ROOT / ".runtime"
AGENT_LOCK_HANDLE = None
MAESTRO_LOG_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "mobile_dev" / "maestro" / "Logs"
MAESTRO_LOG_ARCHIVE = RUNTIME_ROOT / "maestro-log-archive"
PINNED_MAESTRO = RUNTIME_ROOT / "maestro-2.5.1" / "maestro" / "bin" / (
    "maestro.bat" if os.name == "nt" else "maestro"
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_credentials(user_state="SUBSCRIBER"):
    credentials_path = ROOT / "credentials.local.json"
    credentials = {}
    if credentials_path.is_file():
        credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    profiles = credentials.get("profiles", {}) if isinstance(credentials, dict) else {}
    profile = profiles.get(str(user_state or "SUBSCRIBER").upper(), {})
    if not profile and str(user_state or "").upper() == "SUBSCRIBER":
        profile = credentials
    return {
        "TEST_EMAIL": os.getenv("MAESTRO_TEST_EMAIL") or profile.get("email"),
        "TEST_PASSWORD": os.getenv("MAESTRO_TEST_PASSWORD") or profile.get("password"),
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


def maestro_command(yaml_path, user_state="SUBSCRIBER"):
    executable = str(PINNED_MAESTRO) if PINNED_MAESTRO.is_file() else shutil.which(
        "maestro.bat" if os.name == "nt" else "maestro"
    )
    if not executable:
        raise FileNotFoundError("Maestro executable was not found on PATH")
    command = [executable, "test"]
    for maestro_name, value in test_credentials(user_state).items():
        if value:
            command.extend(["-e", f"{maestro_name}={value}"])
    command.append(str(yaml_path))
    return command


def acquire_agent_lock():
    """Keep one polling agent per workspace; OS releases the lock after a crash."""
    global AGENT_LOCK_HANDLE
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = RUNTIME_ROOT / "maestro-agent.lock"
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        handle.close()
        return False
    AGENT_LOCK_HANDLE = handle
    return True


def is_maestro_environment_failure(stdout, stderr):
    log = f"{stdout}\n{stderr}"
    return (
        "ExceptionInInitializerError" in log
        or "maestro.log.lck" in log
        or "Could not initialize class maestro.debuglog" in log
        or "0 devices connected" in log
        or "Not enough devices connected" in log
        or "device offline" in log.casefold()
    )


def prepare_maestro_logs(keep=0):
    """Archive old ZIP logs so Maestro can safely create its next log folder.

    Maestro counts both ZIP files and timestamp directories toward its six-entry
    cleanup threshold. Keeping three ZIPs while timestamp directories remain can
    make Maestro delete the folder it just created before maestro.log.lck opens.
    """
    if not MAESTRO_LOG_DIR.is_dir():
        return []
    entries = sorted(
        (path for path in MAESTRO_LOG_DIR.iterdir() if path.is_file()),
        key=lambda path: path.name,
        reverse=True,
    )
    if len(entries) <= keep:
        return []
    MAESTRO_LOG_ARCHIVE.mkdir(parents=True, exist_ok=True)
    moved = []
    remaining = len(entries)
    # Start with the oldest entries, but continue toward newer entries when a
    # historical ZIP is locked so the directory still falls below the limit.
    for source in reversed(entries):
        if remaining <= keep:
            break
        destination = MAESTRO_LOG_ARCHIVE / source.name
        if destination.exists():
            destination = MAESTRO_LOG_ARCHIVE / f"{source.stem}_{time.time_ns()}{source.suffix}"
        try:
            shutil.move(str(source), str(destination))
            moved.append(destination)
            remaining -= 1
        except (PermissionError, OSError):
            # Locked historical archives must not block a queued test run.
            continue
    return moved


def screenshot_snapshot(folder=SCREENSHOT_ROOT):
    """Return a stable inventory used to identify images changed by one case."""
    folder = Path(folder)
    if not folder.exists():
        return {}
    inventory = {}
    for path in folder.rglob("*.png"):
        if not path.is_file():
            continue
        stat = path.stat()
        inventory[path.relative_to(folder).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return inventory


def connected_device_serial():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
    devices = [line.split()[0] for line in result.stdout.splitlines()[1:]
               if line.strip().endswith("device")]
    return devices[0] if len(devices) == 1 else ""


def start_case_video(case_id):
    serial = connected_device_serial()
    if not serial:
        return None
    safe_case = re.sub(r"[^A-Za-z0-9_-]", "_", str(case_id))
    remote = f"/sdcard/maestro_{safe_case}.mp4"
    subprocess.run(["adb", "-s", serial, "shell", "rm", "-f", remote],
                   capture_output=True, timeout=10)
    process = subprocess.Popen(
        ["adb", "-s", serial, "shell", "screenrecord", "--bit-rate", "4000000",
         "--time-limit", "180", remote], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    return {"serial": serial, "remote": remote, "process": process, "case_id": safe_case}


def stop_case_video(recording, execution_folder, retain=True):
    if not recording:
        return None
    pid_result = subprocess.run(
        ["adb", "-s", recording["serial"], "shell", "pidof", "screenrecord"],
        capture_output=True, text=True, timeout=10,
    )
    for pid in pid_result.stdout.split():
        if pid.isdigit():
            subprocess.run(
                ["adb", "-s", recording["serial"], "shell", "kill", "-2", pid],
                capture_output=True, timeout=10,
            )
    try:
        recording["process"].wait(timeout=15)
    except subprocess.TimeoutExpired:
        recording["process"].terminate()
    if not retain:
        subprocess.run(
            ["adb", "-s", recording["serial"], "shell", "rm", "-f", recording["remote"]],
            capture_output=True, timeout=10,
        )
        return None
    video_dir = Path(execution_folder) / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    destination = video_dir / f"{recording['case_id']}.mp4"
    pulled = subprocess.run(
        ["adb", "-s", recording["serial"], "pull", recording["remote"], str(destination)],
        capture_output=True, timeout=60,
    )
    subprocess.run(["adb", "-s", recording["serial"], "shell", "rm", "-f", recording["remote"]],
                   capture_output=True, timeout=10)
    return destination if pulled.returncode == 0 and destination.is_file() else None


def extract_video_failure_frames(video_path, destination, count=5):
    if not video_path:
        return []
    try:
        import cv2
    except ImportError:
        return []
    capture = cv2.VideoCapture(str(video_path))
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if frames <= 0:
        capture.release()
        return []
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, position in enumerate(
        int((frames - 1) * offset / max(1, count - 1)) for offset in range(count)
    ):
        capture.set(cv2.CAP_PROP_POS_FRAMES, position)
        ok, frame = capture.read()
        if ok:
            path = destination / f"video_evidence_{index + 1:02d}.png"
            cv2.imwrite(str(path), frame)
            outputs.append(path)
    capture.release()
    return outputs


def build_video_failure_plan(case_id, stdout, stderr, video_path, frames, visual_details):
    log = f"{stdout}\n{stderr}"
    failed_step = next(
        (line.strip() for line in reversed(log.splitlines()) if "FAILED" in line),
        "Unknown failed step",
    )
    if "Invalid File Path" in log:
        cause = "A referenced flow path was invalid in the execution workspace."
        actions = ["Preserve the YAML folder structure.", "Validate every runFlow path before rerun."]
    elif "Element not found" in log or "Assertion is false" in log:
        cause = "The expected UI element was not visible in the recorded app state."
        actions = [
            "Inspect the final video frames and hierarchy for the actual screen and label.",
            "Correct navigation, scrolling, selector, or wait behavior using observed evidence.",
            "Rerun only this failed case before promoting the pattern to App Memory.",
        ]
    else:
        cause = "The execution log and retained video require reviewer diagnosis."
        actions = ["Review the retained video timeline.", "Add a grounded correction and rerun the case."]
    return {
        "case_id": case_id, "failed_step": failed_step, "probable_cause": cause,
        "corrective_actions": actions,
        "video": str(video_path) if video_path else "",
        "evidence_frames": [str(path) for path in frames],
        "visual_findings": visual_details,
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


def organize_case_evidence(execution_folder, case_id, screenshots, video_path, log_file,
                           failure_plan_path):
    """Create one reviewer-friendly evidence folder per scenario."""
    execution_folder = Path(execution_folder)
    case_root = execution_folder / "cases" / case_id
    groups = {
        "screenshots": [Path(path) for path in screenshots],
        "video": [Path(video_path)] if video_path else [],
        "logs": [Path(log_file)] if log_file else [],
        "failure": [Path(failure_plan_path)] if failure_plan_path else [],
    }
    manifest = {"case_id": case_id, "folders": {}, "artifacts": []}
    for folder_name, sources in groups.items():
        destination = case_root / folder_name
        copied = []
        for source in sources:
            if not source.is_file():
                continue
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / source.name
            shutil.copy2(source, target)
            copied.append(target.relative_to(execution_folder).as_posix())
        manifest["folders"][folder_name] = copied
        manifest["artifacts"].extend(copied)
    case_root.mkdir(parents=True, exist_ok=True)
    (case_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return case_root


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
    completed, failed, needs_review, cancelled, logs, results = 0, False, False, False, [], []
    job_started = time.monotonic()
    execution_folder = create_execution_folder(
        ROOT / "Reports", f"{job['suite'].title()}_Job_{job['id']}"
    )
    infrastructure_failure = False
    with tempfile.TemporaryDirectory(prefix="maestro-agent-") as temp:
        temp_root = Path(temp)
        scenario_dir = temp_root / "Scenarios"
        common_dir = temp_root / "Common"
        scenario_dir.mkdir()
        common_dir.mkdir()
        for name, content in job.get("scenario_flows", {}).items():
            relative = Path(str(name).replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe scenario flow path: {name}")
            destination = scenario_dir.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        for name, content in job.get("common_flows", {}).items():
            relative = Path(str(name).replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe common flow path: {name}")
            destination = common_dir.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        for test in job["tests"]:
            api(f"/api/agent/jobs/{job['id']}", "PATCH", {"current_case": test["id"], "completed": completed})
            relative = Path(str(test["yaml"]).replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe test YAML path: {test['yaml']}")
            yaml_path = scenario_dir.joinpath(*relative.parts)
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            yaml_path.write_text(test["yaml_content"], encoding="utf-8")
            started = time.monotonic()
            stdout_path = temp_root / f"{test['id']}.stdout.log"
            stderr_path = temp_root / f"{test['id']}.stderr.log"
            screenshots_before = screenshot_snapshot()
            recording = start_case_video(test["id"])
            timed_out = False
            runner_crashed = False
            case_timeout = max(30, int(job.get("case_timeout_seconds", 300)))
            prepare_maestro_logs()
            with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
                process = subprocess.Popen(
                    maestro_command(yaml_path, test.get("user_state")), stdout=stdout_file, stderr=stderr_file,
                    text=True
                )
                while process.poll() is None:
                    time.sleep(1)
                    if time.monotonic() - started >= case_timeout:
                        stop_process_tree(process)
                        timed_out = True
                        break
                    # A failed inline GraalJS command can crash Maestro's debug
                    # reporter while leaving its JVM alive indefinitely. Detect
                    # that fatal signature instead of advertising a stale RUNNING
                    # case until the full timeout expires.
                    if stderr_path.exists() and stderr_path.stat().st_size:
                        stderr_tail = stderr_path.read_text(
                            encoding="utf-8", errors="replace"
                        )[-12000:]
                        if (
                            'Exception in thread "main"' in stderr_tail
                            and (
                                "ShouldNotReachHere" in stderr_tail
                                or "GraalJsEngine" in stderr_tail
                            )
                        ):
                            stop_process_tree(process)
                            runner_crashed = True
                            break
                    state = api(f"/api/agent/jobs/{job['id']}/status")
                    if state and state.get("status") == "cancel_requested":
                        stop_process_tree(process)
                        cancelled = True
                        break
                process.wait()
            stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
            stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
            # Maestro currently emits a failed assertWithAI as WARNED and may
            # still return exit code 0. A functional assertion failure must not
            # be converted into PASS/NEEDS_REVIEW by the portal.
            ai_assertion_failed = bool(re.search(
                r'Warning:\s+Assertion\s+"[\s\S]*?"\s+failed:', stdout, re.I
            ))
            infrastructure_failure = is_maestro_environment_failure(stdout, stderr)
            if infrastructure_failure:
                stderr = (
                    f"{stderr}\nPortal runner stopped the batch because Maestro failed "
                    "during environment initialization; remaining cases were not executed.\n"
                )
            if timed_out:
                stderr = f"{stderr}\nCase exceeded the configured {case_timeout}-second timeout.\n"
            if runner_crashed:
                stderr = (
                    f"{stderr}\nPortal runner terminated a crashed Maestro/GraalJS "
                    "debug reporter instead of leaving the job stale.\n"
                )
            duration = round(time.monotonic() - started, 2)
            status = (
                "CANCELLED" if cancelled else
                ("NEEDS_REVIEW" if infrastructure_failure else
                 ("PASS" if process.returncode == 0 and not timed_out and not runner_crashed and not ai_assertion_failed else "FAIL"))
            )
            # Keep complete failure evidence, but do not spend ADB transfer and
            # disk I/O pulling videos that would immediately be deleted.
            video_path = stop_case_video(
                recording, execution_folder, retain=(status == "FAIL")
            )
            failed = failed or status == "FAIL"
            logs.append(f"[{test['id']}] {status}\n{stdout}\n{stderr}")
            log_file = save_log(
                execution_folder, test["id"], stdout, stderr
            )
            captured = collect_changed_screenshots(
                screenshots_before, execution_folder, test["id"]
            )
            if status == "FAIL":
                captured.extend(extract_video_failure_frames(
                    video_path, execution_folder / "screenshots" / test["id"]
                ))
            ai_result = analyze_scenario(
                execution_folder / "screenshots" / test["id"],
                execution_folder,
                test["id"],
            ) if captured else {
                "total": 0, "passed": 0, "failed": 0, "errors": 0, "details": []
            }
            failure_plan = None
            failure_plan_path = None
            if status == "FAIL":
                failure_plan = build_video_failure_plan(
                    test["id"], stdout, stderr, video_path, captured, ai_result["details"]
                )
                plan_dir = execution_folder / "failure_plans"
                plan_dir.mkdir(parents=True, exist_ok=True)
                failure_plan_path = plan_dir / f"{test['id']}.json"
                failure_plan_path.write_text(
                    json.dumps(failure_plan, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            case_evidence = organize_case_evidence(
                execution_folder, test["id"], captured, video_path, log_file,
                failure_plan_path,
            )
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
                "video": video_path.relative_to(execution_folder).as_posix() if video_path else "",
                "failure_plan": failure_plan_path.relative_to(execution_folder).as_posix() if failure_plan_path else "",
                "case_evidence": case_evidence.relative_to(execution_folder).as_posix(),
                "ai_pass": ai_result["passed"],
                "ai_fail": ai_result["failed"],
                "ai_errors": ai_result["errors"],
                "ai_details": ai_result["details"],
            })
            recorded = api(f"/api/agent/jobs/{job['id']}/results", "POST", {"case_id": test["id"], "name": test.get("name"), "status": status, "duration": duration, "stdout": stdout, "stderr": stderr, "failure_plan": failure_plan})
            segregated_status = (recorded or {}).get("status", status)
            results[-1]["status"] = segregated_status
            needs_review = needs_review or segregated_status == "NEEDS_REVIEW"
            completed += 1
            api(f"/api/agent/jobs/{job['id']}", "PATCH", {"completed": completed, "logs": "\n".join(logs)})
            if cancelled or infrastructure_failure:
                break
    execution_time = round(time.monotonic() - job_started, 2)
    try:
        generate_job_reports(job, results, execution_time, execution_folder)
    except Exception as exc:
        logs.append(f"[REPORT GENERATION] FAIL\n{type(exc).__name__}: {exc}")
    api(f"/api/agent/jobs/{job['id']}", "PATCH", {
        "status": "cancelled" if cancelled else ("failed" if failed else ("needs_review" if needs_review else "passed")),
        "current_case": None,
        "completed": completed,
        "logs": "\n".join(logs),
        "report_folder": execution_folder.name,
    })


def main():
    if not acquire_agent_lock():
        print("Another maestro_agent.py instance already owns this workspace; exiting.")
        raise SystemExit(2)
    print(f"Agent {AGENT} polling {PORTAL}")
    while True:
        job = api("/api/agent/jobs/claim", "POST", {"agent": AGENT})
        execute(job) if job else time.sleep(5)


if __name__ == "__main__": main()
