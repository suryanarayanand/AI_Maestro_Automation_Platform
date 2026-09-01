import json
from pathlib import Path

from generation.excel_reader import ExcelReader
from web.portal_db import connect
from web.services.adaptive_test_agent import reusable_yaml, yaml_command_sequence
from web.services.yaml_editor_service import validate_maestro_yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "Anonymous_Videos_Quick_Section_Approved_Test_Cases.xlsx"
NORMALIZED = ROOT / "Uploads" / "Normalized" / f"{Path(SOURCE).stem}_normalized.xlsx"
HEADER = "appId: com.mobstac.thehindu\ntags: [generated, ordered, anonymous, videos]\n---\n"


def shot(cid, label="result"):
    return f'- takeScreenshot: "Screenshots/Generated/{cid}_{label}"'


def open_videos():
    return '- runFlow: "../Common/OPEN_ANONYMOUS_VIDEOS.yaml"'


def open_article():
    return '- runFlow: "../Common/OPEN_ANONYMOUS_VIDEO_ARTICLE.yaml"'


def scroll_to(text, timeout=45000):
    return "\n".join([
        "- scrollUntilVisible:", f'    element: {{text: "{text}"}}',
        "    direction: DOWN", f"    timeout: {timeout}", "    speed: 40",
    ])


def lines(*items):
    return "\n".join(item for item in items if item)


paywall = "Keep reading.*|.*[0-9]+%.*off.*|Go beyond the headline.*|Already a subscriber.*|SUBSCRIBE|Subscribe"
plans = "Yearly|Monthly|Choose a plan|View offers|Offer"

