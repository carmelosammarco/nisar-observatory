import json
import pytest
from fastapi.testclient import TestClient
from backend import app as module

@pytest.fixture
def saved_runs(tmp_path,monkeypatch):
 jobs=tmp_path/'jobs';jobs.mkdir()
 ident='a'*32;other='b'*32
 records={}
 for name in [ident,other]:
  path=jobs/name;path.mkdir();(path/'P01').mkdir()
  records[name]={'id':name,'status':'completed','created_at':'2026-10-16T00:00:00Z','results':{}}
  (path/'job.json').write_text(json.dumps(records[name]));(path/'P01'/'result.json').write_text('{}')
 raw=tmp_path/'raw';raw.mkdir();(raw/'source.h5').write_bytes(b'original')
 arrays=tmp_path/'arrays';arrays.mkdir();(arrays/'cache.npz').write_bytes(b'cache')
 monkeypatch.setattr(module,'JOBS',records);monkeypatch.setattr(module,'JOBS_DIR',jobs)
 return TestClient(module.app),tmp_path,ident,other

def test_delete_removes_run_and_artifacts_only(saved_runs):
 client,root,ident,other=saved_runs
 assert client.delete('/api/jobs/'+ident).json()=={'deleted':ident}
 assert client.get('/api/jobs/'+ident).status_code==404
 assert [j['id'] for j in client.get('/api/jobs').json()]==[other]
 assert client.get(f'/api/artifacts/{ident}/P01/result.json').status_code==404
 assert not (root/'jobs'/ident).exists()
 assert (root/'jobs'/other/'job.json').exists()
 assert (root/'raw'/'source.h5').read_bytes()==b'original'
 assert (root/'arrays'/'cache.npz').read_bytes()==b'cache'
 assert ident not in [json.loads(p.read_text())['id'] for p in (root/'jobs').glob('*/job.json')]
 assert client.delete('/api/jobs/'+ident).status_code==404

@pytest.mark.parametrize('status',['queued','running'])
def test_active_runs_cannot_be_deleted(saved_runs,status):
 client,root,ident,_=saved_runs;module.JOBS[ident]['status']=status
 assert client.delete('/api/jobs/'+ident).status_code==409
 assert (root/'jobs'/ident/'job.json').exists()
 assert ident in module.JOBS

def test_invalid_run_id_does_not_touch_files(saved_runs):
 client,root,ident,_=saved_runs
 assert client.delete('/api/jobs/not-a-run').status_code==404
 assert (root/'jobs'/ident).exists()
