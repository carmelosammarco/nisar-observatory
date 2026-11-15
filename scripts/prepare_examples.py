"""Download the exact curated native subsets through the app's RAM-only login.
Usage: .venv/bin/python scripts/prepare_examples.py [P01_Mozambique ...]
No full originals are downloaded and no existing files are deleted.
"""
import sys,json,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.examples import CASES,definition,inspect,install
API='http://127.0.0.1:8765'
def call(path,body=None):
 r=requests.get(API+path,timeout=180) if body is None else requests.post(API+path,json=body,timeout=180)
 r.raise_for_status();return r.json()
def wait(j):
 while j['status'] in ['queued','running']:
  time.sleep(3);j=call('/api/jobs/'+j['id'])
 if j['status']!='completed':raise RuntimeError(str({'status':j['status'],'message':j['message'],'source_errors':j.get('source_errors')}))
 return j
for ident in sys.argv[1:] or CASES:
 m=definition(ident)
 if inspect(ident)['ready']:print(ident+': protected inputs already verified',flush=True);continue
 if not call('/api/health')['earthdata_connected']:raise SystemExit('Please sign in through the app Connection tab, then run this helper again.')
 starts=[s['start'][:10] for s in m['sources']];ends=[s['end'][:10] for s in m['sources']]
 catalog=call('/api/search',{'bbox':m['request']['bbox'],'start':min(starts),'end':max(ends),'products':[m['product']],'maturity':'BETA' if all('_X' in s['group'] for s in m['sources']) else 'PROVISIONAL'})
 items=catalog[m['product']]['items'];chosen=[]
 for source in m['sources']:
  matches=[i for i in items if i['name']==source['name'] and i['id']==source['id']]
  if len(matches)!=1:raise RuntimeError('Exact tested observation unavailable; no substitute was selected: '+source['name'])
  chosen.append(matches[0]['id'])
 (ROOT/'Examples'/ident/'catalog-receipt.json').write_text(json.dumps(catalog,indent=2)+'\n')
 print(ident+': downloading '+str(len(chosen))+' native area subsets',flush=True)
 j=wait(call('/api/download-area',{'bbox':m['request']['bbox'],'granules':chosen}))
 report=install(ident,j['saved_areas'],ROOT/'data')
 (ROOT/'Examples'/ident/'download-receipt.json').write_text(json.dumps(j,indent=2)+'\n')
 assert report['ready'],report['issues']
 print(ident+': protected and verified '+str(report['input_count'])+' files, '+str(round(report['input_bytes']/1024**2,2))+' MiB',flush=True)