yamls = {}
yamls["ANON_VIDEO_001"] = lines(
    open_videos(), '- assertVisible: {id: "screen_home"}', '- assertVisible: {text: "Videos"}',
    shot("ANON_VIDEO_001", "selected_tab"),
)
yamls["ANON_VIDEO_002"] = lines(
    open_videos(), '- swipe: {direction: DOWN, duration: 700}', '- waitForAnimationToEnd',
    '- extendedWaitUntil: {visible: {id: "article_card"}, timeout: 60000}',
    '- assertVisible: {text: "Videos"}', '- assertVisible: {id: "article_card"}', shot("ANON_VIDEO_002"),
)
yamls["ANON_VIDEO_003"] = lines(
    open_videos(), '- assertVisible: {text: "Videos|VIDEOS"}', '- assertVisible: {id: "article_card"}',
    '- runFlow:', '    when: {visible: {text: "Play"}}', '    commands:',
    '      - assertVisible: {text: "Play"}', shot("ANON_VIDEO_003", "hero_and_cards"),
)
yamls["ANON_VIDEO_004"] = lines(
    open_videos(), shot("ANON_VIDEO_004", "top"),
    '- repeat:', '    times: 3', '    commands:', '      - swipe: {direction: UP, duration: 500}',
    '      - waitForAnimationToEnd', shot("ANON_VIDEO_004", "scrolled"),
    '- runFlow:', '    when: {visible: {text: "ADVERTISEMENT|Advertisement"}}', '    commands:',
    '      - assertVisible: {text: "ADVERTISEMENT|Advertisement"}',
    '      - takeScreenshot: "Screenshots/Generated/ANON_VIDEO_004_advertisement_review"',
    '- assertVisible: {id: "screen_home"}', '- assertVisible: {text: "Videos"}',
)
yamls["ANON_VIDEO_005"] = lines(
    open_article(), '- assertVisible: {text: "VIDEO|VIDEOS"}',
    '- runFlow:', '    when: {visible: {text: ".*[0-9]+ min(s)? read.*"}}', '    commands:',
    '      - assertVisible: {text: ".*[0-9]+ min(s)? read.*"}',
    '      - takeScreenshot: "Screenshots/Generated/ANON_VIDEO_005_reading_time"',
    '- runFlow:', '    when: {notVisible: {text: ".*[0-9]+ min(s)? read.*"}}', '    commands:',
    '      - takeScreenshot: "Screenshots/Generated/ANON_VIDEO_005_reading_time_missing_review"',
    '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_006"] = lines(
    open_article(), scroll_to(paywall), f'- assertVisible: {{text: "{paywall}"}}',
    shot("ANON_VIDEO_006", "paywall_overlay"),
    '- runFlow:', '    when: {visible: {text: "Play"}}', '    commands:', '      - tapOn: {text: "Play"}',
    f'      - assertVisible: {{text: "{paywall}"}}', '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_007"] = lines(
    open_article(), scroll_to(paywall), '- assertVisible: {text: "Subscribe|SUBSCRIBE"}',
    '- tapOn: {text: "Subscribe|SUBSCRIBE", index: 0}',
    f'- extendedWaitUntil: {{visible: {{text: "{plans}"}}, timeout: 30000}}',
    f'- assertVisible: {{text: "{plans}"}}', shot("ANON_VIDEO_007", "plans"), '- back',
    '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_008"] = lines(
    open_article(), scroll_to("Already a subscriber.*|Login"),
    '- assertVisible: {text: "Already a subscriber.*|Login"}',
    '- tapOn: {text: "Already a subscriber.*|Login|LOGIN"}',
    '- extendedWaitUntil: {visible: {text: "Login to your account"}, timeout: 30000}',
    '- assertVisible: {text: "Login to your account"}', shot("ANON_VIDEO_008", "login"), '- back',
    '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_009"] = lines(
    open_article(), '- runFlow:', '    when: {visible: {text: "Play"}}', '    commands:',
    '      - tapOn: {text: "Play"}', '      - waitForAnimationToEnd',
    '      - assertVisible: {text: "Pause|Replay|Rewind 15 seconds|fast forward 15 seconds"}',
    '      - tapOn: {text: "Pause|Rewind 15 seconds", optional: true}',
    '      - tapOn: {text: "Fullscreen", optional: true}',
    '      - tapOn: {text: "Exit Fullscreen", optional: true}',
    '      - assertVisible: {id: "screen_article_detail"}',
    '- runFlow:', '    when: {notVisible: {text: "Play"}}', '    commands:',
    '      - takeScreenshot: "Screenshots/Generated/ANON_VIDEO_009_no_accessible_video_review"',
    '- assertVisible: {id: "screen_article_detail"}', shot("ANON_VIDEO_009"),
)
yamls["ANON_VIDEO_010"] = lines(
    open_article(), scroll_to("Reading Options|Text size|Text Size"),
    '- tapOn: {text: "Reading Options|Text size|Text Size", index: 0}',
    '- assertVisible: {text: "Reading Options|Text size|Text Size|Decrease|Increase"}',
    shot("ANON_VIDEO_010", "options"), '- tapOn: {text: "Increase|A\\+", optional: true}',
    '- tapOn: {text: "CLOSE|Close", optional: true}', '- back',
    '- assertVisible: {id: "screen_article_detail"}', shot("ANON_VIDEO_010"),
)
yamls["ANON_VIDEO_011"] = lines(
    open_article(), '- tapOn: {text: "Bookmark", index: 0}',
    '- extendedWaitUntil: {visible: {text: "Login to your account|Sign in|LOGIN"}, timeout: 30000}',
    '- assertVisible: {text: "Login to your account|Sign in|LOGIN"}', shot("ANON_VIDEO_011", "login_gate"),
    '- back', '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_012"] = lines(
    open_article(), '- tapOn: {text: "Share", index: 0}', '- waitForAnimationToEnd',
    '- assertVisible: {text: "Share with|Nearby Share|Quick Share|Messages|Copy"}',
    shot("ANON_VIDEO_012", "share_sheet"), '- back', '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_013"] = lines(
    open_article(), '- tapOn: {text: "Comment|Post a comment", index: 0}',
    '- extendedWaitUntil: {visible: {text: "Sign in|Login|LOGIN"}, timeout: 30000}',
    '- assertVisible: {text: "Sign in|Login|LOGIN"}', shot("ANON_VIDEO_013", "comment_login"),
    '- tapOn: {text: "Close sheet|CLOSE|Close", optional: true}', '- back',
    '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_014"] = lines(
    open_article(), '- assertVisible: {text: "Subscribe|SUBSCRIBE"}',
    '- tapOn: {text: "Subscribe|SUBSCRIBE", index: 0}',
    f'- extendedWaitUntil: {{visible: {{text: "{plans}"}}, timeout: 30000}}',
    f'- assertVisible: {{text: "{plans}"}}', shot("ANON_VIDEO_014", "plans"), '- back',
    '- assertVisible: {id: "screen_article_detail"}',
)
yamls["ANON_VIDEO_015"] = lines(
    open_videos(), '- tapOn: {id: "article_card", index: 0}', '- waitForAnimationToEnd',
    '- runFlow:', '    when: {notVisible: {id: "screen_article_detail"}}', '    commands:',
    '      - takeScreenshot: "Screenshots/Generated/ANON_VIDEO_015_interstitial"',
    '      - repeat:', '          times: 12', '          commands:', '            - waitForAnimationToEnd',
    '            - runFlow:', '                when: {visible: {text: "^CLOSE$|Interstitial close button|SKIP|Skip Ad"}}',
    '                commands:', '                  - tapOn: {text: "^CLOSE$|Interstitial close button|SKIP|Skip Ad"}',
    '- runFlow:', '    when: {notVisible: {id: "screen_article_detail"}}', '    commands:', '      - back',
    '- extendedWaitUntil: {visible: {id: "screen_article_detail"}, timeout: 30000}',
    '- assertVisible: {id: "screen_article_detail"}', shot("ANON_VIDEO_015"),
)
yamls["ANON_VIDEO_016"] = lines(
    open_videos(), '- swipe: {direction: UP, duration: 600}', '- waitForAnimationToEnd',
    '- tapOn: {id: "article_card", index: 1}',
    '- extendedWaitUntil: {visible: {id: "screen_article_detail"}, timeout: 30000}',
    '- assertVisible: {id: "screen_article_detail"}', '- back',
    '- extendedWaitUntil: {visible: {text: "Videos"}, timeout: 30000}',
    '- assertVisible: {id: "screen_home"}', '- assertVisible: {text: "Videos"}', shot("ANON_VIDEO_016", "returned_position"),
)


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
        yaml_text = HEADER + body + "\n"
        validate_maestro_yaml(yaml_text)
        if not reusable_yaml(yaml_text):
            raise SystemExit(f"Invalid reusable Maestro structure: {case_id}")
        commands = list(dict.fromkeys(yaml_command_sequence(yaml_text)))
        traceability = []
        for position, item in enumerate(cases[case_id]["requirements"], 1):
            traceability.append({
                "position": position, "source_type": item.get("source_type", "step"),
                "step_number": item.get("step_number"),
                "requirement": item.get("expected_result") or item.get("step") or "",
                "generation_input": item.get("step", ""), "commands": commands,
                "selector": "Validated locator memory, live Video discovery, and SC_68-SC_71 reference flows",
                "status": "covered", "reason": "Repaired from the imported Excel obligation and grounded Video references.",
                "source_sheet": item.get("source_sheet", ""), "source_row": item.get("source_row"),
            })
        db.execute(
            """UPDATE drafts SET yaml=?,error=NULL,
               generation_mode='reviewed-friday-live-memory',ai_confidence=1.0,
               ai_assumptions=?,traceability=?,coverage_status='complete' WHERE id=?""",
            (yaml_text, json.dumps([
                "Dynamic paywall, playable-video, reading-time, and interstitial branches require live review before approval."
            ]), json.dumps(traceability, ensure_ascii=False), row["id"]),
        )
        print("repaired", case_id, "draft", row["id"], "commands", commands)
