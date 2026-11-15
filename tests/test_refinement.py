"""Audit regressions: source/grid identity, scientific support and honest semantics."""
import copy,json
import numpy as np
import pytest
from affine import Affine
from backend import science
from backend.advanced import robust_baseline
from backend.raster_methods import smooth,analysis_grid,geographic_window_mask
from backend.workflow_templates import smooth_array,compile_plan,example_recipe
from backend.workflows import checked_recipe,process
from backend.map_image import legend_spec
from backend.readiness import assess
from test_processing_maturity import scene,BBOX


def test_cache_changes_with_crs_transform_product_revision_and_local_generation(tmp_path,monkeypatch):
 monkeypatch.setattr(science,'DATA',tmp_path);(tmp_path/'raw').mkdir()
 item={'id':'one','product':'GCOV'};grid=science.target_grid(BBOX,100)
 original=science.cache_path(item,BBOX,grid,{})
 for other in [{**grid,'crs':'EPSG:32632'},{**grid,'transform':grid['transform']*Affine.translation(1,1)}]:assert science.cache_path(item,BBOX,other,{})!=original
 assert science.cache_path({**item,'content_sha256':'abc'},BBOX,grid,{})!=original
 (tmp_path/'raw/one.h5').write_bytes(b'first')
 local=science.cache_path(item,BBOX,grid,{})
 assert local!=original
 (tmp_path/'raw/one.h5').write_bytes(b'other')
 assert science.cache_path(item,BBOX,grid,{})!=local


def test_cache_metadata_and_shape_are_checked_before_reuse(tmp_path,monkeypatch):
 monkeypatch.setattr(science,'DATA',tmp_path);item={'id':'one','product':'GCOV'};grid=science.target_grid(BBOX,100);calls=[]
 def read(*args):calls.append(1);return {'array':np.ones(grid['shape'],dtype='float32'),'aux':{},'bytes_transferred':0}
 monkeypatch.setattr(science,'_load_observation',read)
 first=science.load_observation(item,BBOX,grid,{},lambda:False)
 assert science.load_observation(item,BBOX,grid,{},lambda:False)['cache_hit']
 path=science.cache_path(item,BBOX,grid,{})
 with path.open('wb') as f:np.savez(f,array=np.ones((1,1)),metadata=json.dumps({'cache_identity':first['cache_identity']}))
 science.load_observation(item,BBOX,grid,{},lambda:False)
 assert len(calls)==2


def test_baseline_cannot_silently_shrink_and_explicit_end_keeps_exact_dates():
 values=np.ones((3,2,2));dates=['2026-01-01','2026-01-13','2026-01-25']
 with pytest.raises(ValueError,match='5 baseline'):robust_baseline(values,dates,{'baseline_count':5})
 assert robust_baseline(values,dates,{'baseline_end':'2026-01-13','baseline_count':5})[2]==[0,1]
 with pytest.raises(ValueError,match='later'):robust_baseline(values,dates,{'baseline_end':'2026-01-25'})


def test_smoothing_has_identical_edges_support_and_holes_in_every_path():
 a=np.arange(100,dtype='float32').reshape(10,10);a[2,3]=np.nan
 assert np.allclose(smooth(a,1),smooth_array(a,1),equal_nan=True)
 sparse=np.full((10,10),np.nan);sparse[3,3]=7
 assert np.isnan(smooth(sparse,1)).all() and np.isnan(smooth_array(sparse,1)).all()
 assert np.isnan(smooth_array(a,1)[2,3])
 with pytest.raises(ValueError):smooth(a,-1)


def test_generic_threshold_legend_never_invents_water_or_persistence():
 info={'id':'observation_0','unit':'class','kind':'binary'}
 assert legend_spec(info,{}, {'project':'LAB','extra':{'workflow':{'product':'GOFF'}}})==[(0,'Condition not met'),(1,'Condition met')]
 assert legend_spec(info,{}, {'project':'P01'})[1][1]=='Open-water candidate'
 assert 'Latest' in legend_spec({**info,'id':'surface'},{},{'project':'P06','extra':{'surface_method':{'id':'evolving'}}})[1][1]
 assert 'Repeated' in legend_spec({**info,'id':'confirmed_change'},{},{'project':'P06'})[1][1]


