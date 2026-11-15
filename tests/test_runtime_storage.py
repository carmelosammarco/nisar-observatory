"""Durability, process isolation and temporal-stage contract regressions."""
import json,os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from backend.runtime_storage import RuntimeLease,atomic_json,load_jobs,runtime_directory
from backend.readiness import assess
from backend.workflow_templates import Water,Horizontal
from backend.analysis_options import AnalysisOptions

ROOT=Path(__file__).resolve().parents[1]

def child(code,root):
 return subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env={**os.environ,'NISAR_DATA_DIR':str(root),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=30)

def test_lease_blocks_other_process_and_releases(tmp_path):
 code=f'from backend.runtime_storage import RuntimeLease; RuntimeLease({str(tmp_path)!r}).acquire()'
 with RuntimeLease(tmp_path):
  result=child(code,tmp_path)
  assert result.returncode and 'Another server owns' in result.stderr
 assert child(code,tmp_path).returncode==0
 # Child exit releases the OS lock even without explicit release.
 with RuntimeLease(tmp_path):pass
 assert (tmp_path/'.runtime.lock').is_file()

def test_lock_rejects_links_without_touching_target(tmp_path):
 target=tmp_path/'safe';target.write_text('preserve')
 lock=tmp_path/'.runtime.lock';lock.symlink_to(target)
 with pytest.raises(RuntimeError,match='symbolic'):RuntimeLease(tmp_path).acquire()
 assert target.read_text()=='preserve'
 lock.unlink();os.link(target,lock)
 with pytest.raises(RuntimeError,match='hard links'):RuntimeLease(tmp_path).acquire()
 assert target.read_text()=='preserve'

def test_atomic_record_failure_preserves_committed_record(tmp_path,monkeypatch):
 import backend.runtime_storage as storage
 path=tmp_path/'job.json';atomic_json(path,{'value':1})
 def fail(*args):raise OSError('simulated storage failure')
 monkeypatch.setattr(storage.os,'replace',fail)
 with pytest.raises(OSError):atomic_json(path,{'value':2})
 assert json.loads(path.read_text())=={'value':1}
 assert not list(tmp_path.glob('.job-*.tmp'))
 with pytest.raises(ValueError):atomic_json(path,{'bad':float('nan')})
 assert json.loads(path.read_text())=={'value':1}

def test_recovery_is_explicit_durable_and_idempotent(tmp_path):
 name='a'*32;path=tmp_path/name/'job.json'
 atomic_json(path,{'id':name,'status':'running','created_at':'2026-10-22T00:00:00Z','results':{'P01':{'status':'exploratory'}}})
 before=path.read_bytes();loaded,issues=load_jobs(tmp_path)
 assert not issues and loaded[name]['status']=='running' and path.read_bytes()==before
 recovered,issues=load_jobs(tmp_path,recover=True)
 assert not issues and recovered[name]['status']=='interrupted'
 assert recovered[name]['results']['P01']['status']=='exploratory'
 after=path.read_bytes();load_jobs(tmp_path,recover=True);assert path.read_bytes()==after
 bad=tmp_path/('b'*32)/'job.json';bad.parent.mkdir();bad.write_text('not json')
 _,issues=load_jobs(tmp_path,recover=True)
 assert len(issues)==1 and bad.read_text()=='not json'

def test_profile_root_and_app_import_do_not_mutate_jobs(tmp_path,monkeypatch):
 monkeypatch.setenv('NISAR_DATA_DIR','relative')
 with pytest.raises(ValueError,match='absolute'):runtime_directory(tmp_path)
 root=tmp_path/'profile';path=root/'jobs'/('c'*32)/'job.json'
 atomic_json(path,{'id':'c'*32,'status':'running','created_at':'2026-10-22T00:00:00Z','results':{}});before=path.read_bytes()
 result=child('from backend.app import DATA; print(DATA)',root)
 assert result.returncode==0,result.stderr
 assert str(root) in result.stdout and path.read_bytes()==before

