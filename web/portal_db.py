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
        CREATE TABLE IF NOT EXISTS app_memory_screens (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
            hierarchy_file TEXT, screenshot_file TEXT, app_state TEXT NOT NULL DEFAULT 'unknown',
            element_count INTEGER NOT NULL DEFAULT 0, last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS app_memory_elements (
            id INTEGER PRIMARY KEY, screen_id INTEGER NOT NULL, name TEXT NOT NULL,
            locator_type TEXT NOT NULL, locator_value TEXT NOT NULL, class_name TEXT,
            clickable INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1,
            bounds TEXT, source TEXT NOT NULL DEFAULT 'hierarchy', confidence REAL NOT NULL DEFAULT 0.5,
            UNIQUE(screen_id, locator_type, locator_value),
            FOREIGN KEY(screen_id) REFERENCES app_memory_screens(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS app_memory_transitions (
            id INTEGER PRIMARY KEY, from_screen_id INTEGER NOT NULL, to_screen_id INTEGER NOT NULL,
            action TEXT NOT NULL, locator_type TEXT, locator_value TEXT,
            status TEXT NOT NULL DEFAULT 'observed', safe INTEGER NOT NULL DEFAULT 1,
            last_verified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_screen_id, to_screen_id, action, locator_value),
            FOREIGN KEY(from_screen_id) REFERENCES app_memory_screens(id),
            FOREIGN KEY(to_screen_id) REFERENCES app_memory_screens(id)
        );
        CREATE TABLE IF NOT EXISTS app_memory_learning (
            id INTEGER PRIMARY KEY, case_id TEXT, observation_type TEXT NOT NULL,
            payload TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending', source TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT, reviewed_by TEXT
        );
        CREATE TABLE IF NOT EXISTS app_memory_flows (
            id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, flow_type TEXT NOT NULL,
            content_hash TEXT NOT NULL, command_sequence TEXT NOT NULL,
            last_indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS atomic_flow_steps (
            id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, scenario TEXT NOT NULL,
            step_number INTEGER NOT NULL DEFAULT 1, source_text TEXT NOT NULL,
            user_state TEXT NOT NULL DEFAULT '', module TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]', proposal_yaml TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'imported', error TEXT,
            source_file TEXT NOT NULL, source_row INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_file, case_id, step_number)
        );
        CREATE TABLE IF NOT EXISTS published_flows (
            id INTEGER PRIMARY KEY, atomic_step_id INTEGER NOT NULL UNIQUE,
            flow_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL, yaml_path TEXT NOT NULL UNIQUE,
            tags TEXT NOT NULL DEFAULT '[]', user_state TEXT NOT NULL DEFAULT '',
            published_by TEXT, published_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(atomic_step_id) REFERENCES atomic_flow_steps(id)
        );
        CREATE TABLE IF NOT EXISTS testing_bot_messages (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL,
            message TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS app_behavior_rules (
            rule_id TEXT PRIMARY KEY, user_state TEXT NOT NULL,
            intent TEXT NOT NULL, trigger_terms TEXT NOT NULL DEFAULT '[]',
            expected_behavior TEXT NOT NULL, yaml_guidance TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'approved',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS article_references (
            id INTEGER PRIMARY KEY, label TEXT NOT NULL, url TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT 'Article Page', article_type TEXT NOT NULL DEFAULT '',
            user_state TEXT NOT NULL DEFAULT 'ANY', notes TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(url, module, article_type)
        );
        """)
        db.execute(
            "INSERT OR IGNORE INTO portal_settings(key,value) VALUES('case_timeout_seconds','300')"
        )
        db.execute(
            "INSERT OR IGNORE INTO portal_settings(key,value) VALUES('execution_batch_size','10')"
        )
        job_columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
        if "priority" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
        if "request_mode" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN request_mode TEXT NOT NULL DEFAULT 'queue'")
        if "batch_start" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN batch_start INTEGER NOT NULL DEFAULT 0")
        if "batch_number" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN batch_number INTEGER NOT NULL DEFAULT 1")
        if "batch_count" not in job_columns:
            db.execute("ALTER TABLE jobs ADD COLUMN batch_count INTEGER NOT NULL DEFAULT 1")
        result_columns = {row["name"] for row in db.execute("PRAGMA table_info(job_results)")}
        if "execution_status" not in result_columns:
            db.execute("ALTER TABLE job_results ADD COLUMN execution_status TEXT NOT NULL DEFAULT ''")
        if "condition_status" not in result_columns:
            db.execute("ALTER TABLE job_results ADD COLUMN condition_status TEXT NOT NULL DEFAULT 'not_checked'")
        if "condition_details" not in result_columns:
            db.execute("ALTER TABLE job_results ADD COLUMN condition_details TEXT NOT NULL DEFAULT ''")
        flow_columns = {row["name"] for row in db.execute("PRAGMA table_info(app_memory_flows)")}
        for name, definition in (
            ("search_text", "TEXT NOT NULL DEFAULT ''"),
            ("tags", "TEXT NOT NULL DEFAULT '[]'"),
            ("pass_count", "INTEGER NOT NULL DEFAULT 0"),
            ("fail_count", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if name not in flow_columns:
                db.execute(f"ALTER TABLE app_memory_flows ADD COLUMN {name} {definition}")
        draft_columns = {row["name"] for row in db.execute("PRAGMA table_info(drafts)")}
        if "generation_mode" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN generation_mode TEXT NOT NULL DEFAULT 'rules'")
        if "ai_confidence" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN ai_confidence REAL")
        if "ai_assumptions" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN ai_assumptions TEXT NOT NULL DEFAULT '[]'")
        if "traceability" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN traceability TEXT NOT NULL DEFAULT '[]'")
        if "coverage_status" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN coverage_status TEXT NOT NULL DEFAULT 'incomplete'")
        if "user_state" not in draft_columns:
            db.execute("ALTER TABLE drafts ADD COLUMN user_state TEXT NOT NULL DEFAULT ''")
        db.execute("""CREATE TABLE IF NOT EXISTS user_state_rules (
            state TEXT PRIMARY KEY, description TEXT NOT NULL,
            rules TEXT NOT NULL DEFAULT '[]', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        for state, description in (
            ("ANONYMOUS", "User has not authenticated."),
            ("REGISTERED_USER", "Authenticated user without a confirmed subscription."),
            ("NON_SUBSCRIBER", "Authenticated user with no active subscription."),
            ("SUBSCRIBER", "Authenticated user with an active subscription."),
            ("FREE_TRIAL_USER", "Authenticated user with an active free trial."),
            ("EXPIRED_USER", "Authenticated user whose subscription has expired."),
        ):
            db.execute("INSERT OR IGNORE INTO user_state_rules(state,description) VALUES(?,?)", (state, description))
        behavior_rules = (
            ("ANON_LAUNCH_HOME", "ANONYMOUS", "launch anonymous app home",
             '["launch","fresh","anonymous","home","without sign in"]',
             "Clear app state, complete anonymous onboarding, wait for screen_home, and require SUBSCRIBE.",
             "Use appId com.mobstac.thehindu and runFlow ../Common/OPEN_ANONYMOUS_HOME.yaml."),
            ("ANON_BOOKMARK_LOGIN", "ANONYMOUS", "bookmark from article",
             '["bookmark","article","login to your account","screenshot"]',
             "Tapping Bookmark as an anonymous user opens Login to your account. Capture a screenshot and end without authenticating.",
             "Open a verified article, tap the verified Bookmark control, assert Login to your account, takeScreenshot, and stop."),
            ("ANON_COMMENT_LOGIN", "ANONYMOUS", "post comment from article",
             '["post a comment","comment","article","login to your account","screenshot"]',
             "Anonymous comment entry must lead to Login to your account. Do not submit a public comment or authenticate.",
             "ScrollUntilVisible Post a comment, enter only safe test text when required, assert Login to your account, takeScreenshot, and stop."),
            ("ANON_MONETISATION", "ANONYMOUS", "anonymous ads and subscribe",
             '["advertisement","taboola","sticky ad","subscribe","anonymous","home","article"]',
             "Anonymous users can see Subscribe, inline ads, sticky ads, and recommendation advertising. Missing network inventory is not automatically an app bug.",
             "Use validated SUBSCRIBE and ADVERTISEMENT selectors; use conditional handling only for allowed dynamic ad interruptions."),
            ("SUBSCRIBER_ENTITLEMENT", "SUBSCRIBER", "subscriber entitlement",
             '["subscriber","advertisement","subscribe","premium"]',
             "An active subscriber must not see advertisements or Subscribe upsells and can access entitled content.",
             "AssertNotVisible SUBSCRIBE and ADVERTISEMENT after the verified subscriber setup flow."),
            ("SUB_HOME_LAUNCH", "SUBSCRIBER", "launch subscribed home",
             '["launch","subscriber","subscribed credentials","home","fresh state"]',
             "Establish a fresh app state, authenticate with configured subscriber credentials, and wait for screen_home.",
             "Use appId com.mobstac.thehindu and the verified OPEN_SUBSCRIBER_HOME.yaml setup flow; assert screen_home."),
            ("SUB_HOME_NO_MONETISATION", "SUBSCRIBER", "subscriber home monetisation",
             '["home","subscribe button","advertisement","sticky ad","taboola","subscriber"]',
             "A subscribed user must not see the Subscribe upsell, inline advertisements, sticky ads, or Taboola advertising on Home.",
             "Use assertNotVisible for validated SUBSCRIBE and ADVERTISEMENT selectors. Validate sticky/Taboola absence only with current verified selectors."),
            ("SUB_HOME_REFRESH_CONTENT", "SUBSCRIBER", "subscriber home refresh and content",
             '["pull to refresh","home","sections","widgets","timestamps","cards","navigation"]',
             "Pull-to-refresh must complete while Home remains loaded; Home sections, widgets, timestamps, cards, and navigation must remain usable.",
             "Perform a downward refresh gesture, wait for animation, assert screen_home, then validate applicable content with stable locators."),
            ("SUB_ARTICLE_FULL_ACCESS", "SUBSCRIBER", "subscriber article access",
             '["article","premium","full access","paywall","subscribe prompt"]',
             "Subscribed users can read entitled full and premium articles without a paywall or subscription prompt.",
             "Open a verified article_card or controlled premium deep link, assert screen_article_detail, and assertNotVisible the paywall/Subscribe prompt."),
            ("SUB_AI_SUMMARY_ENTITLED", "SUBSCRIBER", "subscriber AI Summary",
             '["ai summary","summary","article faqs","subscriber","subscription prompt"]',
             "On a controlled eligible article, AI Summary opens entitled Summary and Article FAQs content without a subscription prompt.",
             "Use controlled eligible article data; open AI Summary and assert Summary plus Article FAQs, then assert the upsell is absent."),
            ("SUB_ARTICLE_ACTIONS", "SUBSCRIBER", "subscriber bookmark share and comment",
             '["bookmark","share","post comment","article","subscriber","success toast"]',
             "Bookmark can succeed for an authenticated subscriber; Share can open normally; Post Comment must not request login. Never submit a public comment during validation.",
             "Validate Bookmark selected/success state, inspect the stable share sheet, and verify comment entry without final submission or a Login to your account redirect."),
            ("SUB_ARTICLE_FOOTER", "SUBSCRIBER", "subscriber post article sections",
             '["related topics","recommended","headlines","post article","subscriber"]',
             "Related Topics, Recommended, and Headlines are asserted only when supported by the controlled article type.",
             "Scroll with scrollUntilVisible and assert each section required by the selected article test data; do not turn content-dependent sections into universal assertions."),
            ("SUB_ARTICLE_PAGER_SESSION", "SUBSCRIBER", "subscriber article pager",
             '["swipe left","swipe right","article pager","subscriber state","interstitial"]',
             "Left/right article paging must preserve the subscribed session and must not show advertising interstitials.",
             "After every pager swipe assert screen_article_detail, assertNotVisible ad_iframe, and retain subscriber entitlement assertions."),
            ("SUB_FEATURE_ENTITLEMENTS", "SUBSCRIBER", "subscriber entitled features",
             '["games","epaper","e-paper","ebooks","entitled","subscription plan"]',
             "Games, ePaper, Ebooks, and other features are accessible only as allowed by the configured subscription plan.",
             "Use plan-controlled test credentials and validate only entitlements guaranteed by that account's test data."),
            ("SUB_LOGOUT_BOUNDARY", "SUBSCRIBER", "subscriber logout",
             '["logout","log out","anonymous","subscriber","separate flow"]',
             "Logout changes the account from Subscriber to Anonymous and therefore belongs in a separate state-transition flow.",
             "Do not append Logout to ordinary subscriber feature cases; use a dedicated logout flow and verify anonymous Login/Create account state afterward."),
            ("SUB_RESULT_CLASSIFICATION", "SUBSCRIBER", "subscriber pass fail review outcomes",
             '["pass","fail","needs review","conditional","subscriber","expected result"]',
             "PASS requires the asserted subscriber behavior. FAIL applies to authentication failure, lost entitlement, unexpected paywall or login gate, blocked navigation, or missing controlled content. Dynamic article features without controlled test data require review rather than a false failure.",
             "Use strict assertions for screen identity, authentication, entitlement and controlled fixtures. Use conditional runFlow plus screenshots for article-dependent AI Summary, comments and footer sections when controlled data is unavailable."),
            ("SUB_NON_DESTRUCTIVE_ACTIONS", "SUBSCRIBER", "subscriber non destructive interactions",
             '["bookmark","comment","logout","share","non destructive","subscriber"]',
             "Tests must not publish comments, purchase plans, or accidentally log out before the final dedicated boundary case. Bookmark state may be restored after validation when repeatability requires it.",
             "Enter comment text only when needed and exit without submitting; close the share sheet; keep Logout in the last isolated case; restore mutable Bookmark state when practical."),
            ("ARTICLE_EVIDENCE_SETTLE", "ALL", "article screenshot evidence",
             '["article","screenshot","capture","wait","visual","evidence"]',
             "Every Article Page screenshot is captured only after the UI has settled.",
             "Place a parameterless waitForAnimationToEnd immediately before every takeScreenshot."),
            ("ARTICLE_PRESENTATION_VARIANTS", "ALL", "article theme and text size variants",
             '["article","theme","dark","light","text size","reading options"]',
             "The same controlled article is checked in supported themes and multiple text sizes without changing its content identity.",
             "Open one controlled Article Library URL, change theme and text size through validated controls, wait before screenshots, and restore defaults."),
            ("ARTICLE_AUDIO_30_SECONDS", "ALL", "listen to article playback",
             '["article","listen","audio","play","pause","30 seconds"]',
             "When Listen to Article is supported, playback remains active for at least 30 seconds before Pause and progress are verified.",
             "Use a controlled audio-capable reference, verify Play/Pause, retain playback for a measured 30 seconds, then capture settled evidence."),
            ("ARTICLE_RECOMMENDED_NAVIGATION", "ALL", "recommended article navigation",
             '["article","recommended","related","headline","open"]',
             "When Recommended content is supported, one item opens as a new valid article and Back returns safely.",
             "ScrollUntilVisible Recommended, tap one current item without a fixed headline, assert screen_article_detail, capture settled evidence, and use Back."),
        )
        db.executemany(
            """INSERT OR IGNORE INTO app_behavior_rules(
                   rule_id,user_state,intent,trigger_terms,expected_behavior,yaml_guidance)
               VALUES(?,?,?,?,?,?)""",
            behavior_rules,
        )
        username = os.getenv("PORTAL_ADMIN_USER", "admin")
        password = os.getenv("PORTAL_ADMIN_PASSWORD", "admin")
        db.execute(
            "INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
            (username, generate_password_hash(password), "admin"),
        )