def test_removed_tracking_is_never_executed(monkeypatch):
 from backend import processors
 raw=example_recipe('P01_Mozambique');raw['context']={};raw['options']={'resolution':200};raw['steps']=[s for s in raw['steps'] if s['operation']!='water_tracking'];raw['steps'][1]['parameters']['comparison_date']=None
 r=checked_recipe(raw);grid=science.target_grid(BBOX,200)
 monkeypatch.setattr(processors,'patch_history',lambda *args:pytest.fail('Removed tracking still ran'))
 out=process(r,scene('GCOV',grid,[.1,.001]),grid)
 assert 'tracking' not in out['extra']


def test_fire_numeric_domain_is_clipped_to_selected_geographic_rectangle():
 from backend.fire import process as fire
 grid=analysis_grid([25,50,26,51],1000);y,x=np.indices(grid['shape']);obs=[]
 for i in range(4):
  change=(.02*x+.01*y+np.where((x>20)&(x<45)&(y>20)&(y<70),4,0)) if i==3 else np.zeros(grid['shape'])
  obs.append({'item':{'id':str(i),'name':str(i),'product':'GCOV','group':'view','start':f'2026-01-{1+7*i:02}T00:00:00Z','end':f'2026-01-{1+7*i:02}T00:01:00Z'},'array':.1*10**(change/10),'aux':{'cross_power':.02*10**(-change/10)},'attrs':{},'path':'HH','quality_paths':[],'bytes_transferred':0,'warnings':[]})
 result=fire(obs,grid,{'baseline_count':3,'smoothing_m':1000,'patch_area_m2':0})
 outside=~geographic_window_mask(grid);assert outside.any()
 for ident in ['fire_score','fire_candidate','change_intensity']:
  assert not np.isfinite(result['layers'][ident]['data'][outside]).any(),ident


def test_preflight_is_metadata_only_and_resolves_per_view_baselines():
 grid=science.target_grid(BBOX,200);items=[o['item'] for o in scene('GCOV',grid,[.1,.1,.1,.2])]
 report=assess(items,BBOX,grid,'P03',{'fire_method':'combined','baseline_count':3},product='GCOV')
 assert report['ready'] and len(report['groups'][0]['baseline_dates'])==3 and len(report['groups'][0]['comparison_dates'])==1
 bad=assess(items,BBOX,grid,'P03',{'fire_method':'combined','baseline_count':5},product='GCOV')
 assert not bad['ready'] and 'baseline' in ' '.join(bad['errors'])


def test_preflight_resource_budget_and_tree_are_honest(monkeypatch):
 grid=science.target_grid(BBOX,200);items=[o['item'] for o in scene('GUNW',grid,[0,0])]
 items[1]['start']=items[0]['end'];items[1]['end']='2026-09-01T00:00:00Z'
 report=assess(items,BBOX,grid,'P04',{'reference_bbox':BBOX},product='GUNW')
 assert report['ready'] and any('tree' in w for w in report['warnings'])
 monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','1')
 report=assess(items,BBOX,{**grid,'shape':(1000,1000)},'P04',{'reference_bbox':BBOX},product='GUNW')
 assert not report['ready'] and any('memory' in e for e in report['errors'])


def test_geotiff_metadata_and_execution_identity_ignore_display(tmp_path):
 from backend.exports import export_result
 import rasterio
 grid=science.target_grid(BBOX,200);obs=scene('GCOV',grid,[.01,.1]);raw={'product':'GCOV','steps':[{'operation':'threshold','parameters':{'value':.05}},{'operation':'summary','parameters':{'statistic':'frequency'}}]}
 fingerprints=[]
 for style in ['rainbow','diverging']:
  r=process(checked_recipe(raw),copy.deepcopy(obs),grid);r['display_preferences']={'palette':style};out=tmp_path/style;exported=export_result(r,grid,out)
  fingerprints.append(exported['extra']['execution_fingerprint'])
  with rasterio.open(out/'observation_0.tif') as ds:
   assert ds.units==('class',) and ds.descriptions[0]
   assert json.loads(ds.tags(1)['classes'])=={'0':'Condition not met','1':'Condition met'}
  assert 'independent' in exported['extra']['result_passport']['validation']
 assert fingerprints[0]==fingerprints[1]


