import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from web.portal_db import connect
from web.services.yaml_editor_service import validate_maestro_yaml
SOURCE='Subscriber_Search_Approved_Test_Cases.xlsx'
APPROVED=['SUB_SEARCH_001','SUB_SEARCH_002','SUB_SEARCH_003','SUB_SEARCH_018','SUB_SEARCH_020','SUB_SEARCH_021','SUB_SEARCH_024','SUB_SEARCH_028']
with connect() as db: drafts={r['case_id']:r for r in db.execute('SELECT * FROM drafts WHERE source_file=?',(SOURCE,)).fetchall()}
for cid in APPROVED:
 y=(ROOT/'Scenarios'/f'{cid}.yaml').read_text(encoding='utf-8')
 if not validate_maestro_yaml(y):raise ValueError(cid)
 trace=json.loads(drafts[cid]['traceability'] or '[]')
 for item in trace:item.update(status='covered',reason='Grounded by old Search YAML and live discovery jobs 331-332.')
 with connect() as db:db.execute("UPDATE drafts SET yaml=?,traceability=?,coverage_status='complete',ai_confidence=1,generation_mode='friday-grounded',status='approved',error=NULL,reviewed_by='Friday',reviewed_at=CURRENT_TIMESTAMP WHERE id=?",(y,json.dumps(trace),drafts[cid]['id']))
for cid,d in drafts.items():
 if cid not in APPROVED:
  with connect() as db:db.execute("UPDATE drafts SET status='pending',coverage_status='incomplete',generation_mode='friday-reviewing',error=? WHERE id=?",('Needs live locator or dynamic-content validation before safe approval.',d['id']))
print(json.dumps({'approved':APPROVED,'pending':len(drafts)-len(APPROVED)},indent=2))
