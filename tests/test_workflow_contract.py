"""Editor/backend parity, dependency errors and normative registry freshness."""
import copy,itertools,json,subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend import app as service
from backend.workflows import Step,checked_recipe,operator_registry
from backend.workflow_parameters import PARAMS,parameter_defaults
from backend.workflow_contract import RULES,inspect_sequence
from backend.workflow_templates import OUTPUTS,example_recipe,compile_plan
from backend.examples import CASES
ROOT=Path(__file__).resolve().parents[1]


def browser_reports(cases):
 registry=operator_registry()
 result=subprocess.run(['node',str(ROOT/'tests/helpers/workflow_contract_runner.cjs')],input=json.dumps({'rules':registry['workflow_rules'],'outputs':registry['scientific_outputs'],'cases':cases}),text=True,capture_output=True,timeout=60)
 assert result.returncode==0,result.stderr
 return json.loads(result.stdout)


def canonical(steps):return [Step.model_validate(s).model_dump(mode='json') for s in steps]


def cases_for_parity():
 cases=[]
 elementary=['db','los','network','trend','rate','baseline','smooth','threshold','patches','summary']
 for product in ['GCOV','GUNW','GOFF']:
  for length in range(4):
   for ops in itertools.product(elementary,repeat=length):cases.append({'product':product,'steps':canonical([{'operation':op} for op in ops])})
 for ident in CASES:
  recipe=example_recipe(ident);steps=canonical(recipe['steps']);product=recipe['product']
  for n in range(len(steps)+1):cases.append({'product':product,'steps':copy.deepcopy(steps[:n])})
  for n in range(len(steps)):
   cases.append({'product':product,'steps':copy.deepcopy(steps[:n]+steps[n+1:])})
   duplicate=copy.deepcopy(steps);duplicate.insert(n,copy.deepcopy(steps[n]));cases.append({'product':product,'steps':duplicate})
   if n+1<len(steps):
    reordered=copy.deepcopy(steps);reordered[n],reordered[n+1]=reordered[n+1],reordered[n];cases.append({'product':product,'steps':reordered})
  for other in ['GCOV','GUNW','GOFF']:cases.append({'product':other,'steps':copy.deepcopy(steps)})
  if steps[-1]['operation']=='publish':
   for layer in [*OUTPUTS.get(ident[:3],{}),'unknown_map']:
    changed=copy.deepcopy(steps);changed[-1]['parameters']['layer']=layer;cases.append({'product':product,'steps':changed})
   for op in ['smooth','threshold','patches']:
    changed=copy.deepcopy(steps);changed.insert(-1,Step(operation=op).model_dump(mode='json'));cases.append({'product':product,'steps':changed})
 return cases


def test_browser_and_backend_agree_on_generated_sequences():
 cases=cases_for_parity();browser=browser_reports(cases)
 assert len(cases)>3500 and len(browser)==len(cases)
 for index,(case,actual) in enumerate(zip(cases,browser)):
  expected=inspect_sequence(case['product'],case['steps'],OUTPUTS,parameter_defaults())
  assert actual==expected,(index,case,actual,expected)


def test_complete_contract_decisions_match_the_actual_recipe_validator():
 cases=cases_for_parity()
 for case in cases:
  report=inspect_sequence(case['product'],case['steps'],OUTPUTS,parameter_defaults())
  try:checked_recipe({'product':case['product'],'steps':case['steps']});accepted=True
  except ValueError:accepted=False
  assert accepted==report['complete'],(case,report)


def test_frontend_fixture_is_exported_from_current_backend_rules_and_defaults():
 fixture=json.loads((ROOT/'tests/frontend/fixtures/scientific-blocks.json').read_text());registry=operator_registry()
 assert fixture['rules']==registry['workflow_rules']
 assert fixture['outputs']==registry['scientific_outputs'] and fixture['operators']==registry['operators']
 for op in registry['operators']:
  assert op['defaults']==parameter_defaults()[op['id']]
 assert registry['operators'][next(i for i,o in enumerate(registry['operators']) if o['id']=='trend')]['defaults']['annualized'] is False


def test_inspection_is_metadata_only_and_accepts_incomplete_drafts(monkeypatch):
 from backend import science
 monkeypatch.setattr(science,'open_science',lambda *args:pytest.fail('Draft inspection must not read science files'))
 client=TestClient(service.app)
 report=client.post('/api/workflows/inspect',json={'product':'GCOV','steps':[{'operation':'water_rule'}]}).json()
 assert not report['complete'] and report['missing']==['wetland_history'] and report['minimum_sources']==3
 body={'product':'GUNW','steps':[{'operation':'los'},{'operation':'network'},{'operation':'baseline','parameters':{'count':2}},{'operation':'summary'}]}
 report=client.post('/api/workflows/inspect',json=body).json()
 assert report['complete'] and report['minimum_sources']==2
 assert report['rows'][2]['domain']=='epochs'
 assert client.post('/api/workflows/inspect',json={'product':'GCOV','steps':[{'operation':'execute_python'}]}).status_code==422


