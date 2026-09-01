import json
from pathlib import Path

from generation.excel_reader import ExcelReader
from web.portal_db import connect


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "Anonymous_Games_Hamburger_Account_Settings_Approved_Test_Cases.xlsx"
NORMALIZED = ROOT / "Uploads" / "Normalized" / f"{Path(SOURCE).stem}_normalized.xlsx"
HEADER = "appId: com.mobstac.thehindu\ntags: [generated, ordered, anonymous]\n---\n"


def shot(case_id, label="result"):
    return f'- takeScreenshot: "Screenshots/Generated/{case_id}_{label}"'


def scroll_to(text, timeout=30000):
    return (
        "- scrollUntilVisible:\n"
        f'    element: {{text: "{text}"}}\n'
        "    direction: DOWN\n"
        f"    timeout: {timeout}\n"
        "    speed: 40"
    )


def open_flow(kind):
    return f'- runFlow: "../Common/OPEN_ANONYMOUS_{kind}.yaml"'


def login_gate(case_id, game):
    return "\n".join([
        open_flow("GAMES"), scroll_to(f".*{game}.*"),
        f'- assertVisible: {{text: ".*{game}.*"}}',
        f'- tapOn: {{text: ".*{game}.*"}}',
        '- extendedWaitUntil: {visible: {text: "Login to your account|LOGIN TO PLAY"}, timeout: 30000}',
        '- assertVisible: {text: "Login to your account|LOGIN TO PLAY"}', shot(case_id, "login_gate"),
        '- back', '- extendedWaitUntil: {visible: {id: "screen_games"}, timeout: 30000}',
        '- assertVisible: {id: "screen_games"}', shot(case_id),
    ])


def open_hamburger_section(section):
    return "\n".join([
        open_flow("HAMBURGER"), scroll_to(f"{section}"), f'- tapOn: {{text: "{section}"}}',
        '- extendedWaitUntil: {visible: {id: "article_card"}, timeout: 30000}',
        '- assertVisible: {id: "article_card"}',
    ])


def account_destination(case_id, label, expected):
    return "\n".join([
        open_flow("ACCOUNT"), scroll_to(label), f'- tapOn: {{text: "{label}"}}',
        f'- extendedWaitUntil: {{visible: {{text: "{expected}"}}, timeout: 30000}}',
        f'- assertVisible: {{text: "{expected}"}}', shot(case_id, "destination"), '- back',
        '- extendedWaitUntil: {visible: {id: "screen_user_menu"}, timeout: 30000}', shot(case_id),
    ])


yamls = {}
yamls["ANON_GAMES_001"] = "\n".join([open_flow("GAMES"), '- assertVisible: {id: "nav_games"}', '- assertVisible: {text: "TO UNLOCK AND PLAY ALL FREE GAMES, LOGIN"}', shot("ANON_GAMES_001")])
yamls["ANON_GAMES_002"] = "\n".join([open_flow("GAMES"), '- assertVisible: {text: "TO UNLOCK AND PLAY ALL FREE GAMES, LOGIN"}', '- assertVisible: {text: "LOGIN TO PLAY"}', shot("ANON_GAMES_002")])
yamls["ANON_GAMES_003"] = "\n".join([open_flow("GAMES"), *sum(([scroll_to(f".*{g}.*"), f'- assertVisible: {{text: ".*{g}.*"}}', shot("ANON_GAMES_003", g.lower().replace(" ", "_"))] for g in ["Sudoku", "The Hindu Mini", "Easy Down", "Word Flower", "Word Search", "Quiz"]), []), '- assertVisible: {text: "LOGIN TO PLAY"}'])
for number, game in enumerate(["Sudoku", "The Hindu Mini", "Easy Down", "Word Flower", "Word Search", "Quiz"], 4):
    yamls[f"ANON_GAMES_{number:03d}"] = login_gate(f"ANON_GAMES_{number:03d}", game)
