"""Known-value calculations and persistent workflow/API behavior, without NASA access."""
import copy,json,time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend import app as service
from backend.workflows import Recipe,process,checked_recipe
from backend.science import target_grid
from test_processing_maturity import scene,BBOX,REFERENCE

def recipe(product='GCOV',steps=None,**kw):
 return Recipe(product=product,steps=steps or [{'operation':'db'},{'operation':'baseline','parameters':{'count':1}},{'operation':'summary','parameters':{'statistic':'mean'}}],**kw)

def test_db_baseline_summary_has_known_units_sign_and_missing_support():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.01,.1]);obs[1]['array'][0,0]=np.nan
 r=process(recipe(),obs,grid)
 assert r['layers']['summary']['data'][2,2]==pytest.approx(5)
 assert r['layers']['change']['data'][2,2]==pytest.approx(10)
 assert np.isnan(r['layers']['summary']['data'][0,0])
 assert r['layers']['count']['data'][0,0]==1
 assert r['unit']=='dB' and len(r['extra']['step_history'])==3
 assert r['report']['findings'] and 'accuracy' in r['report']['findings'][1]

def test_smoothing_preserves_missing_centers_and_constant_values():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1]);obs[0]['array'][0,0]=np.nan
 r=process(recipe(steps=[{'operation':'smooth','parameters':{'sigma_m':80}},{'operation':'summary'}]),obs,grid)
 a=r['layers']['summary']['data'];assert np.isnan(a[0,0]);assert np.nanmin(a)==pytest.approx(.1);assert np.nanmax(a)==pytest.approx(.1)

def test_threshold_patch_area_and_frequency_are_not_interpolated_time():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[0.,0.]);obs[0]['array'][2:4,2:4]=2;obs[1]['array'][2,2]=2
 r=process(recipe(steps=[{'operation':'threshold','parameters':{'value':1}},{'operation':'patches','parameters':{'minimum_m2':80000}},{'operation':'summary','parameters':{'statistic':'frequency'}}]),obs,grid)
 assert r['layers']['summary']['unit']=='fraction'
 assert r['layers']['summary']['data'][2,2]==.5
 assert r['layers']['observation_1']['data'][2,2]==0

