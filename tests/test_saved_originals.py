"""Local availability and duplicate-download behavior; isolated synthetic metadata."""
import json,copy
from types import SimpleNamespace
from fastapi.testclient import TestClient
from backend import app as module
NAME='NISAR_L2_PR_GCOV_001_001_A_001_4005_DHDH_A_20260801T000000_20260801T000030_M00100_P_F_J_001.h5'

def setup(monkeypatch,tmp_path):
 raw=tmp_path/'raw';raw.mkdir();jobs=tmp_path/'jobs';jobs.mkdir()
 monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS_DIR',jobs);monkeypatch.setattr(module,'JOBS',{});monkeypatch.setattr(module,'CATALOG',{})
 ident='local-'+'a'*16;item={'id':ident,'name':NAME,'product':'GCOV','group':'one','start':'2026-08-01T00:00:00Z','end':'2026-08-01T00:00:30Z','size_mb':1}
 (raw/(ident+'.h5')).write_bytes(b'SYNTHETIC LOCAL AVAILABILITY TEST ONLY');(raw/(ident+'.json')).write_text(json.dumps(item))
 return item,TestClient(module.app)

def test_search_matches_saved_filename_and_keeps_catalog_identity(monkeypatch,tmp_path):
 saved,client=setup(monkeypatch,tmp_path);remote={**saved,'id':'G123-ASF','url':'https://datapool.asf.alaska.edu/test.h5'}
 monkeypatch.setattr(module,'search',lambda *args:{'items':[copy.deepcopy(remote)],'hits':1})
 response=client.post('/api/search',json={'bbox':[0,0,1,1],'start':'2026-08-01','end':'2026-08-02','products':['GCOV']})
 item=response.json()['GCOV']['items'][0]
 assert item['local'] and item['id']==saved['id'] and item['catalog_id']=='G123-ASF'
 assert client.get('/api/local').json()[0]['local'] is True

def test_duplicate_download_is_rejected_without_transfer(monkeypatch,tmp_path):
 saved,client=setup(monkeypatch,tmp_path);module.CATALOG[saved['id']]=saved
 calls=[];monkeypatch.setattr(module,'POOL',SimpleNamespace(submit=lambda *a:calls.append(a)))
 response=client.post('/api/download',json={'granules':[saved['id']]})
 assert response.status_code==409 and 'already saved' in response.json()['detail']
 assert not calls and not module.JOBS
 assert (tmp_path/'raw'/(saved['id']+'.h5')).is_file()

def test_mixed_download_queues_only_new_files(monkeypatch,tmp_path):
 saved,client=setup(monkeypatch,tmp_path);new={**saved,'id':'G124-ASF','name':NAME.replace('20260801','20260813')};module.CATALOG.update({saved['id']:saved,new['id']:new})
 monkeypatch.setattr(module.AUTH,'session',object());calls=[]
 monkeypatch.setattr(module,'POOL',SimpleNamespace(submit=lambda *a:calls.append(a)))
 response=client.post('/api/download',json={'granules':[saved['id'],new['id'],new['id']]})
 assert response.status_code==200
 assert [i['id'] for i in calls[0][2]]==[new['id']]
