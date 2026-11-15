"""Disk pressure must stop new work without changing saved science or results."""
from collections import namedtuple
from types import SimpleNamespace
import pytest
import numpy as np
from fastapi.testclient import TestClient
from backend import storage_budget as storage

Usage=namedtuple('Usage','total used free')
def free(monkeypatch,n):monkeypatch.setattr(storage.shutil,'disk_usage',lambda p:Usage(10**12,0,n))

def test_budget_checks_destination_and_boundaries(tmp_path,monkeypatch):
 monkeypatch.setenv('NISAR_DISK_RESERVE_MB','2');seen=[]
 monkeypatch.setattr(storage.shutil,'disk_usage',lambda p:(seen.append(p) or Usage(100,0,3*storage.MIB)))
 assert storage.require_space(tmp_path/'missing'/'child',storage.MIB)['fits']
 assert seen[-1]==tmp_path
 with pytest.raises(storage.InsufficientStorage,match='safety reserve'):storage.require_space(tmp_path,storage.MIB+1)
 for value in ['-1','oops','1.2']:
  monkeypatch.setenv('NISAR_DISK_RESERVE_MB',value)
  with pytest.raises(ValueError,match='nonnegative integer'):storage.disk_reserve_bytes()

def test_full_download_low_space_stops_before_network_and_keeps_original(tmp_path,monkeypatch):
 from backend import access
 monkeypatch.setattr(access,'DATA',tmp_path);(tmp_path/'raw').mkdir();existing=tmp_path/'raw'/'old.h5';existing.write_bytes(b'preserve')
 free(monkeypatch,0)
 with pytest.raises(storage.InsufficientStorage):access.download({'id':'new'},lambda:False,lambda *a:None)
 assert existing.read_bytes()==b'preserve' and not list(tmp_path.rglob('*.part'))
 # Reuse is allowed without allocating disk space or making a connection.
 assert access.download({'id':'old'},lambda:False,lambda *a:None)==str(existing)

def test_subset_low_space_avoids_source_read_and_cache_low_space_preserves_old(tmp_path,monkeypatch):
 from backend import science,subsets
 from test_subsets import setup,BBOX
 item,client=setup(monkeypatch,tmp_path)
 free(monkeypatch,0)
 monkeypatch.setattr(science,'open_science',lambda *a:pytest.fail('must not read source'))
 with pytest.raises(storage.InsufficientStorage):subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 assert not list(tmp_path.rglob('*.part'))
 grid=science.target_grid(BBOX,100)
 monkeypatch.setattr(science,'_load_observation',lambda *a:{'array':np.ones(grid['shape'],dtype='float32'),'aux':{}})
 with pytest.raises(storage.InsufficientStorage):science.load_observation(item,BBOX,grid,{},lambda:False)
 assert not list(tmp_path.rglob('*.npz'))

def test_export_pressure_keeps_existing_outputs_and_creates_no_staging(tmp_path,monkeypatch):
 from backend.exports import export_result
 destination=tmp_path/'new';kept=tmp_path/'saved';kept.mkdir();(kept/'result.json').write_text('preserve')
 free(monkeypatch,0)
 result={'layers':{'one':{'data':np.ones((2,2),dtype='float32')}}}
 with pytest.raises(storage.InsufficientStorage):export_result(result,{},destination)
 assert not destination.exists() and not list(tmp_path.glob('.export-*'))
 assert (kept/'result.json').read_text()=='preserve' and 'data' in result['layers']['one']

def test_low_space_import_returns_clear_507_without_partial(tmp_path,monkeypatch):
 from test_subsets import setup
 _,client=setup(monkeypatch,tmp_path);free(monkeypatch,0)
 result=client.post('/api/import',content=b'something',headers={'x-filename':'source.h5'})
 assert result.status_code==507 and 'safety reserve' in result.json()['detail']
 assert not list(tmp_path.rglob('*.part'))

