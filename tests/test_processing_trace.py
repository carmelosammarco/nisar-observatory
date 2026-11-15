"""Actual intermediate measurements, trace isolation, map links and export provenance."""
import re
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import numpy as np
import pytest
from backend.processing_trace import capture,snapshot,enabled,estimated_snapshot_count
from backend.workflows import checked_recipe,process
from backend.workflow_templates import example_recipe
from backend.science import target_grid
from test_processing_maturity import scene,BBOX


def raw_example(ident):
 raw=example_recipe(ident);raw['context']={};raw['options']={};raw['display']=None
 for step in raw['steps']:
  if step['operation']=='flood_history':step['parameters']['comparison_date']=None
  if step['operation']=='surface_baseline':step['parameters'].update(count=1,end=None)
 return raw


def test_capture_is_optional_isolated_and_keeps_only_latest_per_view_component():
 recipe=SimpleNamespace(method='custom',steps=[SimpleNamespace(operation='offset_screen')])
 source=np.ones((3,4),dtype='float32')
 assert not enabled('offset_screen')
 with capture(recipe) as collector:
  snapshot('offset_screen','slantRangeOffset',source,'Input','m',group='first',start='2026-01-01')
  source[:]=2
  snapshot('offset_screen','slantRangeOffset',source,'Input','m',group='first',start='2026-01-13')
  snapshot('offset_screen','slantRangeOffset',source,'Input','m',group='second')
  snapshot('unknown_step','ignored',source,'No entry','m')
  with ThreadPoolExecutor(max_workers=1) as pool:assert not pool.submit(enabled,'offset_screen').result(timeout=2)
  assert len(collector.snapshots)==2
  source[:]=99
 assert not enabled('offset_screen')
 for name,entry in collector.snapshots.items():
  assert re.fullmatch('[a-z0-9_]+',name)
  assert np.all(entry['layer']['data']==2)
 assert next(v for v in collector.snapshots.values() if v['layer']['trace_group']=='first')['layer']['start']=='2026-01-13'


def test_elementary_steps_point_to_their_actual_saved_outputs():
 grid=target_grid(BBOX,200)
 recipe=checked_recipe({'product':'GCOV','steps':[{'operation':'db'},{'operation':'baseline'},{'operation':'summary'}]})
 result=process(recipe,scene('GCOV',grid,[.1,.01]),grid)
 stages=result['extra']['processing_trace']['stages']
 assert [[m['id'] for m in s['maps']] for s in stages]==[['step_0_latest'],['step_1_latest','step_1_baseline'],['summary']]
 assert not result['extra']['processing_trace']['snapshot_maps']
 assert stages[1]['maps'][0]['unit']=='dB'


def test_flood_snapshot_is_the_exact_pre_comparison_baseline_and_links_all_results():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.001])
 recipe=checked_recipe(raw_example('P01_Mozambique'));result=process(recipe,obs,grid)
 stage=result['extra']['processing_trace']['stages'][1]
 layer=result['layers'][next(m['id'] for m in stage['maps'] if m['role']=='Captured intermediate')]
 np.testing.assert_array_equal(layer['data'],10*np.log10(obs[0]['array']))
 assert layer['start']==obs[0]['item']['start'] and layer['unit']=='dB'
 assert {'event','recovery','recovery_lower_days','recovery_upper_days','unresolved'}<=set(m['id'] for m in stage['maps'])
 tracking=result['extra']['processing_trace']['stages'][2]
 assert not tracking['maps'] and tracking['diagnostic_keys']==['tracking']


def test_joint_wetland_rule_links_sigma_inputs_and_occupancy_to_the_correct_steps():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.01,.001])
 for o in obs:o['aux']={'water_hh_sigma_power':o['array'].copy(),'water_hv_sigma_power':o['array']*.1}
 result=process(checked_recipe(raw_example('P02_Wheeler_Marsh')),obs,grid)
 stages=result['extra']['processing_trace']['stages']
 assert {'water','hh_sigma','hv_sigma'}<=set(m['id'] for m in stages[0]['maps'])
 assert 'occupancy' in [m['id'] for m in stages[1]['maps']]
 assert all(s['maps'] or s['diagnostic_keys'] for s in stages)