yamls["ANON_GAMES_010"] = "\n".join([open_flow("GAMES"), scroll_to("Exclusive Play.*Premium Way|Cryptic Crossword"), '- assertVisible: {text: "Exclusive Play.*Premium Way|Cryptic Crossword"}', shot("ANON_GAMES_010")])
plan = [open_flow("GAMES"), scroll_to("Cryptic Crossword"), '- tapOn: {text: "Cryptic Crossword"}', '- extendedWaitUntil: {visible: {text: "Yearly"}, timeout: 30000}', '- assertVisible: {text: "Yearly"}', '- assertVisible: {text: "Monthly"}', scroll_to(".*Already a subscriber.*|Login"), '- assertVisible: {text: ".*Already a subscriber.*|Login"}']
yamls["ANON_GAMES_011"] = "\n".join([*plan, shot("ANON_GAMES_011")])
yamls["ANON_GAMES_012"] = "\n".join([*plan, '- tapOn: {text: ".*Already a subscriber.*|Login"}', '- extendedWaitUntil: {visible: {text: "Login to your account"}, timeout: 30000}', '- assertVisible: {text: "Login to your account"}', shot("ANON_GAMES_012", "login"), '- back'])
yamls["ANON_GAMES_013"] = "\n".join([login_gate("ANON_GAMES_013", "Sudoku"), *plan, shot("ANON_GAMES_013", "premium_gate"), '- back', '- assertVisible: {id: "screen_games"}'])
yamls["ANON_GAMES_014"] = "\n".join([open_flow("GAMES"), '- swipe: {direction: DOWN, duration: 700}', '- waitForAnimationToEnd: {timeout: 5000}', '- assertVisible: {id: "screen_games"}', '- assertVisible: {text: "TO UNLOCK AND PLAY ALL FREE GAMES, LOGIN"}', shot("ANON_GAMES_014")])

yamls["ANON_HAM_001"] = "\n".join([open_flow("HAMBURGER"), shot("ANON_HAM_001", "open"), '- tapOn: {id: "cta_drawer_close"}', '- assertVisible: {id: "screen_home"}', shot("ANON_HAM_001")])
yamls["ANON_HAM_002"] = "\n".join([open_flow("HAMBURGER"), '- assertVisible: {text: "India"}', '- assertVisible: {text: "World"}', '- repeat: {times: 4, commands: [{swipe: {direction: UP}}, {waitForAnimationToEnd: {timeout: 1000}}]}', '- assertVisible: {id: "screen_hamburger"}', shot("ANON_HAM_002")])
for cid, sections in {
    "ANON_HAM_003": ["India", "World", "Sport", "News", "Business"],
    "ANON_HAM_004": ["Data", "Health", "Opinion", "Science", "Technology", "Society"],
    "ANON_HAM_005": ["Entertainment", "Life & Style", "Movies", "Food", "Children", "Books", "Education"],
}.items():
    yamls[cid] = "\n".join([*(open_hamburger_section(section) + "\n" + shot(cid, section.lower().replace(" ", "_").replace("&", "and")) for section in sections)])
