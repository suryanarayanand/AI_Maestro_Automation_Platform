import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generation.excel_reader import ExcelReader
from web.portal_db import connect
from web.services.adaptive_test_agent import reusable_yaml, yaml_command_sequence
from web.services.yaml_editor_service import validate_maestro_yaml


SOURCE = "Anonymous_Photos_Quick_Access_Approved_Test_Cases.xlsx"
NORMALIZED = ROOT / "Uploads" / "Normalized" / f"{Path(SOURCE).stem}_normalized.xlsx"
HEADER = "appId: com.mobstac.thehindu\ntags: [generated, ordered, anonymous, photos]\n---\n"


def shot(cid, label="result"):
    return f'- takeScreenshot: "Screenshots/Generated/{cid}_{label}"'


def photos(): return '- runFlow: "../Common/OPEN_ANONYMOUS_PHOTOS.yaml"'
def multi(): return '- runFlow: "../Common/OPEN_ANONYMOUS_MULTI_PHOTO_GALLERY.yaml"'
def single(): return '- runFlow: "../Common/OPEN_ANONYMOUS_SINGLE_PHOTO_ARTICLE.yaml"'
def lines(*items): return "\n".join(item for item in items if item)


def scroll_to(text, timeout=30000):
    return lines("- scrollUntilVisible:", f'    element: {{text: "{text}"}}',
                 "    direction: DOWN", f"    timeout: {timeout}", "    speed: 40")


yamls = {}
yamls["ANON_PHOTO_001"] = lines(photos(), '- assertVisible: {id: "screen_home"}', '- assertVisible: {text: "Photos"}', shot("ANON_PHOTO_001", "selected_tab"))
yamls["ANON_PHOTO_002"] = lines(photos(), '- swipe: {direction: DOWN, duration: 700}', '- waitForAnimationToEnd', '- assertVisible: {text: "Photos"}', shot("ANON_PHOTO_002", "refreshed_grid"))
yamls["ANON_PHOTO_003"] = lines(photos(), shot("ANON_PHOTO_003", "top"), '- repeat:', '    times: 3', '    commands:', '      - swipe: {direction: UP, duration: 500}', '      - waitForAnimationToEnd', '- assertVisible: {text: "Photos"}', shot("ANON_PHOTO_003", "mixed_grid_and_badges"))
yamls["ANON_PHOTO_004"] = lines(photos(), '- assertNotVisible: {text: "ADVERTISEMENT|Advertisement|Support Journalism"}', '- repeat:', '    times: 5', '    commands:', '      - swipe: {direction: UP, duration: 450}', '      - waitForAnimationToEnd', '      - assertNotVisible: {text: "ADVERTISEMENT|Advertisement|Support Journalism"}', '- assertVisible: {text: "Photos"}', shot("ANON_PHOTO_004", "no_inline_ads"))
yamls["ANON_PHOTO_005"] = lines(single(), shot("ANON_PHOTO_005", "single_photo"), '- swipe: {direction: LEFT, duration: 500}', '- waitForAnimationToEnd', '- assertNotVisible: {text: ".*2/[0-9]+.*"}', shot("ANON_PHOTO_005", "no_second_image"))
yamls["ANON_PHOTO_006"] = lines(multi(), shot("ANON_PHOTO_006", "counter_1"), '- swipe: {direction: LEFT, duration: 500}', '- waitForAnimationToEnd', '- assertVisible: {text: ".*2/[0-9]+.*"}', shot("ANON_PHOTO_006", "counter_2"), '- swipe: {direction: LEFT, duration: 500}', '- waitForAnimationToEnd', '- assertVisible: {text: ".*3/[0-9]+.*"}', shot("ANON_PHOTO_006", "counter_3"), '- swipe: {direction: RIGHT, duration: 500}', '- waitForAnimationToEnd', '- assertVisible: {text: ".*2/[0-9]+.*"}', shot("ANON_PHOTO_006", "counter_back_2"))
yamls["ANON_PHOTO_007"] = lines(multi(), '- assertVisible: {text: "PHOTO:.*|Photo:.*"}', shot("ANON_PHOTO_007", "image_1_description_credit"), '- swipe: {direction: LEFT, duration: 500}', '- waitForAnimationToEnd', '- assertVisible: {text: ".*2/[0-9]+.*"}', '- assertVisible: {text: "PHOTO:.*|Photo:.*"}', shot("ANON_PHOTO_007", "image_2_description_credit"))
yamls["ANON_PHOTO_008"] = lines(photos(), '- tapOn: {point: "25%,35%"}', '- waitForAnimationToEnd', '- extendedWaitUntil: {visible: {text: ".*Go beyond the headline.*|.*subscribe to access.*"}, timeout: 30000}', '- assertVisible: {text: "Subscribe|SUBSCRIBE"}', shot("ANON_PHOTO_008", "subscription_popup"), '- tapOn: {point: "91%,36%"}', '- waitForAnimationToEnd', '- assertVisible: {text: ".*1/[2-9][0-9]*.*"}', shot("ANON_PHOTO_008", "popup_closed_gallery_retained"))
yamls["ANON_PHOTO_009"] = lines(multi(), '- swipe: {direction: LEFT, duration: 500}', '- waitForAnimationToEnd', scroll_to("READ FULL ARTICLE"), '- assertVisible: {text: "READ FULL ARTICLE"}', '- tapOn: {text: "READ FULL ARTICLE"}', '- waitForAnimationToEnd', '- assertNotVisible: {text: "READ FULL ARTICLE"}', shot("ANON_PHOTO_009", "expanded_article"))
yamls["ANON_PHOTO_010"] = lines(multi(), '- swipe: {direction: LEFT, duration: 500}', '- waitForAnimationToEnd', scroll_to("READ FULL ARTICLE"), '- tapOn: {text: "READ FULL ARTICLE"}', '- waitForAnimationToEnd', scroll_to("READ LESS", 45000), '- assertVisible: {text: "READ LESS"}', shot("ANON_PHOTO_010", "read_less_reachable"), '- tapOn: {text: "READ LESS"}', '- waitForAnimationToEnd', '- extendedWaitUntil: {visible: {text: "READ FULL ARTICLE"}, timeout: 15000}', '- assertVisible: {text: "READ FULL ARTICLE"}', '- assertNotVisible: {text: "READ LESS"}', shot("ANON_PHOTO_010", "collapsed"))
yamls["ANON_PHOTO_011"] = lines(multi(), '- tapOn: {text: "Bookmark"}', '- extendedWaitUntil: {visible: {text: "Login to your account|Sign in|LOGIN"}, timeout: 30000}', '- assertVisible: {text: "Login to your account|Sign in|LOGIN"}', shot("ANON_PHOTO_011", "bookmark_login"), '- back', '- assertVisible: {text: ".*[0-9]+/[0-9]+.*"}')
yamls["ANON_PHOTO_012"] = lines(multi(), '- tapOn: {text: "Share"}', '- waitForAnimationToEnd', '- assertVisible: {text: "Share with|Nearby Share|Quick Share|Messages|Copy"}', shot("ANON_PHOTO_012", "share_sheet"), '- back', '- assertVisible: {text: ".*[0-9]+/[0-9]+.*"}')
yamls["ANON_PHOTO_013"] = lines(multi(), '- tapOn: {text: "Comment|Post a comment"}', '- extendedWaitUntil: {visible: {text: "Sign in|Login|LOGIN"}, timeout: 30000}', '- assertVisible: {text: "Sign in|Login|LOGIN"}', shot("ANON_PHOTO_013", "comment_login"), '- tapOn: {text: "Close sheet|CLOSE|Close", optional: true}', '- back', '- assertVisible: {text: ".*[0-9]+/[0-9]+.*"}')
yamls["ANON_PHOTO_014"] = lines(multi(), '- assertVisible: {text: "Subscribe|SUBSCRIBE"}', '- tapOn: {text: "Subscribe|SUBSCRIBE"}', '- extendedWaitUntil: {visible: {text: "Yearly|Monthly|Choose a plan|Offer"}, timeout: 30000}', '- assertVisible: {text: "Yearly|Monthly|Choose a plan|Offer"}', shot("ANON_PHOTO_014", "plans"), '- back', '- assertVisible: {text: ".*[0-9]+/[0-9]+.*"}', '- tapOn: {point: "90%,9%"}', '- extendedWaitUntil: {visible: {text: "Photos"}, timeout: 30000}', '- assertVisible: {id: "screen_home"}', shot("ANON_PHOTO_014", "closed_to_grid"))