def test_phase_reference_uses_source_wavelength_and_fixed_pixels():
 grid=target_grid(BBOX,200);obs=scene('GUNW',grid,[0.,0.]);obs[0]['array'][:,grid['shape'][1]//2:]=np.pi
 r=process(recipe('GUNW',[{'operation':'los'},{'operation':'summary'}],options={'reference_bbox':REFERENCE}),obs,grid)
 assert np.nanmin(r['layers']['observation_0']['data'])==pytest.approx(-6)
 assert r['extra']['reference_diagnostics']['fixed_pixels']>0
 with pytest.raises(ValueError,match='reference'):process(recipe('GUNW',[{'operation':'los'},{'operation':'summary'}]),obs,grid)

def test_offset_rate_uses_exact_pair_days_and_annualization():
 grid=target_grid(BBOX,200);obs=scene('GOFF',grid,[12.])
 r=process(recipe('GOFF',[{'operation':'rate','parameters':{'annualized':True}},{'operation':'summary'}]),obs,grid)
 assert np.nanmedian(r['layers']['summary']['data'])==pytest.approx(365.25)
 assert r['unit']=='m/year' and r['extra']['offset_filter_diagnostics']

@pytest.mark.parametrize('product,steps',[
 ('GUNW',[{'operation':'smooth'},{'operation':'summary'}]),
 ('GCOV',[{'operation':'baseline'},{'operation':'db'},{'operation':'summary'}]),
 ('GCOV',[{'operation':'threshold'},{'operation':'smooth'},{'operation':'summary','parameters':{'statistic':'frequency'}}]),
 ('GCOV',[{'operation':'summary'},{'operation':'db'}]),
 ('GOFF',[{'operation':'db'},{'operation':'summary'}]),
 ('GCOV',[{'operation':'patches'},{'operation':'summary'}]),
 ('GCOV',[{'operation':'summary','parameters':{'statistic':'frequency'}}]),
 ('GCOV',[{'operation':'summary','parameters':{'statistic':'eval'}}]),
])
def test_invalid_scientific_order_or_code_is_rejected(product,steps):
 with pytest.raises(ValueError):recipe(product,steps)

def test_persistence_import_export_forbids_secrets_and_is_separate_from_cache(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'DATA',tmp_path);monkeypatch.setattr(service,'JOBS',{})
 c=TestClient(service.app);raw=recipe(name='My named experiment').model_dump(mode='json')
 saved=c.post('/api/workflows',json=raw);assert saved.status_code==200,saved.text;ident=saved.json()['id']
 assert c.get('/api/workflows').json()[0]['name']==raw['name']
 export=c.get(f'/api/workflows/{ident}/export');assert export.json()==raw
 assert 'attachment' in export.headers['content-disposition']
 assert c.delete('/api/cache').status_code==200
 assert c.get('/api/workflows').json()[0]['id']==ident
 raw['options']['password']='never-include-this'
 denied=c.post('/api/workflows/validate',json=raw);assert denied.status_code==422 and 'never-include-this' not in denied.text
 assert c.delete('/api/workflows/'+ident).status_code==200
 assert c.get('/api/workflows').json()==[]

def test_full_custom_run_is_reopenable_exportable_and_records_exact_recipe(tmp_path,monkeypatch):
 from backend import workflows
 data=tmp_path/'data';data.mkdir();jobs=data/'jobs';jobs.mkdir();(data/'raw').mkdir()
 monkeypatch.setattr(service,'DATA',data);monkeypatch.setattr(service,'JOBS_DIR',jobs);monkeypatch.setattr(service,'JOBS',{});monkeypatch.setattr(service,'CATALOG',{})
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.01,.1])
 for o in obs:service.CATALOG[o['item']['id']]=o['item'];(data/'raw'/(o['item']['id']+'.h5')).write_bytes(b'fixture')
 def load(item,bbox,target,options,cancel):
  out=copy.deepcopy(obs[int(item['id'])]);out['array']=np.full(target['shape'],.01 if item['id']=='0' else .1,dtype='float32');out['reader_version']='synthetic';return out
 monkeypatch.setattr(workflows,'load_observation',load,raising=False)
 c=TestClient(service.app);r=c.post('/api/workflows/run',json={'recipe':recipe(options={'resolution':200}).model_dump(mode='json'),'bbox':BBOX,'granules':['0','1']})
 assert r.status_code==200,r.text;ident=r.json()['id']
 for _ in range(300):
  job=c.get('/api/jobs/'+ident).json()
  if job['status'] not in ['queued','running']:break
  time.sleep(.01)
 assert job['status']=='completed',job
 result=c.get(f'/api/artifacts/{ident}/LAB/result.json');assert result.status_code==200
 body=result.json();assert body['extra']['workflow_actual_bbox']==BBOX and len(body['extra']['workflow_actual_inputs'])==2
 assert c.get(f'/api/artifacts/{ident}/LAB/workflow.json').json()['steps'][0]['operation']=='db'
 assert c.get(f'/api/artifacts/{ident}/LAB/summary.tif').status_code==200
 assert c.get(f'/api/visualization/{ident}/LAB/summary').status_code==200
 assert c.get(f'/api/map-image/{ident}/LAB/summary').status_code==200
 assert c.put(f'/api/jobs/{ident}/display/LAB',json={'layer':'summary','unit':'dB','palette':'rainbow','mode':'custom','low':0,'high':10}).status_code==200

@pytest.mark.parametrize('method', ['P01','P02','P03','P04','P05','P06','P07'])
def test_guided_adapters_preserve_existing_scientific_outputs(method):
 from backend.engines import PRODUCT_FOR,MINIMUM
 from backend.processors import process as original
 grid=target_grid(BBOX,200);product=PRODUCT_FOR[method]
 observations=scene(product,grid,[.1]*max(3,MINIMUM[method]))
 options={'reference_bbox':REFERENCE,'event_date':'2026-08-05'}
 expected=original(method,copy.deepcopy(observations),grid,options)
 actual=process(Recipe(name='Adapted method',product=product,method=method,options=options),copy.deepcopy(observations),grid)
 assert actual['project']=='LAB' and actual['extra']['workflow_method']==method
 assert actual['metrics']==expected['metrics']
 for key in expected['layers']:assert np.allclose(expected['layers'][key]['data'],actual['layers'][key]['data'],equal_nan=True)

def test_reference_or_code_injection_does_not_reach_export(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'DATA',tmp_path)
 c=TestClient(service.app);raw=recipe().model_dump(mode='json')
 for bad in [dict(raw,engine_version='999'),dict(raw,code='print(1)'),dict(raw,steps=[{'operation':'exec','parameters':{'code':'anything'}}])]:
  assert c.post('/api/workflows/validate',json=bad).status_code==422
 assert c.get('/api/workflows/../../etc/passwd/export').status_code!=200

def test_custom_workflow_rejects_mixed_measurement_paths_and_duplicate_epochs():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.01,.1])
 obs[1]['path']+='different_channel'
 with pytest.raises(ValueError,match='different measurement'):process(recipe(),obs,grid)
 obs[1]['path']=obs[0]['path'];obs[1]['item']['start']=obs[0]['item']['start'];obs[1]['item']['end']=obs[0]['item']['end']
 with pytest.raises(ValueError,match='one source revision'):process(recipe(),obs,grid)