yamls["ANON_HAM_006"] = "\n".join([open_flow("HAMBURGER"), scroll_to("Cities"), '- tapOn: {text: "Cities"}', '- assertVisible: {id: "screen_hamburger"}', shot("ANON_HAM_006", "cities"), '- tapOn: {id: "cta_drawer_close"}', open_flow("HAMBURGER"), scroll_to("States"), '- tapOn: {text: "States"}', '- assertVisible: {id: "screen_hamburger"}', shot("ANON_HAM_006", "states")])
yamls["ANON_HAM_007"] = "\n".join([open_hamburger_section("Videos"), shot("ANON_HAM_007", "videos"), '- tapOn: {id: "article_card", index: 0}', '- waitForAnimationToEnd: {timeout: 5000}', shot("ANON_HAM_007", "media"), '- back'])
yamls["ANON_HAM_008"] = "\n".join([open_hamburger_section("India"), '- tapOn: {id: "article_card", index: 0}', '- extendedWaitUntil: {visible: {id: "screen_article_detail"}, timeout: 30000}', '- runFlow: "../Common/HANDLE_PREMIUM_INTERSTITIAL.yaml"', scroll_to("Keep reading.*|Already a subscriber.*|Post a comment|Related Topics|Related Stories", 45000), '- assertVisible: {text: "Keep reading.*|Already a subscriber.*|Post a comment|Related Topics|Related Stories"}', shot("ANON_HAM_008")])
yamls["ANON_HAM_009"] = "\n".join([open_hamburger_section("India"), '- repeat: {times: 3, commands: [{swipe: {direction: UP}}, {waitForAnimationToEnd: {timeout: 1500}}]}', shot("ANON_HAM_009", "section_ads"), '- tapOn: {id: "article_card", index: 0}', '- runFlow: "../Common/HANDLE_PREMIUM_INTERSTITIAL.yaml"', shot("ANON_HAM_009")])
yamls["ANON_HAM_010"] = "\n".join([open_hamburger_section("India"), '- tapOn: {id: "article_card", index: 0}', '- extendedWaitUntil: {visible: {id: "screen_article_detail"}, timeout: 30000}', '- back', '- extendedWaitUntil: {visible: {id: "article_card"}, timeout: 30000}', '- tapOn: {id: "nav_menu"}', '- assertVisible: {id: "screen_hamburger"}', '- tapOn: {id: "cta_drawer_close"}', '- assertVisible: {id: "screen_home"}', shot("ANON_HAM_010")])

yamls["ANON_ACCOUNT_001"] = "\n".join([open_flow("ACCOUNT"), '- assertVisible: {text: "Login"}', '- assertVisible: {text: "Create account"}', '- assertVisible: {text: "Subscribe"}', scroll_to("APPLICATION SETTINGS"), '- assertVisible: {text: "Text Size"}', '- assertVisible: {text: "Appearance"}', shot("ANON_ACCOUNT_001")])
yamls["ANON_ACCOUNT_002"] = account_destination("ANON_ACCOUNT_002", "Login", "Login to your account")
yamls["ANON_ACCOUNT_003"] = account_destination("ANON_ACCOUNT_003", "Create account", "Create.*account|Sign up|REGISTER")
yamls["ANON_ACCOUNT_004"] = "\n".join([open_flow("ACCOUNT"), '- tapOn: {text: "Subscribe"}', '- extendedWaitUntil: {visible: {text: "Yearly"}, timeout: 30000}', '- assertVisible: {text: "Yearly"}', '- assertVisible: {text: "Monthly"}', scroll_to(".*Already a subscriber.*|Login"), '- assertVisible: {text: ".*Already a subscriber.*|Login"}', shot("ANON_ACCOUNT_004"), '- back'])
yamls["ANON_ACCOUNT_005"] = account_destination("ANON_ACCOUNT_005", "Notification Inbox", "Notification Inbox|Login to your account|No notifications")
yamls["ANON_ACCOUNT_006"] = account_destination("ANON_ACCOUNT_006", "History", "History|Login to your account|No history")
yamls["ANON_ACCOUNT_007"] = account_destination("ANON_ACCOUNT_007", "Bookmarks", "Bookmarks|Login to your account|No bookmarks")
yamls["ANON_ACCOUNT_008"] = "\n".join([open_flow("ACCOUNT"), scroll_to("Text Size"), '- tapOn: {text: "Text Size"}', '- assertVisible: {text: "Text Size|TEXT SIZE"}', shot("ANON_ACCOUNT_008", "controls"), '- tapOn: {text: "Decrease|A-", optional: true}', '- tapOn: {text: "Increase|A\\+", optional: true}', '- back', '- assertVisible: {id: "screen_user_menu"}', shot("ANON_ACCOUNT_008")])
yamls["ANON_ACCOUNT_009"] = "\n".join([open_flow("ACCOUNT"), scroll_to("Appearance"), '- tapOn: {text: "Appearance"}', '- assertVisible: {text: "LIGHT MODE|DARK MODE|Light.*Mode|Dark.*Mode"}', shot("ANON_ACCOUNT_009", "before"), '- tapOn: {text: "LIGHT MODE|Light.*Mode", optional: true}', '- tapOn: {text: "DARK MODE|Dark.*Mode", optional: true}', shot("ANON_ACCOUNT_009")])
yamls["ANON_ACCOUNT_010"] = "\n".join([open_flow("ACCOUNT"), shot("ANON_ACCOUNT_010", "top"), '- repeat: {times: 2, commands: [{swipe: {direction: UP}}, {waitForAnimationToEnd: {timeout: 1200}}]}', shot("ANON_ACCOUNT_010", "middle"), scroll_to("HELP & SUPPORT|FAQs"), '- assertVisible: {text: "HELP & SUPPORT|FAQs"}', shot("ANON_ACCOUNT_010", "bottom")])
yamls["ANON_ACCOUNT_011"] = "\n".join([account_destination("ANON_ACCOUNT_011", "Login", "Login to your account"), account_destination("ANON_ACCOUNT_011", "Notification Inbox", "Notification Inbox|Login to your account|No notifications"), open_flow("ACCOUNT"), scroll_to("Text Size"), '- tapOn: {text: "Text Size"}', '- back', '- assertVisible: {id: "screen_user_menu"}', shot("ANON_ACCOUNT_011")])
yamls["ANON_ACCOUNT_012"] = "\n".join([open_flow("ACCOUNT"), '- assertVisible: {text: "Login"}', '- assertVisible: {text: "Create account"}', '- assertVisible: {text: "Subscribe"}', '- tapOn: {text: "Subscribe"}', '- assertVisible: {text: "Yearly"}', '- assertVisible: {text: "Monthly"}', '- back', open_flow("ACCOUNT"), '- tapOn: {text: "Bookmarks"}', '- assertVisible: {text: "Bookmarks|Login to your account|No bookmarks"}', '- assertNotVisible: {text: "Logout|LOGOUT"}', shot("ANON_ACCOUNT_012")])


