"""Cancellation must remain control flow and preserve completed inputs/results."""
import json,threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pytest
from backend.execution import ProcessingCancelled,checkpoint,execution_scope


def test_scopes_reset_and_are_thread_local():
 with execution_scope(lambda:False):
  with pytest.raises(ProcessingCancelled),execution_scope(lambda:True):pass
  checkpoint()
  with ThreadPoolExecutor(max_workers=1) as pool:
   assert pool.submit(checkpoint).result(timeout=2) is None
 checkpoint()
 # The signal must bypass application/source handlers for bad data.
 assert not issubclass(ProcessingCancelled,Exception)


def test_cpu_kernel_stops_at_entry_and_exit(monkeypatch):
 from backend.raster_methods import smooth
 import backend.raster_methods as methods
 a=np.ones((12,15),dtype='float32');cancelled=[False];original=methods.ndimage.gaussian_filter
 def stop_after_call(*args,**kwargs):
  result=original(*args,**kwargs);cancelled[0]=True;return result
 monkeypatch.setattr(methods.ndimage,'gaussian_filter',stop_after_call)
 with execution_scope(lambda:cancelled[0]),pytest.raises(ProcessingCancelled):smooth(a,1.)
 np.testing.assert_array_equal(a,np.ones_like(a))


def test_worker_cancellation_is_terminal_and_keeps_committed_results(tmp_path,monkeypatch):
 from backend import app as service
 monkeypatch.setattr(service,'JOBS',{});monkeypatch.setattr(service,'JOBS_DIR',tmp_path)
 job=service.newjob('analysis');job['results']['P01']={'status':'exploratory','url':'committed'}
 def worker(job):
  service.update(job,status='running');job['cancelled']=True
  try:checkpoint()
  except Exception:raise AssertionError('Cancellation was mistaken for bad input')
 with ThreadPoolExecutor(max_workers=1) as pool:
  monkeypatch.setattr(service,'POOL',pool)
  service.submit_job(worker,job).result(timeout=3)
  # A cancelled job must not poison the reusable worker context.
  assert pool.submit(checkpoint).result(timeout=3) is None
 assert job['status']=='cancelled' and not service.busy()
 assert job['results']['P01']['url']=='committed'
 saved=json.loads((tmp_path/job['id']/'job.json').read_text())
 assert saved['status']=='cancelled' and saved['results']==job['results']


@pytest.mark.parametrize('wrapped_io_error',[False,True])
def test_cancelled_lab_source_is_not_reported_as_unreadable(tmp_path,monkeypatch,wrapped_io_error):
 from backend import app as service,workflows,science
 from fastapi.testclient import TestClient
 monkeypatch.setattr(service,'JOBS',{});monkeypatch.setattr(service,'JOBS_DIR',tmp_path/'jobs');(tmp_path/'jobs').mkdir()
 items=[{'id':str(i),'name':'synthetic','product':'GCOV','group':'same','start':date+'T00:00:00Z','end':date+'T00:01:00Z'} for i,date in enumerate(['2026-01-01','2026-01-13'])]
 monkeypatch.setattr(service,'CATALOG',{i['id']:i for i in items})
 local=tmp_path/'input.h5';local.write_bytes(b'untouched source')
 monkeypatch.setattr(service,'DATA',tmp_path);monkeypatch.setattr(science,'DATA',tmp_path)
 (tmp_path/'raw').mkdir()
 for item in items:(tmp_path/'raw'/(item['id']+'.h5')).write_bytes(local.read_bytes())
 futures=[];submit=service.submit_job;entered=threading.Event();resume=threading.Event()
 def captured(*args):
  future=submit(*args);futures.append(future);return future
 monkeypatch.setattr(service,'submit_job',captured)
 def cancel_read(*args):
  entered.set();assert resume.wait(3),'Test did not release the reader'
  if wrapped_io_error:raise OSError('Native I/O wrapper error after cancellation')
  checkpoint()
 monkeypatch.setattr(workflows,'load_observation',cancel_read)
 recipe={'name':'Cancellation fixture','product':'GCOV','method':'custom','steps':[{'operation':'db','parameters':{}},{'operation':'summary','parameters':{}}]}
 with ThreadPoolExecutor(max_workers=1) as pool:
  monkeypatch.setattr(service,'POOL',pool)
  client=TestClient(service.app)
  try:
   response=client.post('/api/workflows/run',json={'recipe':recipe,'bbox':[0,0,.01,.01],'granules':['0','1']})
   assert response.status_code==200,response.text
   assert entered.wait(3)
   cancel=client.post('/api/jobs/'+response.json()['id']+'/cancel')
   assert cancel.status_code==200,cancel.text
  finally:resume.set()
  futures[0].result(timeout=3)
 job=next(iter(service.JOBS.values()))
 assert job['status']=='cancelled' and not job.get('source_errors') and not job['results']
 assert local.read_bytes()==b'untouched source'


