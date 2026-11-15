"""Authorized five-date native-area extraction; never installs an Example."""
from pathlib import Path
import json,time,requests
R=Path(__file__).resolve().parent;API='http://127.0.0.1:8765';BBOX=[160.15,54.51,160.50,54.70]
DATES=['2026-06-18','2026-06-30','2026-07-12','2026-07-24','2026-08-17'];GROUP='060_D_061_4005_DHDH_P05023'
def call(path,body=None):
 r=requests.get(API+path,timeout=90) if body is None else requests.post(API+path,json=body,timeout=120);r.raise_for_status();return r.json()
def main():
 assert call('/api/health')['earthdata_connected'],'Sign in through Connection; no credentials belong in this script.'
 c=call('/api/search',{'bbox':BBOX,'start':DATES[0],'end':DATES[-1],'products':['GCOV'],'maturity':'PROVISIONAL'});(R/'sources/catalog.json').write_text(json.dumps(c,indent=2));assert not c['GCOV'].get('error'),c['GCOV'].get('error')
 chosen=[]
 for date in DATES:
  matched=[i for i in c['GCOV']['items'] if i['group']==GROUP and i['start'][:10]==date];assert matched,'Missing required date '+date
  chosen.append(sorted(matched,key=lambda i:i['name'])[-1])
 (R/'sources/selected-scenes.json').write_text(json.dumps(chosen,indent=2))
 j=call('/api/download-area',{'bbox':BBOX,'granules':[i['id'] for i in chosen]});(R/'results/download-job.json').write_text(json.dumps(j,indent=2));last=''
 while j['status'] in ['queued','running']:
  if j['message']!=last:print(j['message'],flush=True);last=j['message']
  time.sleep(5);j=call('/api/jobs/'+j['id'])
 (R/'results/download-receipt.json').write_text(json.dumps(j,indent=2));assert j['status']=='completed' and len(j.get('saved_areas',[]))==5,j
 print('Five real native-grid area files saved. No Example installed.',flush=True)
if __name__=='__main__':main()
