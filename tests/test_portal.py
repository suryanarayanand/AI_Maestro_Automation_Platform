import tempfile
import unittest
from pathlib import Path

import web.portal_db as portal_db
from app import app
from web.services.job_queue_service import create_batched_jobs
from web.services.result_validation_service import excel_condition_verdict


class PortalTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = portal_db.DB_PATH
        portal_db.DB_PATH = Path(self.temp_dir.name) / "portal-test.db"
        portal_db.init_db()
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.test_client()

    def tearDown(self):
        portal_db.DB_PATH = self.original_db
        self.temp_dir.cleanup()

    def sign_in(self):
        with self.client.session_transaction() as session:
            session["username"] = "admin"
            session["role"] = "admin"

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_primary_portal_pages_render(self):
        self.sign_in()
        for path in ("/", "/generator", "/article-library", "/yaml-editor", "/suites", "/jobs", "/reports", "/devices", "/settings"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_test_design_workspace_combines_full_and_atomic_flows(self):
        self.sign_in()
        response = self.client.get("/generator")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Test Design Workspace", html)
        self.assertIn("Upload and generate YAML", html)
        self.assertIn("Import atomic catalogue", html)
        self.assertIn("YAML drafts and approvals", html)
        self.assertIn("Evidence-grounded reusable steps", html)
        self.assertNotIn(">Agent Workspace<", html)

    def test_legacy_agent_workspace_redirects_to_unified_workspace(self):
        self.sign_in()
        response = self.client.get("/flow-workspace")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/generator", response.location)
        self.assertIn("#atomic-flows", response.location)

    def test_article_library_is_available_from_portal(self):
        self.sign_in()
        response = self.client.get("/article-library")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Article Reference Library", html)
        self.assertIn("New article reference", html)
        self.assertIn("Import Article URLs", html)

    def test_friday_understands_article_coverage_question(self):
        self.sign_in()
        response = self.client.post(
            "/api/testing-bot/ask",
            json={"question": "What is anonymous Article Page coverage and what is missing?"},
        )
        self.assertEqual(response.status_code, 200)
        answer = response.get_json()["answer"]
        self.assertTrue("Article" in answer or "article" in answer)
        self.assertNotEqual(
            answer,
            "Anonymous flows clear state and require SUBSCRIBE plus ADVERTISEMENT. "
            "Subscriber flows clear state, authenticate again, and require both to be absent.",
        )

    def test_suite_action_queues_agent_job(self):
        self.sign_in()
        response = self.client.post("/run-suite/smoke")
        self.assertEqual(response.status_code, 302)
        with portal_db.connect() as db:
            job = db.execute("SELECT * FROM jobs").fetchone()
        self.assertEqual(job["suite"], "smoke")
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["priority"], 0)
        self.assertEqual(job["request_mode"], "queue")

    def test_suites_page_shows_latest_completed_result(self):
        self.sign_in()
        with portal_db.connect() as db:
            older = db.execute(
                "INSERT INTO jobs(suite,status,finished_at) VALUES('smoke','passed',CURRENT_TIMESTAMP)"
            ).lastrowid
            latest = db.execute(
                "INSERT INTO jobs(suite,status,finished_at) VALUES('smoke','failed',CURRENT_TIMESTAMP)"
            ).lastrowid
            db.execute("INSERT INTO jobs(suite,status) VALUES('smoke','queued')")

        response = self.client.get("/suites")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn(f"Job #{latest}", html)
        self.assertIn("status-failed", html)
        self.assertNotIn(f"Job #{older}", html)

    def test_overview_shows_latest_completed_result_and_active_case_metric(self):
        self.sign_in()
        with portal_db.connect() as db:
            latest = db.execute(
                "INSERT INTO jobs(suite,status,finished_at) VALUES('smoke','passed',CURRENT_TIMESTAMP)"
            ).lastrowid
            db.execute("INSERT INTO jobs(suite,status) VALUES('sanity','queued')")

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Unique active suite cases", html)
        self.assertIn(f"Job #{latest}", html)
        self.assertIn("Last completed", html)

    def test_run_now_job_is_claimed_before_normal_queue(self):
        self.sign_in()
        self.client.post("/run-suite/sanity/queue")
        self.client.post("/run-suite/smoke/run-now")
        response = self.client.post(
            "/api/agent/jobs/claim",
            json={"agent": "test-agent"},
            headers={"X-Agent-Token": "change-me"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["suite"], "smoke")

    def test_run_next_promotes_existing_queued_job(self):
        self.sign_in()
        self.client.post("/run-suite/smoke/queue")
        self.client.post("/run-suite/sanity/queue")
        with portal_db.connect() as db:
            sanity_id = db.execute("SELECT id FROM jobs WHERE suite='sanity'").fetchone()["id"]
        self.client.post(f"/jobs/{sanity_id}/run-next")
        with portal_db.connect() as db:
            next_job = db.execute("SELECT suite FROM jobs WHERE status='queued' ORDER BY priority DESC,id ASC").fetchone()
        self.assertEqual(next_job["suite"], "sanity")

    def test_claimed_job_includes_common_flow_dependencies(self):
        self.sign_in()
        self.client.post("/run-suite/smoke/queue")
        response = self.client.post(
            "/api/agent/jobs/claim",
            json={"agent": "test-agent"},
            headers={"X-Agent-Token": "change-me"},
        )
        payload = response.get_json()
        self.assertIn("common_flows", payload)
        self.assertIn("LOGIN.yaml", payload["common_flows"])
        self.assertEqual(payload["case_timeout_seconds"], 300)

    def test_execution_timeout_can_be_saved_in_settings(self):
        self.sign_in()

        response = self.client.post(
            "/settings", data={"case_timeout_seconds": "420"}, follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Execution settings saved", response.get_data(as_text=True))
        with portal_db.connect() as db:
            value = db.execute(
                "SELECT value FROM portal_settings WHERE key='case_timeout_seconds'"
            ).fetchone()["value"]
        self.assertEqual(value, "420")

    def test_execution_timeout_rejects_unsafe_value(self):
        self.sign_in()

        response = self.client.post(
            "/settings", data={"case_timeout_seconds": "5"}, follow_redirects=True
        )

        self.assertIn("between 30 and 3600 seconds", response.get_data(as_text=True))

    def test_suite_is_split_into_ordered_batches_of_ten(self):
        tests = [{"id": f"CASE_{index:02d}"} for index in range(21)]
        job_ids = create_batched_jobs("large-suite", tests)
        with portal_db.connect() as db:
            jobs = db.execute(
                "SELECT total,batch_start,batch_number,batch_count FROM jobs ORDER BY id"
            ).fetchall()
        self.assertEqual(len(job_ids), 3)
        self.assertEqual(
            [tuple(job) for job in jobs],
            [(10, 0, 1, 3), (10, 10, 2, 3), (1, 20, 3, 3)],
        )

    def test_maestro_pass_requires_complete_excel_traceability(self):
        traceability = (
            '[{"source_type":"expected_result","status":"covered",'
            '"commands":["assertVisible"]}]'
        )
        with portal_db.connect() as db:
            db.execute(
                """INSERT INTO drafts(
                       case_id,name,yaml,source_file,status,coverage_status,traceability
                   ) VALUES('EXCEL_1','Excel case','appId: test','source.xlsx',
                            'approved','complete',?)""",
                (traceability,),
            )
        status, condition, details = excel_condition_verdict("EXCEL_1", "PASS")
        self.assertEqual((status, condition), ("PASS", "verified_excel_pass"))
        self.assertIn("source.xlsx", details)

    def test_untraced_maestro_pass_is_segregated_for_review(self):
        status, condition, _ = excel_condition_verdict("LEGACY_1", "PASS")
        self.assertEqual(status, "NEEDS_REVIEW")
        self.assertEqual(condition, "missing_excel_traceability")

    def test_agent_api_rejects_wrong_token(self):
        response = self.client.post("/api/agent/jobs/claim", headers={"X-Agent-Token": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_queued_job_can_be_cancelled(self):
        self.sign_in()
        self.client.post("/run-suite/smoke/queue")
        with portal_db.connect() as db:
            job_id = db.execute("SELECT id FROM jobs").fetchone()["id"]
        self.client.post(f"/jobs/{job_id}/cancel")
        with portal_db.connect() as db:
            status = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()["status"]
        self.assertEqual(status, "cancelled")

    def test_running_job_changes_to_cancel_requested(self):
        self.sign_in()
        self.client.post("/run-suite/smoke/queue")
        with portal_db.connect() as db:
            job_id = db.execute("SELECT id FROM jobs").fetchone()["id"]
            db.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
        self.client.post(f"/jobs/{job_id}/cancel")
        with portal_db.connect() as db:
            status = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()["status"]
        self.assertEqual(status, "cancel_requested")

    def test_agent_can_read_cancellation_status(self):
        self.sign_in()
        self.client.post("/run-suite/smoke/queue")
        with portal_db.connect() as db:
            job_id = db.execute("SELECT id FROM jobs").fetchone()["id"]
        response = self.client.get(
            f"/api/agent/jobs/{job_id}/status",
            headers={"X-Agent-Token": "change-me"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "queued")


if __name__ == "__main__":
    unittest.main()
