"""Typed block compilation, scientific edits and protected example contracts."""
import copy
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend import app as service
from backend.examples import CASES,definition
from backend.workflows import Recipe,checked_recipe,process,templates
from backend.science import target_grid
from test_processing_maturity import scene,BBOX

@pytest.mark.parametrize('ident',CASES)
def test_each_example_has_an_importable_editable_recipe(ident):
 r=checked_recipe(templates.example_recipe(ident));m=definition(ident)
 assert r.method=='custom' and len(r.context.sources)==len(m['sources'])
 assert r.context.bbox==m['request']['bbox']
 assert r.steps[-1].operation==('summary' if m['tool']=='P04' else 'publish')
 if templates.is_scientific(r.steps):
  plan=templates.compile_plan(r.product,r.steps,r.options)
  assert plan.method==m['tool'] and plan.output==m['request']['display']['layer']
  for key,value in m['request']['options'].items():assert plan.options[key]==value,(ident,key)

@pytest.mark.parametrize('ident',CASES)
def test_missing_required_dependency_is_rejected(ident):
 raw=templates.example_recipe(ident)
 if raw['steps'][0]['operation']=='los':raw['steps'].pop(1)
 elif ident=='P07_Samudra_Tapu':raw['steps']=[s for s in raw['steps'] if s['operation']!='rate_units']
 else:raw['steps'].pop(0)
 with pytest.raises(ValueError):checked_recipe(raw)

def test_optional_smoothing_patch_tracking_and_bias_are_real_choices():
 for ident,operation,key,expected in [('P03_Timber_Fire','smooth','smoothing_m',0),('P03_Timber_Fire','patches','patch_area_m2',0),('P06_Krasheninnikov','smooth','smoothing_m',0),('P01_Mozambique','water_tracking','patch_area_m2',0),('P07_Samudra_Tapu','offset_screen','offset_filter',False),('P07_Samudra_Tapu','offset_bias','offset_stable_bias',False)]:
  raw=templates.example_recipe(ident);raw['steps']=[s for s in raw['steps'] if s['operation']!=operation];r=checked_recipe(raw)
  assert templates.compile_plan(r.product,r.steps,r.options).options[key]==expected

def test_shared_step_changes_override_old_example_options():
 raw=templates.example_recipe('P03_Timber_Fire');raw['steps'][1]['parameters']['sigma_m']=120;raw['steps'][3]['parameters']['value']=3
 r=checked_recipe(raw);p=templates.compile_plan(r.product,r.steps,r.options)
 assert p.options['smoothing_m']==120 and p.options['score_threshold']==3

def test_post_steps_have_separate_output_and_do_not_relabel_original_findings():
 raw=templates.example_recipe('P01_Mozambique');raw['context']={};raw['options']={'resolution':200};raw['steps'][1]['parameters']['comparison_date']=None;raw['steps'][-1]['parameters']['layer']='change';raw['steps'].insert(-1,{'operation':'threshold','parameters':{'value':-3,'direction':'below'}})
 r=checked_recipe(raw);grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.001]);out=process(r,obs,grid)
 assert np.nanmin(out['layers']['workflow_output']['data'])==1
 assert out['layers']['workflow_output']['unit']=='class' and out['layers']['change']['unit']=='dB'
 assert out['extra']['workflow_output_statistics']['median']==1
 assert 'original' in out['report']['findings'][-1].lower()
 assert out['_workflow_display']['layer']=='workflow_output'

def test_category_smoothing_and_unrelated_product_or_order_are_rejected():
 raw=templates.example_recipe('P01_Mozambique');raw['steps'].insert(-1,{'operation':'smooth','parameters':{'sigma_m':80}})
 with pytest.raises(ValueError,match='category'):checked_recipe(raw)
 raw=templates.example_recipe('P07_Samudra_Tapu');raw['product']='GCOV'
 with pytest.raises(ValueError):checked_recipe(raw)
 raw=templates.example_recipe('P03_Timber_Fire');raw['steps'][0],raw['steps'][2]=raw['steps'][2],raw['steps'][0]
 with pytest.raises(ValueError):checked_recipe(raw)

def test_source_smoothing_executes_without_mutating_inputs():
 raw=templates.example_recipe('P01_Mozambique');raw['context']={};raw['options']={'resolution':200};raw['steps'][1]['parameters']['comparison_date']=None;raw['steps'].insert(0,{'operation':'source_smooth','parameters':{'sigma_m':200}})
 r=checked_recipe(raw);grid=target_grid(BBOX,200);obs=scene('GCOV',grid,[.1,.1]);obs[-1]['array'][3,3]=.001;before=obs[-1]['array'].copy();out=process(r,obs,grid)
 assert np.array_equal(obs[-1]['array'],before)
 assert out['layers']['change']['data'][3,3]>-20
 assert out['extra']['scientific_blocks']['source_smoothing']==200

def test_recipe_endpoint_does_not_start_analysis_or_expose_paths():
 c=TestClient(service.app)
 for ident in CASES:
  response=c.get('/api/examples/'+ident+'/workflow');assert response.status_code==200,response.text
  recipe=response.json();assert recipe['method']=='custom' and 'password' not in response.text
  assert not any('/Users/' in str(s) for s in recipe['context']['sources'])
 assert c.get('/api/examples/not-real/workflow').status_code==422

@pytest.mark.parametrize('ident',CASES)
def test_current_method_can_be_adapted_without_inheriting_example_geography(ident):
 m=definition(ident);response=TestClient(service.app).post('/api/workflows/from-method',json={'method':m['tool'],'options':m['request']['options']})
 assert response.status_code==200,response.text
 r=checked_recipe(response.json());assert r.method=='custom' and r.context.bbox is None and r.context.sources==[] and r.display is None
 if templates.is_scientific(r.steps):assert templates.compile_plan(r.product,r.steps,r.options).method==m['tool']

def test_unsupported_modes_and_credentials_do_not_become_editable_templates():
 c=TestClient(service.app)
 for method,options in [('P03',{'fire_method':'relative'}),('P06',{'surface_method':'legacy'}),('P01',{'password':'secret'})]:
  response=c.post('/api/workflows/from-method',json={'method':method,'options':options});assert response.status_code==422
  assert 'secret' not in response.text