@pytest.mark.parametrize('operation,parameters',[
 ('smooth',{'sigma_m':0}),('smooth',{'sigma_m':1001}),('baseline',{'count':0}),('dual_change',{'baseline_count':2}),
 ('horizontal_velocity',{'condition_limit':101}),('flood_history',{'comparison_date':'2026-02-30'}),
 ('event_pairs',{'timestamp':'2026-06-16T12:00:00'}),('event_pairs',{'timestamp':'2026-06-16T12:00:00+01:60'})])
def test_browser_and_typed_backend_both_reject_invalid_parameter_values(operation,parameters):
 with pytest.raises(ValueError):Step(operation=operation,parameters=parameters)
 report=browser_reports([{'product':'GCOV' if operation not in ['event_pairs','horizontal_velocity'] else 'GUNW' if operation=='event_pairs' else 'GOFF','steps':[{'operation':operation,'parameters':parameters}]}])[0]
 assert report['parameter_issues'] and not report['complete']


def test_network_baseline_minimum_is_epochs_and_wetland_remains_three():
 steps=canonical([{'operation':'los'},{'operation':'network'},{'operation':'baseline','parameters':{'count':2}},{'operation':'summary'}])
 assert inspect_sequence('GUNW',steps,OUTPUTS)['minimum_sources']==2
 wetland=example_recipe('P02_Wheeler_Marsh');assert inspect_sequence('GCOV',wetland['steps'],OUTPUTS)['minimum_sources']==3


def test_smoothing_forms_and_internal_blocks_share_the_same_positive_range():
 assert PARAMS['smooth'].model_json_schema()['properties']['sigma_m']==PARAMS['source_smooth'].model_json_schema()['properties']['sigma_m']
 assert Step(operation='smooth',parameters={'sigma_m':.5}).parameters['sigma_m']==.5

def test_saved_workflow_contract_record_and_geotiff_tags_match_the_registry(tmp_path):
 import numpy as np,rasterio
 from backend.workflows import process,workflow_contract_record
 from backend.exports import export_result
 from backend.science import target_grid
 from test_processing_maturity import scene,BBOX
 recipe=checked_recipe({'product':'GCOV','steps':[{'operation':'db'},{'operation':'baseline'},{'operation':'summary'}]})
 grid=target_grid(BBOX,200);result=process(recipe,scene('GCOV',grid,[.1,.01]),grid)
 record=result['extra']['workflow_contract'];assert record['sha256']==workflow_contract_record()['sha256']
 assert record['step_io'][1]['input']=='dB' and record['step_io'][1]['scope']=='observed measurements'
 assert result['extra']['step_history'][0]['input_unit']=='power'
 exported=export_result(result,grid,tmp_path/'run')
 with rasterio.open(tmp_path/'run/summary.tif') as src:
  assert src.tags()['workflow_rules_sha256']==record['sha256'] and src.tags()['workflow_rules_version']==RULES['version']
  assert np.isfinite(src.read(1)).any()
 assert exported['extra']['workflow_contract']==record

def test_canonical_recipe_acceptance_matches_the_frozen_pre_refactor_backend():
 import hashlib
 baseline=json.loads((ROOT/'tests/fixtures/workflow-acceptance-0.8.2.json').read_text());cases=cases_for_parity()
 digest=hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert baseline['source_commit']=='8acbe66' and baseline['case_count']==len(cases) and baseline['cases_sha256']==digest
 accepted=[]
 for case in cases:
  try:checked_recipe(case);accepted.append(True)
  except ValueError:accepted.append(False)
 assert accepted==baseline['accepted']


def test_operator_ids_parameters_and_semantic_blocks_are_one_consistent_registry():
 from backend import workflow_templates as templates
 registry=operator_registry();identifiers={o['id'] for o in registry['operators']}
 assert identifiers==set(PARAMS)==set(Step.model_json_schema()['properties']['operation']['enum'])
 assert set(RULES['scientific_ids'])==templates.SPECIAL
 for ident,spec in RULES['elementary'].items():assert spec['products']==next(o['products'] for o in registry['operators'] if o['id']==ident)