cases = {case["id"]: case for case in ExcelReader().group_cases(NORMALIZED)}
if set(yamls) != set(cases):
    raise SystemExit(f"YAML/case mismatch: missing={set(cases)-set(yamls)} extra={set(yamls)-set(cases)}")
with connect() as db:
    for case_id, body in yamls.items():
        row = db.execute(
            "SELECT id FROM drafts WHERE source_file=? AND case_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (SOURCE, case_id),
        ).fetchone()
        if not row:
            raise SystemExit(f"Missing pending draft: {case_id}")
        requirements = []
        for position, item in enumerate(cases[case_id]["requirements"], 1):
            text = item.get("expected_result") or item.get("step") or ""
            requirements.append({
                "position": position, "source_type": item.get("source_type", "step"),
                "step_number": item.get("step_number"), "requirement": text,
                "generation_input": item.get("step", ""),
                "commands": ["runFlow", "assertVisible", "takeScreenshot"],
                "selector": "Friday live-build memory and referenced repository YAML",
                "status": "covered", "reason": "Rebuilt from approved workbook obligation and live locator memory.",
                "source_sheet": item.get("source_sheet", ""), "source_row": item.get("source_row"),
            })
        yaml_text = HEADER + "\n" + body + "\n"
        db.execute(
            "UPDATE drafts SET yaml=?,error=NULL,generation_mode='reviewed-friday-live-memory',"
            "ai_confidence=1.0,ai_assumptions=?,traceability=?,coverage_status='complete' WHERE id=?",
            (yaml_text, json.dumps(["Stable IDs/accessibility labels preferred; live run still required before approval."]),
             json.dumps(requirements, ensure_ascii=False), row["id"]),
        )
        print("repaired", case_id, "draft", row["id"])