def test_editable_network_and_trend_match_existing_p04():
 from backend.processors import process as guided
 grid=target_grid(BBOX,200);obs=scene('GUNW',grid,[0.,0.,0.])
 # Connected three-pair chain; nonzero phase change only outside the reference.
 for i,o in enumerate(obs):o['array'][:,grid['shape'][1]//2:]=i+1
 options={'reference_bbox':REFERENCE}
 steps=[{'operation':'los'},{'operation':'network','parameters':{'require_cycles':False}},{'operation':'trend','parameters':{'annualized':True}},{'operation':'summary'}]
 out=process(recipe('GUNW',steps,options=options),copy.deepcopy(obs),grid)
 expected=guided('P04',copy.deepcopy(obs),grid,options)
 assert np.array_equal(out['layers']['summary']['data'],expected['layers']['los_rate_year']['data'],equal_nan=True)
 assert len(out['series'])==len(expected['extra']['los_model']['epochs'])
 assert out['layers']['observation_0']['unit']=='cm' and out['layers']['summary']['unit']=='cm/year'
 for key in ['observation_0','change']:assert key in out['layers']
 assert out['extra']['trend_fit']['span_days']>0
 assert out['extra']['network_reconstruction']['redundancy']==0

@pytest.mark.parametrize('steps',[
 [{'operation':'los'},{'operation':'trend'},{'operation':'summary'}],
 [{'operation':'los'},{'operation':'rate'},{'operation':'network'},{'operation':'summary'}],
 [{'operation':'los'},{'operation':'network'},{'operation':'network'},{'operation':'summary'}],
 [{'operation':'los'},{'operation':'network'},{'operation':'trend'},{'operation':'baseline'},{'operation':'summary'}],
])
def test_invalid_network_temporal_domains_are_rejected(steps):
 with pytest.raises(ValueError):recipe('GUNW',steps)

def test_network_redundancy_gate_and_daily_trend():
 grid=target_grid(BBOX,200);obs=scene('GUNW',grid,[0.,0.,0.])
 for o in obs:o['array'][:,grid['shape'][1]//2:]=1
 base=[{'operation':'los'},{'operation':'network','parameters':{'require_cycles':False}},{'operation':'trend','parameters':{'annualized':True}},{'operation':'summary'}]
 yearly=process(recipe('GUNW',base,options={'reference_bbox':REFERENCE}),copy.deepcopy(obs),grid)
 base[2]['parameters']['annualized']=False
 daily=process(recipe('GUNW',base,options={'reference_bbox':REFERENCE}),copy.deepcopy(obs),grid)
 assert np.allclose(yearly['layers']['summary']['data']/365.25,daily['layers']['summary']['data'],equal_nan=True)
 base[1]['parameters']['require_cycles']=True
 with pytest.raises(ValueError,match='redundant pair cycle'):process(recipe('GUNW',base,options={'reference_bbox':REFERENCE}),obs,grid)

def test_editable_los_accepts_the_same_reference_polygon_as_guided_processing():
 from backend.processors import process as guided
 grid=target_grid(BBOX,200);obs=scene('GUNW',grid,[0.,0.]);obs[0]['array'][:,grid['shape'][1]//2:]=np.pi
 w,s,e,n=REFERENCE
 context={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'reference','name':'Independent reference'},'geometry':{'type':'Polygon','coordinates':[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}}]}
 options={'spatial_context':context}
 out=process(recipe('GUNW',[{'operation':'los'},{'operation':'summary'}],options=options),copy.deepcopy(obs),grid)
 expected=guided('P04',copy.deepcopy(obs),grid,options)
 assert out['extra']['reference_diagnostics']['fixed_pixels']>0
 assert np.array_equal(out['layers']['observation_0']['data'],expected['layers']['pair_0']['data']/10,equal_nan=True)

def test_temporal_baseline_changes_epoch_meaning_and_keeps_later_frame():
 grid=target_grid(BBOX,200);obs=scene('GUNW',grid,[0.,0.]);obs[0]['array'][:,grid['shape'][1]//2:]=np.pi;obs[1]['array'][:,grid['shape'][1]//2:]=np.pi
 steps=[{'operation':'los'},{'operation':'network'},{'operation':'baseline','parameters':{'count':2}},{'operation':'summary'}]
 out=process(recipe('GUNW',steps,options={'reference_bbox':REFERENCE}),obs,grid)
 assert len(out['series'])==3
 assert out['layers']['observation_0']['frame_scope']=='processed_epoch'
 assert np.nanmax(out['layers']['observation_0']['data'])==pytest.approx(3)
 assert any('first date need not remain zero' in note for note in out['notes'])
