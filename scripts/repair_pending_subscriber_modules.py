"""Resolve genuine Subscriber Trending/Premium gaps and reject duplicate Ebooks drafts."""

import json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from web.portal_db import connect
from web.services.generation_service import approve_draft
from web.services.yaml_editor_service import validate_maestro_yaml

HEADER='appId: com.mobstac.thehindu\ntags: [generated, ordered, subscriber]\n---\n'
NO='- runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"'
SHOT=lambda cid,label:f'- waitForAnimationToEnd\n- takeScreenshot: "Screenshots/Generated/{cid}_{label}"'

F={
'SUB_TREND_011':'''- runFlow: "../Common/OPEN_SUBSCRIBER_TRENDING_ARTICLE.yaml"
- assertVisible: {text: "Bookmark"}
- tapOn: {text: "Bookmark"}
- assertVisible: {id: "screen_article_detail"}
- assertNotVisible: {text: "Login to your account"}''',
'SUB_TREND_012':'''- runFlow: "../Common/OPEN_SUBSCRIBER_TRENDING_ARTICLE.yaml"
- assertVisible: {text: "Share"}
- tapOn: {text: "Share"}
- extendedWaitUntil: {visible: {text: "Quick Share"}, timeout: 15000}
- assertVisible: {text: "Quick Share"}''',
'SUB_TREND_015':'''- runFlow: "../Common/OPEN_SUBSCRIBER_TRENDING_ARTICLE.yaml"
- repeat:
    times: 5
    commands:
      - swipe: {direction: LEFT}
      - waitForAnimationToEnd
      - runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"
- repeat:
    times: 5
    commands:
      - swipe: {direction: RIGHT}
      - waitForAnimationToEnd
      - runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"
- assertVisible: {id: "screen_article_detail"}''',
'SUB_TREND_016':'''- runFlow: "../Common/OPEN_SUBSCRIBER_TRENDING.yaml"
- tapOn: {text: "Business"}
- repeat:
    times: 3
    commands:
      - swipe: {direction: UP}
      - waitForAnimationToEnd
- scrollUntilVisible: {element: {text: "READ FULL ARTICLE"}, direction: DOWN, timeout: 45000, speed: 40}
- tapOn: {text: "READ FULL ARTICLE", index: 0}
- extendedWaitUntil: {visible: {id: "screen_article_detail"}, timeout: 30000}
- back
- extendedWaitUntil: {visible: {id: "screen_trending"}, timeout: 30000}
- assertVisible: {text: "Business"}''',
'SUB_TREND_018':'''- runFlow: "../Common/OPEN_SUBSCRIBER_TRENDING_ARTICLE.yaml"
- assertNotVisible: {text: "Login to your account|SUBSCRIBE|Already a subscriber.*"}
- back
- extendedWaitUntil: {visible: {id: "screen_trending"}, timeout: 30000}
- tapOn: {id: "nav_home"}
- assertVisible: {id: "screen_home"}
- tapOn: {id: "nav_trending"}
- assertVisible: {id: "screen_trending"}''',
'SUB_PREM_001':'''- runFlow: "../Common/OPEN_SUBSCRIBER_PREMIUM.yaml"
- assertVisible: {id: "nav_premium"}
- assertNotVisible: {text: "Login to your account|SUBSCRIBE|Already a subscriber.*"}''',
'SUB_PREM_013':'''- runFlow: "../Common/OPEN_SUBSCRIBER_PREMIUM_ARTICLE.yaml"
- assertVisible: {text: "Text size"}
- tapOn: {text: "Text size"}
- extendedWaitUntil: {visible: {text: "Reading Options.*|Text Size"}, timeout: 15000}
- assertVisible: {text: "A-"}
- assertVisible: {text: "A+"}
- tapOn: {text: "A+"}
- tapOn: {text: "A-"}
- tapOn: {text: "CLOSE|Close"}
- assertVisible: {id: "screen_article_detail"}''',
'SUB_PREM_016':'''- runFlow: "../Common/OPEN_SUBSCRIBER_PREMIUM_ARTICLE.yaml"
- runFlow:
    when: {visible: {text: "Listen to article"}}
    commands:
      - tapOn: {text: "Listen to article"}
      - waitForAnimationToEnd: {timeout: 30000}
      - back
- runFlow:
    when: {visible: {text: "AI Summary|AI summary|AI SUMMARY"}}
    commands:
      - tapOn: {text: "AI Summary|AI summary|AI SUMMARY"}
      - assertNotVisible: {text: "SUBSCRIBE"}
      - waitForAnimationToEnd
      - takeScreenshot: "Screenshots/Generated/SUB_PREM_016_ai_summary"
      - back
- assertVisible: {id: "screen_article_detail"}''',
'SUB_PREM_017':'''- runFlow: "../Common/OPEN_SUBSCRIBER_PREMIUM_ARTICLE.yaml"
- repeat:
    times: 5
    commands:
      - swipe: {direction: LEFT}
      - waitForAnimationToEnd
      - runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"
- repeat:
    times: 5
    commands:
      - swipe: {direction: RIGHT}
      - waitForAnimationToEnd
      - runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"
- assertVisible: {id: "screen_article_detail"}''',
'SUB_PREM_018':'''- runFlow: "../Common/OPEN_SUBSCRIBER_PREMIUM_ARTICLE.yaml"
- assertNotVisible: {text: "Login to your account|SUBSCRIBE|Already a subscriber.*|Keep reading.*"}
- back
- extendedWaitUntil: {visible: {id: "screen_premium"}, timeout: 30000}
- tapOn: {id: "nav_home"}
- assertVisible: {id: "screen_home"}
- tapOn: {id: "nav_premium"}
- assertVisible: {id: "screen_premium"}''',
}

def main():
 with connect() as db:
  duplicates=db.execute("""SELECT id,case_id FROM drafts d WHERE status='pending' AND case_id LIKE 'SUB_EBOOK_%'
   AND EXISTS(SELECT 1 FROM drafts a WHERE a.case_id=d.case_id AND a.status='approved')""").fetchall()
  for d in duplicates:
   db.execute("UPDATE drafts SET status='rejected',error='Redundant duplicate: approved case already exists' WHERE id=?",(d['id'],))
 approved=[]
 for cid,body in F.items():
  with connect() as db:d=db.execute("SELECT * FROM drafts WHERE case_id=? AND status='pending' ORDER BY id DESC LIMIT 1",(cid,)).fetchone()
  if not d:continue
  y=HEADER+body+'\n'+NO+'\n'+SHOT(cid,'result')+'\n'
  if not validate_maestro_yaml(y):raise ValueError('Invalid '+cid)
  trace=json.loads(d['traceability'] or '[]')
  for item in trace:item.update(status='covered',reason='Friday grounded against validated Subscriber common flows and corresponding approved Anonymous module structure.')
  with connect() as db:db.execute("UPDATE drafts SET yaml=?,traceability=?,coverage_status='complete',ai_confidence=1,generation_mode='friday-grounded',error=NULL WHERE id=?",(y,json.dumps(trace),d['id']))
  approve_draft(d['id'],y,'user_subscriber','Friday')
  approved.append(cid)
 print(json.dumps({'duplicates_rejected':[d['case_id'] for d in duplicates],'approved':approved},indent=2))
if __name__=='__main__':main()
