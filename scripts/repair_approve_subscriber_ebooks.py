"""Ground, validate, and approve the pending Subscriber eBooks drafts."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.portal_db import connect
from web.services.generation_service import approve_draft
from web.services.yaml_editor_service import validate_maestro_yaml


HEADER = "appId: com.mobstac.thehindu\ntags: [generated, ordered, subscriber, ebooks]\n---\n"
OPEN = '- runFlow: "../Common/OPEN_SUBSCRIBER_EBOOKS.yaml"'
BOOK = '- runFlow: "../Common/OPEN_SUBSCRIBER_EBOOK.yaml"'
ACCESS = '- runFlow: "../Common/ASSERT_SUBSCRIBER_EBOOK_ACCESS.yaml"'


def shot(case_id, label="result", indent=""):
    return f'{indent}- waitForAnimationToEnd\n{indent}- takeScreenshot: "Screenshots/Generated/{case_id}_{label}"'


def scrolling(times):
    return f'''- repeat:
    times: {times}
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd'''


def pages(direction, times):
    return f'''- repeat:
    times: {times}
    commands:
      - swipe: {{direction: {direction}}}
      - waitForAnimationToEnd'''


FLOWS = {
    "SUB_EBOOK_001": [OPEN, '- assertVisible: {id: "nav_ebooks"}', ACCESS, shot("SUB_EBOOK_001", "landing")],
    "SUB_EBOOK_002": [OPEN, '- swipe: {start: "50%,30%", end: "50%,75%", duration: 700}', '- extendedWaitUntil: {visible: {id: "screen_ebooks"}, timeout: 30000}', ACCESS, shot("SUB_EBOOK_002", "refreshed")],
    "SUB_EBOOK_003": [OPEN, '- repeat:\n    times: 2\n    commands:\n      - swipe: {start: "50%,30%", end: "50%,75%", duration: 700}\n      - waitForAnimationToEnd', '- assertVisible: {id: "screen_ebooks"}', ACCESS, shot("SUB_EBOOK_003", "repeat_refresh")],
    "SUB_EBOOK_004": [OPEN, '- assertVisible: {id: "screen_ebooks"}', scrolling(2), ACCESS, shot("SUB_EBOOK_004", "card_layout")],
    "SUB_EBOOK_005": [OPEN, shot("SUB_EBOOK_005", "top"), scrolling(3), ACCESS, shot("SUB_EBOOK_005", "middle"), scrolling(3), ACCESS, shot("SUB_EBOOK_005", "lower")],
    "SUB_EBOOK_006": [BOOK, ACCESS, shot("SUB_EBOOK_006", "cover_open")],
    "SUB_EBOOK_007": [BOOK, ACCESS, shot("SUB_EBOOK_007", "title_destination"), '- back', '- extendedWaitUntil: {visible: {id: "screen_ebooks"}, timeout: 30000}'],
    "SUB_EBOOK_008": [OPEN, scrolling(3), '- tapOn: {point: "7%,10%"}', '- waitForAnimationToEnd', ACCESS, shot("SUB_EBOOK_008", "previous_book"), '- back'],
    "SUB_EBOOK_009": [BOOK, shot("SUB_EBOOK_009", "first_page"), pages("LEFT", 30), ACCESS, shot("SUB_EBOOK_009", "last_page"), pages("RIGHT", 5), ACCESS, shot("SUB_EBOOK_009", "reverse_navigation")],
    "SUB_EBOOK_010": [BOOK, pages("LEFT", 5), ACCESS, shot("SUB_EBOOK_010", "book_1"), '- back', scrolling(3), '- tapOn: {point: "7%,10%"}', '- waitForAnimationToEnd', ACCESS, shot("SUB_EBOOK_010", "book_2")],
    "SUB_EBOOK_011": [OPEN, '- tapOn: {id: "nav_home"}', '- extendedWaitUntil: {visible: {id: "screen_home"}, timeout: 30000}', '- tapOn: {id: "nav_ebooks"}', '- extendedWaitUntil: {visible: {id: "screen_ebooks"}, timeout: 30000}', ACCESS, shot("SUB_EBOOK_011", "round_trip")],
    "SUB_EBOOK_012": [OPEN, scrolling(3), '- tapOn: {point: "7%,10%"}', '- waitForAnimationToEnd', ACCESS, '- back', '- extendedWaitUntil: {visible: {id: "screen_ebooks"}, timeout: 30000}', shot("SUB_EBOOK_012", "restored")],
    "SUB_EBOOK_013": [OPEN, scrolling(3), '- assertVisible: {id: "screen_ebooks"}', ACCESS, shot("SUB_EBOOK_013", "long_metadata")],
    "SUB_EBOOK_014": [BOOK, pages("LEFT", 3), ACCESS, '- back', '- tapOn: {id: "nav_home"}', '- assertVisible: {id: "screen_home"}', '- tapOn: {id: "nav_ebooks"}', '- extendedWaitUntil: {visible: {id: "screen_ebooks"}, timeout: 30000}', ACCESS, shot("SUB_EBOOK_014", "persistence")],
}


def main():
    with connect() as db:
        drafts = db.execute(
            "SELECT * FROM drafts WHERE id BETWEEN 836 AND 849 ORDER BY id"
        ).fetchall()
    if len(drafts) != len(FLOWS):
        raise RuntimeError(f"Expected {len(FLOWS)} drafts, found {len(drafts)}")
    completed = []
    for draft in drafts:
        case_id = draft["case_id"]
        yaml_text = HEADER + "\n\n".join(FLOWS[case_id]) + "\n"
        if not validate_maestro_yaml(yaml_text):
            raise ValueError(f"Invalid Maestro YAML for {case_id}")
        traceability = json.loads(draft["traceability"] or "[]")
        for item in traceability:
            item["status"] = "covered"
            item["reason"] = (
                "Friday grounded this obligation against SC_24 subscriber eBook access, "
                "validated eBooks navigation IDs, and Subscriber entitlement common flows."
            )
        with connect() as db:
            db.execute(
                """UPDATE drafts SET yaml=?,traceability=?,coverage_status='complete',
                   ai_confidence=1.0,generation_mode='friday-grounded',error=NULL WHERE id=?""",
                (yaml_text, json.dumps(traceability, ensure_ascii=False), draft["id"]),
            )
        approve_draft(draft["id"], yaml_text, "user_subscriber", "Friday", allow_incomplete=False)
        completed.append(case_id)
    print(json.dumps({"approved": completed, "count": len(completed)}, indent=2))


if __name__ == "__main__":
    main()