def test_cancel_during_export_removes_only_uncommitted_staging(tmp_path,monkeypatch):
 from backend import exports
 from test_science import observations
 from backend.science import target_grid
 from backend.processors import process
 grid=target_grid([0,0,.01,.01],100)
 result=process('P01',observations('GCOV',grid,2),grid,{})
 prior=tmp_path/'prior';prior.mkdir();(prior/'saved.tif').write_bytes(b'committed')
 cancelled=[False];original=exports.colorize
 def stop_after_render(*args,**kwargs):
  out=original(*args,**kwargs);cancelled[0]=True;return out
 monkeypatch.setattr(exports,'colorize',stop_after_render)
 with execution_scope(lambda:cancelled[0]),pytest.raises(ProcessingCancelled):exports.export_result(result,grid,tmp_path/'new')
 assert not (tmp_path/'new').exists() and not list(tmp_path.glob('.export-*'))
 assert (prior/'saved.tif').read_bytes()==b'committed'


def test_cancel_immediately_before_result_commit(tmp_path,monkeypatch):
 from backend import exports
 cancelled=[False]
 def stage(result,grid,directory):
  (directory/'result.json').write_text('{}');cancelled[0]=True;return result
 monkeypatch.setattr(exports,'_export_result',stage)
 with execution_scope(lambda:cancelled[0]),pytest.raises(ProcessingCancelled):exports.export_result({'layers':{}},{},tmp_path/'new')
 assert not (tmp_path/'new').exists() and not list(tmp_path.glob('.export-*'))


def test_cancel_after_cache_compression_does_not_publish_partial_cache(tmp_path,monkeypatch):
 from backend import science
 from test_subsets import setup,BBOX
 item,_=setup(monkeypatch,tmp_path)
 grid=science.target_grid(BBOX,100);cancelled=[False];original=science.np.savez_compressed
 def stop_after_write(*args,**kwargs):
  result=original(*args,**kwargs);cancelled[0]=True;return result
 monkeypatch.setattr(science.np,'savez_compressed',stop_after_write)
 with pytest.raises(ProcessingCancelled):science.load_observation(item,BBOX,grid,{},lambda:cancelled[0])
 assert not list((tmp_path/'arrays').iterdir())
 assert (tmp_path/'raw'/(item['id']+'.h5')).is_file()


def test_cancel_on_cache_hit_preserves_cache_and_does_not_start_new_read(tmp_path,monkeypatch):
 from backend import science
 from test_subsets import setup,BBOX
 item,_=setup(monkeypatch,tmp_path);grid=science.target_grid(BBOX,100)
 science.load_observation(item,BBOX,grid,{},lambda:False)
 path=science.cache_path(item,BBOX,grid,{});before=path.read_bytes();cancelled=[False];original=science.np.load
 def cancel_on_load(*args,**kwargs):
  result=original(*args,**kwargs);cancelled[0]=True;return result
 monkeypatch.setattr(science.np,'load',cancel_on_load)
 with pytest.raises(ProcessingCancelled):science.load_observation(item,BBOX,grid,{},lambda:cancelled[0])
 assert path.read_bytes()==before