def test_repeated_map_operations_keep_their_own_parameters_and_internal_sigma():
 raw=example_recipe('P03_Timber_Fire');raw['steps'][-1]['parameters']['layer']='fire_score'
 raw['steps'].insert(-1,{'operation':'smooth','parameters':{'sigma_m':160}})
 raw['steps'].insert(-1,{'operation':'threshold','parameters':{'value':4,'direction':'above'}})
 raw['steps'].insert(-1,{'operation':'patches','parameters':{'minimum_m2':50000}})
 r=checked_recipe(raw);plan=compile_plan(r.product,r.steps,r.options)
 assert plan.options['smoothing_m']==80 and plan.options['score_threshold']==2
 assert [s.operation for s in plan.post]==['smooth','threshold','patches']
 assert plan.post[0].parameters['sigma_m']==160 and plan.post[1].parameters['value']==4


def test_preflight_api_never_reads_arrays_and_saved_recipe_can_exist_without_data(monkeypatch,tmp_path):
 from fastapi.testclient import TestClient
 from backend import app as service,workflows
 monkeypatch.setattr(service,'DATA',tmp_path);monkeypatch.setattr(service,'CATALOG',{})
 monkeypatch.setattr(workflows,'load_observation',lambda *a:pytest.fail('Metadata check read science'))
 client=TestClient(service.app);raw={'product':'GCOV','steps':[{'operation':'summary'}]}
 response=client.post('/api/workflows/preflight',json={'recipe':raw,'bbox':BBOX,'granules':[]})
 assert response.status_code==200 and not response.json()['ready']
 assert client.post('/api/workflows',json=raw).status_code==200


def test_legacy_surface_legend_retains_its_original_persistence_meaning():
 assert legend_spec({'id':'surface','unit':'class','kind':'binary'},{},{'project':'P06'})[1][1]=='Persistent change candidate'


def test_asset_hashing_tracks_edits_and_api_keeps_no_store(tmp_path):
 import importlib.util,hashlib
 from pathlib import Path
 from fastapi.testclient import TestClient
 from backend.app import app
 spec=importlib.util.spec_from_file_location('asset_stamp',Path(__file__).resolve().parents[1]/'scripts/stamp_assets.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 front=tmp_path/'frontend';front.mkdir();asset=front/'app.js';asset.write_text('first')
 (front/'index.html').write_text('<script src="/app.js?v=old"></script><link href="https://example.org/x.css">')
 assert module.stamp(tmp_path) and not module.stamp(tmp_path)
 old=(front/'index.html').read_text();asset.write_text('second')
 assert module.stamp(tmp_path) and old!=(front/'index.html').read_text()
 assert 'https://example.org/x.css' in (front/'index.html').read_text()
 c=TestClient(app)
 assert c.get('/').headers['cache-control']=='no-cache'
 assert c.get('/workflow-workspace.js').headers['cache-control']=='no-cache'
 assert c.get('/api/health').headers['cache-control']=='no-store'


def test_failed_export_leaves_no_partial_run_and_never_overwrites_saved_data(tmp_path,monkeypatch):
 from backend import exports
 grid=science.target_grid(BBOX,200);folder=tmp_path/'run';calls=[]
 def fail(result,grid,directory):
  (directory/'partial.tif').write_bytes(b'new temporary output');raise ValueError('Synthetic export failure')
 monkeypatch.setattr(exports,'_export_result',fail)
 with pytest.raises(ValueError,match='Synthetic export'):exports.export_result({'layers':{'new':{'data':np.ones(grid['shape'],dtype='float32')}}},grid,folder)
 assert not folder.exists() and not list(tmp_path.glob('.export-*'))
 folder.mkdir();(folder/'keep.tif').write_bytes(b'existing user result')
 with pytest.raises(ValueError,match='already contains'):exports.export_result({'layers':{'new':{'data':np.ones(grid['shape'],dtype='float32')}}},grid,folder)
 assert (folder/'keep.tif').read_bytes()==b'existing user result'


def test_combined_fire_short_baseline_error_names_the_actual_requirement():
 grid=science.target_grid(BBOX,200);items=[o['item'] for o in scene('GCOV',grid,[.1,.1,.2])]
 report=assess(items,BBOX,grid,'P03',{'fire_method':'combined','baseline_count':2},product='GCOV')
 assert not report['ready']
 errors=' '.join(report['errors'])
 assert 'at least 3 baseline observations and 1 later observation per viewing group' in errors
 assert 'found 2 baseline and 1 later' in errors
