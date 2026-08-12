import os
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "portal.db"


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect():
    connection = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'reviewer'
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, name TEXT NOT NULL,
            yaml TEXT NOT NULL, source_file TEXT, status TEXT NOT NULL DEFAULT 'pending',
            error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT, reviewed_by TEXT
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY, suite TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
            current_case TEXT, completed INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0, logs TEXT NOT NULL DEFAULT '',
            report_folder TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT, finished_at TEXT, agent TEXT
        );
        CREATE TABLE IF NOT EXISTS job_results (
            id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, case_id TEXT NOT NULL,
            name TEXT, status TEXT NOT NULL, duration REAL NOT NULL DEFAULT 0,
            stdout TEXT NOT NULL DEFAULT '', stderr TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS portal_settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        db.execute(
            "INSERT OR IGNORE INTO portal_settings(key,value) VALUES('case_timeout_seconds','300')"
        )
        job_columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
        if "priority" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
        if "request_mode" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN request_mode TEXT NOT NULL DEFAULT 'queue'")
        draft_columns = {row["name"] for row in db.execute("PRAGMA table_info(drafts)")}
        if "generation_mode" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN generation_mode TEXT NOT NULL DEFAULT 'rules'")
        if "ai_confidence" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN ai_confidence REAL")
        if "ai_assumptions" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN ai_assumptions TEXT NOT NULL DEFAULT '[]'")
        username = os.getenv("PORTAL_ADMIN_USER", "admin")
        password = os.getenv("PORTAL_ADMIN_PASSWORD", "admin")
        db.execute(
            "INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
            (username, generate_password_hash(password), "admin"),
        )