def test_application_lifespan_recovers_and_owns_storage(tmp_path):
 code='''
from fastapi.testclient import TestClient
from backend.app import app,DATA
from backend.runtime_storage import RuntimeLease,atomic_json
atomic_json(DATA/'jobs'/('d'*32)/'job.json',{'id':'d'*32,'status':'queued','created_at':'2026-10-22T00:00:00Z','results':{}})
with TestClient(app) as client:
 assert client.get('/api/health').json()['runtime_owner'] is True
 try: RuntimeLease(DATA).acquire()
 except RuntimeError: pass
 else: raise AssertionError('second owner accepted')
 assert client.get('/api/jobs').status_code==200
assert app.state.runtime_owner is False
with RuntimeLease(DATA):pass
# A second lifespan can recreate the worker pool after clean shutdown.
with TestClient(app) as client: assert client.get('/api/health').json()['runtime_owner']
'''
 result=child(code,tmp_path)
 assert result.returncode==0,result.stderr
 saved=json.loads((tmp_path/'jobs'/('d'*32)/'job.json').read_text())
 assert saved['status']=='interrupted'

def source(start,end=None,product='GUNW'):
 return {'start':start,'end':end or start,'group':'same','product':product}
GRID={'shape':[10,10],'resolution':100}
BOX=[0,0,1,1]

def test_temporal_baseline_uses_reconstructed_epochs_not_pair_count():
 items=[source('2026-01-01T00:00:00Z','2026-01-13T00:00:00Z'),source('2026-01-13T01:00:00+01:00','2026-01-25T00:00:00Z')]
 steps=[SimpleNamespace(operation='network',parameters={}),SimpleNamespace(operation='baseline',parameters={'count':2})]
 report=assess(items,BOX,GRID,'custom',{'reference_bbox':BOX},steps,'GUNW')
 assert report['ready'],report['errors']
 assert report['stage_baselines'][0]['available_frames']==3
 steps[-1].parameters['count']=3
 assert not assess(items,BOX,GRID,'custom',{'reference_bbox':BOX},steps,'GUNW')['ready']

def test_explicit_flood_baseline_reports_all_precomparison_dates():
 items=[source(f'2026-01-{day:02}T00:00:00Z',product='GCOV') for day in [1,5,9,17]]
 report=assess(items,BOX,GRID,'P01',{'baseline_count':1,'flood_date':'2026-01-17'},product='GCOV')
 row=report['groups'][0]
 assert report['ready'] and len(row['baseline_dates'])==3 and len(row['context_baseline_dates'])==1
 assert row['comparison_dates']==['2026-01-17T00:00:00Z']

def test_editable_parameters_share_common_bounds():
 for model,field,shared in [(Water,'threshold_db','water_threshold'),(Water,'hv_db','water_hv_threshold'),(Horizontal,'height_m','offset_geometry_height_m'),(Horizontal,'condition_limit','offset_condition_limit')]:
  a=model.model_json_schema()['properties'][field];b=AnalysisOptions.model_json_schema()['properties'][shared]
  assert (a.get('minimum'),a.get('maximum'))==(b.get('minimum'),b.get('maximum'))
  for boundary in ['minimum','maximum']:
   if boundary in a:model.model_validate({field:a[boundary]})
  with pytest.raises(ValueError):model.model_validate({field:a['maximum']+1})

def test_shutdown_drains_worker_even_when_metadata_disk_write_fails(tmp_path):
 code='''
from fastapi.testclient import TestClient
import backend.app as service
from backend.runtime_storage import RuntimeLease
with TestClient(service.app):
 service.JOBS['e'*32]={'id':'e'*32,'status':'queued','results':{},'created_at':'2026-10-22T00:00:00Z'}
 def full(*args):raise OSError('simulated full disk')
 service.savejob=full
assert service.POOL._shutdown
assert service.JOBS['e'*32]['cancelled'] is True
assert service.JOBS['e'*32]['status']=='interrupted'
assert service.app.state.storage_issues
with RuntimeLease(service.DATA):pass
'''
 result=child(code,tmp_path)
 assert result.returncode==0,result.stderr
