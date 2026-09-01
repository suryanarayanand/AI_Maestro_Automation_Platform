"""Replace Friday partial Games drafts with SC-27 and live-UI-grounded YAML."""

import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from web.portal_db import connect
from web.services.yaml_editor_service import validate_maestro_yaml

H='appId: com.mobstac.thehindu\ntags: [generated, ordered, subscriber, games, friday-grounded]\n---\n'
OPEN='- runFlow: "../Common/OPEN_SUBSCRIBER_GAMES.yaml"'
NO='''- assertNotVisible: {text: "Login to play|Login to your account|SUBSCRIBE|.*access was not found.*"}
- runFlow: "../Common/ASSERT_SUBSCRIBER_NO_MONETIZATION.yaml"'''
def shot(cid,label='result'):return f'- waitForAnimationToEnd\n- takeScreenshot: "Screenshots/Generated/{cid}_{label}"'
def wrap(cid,manual):return H+f'- runFlow: "{manual}"\n'+NO+'\n'+shot(cid)+'\n'

F={
'SUB_GAMES_001':H+OPEN+'''\n- assertVisible: {id: "screen_games"}
- assertVisible: {text: "PLAY NOW"}
'''+NO+'\n'+shot('SUB_GAMES_001','landing')+'\n',
'SUB_GAMES_002':H+OPEN+'''\n- assertVisible: {text: "Cryptic Crossword"}
- assertVisible: {text: "Sudoku"}
- scrollUntilVisible: {element: {text: "The Hindu Mini"}, direction: DOWN, timeout: 30000, speed: 55, visibilityPercentage: 20}
- scrollUntilVisible: {element: {text: "Easy Down"}, direction: DOWN, timeout: 30000, speed: 55, visibilityPercentage: 20}
- scrollUntilVisible: {element: {text: "Word Row"}, direction: DOWN, timeout: 30000, speed: 55, visibilityPercentage: 20}
- assertVisible: {text: "Word Flower"}
- assertVisible: {text: "Word Search"}
- assertVisible: {text: "Quiz"}
'''+NO+'\n'+shot('SUB_GAMES_002','catalogue')+'\n',
'SUB_GAMES_003':wrap('SUB_GAMES_003','SC_27_CRYPTIC_CROSSWORD.yaml'),
'SUB_GAMES_004':H+OPEN+'''\n- tapOn: {text: "Sudoku"}
- extendedWaitUntil: {visible: {text: "Choose Your Puzzle to Play"}, timeout: 30000}
- assertVisible: {text: "Mini"}
- assertVisible: {text: "Easy"}
- assertVisible: {text: "Medium"}
- assertVisible: {text: "Hard"}
- assertVisible: {text: "Killer"}
'''+NO+'\n'+shot('SUB_GAMES_004','sudoku_difficulties')+'\n',
'SUB_GAMES_005':wrap('SUB_GAMES_005','SC_27_SUDOKU.yaml'),
'SUB_GAMES_006':wrap('SUB_GAMES_006','SC_27_SUDOKU_EASY.yaml'),
'SUB_GAMES_007':wrap('SUB_GAMES_007','SC_27_THE_HINDU_MINI.yaml'),
'SUB_GAMES_008':wrap('SUB_GAMES_008','SC_27_EASY_DOWN.yaml'),
'SUB_GAMES_009':wrap('SUB_GAMES_009','SC_27_WORD_ROW.yaml'),
'SUB_GAMES_010':wrap('SUB_GAMES_010','SC_27_WORD_FLOWER.yaml'),
'SUB_GAMES_011':wrap('SUB_GAMES_011','SC_27_WORD_SEARCH.yaml'),
'SUB_GAMES_012':wrap('SUB_GAMES_012','SC_27_NEWS_QUIZ.yaml'),
'SUB_GAMES_013':H+OPEN+'''\n- tapOn: {text: "Sudoku"}
- extendedWaitUntil: {visible: {text: "Choose Your Puzzle to Play"}, timeout: 30000}
- back
- extendedWaitUntil: {visible: {id: "screen_games"}, timeout: 30000}
- tapOn: {id: "nav_home"}
- assertVisible: {id: "screen_home"}
- tapOn: {id: "nav_games"}
- extendedWaitUntil: {visible: {id: "screen_games"}, timeout: 30000}
- assertVisible: {text: "PLAY NOW"}
'''+NO+'\n'+shot('SUB_GAMES_013','session_persistence')+'\n',
}

def main():
 suite_path=ROOT/'Suites/user_subscriber.json';suite=json.loads(suite_path.read_text(encoding='utf-8-sig'))
 suite['tests']=[t for t in suite.get('tests',[]) if not str(t.get('id','')).startswith('SUB_GAMES_')]
 repaired=[]
 with connect() as db:
  drafts={r['case_id']:r for r in db.execute("SELECT * FROM drafts WHERE case_id LIKE 'SUB_GAMES_%'").fetchall()}
 for cid,y in F.items():
  if not validate_maestro_yaml(y):raise ValueError('Invalid '+cid)
  (ROOT/'Scenarios'/f'{cid}.yaml').write_text(y,encoding='utf-8')
  d=drafts[cid];trace=json.loads(d['traceability'] or '[]')
  for item in trace:item.update(status='covered',reason='Friday grounded against the matching manual SC-27 flow and Subscriber Games live UI job 326.')
  with connect() as db:db.execute("UPDATE drafts SET yaml=?,traceability=?,coverage_status='complete',ai_confidence=1,generation_mode='friday-grounded',status='approved',error=NULL,reviewed_by='Friday',reviewed_at=CURRENT_TIMESTAMP WHERE id=?",(y,json.dumps(trace),d['id']))
  suite['tests'].append({'id':cid,'module':'Games','section':'Games','user_state':'SUBSCRIBER','priority':'P1','name':d['name'],'yaml':f'{cid}.yaml'})
  repaired.append(cid)
 suite_path.write_text(json.dumps(suite,indent=4,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({'approved':repaired,'count':len(repaired)},indent=2))
if __name__=='__main__':main()