def test_fire_threshold_snapshot_is_before_patch_filtering_and_baselines_are_per_view():
 from test_fire import observations,GRID
 raw=raw_example('P03_Timber_Fire');recipe=checked_recipe(raw)
 result=process(recipe,observations(),GRID)
 trace=result['extra']['processing_trace'];threshold=next(s for s in trace['stages'] if s['operation']=='threshold')
 layer=result['layers'][threshold['maps'][0]['id']]
 score=result['layers']['fire_score']['data'];cutoff=next(s.parameters['value'] for s in recipe.steps if s.operation=='threshold')
 np.testing.assert_array_equal(layer['data'],np.where(np.isfinite(score),score>=cutoff,np.nan).astype('float32'))
 baselines=[x for x in result['layers'].values() if x.get('trace_operation')=='dual_change']
 assert len(baselines)==4 and len({x['trace_group'] for x in baselines})==2
 assert all(x['unit']=='power' for x in baselines)
 assert trace['snapshot_maps']<=estimated_snapshot_count(recipe.steps,[o['item'] for o in observations()])


def test_volcano_signed_threshold_keeps_missing_values_and_precedes_patch_filtering():
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.2,.3]);obs[0]['array'][0,0]=np.nan
 result=process(checked_recipe(raw_example('P06_Krasheninnikov')),obs,grid)
 trace=result['extra']['processing_trace'];stage=next(s for s in trace['stages'] if s['operation']=='signed_change')
 layer=result['layers'][stage['maps'][0]['id']];departure=result['layers']['latest_departure']['data']
 cutoff=result['extra']['surface_method']['change_threshold_db']
 expected=(departure>=cutoff).astype('int8')-(-departure>=cutoff).astype('int8')
 np.testing.assert_array_equal(layer['data'],np.where(np.isfinite(departure),expected,np.nan).astype('float32'))
 assert layer['classes']['-1']=='Dimming candidate' and np.isnan(layer['data'][0,0])
 assert len([x for x in result['layers'].values() if x.get('trace_operation')=='surface_baseline'])==2


def test_quake_selection_snapshot_is_input_phase_not_a_displacement_relabel():
 grid=target_grid(BBOX,200);obs=scene('GUNW',grid,[.1,.2])
 raw=raw_example('P05_Venezuela');raw['options']={'reference_bbox':[BBOX[0],BBOX[1],BBOX[0]+.01,BBOX[3]]}
 raw['steps'][0]['parameters'].update(date='2026-08-05',timestamp=None,mosaic=False)
 result=process(checked_recipe(raw),obs,grid)
 selected=result['extra']['event_measurement']['selected_source'];source=next(o for o in obs if o['item']['id']==selected)
 layer=next(x for x in result['layers'].values() if x.get('trace_operation')=='event_pairs')
 np.testing.assert_array_equal(layer['data'],source['array'])
 assert layer['unit']=='rad' and layer['start']==source['item']['start']


def test_glacier_snapshots_keep_native_offsets_and_unannualized_horizontal_speed():
 from test_horizontal_glacier import geometry
 grid=target_grid(BBOX,200);obs=scene('GOFF',grid,[2.])
 for o in obs:
  o['aux']={'other_offset':np.full(grid['shape'],3.,dtype='float32'),**{'geometry_'+k:v for k,v in geometry(grid['shape']).items()}}
 recipe=checked_recipe(raw_example('P07_Samudra_Tapu'));result=process(recipe,obs,grid)
 native=[x for x in result['layers'].values() if x.get('trace_operation')=='offset_screen']
 assert len(native)==2 and all(x['unit']=='m' for x in native)
 assert set(round(float(np.nanmedian(x['data'])),4) for x in native)=={2.,3.}
 daily=next(x for x in result['layers'].values() if x.get('trace_operation')=='horizontal_velocity')
 assert daily['unit']=='m/day' and result['layers']['horizontal_speed']['unit']=='m/year'
 np.testing.assert_array_equal(daily['data']*365.25,result['layers']['horizontal_speed']['data'])
 assert all(s['maps'] or s['diagnostic_keys'] for s in result['extra']['processing_trace']['stages'])