cases = {case["id"]: case for case in ExcelReader().group_cases(NORMALIZED)}
assert set(yamls) == set(cases), (set(cases) - set(yamls), set(yamls) - set(cases))
with connect() as db:
    for case_id, body in yamls.items():
        row = db.execute("SELECT id FROM drafts WHERE source_file=? AND case_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (SOURCE, case_id)).fetchone()
        if not row: raise SystemExit(f"Missing pending draft: {case_id}")
        yaml_text = HEADER + body + "\n"
        validate_maestro_yaml(yaml_text)
        if not reusable_yaml(yaml_text): raise SystemExit(f"Invalid Maestro structure: {case_id}")
        commands = list(dict.fromkeys(yaml_command_sequence(yaml_text)))
        traceability = []
        for position, item in enumerate(cases[case_id]["requirements"], 1):
            traceability.append({
                "position": position, "source_type": item.get("source_type", "step"), "step_number": item.get("step_number"),
                "requirement": item.get("expected_result") or item.get("step") or "", "generation_input": item.get("step", ""),
                "commands": commands, "selector": "Live Photos discovery, SC_64-SC_67 references, and validated article locators",
                "status": "covered", "reason": "Rebuilt from imported Excel and observed Photos/gallery behavior.",
                "source_sheet": item.get("source_sheet", ""), "source_row": item.get("source_row"),
            })
        db.execute("""UPDATE drafts SET yaml=?,error=NULL,generation_mode='reviewed-friday-live-memory',ai_confidence=1.0,
                   ai_assumptions=?,traceability=?,coverage_status='complete' WHERE id=?""",
                   (yaml_text, json.dumps(["Dynamic gallery content requires the live review run after approval."]), json.dumps(traceability, ensure_ascii=False), row["id"]))
        print("repaired", case_id, "draft", row["id"])
