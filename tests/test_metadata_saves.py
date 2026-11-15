"""Disk-pressure and commit-boundary failures must never report a false save."""
import json,os,stat
import pytest
from fastapi.testclient import TestClient
from backend import app as service
from backend import runtime_storage as storage
from backend.storage_budget import InsufficientStorage
from test_workflows import recipe


def test_guarded_save_reserves_space_before_replacing(tmp_path,monkeypatch):
 from backend import storage_budget
 path=tmp_path/'saved.json';storage.atomic_json(path,{'old':1});before=path.read_bytes()
 def reject(*args,**kwargs):raise InsufficientStorage('Not enough free space')
 monkeypatch.setattr(storage_budget,'require_space',reject)
 with pytest.raises(InsufficientStorage):storage.guarded_json(path,{'new':2})
 assert path.read_bytes()==before and not list(tmp_path.glob('.job-*.tmp'))


@pytest.mark.parametrize('failure',['replace','file_sync','directory_sync'])
def test_tool_save_failure_does_not_claim_success(tmp_path,monkeypatch,failure):
 monkeypatch.setattr(service,'DATA',tmp_path)
 client=TestClient(service.app);raw=recipe(name='Original').model_dump(mode='json')
 saved=client.post('/api/workflows',json=raw);assert saved.status_code==200
 ident=saved.json()['id'];path=tmp_path/'workflows'/(ident+'.json');before=path.read_bytes()
 real_sync=storage.os.fsync
 def sync(fd):
  directory=stat.S_ISDIR(os.fstat(fd).st_mode)
  if directory==(failure=='directory_sync'):raise OSError('injected disk error')
  real_sync(fd)
 def replace(*args):raise OSError('injected replacement error')
 if failure=='replace':monkeypatch.setattr(storage.os,'replace',replace)
 else:monkeypatch.setattr(storage.os,'fsync',sync)
 raw['name']='Updated';response=client.put('/api/workflows/'+ident,json=raw)
 assert response.status_code==507 and 'reopen My Tools' in response.json()['detail']
 if failure=='directory_sync':assert json.loads(path.read_text())['name']=='Updated'
 else:assert path.read_bytes()==before
 assert not list(path.parent.glob('.job-*.tmp'))


def test_tool_low_space_create_and_update_preserve_saved_files(tmp_path,monkeypatch):
 from backend import storage_budget
 monkeypatch.setattr(service,'DATA',tmp_path)
 client=TestClient(service.app);raw=recipe(name='Original').model_dump(mode='json')
 ident=client.post('/api/workflows',json=raw).json()['id'];path=tmp_path/'workflows'/(ident+'.json');before=path.read_bytes()
 def reject(*args,**kwargs):raise InsufficientStorage('Not enough free space')
 monkeypatch.setattr(storage_budget,'require_space',reject)
 assert client.post('/api/workflows',json=raw).status_code==507
 raw['name']='Updated';assert client.put('/api/workflows/'+ident,json=raw).status_code==507
 assert path.read_bytes()==before and len(list(path.parent.glob('*.json')))==1


def test_tool_save_does_not_follow_legacy_temporary_symlink(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'DATA',tmp_path)
 client=TestClient(service.app);raw=recipe(name='Original').model_dump(mode='json')
 ident=client.post('/api/workflows',json=raw).json()['id'];folder=tmp_path/'workflows'
 target=tmp_path/'preserve';target.write_text('Do not overwrite')
 (folder/(ident+'.tmp')).symlink_to(target)
 raw['name']='Unicode · café';assert client.put('/api/workflows/'+ident,json=raw).status_code==200
 assert client.get('/api/workflows/'+ident+'/export').json()==raw
 assert target.read_text()=='Do not overwrite'


def test_reference_report_storage_failure_is_actionable_and_not_completed(tmp_path,monkeypatch):
 from test_reference_assistant import observations,options,BBOX
 grid,seq=observations()
 (tmp_path/'jobs').mkdir();(tmp_path/'raw').mkdir()
 monkeypatch.setattr(service,'DATA',tmp_path);monkeypatch.setattr(service,'JOBS_DIR',tmp_path/'jobs');monkeypatch.setattr(service,'JOBS',{})
 monkeypatch.setattr(service,'CATALOG',{o['item']['id']:o['item'] for o in seq})
 for o in seq:(tmp_path/'raw'/(o['item']['id']+'.h5')).write_bytes(b'preserved synthetic input')
 monkeypatch.setattr(service,'load_observation',lambda item,*args:next(o for o in seq if o['item']['id']==item['id']))
 def reject(*args,**kwargs):raise OSError('injected report storage error')
 monkeypatch.setattr(service,'guarded_json',reject)
 job={'id':'f'*32,'cancelled':False,'created_at':'2026-10-22T00:00:00Z','results':{},'status':'queued'}
 (tmp_path/'jobs'/job['id']).mkdir();service.JOBS[job['id']]=job
 body=service.RunQuery(bbox=BBOX,granules=list(service.CATALOG),projects=['P04'],options={**options(),'resolution':100})
 service.reference_work(job,[o['item'] for o in seq],body)
 assert job['status']=='failed' and 'storage drive' in job['message'] and 'schema' not in job['message']
 assert 'assistant_url' not in job
 assert all(p.read_bytes()==b'preserved synthetic input' for p in (tmp_path/'raw').glob('*.h5'))