def test_post_operation_evidence_uses_post_map_not_internal_threshold():
 raw=raw_example('P01_Mozambique');raw['steps'][-1]['parameters']['layer']='change'
 raw['steps'].insert(-1,{'operation':'threshold','parameters':{'value':-3,'direction':'below'}})
 grid=target_grid(BBOX,200);result=process(checked_recipe(raw),scene('GCOV',grid,[.1,.001]),grid)
 assert [m['id'] for m in result['extra']['processing_trace']['stages'][-2]['maps']]==['workflow_post_0']
 assert [m['id'] for m in result['extra']['processing_trace']['stages'][-1]['maps']]==['workflow_output']


def test_trace_joins_existing_atomic_exports_with_intermediate_tags(tmp_path):
 import rasterio,json
 from backend.exports import export_result
 grid=target_grid(BBOX,200);result=process(checked_recipe(raw_example('P01_Mozambique')),scene('GCOV',grid,[.1,.001]),grid)
 saved=export_result(result,grid,tmp_path/'run')
 trace=saved['extra']['processing_trace'];available={l['id']:l for l in saved['layers']}
 for stage in trace['stages']:
  for m in stage['maps']:
   assert m['id'] in available and (tmp_path/'run'/available[m['id']]['raster']).is_file()
 layer=next(l for l in saved['layers'] if l.get('trace_operation'))
 assert 'Intermediate processing evidence' in layer['interpretation']
 with rasterio.open(tmp_path/'run'/layer['raster']) as src:
  assert src.tags(1)['processing_stage']=='flood_history' and src.tags(1)['intermediate']=='true'
 assert json.loads((tmp_path/'run/result.json').read_text())['extra']['processing_trace']==trace


def test_readiness_accounts_for_extra_trace_maps_without_reading_science():
 from backend.readiness import assess
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.001]);recipe=checked_recipe(raw_example('P01_Mozambique'))
 items=[o['item'] for o in obs]
 with_trace=assess(items,BBOX,grid,'P01',recipe.options,recipe.steps,'GCOV')
 without=assess(items,BBOX,grid,'P01',recipe.options,(),'GCOV')
 assert with_trace['ready'] and with_trace['estimated_trace_maps']==1
 assert with_trace['estimated_grid_bytes']-without['estimated_grid_bytes']==np.prod(grid['shape'])*4
 assert with_trace['estimated_trace_bytes']==np.prod(grid['shape'])*4


def test_capture_resets_after_failure_and_never_merges_colliding_view_identities(monkeypatch):
 import backend.processing_trace as trace
 recipe=SimpleNamespace(method='custom',steps=[SimpleNamespace(operation='offset_screen')])
 with pytest.raises(ValueError,match='unexpected'),capture(recipe):raise ValueError('unexpected')
 assert not enabled('offset_screen')
 monkeypatch.setattr(trace.hashlib,'sha256',lambda value:SimpleNamespace(hexdigest=lambda:'0'*64))
 with capture(recipe) as collector:
  snapshot('offset_screen','component',np.ones((2,2)),'First','m',group='a')
  with pytest.raises(ValueError,match='collision'):snapshot('offset_screen','component',np.zeros((2,2)),'Second','m',group='b')
  assert np.all(next(iter(collector.snapshots.values()))['layer']['data']==1)


def test_fitted_water_threshold_is_distinguished_from_recipe_starting_value(monkeypatch):
 from backend import processors
 grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.1]);h,w=grid['shape'];wet=np.zeros((h,w),bool);wet[:,:w//2]=True
 for o in obs:o['array'][wet]=.025
 contexts=[{'role':role,'mask':mask,'name':role,'properties':{'date':obs[0]['item']['start'][:10],'split':'train','source':'Synthetic label fixture'}} for role,mask in [('water',wet),('dry',~wet)]]
 monkeypatch.setattr(processors,'context_masks',lambda *args:contexts)
 result=process(checked_recipe(raw_example('P01_Mozambique')),obs,grid)
 validation=result['extra']['water_validation'];assert validation['calibration_cells']>0 and validation['threshold_db']!=-17
 stage=result['extra']['processing_trace']['stages'][0]
 assert 'water_validation' in stage['diagnostic_keys']
 assert 'Effective threshold:' in stage['parameter_note'] and 'not held-out accuracy' in stage['parameter_note']
