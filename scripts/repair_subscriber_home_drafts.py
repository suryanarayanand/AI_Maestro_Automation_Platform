import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def flow(case_id, body, tags):
    return f'''appId: com.mobstac.thehindu
tags: [generated, ordered, subscriber, home, {tags}]
---
{body.strip()}
'''


OPEN = '''- runFlow: "../Common/OPEN_SUBSCRIBER_HOME.yaml"'''
NO_HOME_ADS = '''- assertNotVisible: {text: "SUBSCRIBE"}
- assertNotVisible: {text: "ADVERTISEMENT"}
- assertNotVisible: {id: "aw0"}'''
NO_ARTICLE_GATE = '''- assertNotVisible: {text: "SUBSCRIBE|Already a subscriber.*|Keep reading.*|.*[0-9]+%.*off.*"}
- assertNotVisible: {text: "ADVERTISEMENT"}
- assertNotVisible: {id: "ad_iframe"}'''


YAMLS = {
    "SUB_HOME_003": flow("003", f'''{OPEN}
- repeat:
    times: 6
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd: {{timeout: 1200}}
      - assertVisible: {{id: "screen_home"}}
      - assertNotVisible: {{text: "SUBSCRIBE"}}
      - assertNotVisible: {{text: "ADVERTISEMENT"}}
      - assertNotVisible: {{id: "aw0"}}
      - assertNotVisible: {{text: "Image for Taboola Advertising Unit"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_003_home_without_monetisation"''', "no-monetisation"),

    "SUB_HOME_004": flow("004", f'''{OPEN}
- repeat:
    times: 4
    commands:
      - assertVisible: {{id: "screen_home"}}
      - assertVisible: {{id: "article_card", index: 0}}
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd: {{timeout: 1200}}
- tapOn: {{id: "nav_menu"}}
- extendedWaitUntil: {{visible: {{id: "screen_hamburger"}}, timeout: 15000}}
- assertVisible: {{id: "screen_hamburger"}}
- tapOn: {{text: "India", index: 0}}
- scrollUntilVisible: {{element: {{text: "India", index: 1}}, direction: DOWN, timeout: 30000}}
- tapOn: {{text: "India", index: 1}}
- waitForAnimationToEnd: {{timeout: 5000}}
- assertVisible: {{text: "India"}}
- tapOn: {{id: "nav_home"}}
- extendedWaitUntil: {{visible: {{id: "screen_home"}}, timeout: 20000}}
{NO_HOME_ADS}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_004_home_section_return"''', "content-navigation"),

    "SUB_HOME_005": flow("005", f'''{OPEN}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- repeat:
    times: 10
    commands:
      - assertVisible: {{id: "screen_article_detail"}}
      - assertNotVisible: {{text: "SUBSCRIBE|Already a subscriber.*|Keep reading.*|.*[0-9]+%.*off.*"}}
      - assertNotVisible: {{text: "ADVERTISEMENT"}}
      - assertNotVisible: {{id: "ad_iframe"}}
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd: {{timeout: 1200}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_005_full_article_access"''', "full-article"),

    "SUB_HOME_006": flow("006", f'''{OPEN}
- tapOn: {{id: "nav_premium"}}
- extendedWaitUntil: {{visible: {{id: "screen_premium"}}, timeout: 20000}}
- tapOn: {{text: "OKAY", optional: true}}
- tapOn: {{text: "All Stories", optional: true}}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- repeat:
    times: 10
    commands:
      - assertVisible: {{id: "screen_article_detail"}}
      - assertNotVisible: {{text: "SUBSCRIBE|Already a subscriber.*|Keep reading.*|.*[0-9]+%.*off.*"}}
      - assertNotVisible: {{text: "ADVERTISEMENT"}}
      - assertNotVisible: {{id: "ad_iframe"}}
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd: {{timeout: 1200}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_006_premium_article_entitled"''', "premium-article"),

    "SUB_HOME_007": flow("007", f'''{OPEN}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- repeat:
    while: {{notVisible: {{text: "AI Summary|Summary"}}}}
    times: 10
    commands:
      - swipe: {{direction: LEFT}}
      - waitForAnimationToEnd: {{timeout: 3000}}
      - assertVisible: {{id: "screen_article_detail"}}
      - assertNotVisible: {{id: "ad_iframe"}}
- assertVisible: {{text: "AI Summary|Summary"}}
- tapOn: {{text: "AI Summary|Summary"}}
- extendedWaitUntil: {{visible: {{text: "Summary"}}, timeout: 20000}}
- assertVisible: {{text: "Summary"}}
- assertVisible: {{text: "Article FAQs"}}
- assertNotVisible: {{text: "SUBSCRIBE|Go beyond the headline.*"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_007_entitled_ai_summary"
- tapOn: {{text: "Close sheet", optional: true}}
- back''', "ai-summary"),

    "SUB_HOME_008": flow("008", f'''{OPEN}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- runFlow:
    when: {{visible: {{text: "Remove bookmark"}}}}
    commands:
      - tapOn: {{text: "Remove bookmark"}}
- extendedWaitUntil: {{visible: {{text: "Bookmark"}}, timeout: 15000}}
- tapOn: {{text: "Bookmark"}}
- extendedWaitUntil: {{visible: {{text: "Remove bookmark|success"}}, timeout: 15000}}
- assertNotVisible: {{text: "Login to your account"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_008_bookmark_selected"
- runFlow:
    when: {{visible: {{text: "Remove bookmark"}}}}
    commands:
      - tapOn: {{text: "Remove bookmark"}}''', "bookmark"),

    "SUB_HOME_009": flow("009", f'''{OPEN}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- assertVisible: {{text: "Share"}}
- tapOn: {{text: "Share"}}
- extendedWaitUntil: {{visible: {{text: "Quick Share"}}, timeout: 15000}}
- assertVisible: {{text: "Quick Share"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_009_share_sheet"
- back
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 15000}}
- assertVisible: {{id: "screen_article_detail"}}''', "share"),

    "SUB_HOME_010": flow("010", f'''{OPEN}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- scrollUntilVisible:
    element: {{text: "Post a comment"}}
    direction: DOWN
    timeout: 120000
    speed: 40
    visibilityPercentage: 40
    centerElement: true
- assertVisible: {{text: "Post a comment"}}
- tapOn: {{text: "Post a comment"}}
- assertNotVisible: {{text: "Login to your account|SIGN IN AND JOIN THE CONVERSATION.*"}}
- inputText: "Automation validation draft - do not submit"
- hideKeyboard
- takeScreenshot: "Screenshots/Generated/SUB_HOME_010_comment_draft_not_submitted"
- back
- extendedWaitUntil: {{visible: {{id: "screen_home"}}, timeout: 20000}}
- assertVisible: {{id: "screen_home"}}
- assertNotVisible: {{text: "Automation validation draft - do not submit"}}''', "comment"),

    "SUB_HOME_011": flow("011", f'''{OPEN}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- scrollUntilVisible:
    element: {{text: "Post a comment"}}
    direction: DOWN
    timeout: 120000
    speed: 40
    visibilityPercentage: 40
- assertVisible: {{text: "Post a comment"}}
- scrollUntilVisible: {{element: {{text: "Related Topics"}}, direction: DOWN, timeout: 60000}}
- assertVisible: {{text: "Related Topics"}}
- scrollUntilVisible: {{element: {{text: "Recommended"}}, direction: DOWN, timeout: 60000}}
- assertVisible: {{text: "Recommended"}}
- scrollUntilVisible: {{element: {{text: "Headlines"}}, direction: DOWN, timeout: 60000}}
- assertVisible: {{text: "Headlines"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_011_post_article_sections"''', "post-article"),

    "SUB_HOME_012": flow("012", f'''{OPEN}
- evalScript: ${{output.homeFeedSwipes = 1 + Math.floor(Math.random() * 4)}}
- repeat:
    times: ${{output.homeFeedSwipes}}
    commands:
      - swipe: {{direction: UP}}
      - waitForAnimationToEnd: {{timeout: 1200}}
- tapOn: {{id: "article_card", index: 0}}
- tapOn: {{text: "Close sheet", optional: true}}
- extendedWaitUntil: {{visible: {{id: "screen_article_detail"}}, timeout: 25000}}
- repeat:
    times: 5
    commands:
      - swipe: {{direction: LEFT}}
      - waitForAnimationToEnd: {{timeout: 3000}}
      - assertVisible: {{id: "screen_article_detail"}}
      - assertNotVisible: {{text: "SUBSCRIBE|Already a subscriber.*|Keep reading.*"}}
      - assertNotVisible: {{id: "ad_iframe"}}
- repeat:
    times: 5
    commands:
      - swipe: {{direction: RIGHT}}
      - waitForAnimationToEnd: {{timeout: 3000}}
      - assertVisible: {{id: "screen_article_detail"}}
      - assertNotVisible: {{text: "SUBSCRIBE|Already a subscriber.*|Keep reading.*"}}
      - assertNotVisible: {{id: "ad_iframe"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_012_pager_session_retained"''', "article-pager"),

    "SUB_HOME_013": flow("013", f'''{OPEN}
{NO_HOME_ADS}
- tapOn: {{id: "nav_games"}}
- extendedWaitUntil: {{visible: {{id: "screen_games"}}, timeout: 20000}}
- assertNotVisible: {{text: "SUBSCRIBE"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_013_games_entitled"
- tapOn: {{id: "nav_ebooks"}}
- extendedWaitUntil: {{visible: {{id: "screen_ebooks"}}, timeout: 20000}}
- assertNotVisible: {{text: "SUBSCRIBE"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_013_ebooks_entitled"
- tapOn: {{id: "nav_home"}}
- assertVisible: {{id: "screen_home"}}''', "plan-entitlements"),

    "SUB_HOME_014": flow("014", f'''{OPEN}
- tapOn: {{id: "nav_account"}}
- extendedWaitUntil: {{visible: {{id: "screen_user_menu"}}, timeout: 15000}}
- assertVisible: {{id: "screen_user_menu"}}
- scrollUntilVisible:
    element: {{text: "Logout|Log out|LOGOUT|Log Out"}}
    direction: DOWN
    timeout: 120000
- tapOn: {{text: "Logout|Log out|LOGOUT|Log Out"}}
- tapOn: {{text: "Logout|Log out|Yes|OK|Confirm", optional: true}}
- waitForAnimationToEnd: {{timeout: 5000}}
- extendedWaitUntil: {{visible: {{id: "screen_home"}}, timeout: 20000}}
- tapOn: {{id: "nav_account"}}
- extendedWaitUntil: {{visible: {{id: "screen_user_menu"}}, timeout: 15000}}
- assertVisible: {{id: "cta_login"}}
- assertVisible: {{text: "Create account"}}
- takeScreenshot: "Screenshots/Generated/SUB_HOME_014_anonymous_after_logout"''', "logout-boundary"),
}


with sqlite3.connect(ROOT / "portal.db") as db:
    for case_id, yaml in YAMLS.items():
        pending = db.execute(
            "SELECT id FROM drafts WHERE case_id=? AND status='pending' ORDER BY id DESC",
            (case_id,),
        ).fetchall()
        if not pending:
            raise SystemExit(f"No pending draft found for {case_id}")
        newest = pending[0][0]
        db.execute(
            """UPDATE drafts SET yaml=?,coverage_status='complete',
               generation_mode='reviewed-repository',ai_confidence=1.0,ai_assumptions=?
               WHERE id=?""",
            (yaml, json.dumps(["Rebuilt from approved Excel behavior, validated locators, "
                               "and existing Subscriber repository flows."]), newest),
        )
        for older in pending[1:]:
            db.execute(
                "UPDATE drafts SET status='rejected',error=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
                ("Superseded duplicate Subscriber import draft", older[0]),
            )
        print(f"Repaired {case_id} draft #{newest}; rejected {len(pending) - 1} duplicates")