def test_metadata_readiness_reports_disk_shortage(tmp_path,monkeypatch):
 from backend.readiness import assess
 free(monkeypatch,0)
 report=assess([],[-1,-1,1,1],{'shape':[2,2],'resolution':100},'custom',{},product='GCOV')
 assert not report['ready'] and report['disk_space']['fits'] is False
 assert any('disk space' in error for error in report['errors'])

def test_mid_download_space_loss_removes_only_new_partial(tmp_path,monkeypatch):
 from backend import access
 monkeypatch.setattr(access,'DATA',tmp_path);(tmp_path/'raw').mkdir();old=tmp_path/'raw'/'old.h5';old.write_bytes(b'keep')
 checks=[]
 def dropping(path):
  checks.append(path);return Usage(10**12,0,10**10 if len(checks)<3 else 0)
 monkeypatch.setattr(storage.shutil,'disk_usage',dropping)
 class Response:
  headers={}
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def raise_for_status(self):pass
  def iter_content(self,*args):yield b'\x89HDF\r\n\x1a\n'
 monkeypatch.setattr(access.AUTH,'session',SimpleNamespace(get=lambda *a,**kw:Response()))
 with pytest.raises(storage.InsufficientStorage):access.download({'id':'new','url':'https://datapool.asf.alaska.edu/file.h5'},lambda:False,lambda *args:None)
 assert not (tmp_path/'raw'/'new.h5').exists() and not list(tmp_path.rglob('*.part'))
 assert old.read_bytes()==b'keep'

def test_job_admission_does_not_leave_a_ghost_when_metadata_fails(tmp_path,monkeypatch):
 from backend import app as service
 monkeypatch.setattr(service,'JOBS',{})
 def full(*args):raise OSError('simulated full disk')
 monkeypatch.setattr(service,'savejob',full)
 from fastapi import HTTPException
 with pytest.raises(HTTPException) as error:service.newjob('analysis',request={'product':'GCOV'})
 assert error.value.status_code==507 and 'No job was started' in error.value.detail
 assert not service.JOBS and not service.busy()

def test_failed_worker_unblocks_queue_even_when_final_status_cannot_be_saved(tmp_path,monkeypatch):
 from concurrent.futures import ThreadPoolExecutor
 from backend import app as service
 monkeypatch.setattr(service,'JOBS',{});monkeypatch.setattr(service,'JOBS_DIR',tmp_path)
 job=service.newjob('analysis')
 def full(*args):raise OSError('simulated full disk')
 monkeypatch.setattr(service,'savejob',full)
 def worker(job):job['status']='running';raise OSError('failed during processing')
 with ThreadPoolExecutor(max_workers=1) as pool:
  monkeypatch.setattr(service,'POOL',pool)
  future=service.submit_job(worker,job)
  with pytest.raises(OSError):future.result(timeout=3)
 assert job['status']=='failed' and not service.busy()
 assert 'Saved files were preserved' in job['message']

def test_worker_submission_failure_is_a_terminal_clear_503(tmp_path,monkeypatch):
 from fastapi import HTTPException
 from backend import app as service
 monkeypatch.setattr(service,'JOBS',{});monkeypatch.setattr(service,'JOBS_DIR',tmp_path)
 job=service.newjob('analysis')
 def unavailable(*args):raise RuntimeError('pool stopped')
 monkeypatch.setattr(service,'POOL',SimpleNamespace(submit=unavailable))
 with pytest.raises(HTTPException) as error:service.submit_job(lambda job:None,job)
 assert error.value.status_code==503 and job['status']=='failed' and not service.busy()

def test_unavailable_filesystem_has_a_clear_preservation_error(tmp_path,monkeypatch):
 def missing(path):raise OSError('device unavailable')
 monkeypatch.setattr(storage.shutil,'disk_usage',missing)
 with pytest.raises(storage.InsufficientStorage,match='drive is mounted and readable'):storage.storage_status(tmp_path)
 assert not list(tmp_path.iterdir())
