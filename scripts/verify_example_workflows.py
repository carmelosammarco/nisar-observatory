"""Replay protected native subsets, compare editable plans with established processors.

Run one case per process to release large native arrays between studies. The
replay owns NISAR_DATA_DIR and writes its array cache. Use a separate temporary
NISAR_DATA_DIR when the app is running; otherwise stop the app first. Protected
inputs are read from Examples. No remote files or login are needed. Writes
bounded verification receipts under docs/validation.
"""
import argparse,hashlib,json,sys,subprocess,gc
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.examples import CASES,setup
from backend.workflows import checked_recipe,process,templates
from backend.processors import process as established
from backend.app import RunQuery,processing_grid,APP_VERSION
from backend.science import load_observation
OUT=ROOT/'docs/validation/workflows/seven-examples'

def digest(a):
 a=np.asarray(a,dtype='float32');return hashlib.sha256(np.where(np.isnan(a),0,a).tobytes()+np.isnan(a).tobytes()).hexdigest()
def compare_saved_browser(root,browser,mapping,hashes):
 """Saved UI runs are optional evidence; clearing Runs must not prevent replay."""
 import re,rasterio
 match=re.fullmatch(r'/api/artifacts/([a-f0-9]{32})/LAB/[^/]+\.tif',browser['raster'])
 if not match:raise ValueError('Unexpected browser artifact path')
 folder=root/'data/jobs'/match[1]/'LAB'
 files=[folder/(new+'.tif') for new in mapping.values()]
 if not any(p.is_file() for p in files):
  return {'browser_export_check':'not available: historical saved run was cleared; direct protected-input comparison still completed'}
 if not all(p.is_file() for p in files):raise ValueError('Historical browser run is incomplete. Restore or delete the partial run before comparing exports.')
 for old,new in mapping.items():
  with rasterio.open(folder/(new+'.tif')) as src:a=src.read(1,masked=True).filled(np.nan)
  if digest(a)!=hashes[old]:raise ValueError('Browser raster differs: '+new)
 return {'browser_run':match[1],'browser_numeric_maps_identical':len(mapping)}

def verify(ident):
 payload=setup(ident);m=payload['example'];r=checked_recipe(templates.example_recipe(ident));plan=templates.compile_plan(r.product,r.steps,r.options) if templates.is_scientific(r.steps) else None
 query=RunQuery(**payload['request']);grid=processing_grid(query,r.product)
 original_options=payload['request']['options'];new_options=plan.options if plan else r.options
 old_obs=[load_observation(item,r.context.bbox,grid,original_options,lambda:False) for item in payload['items']]
 expected=established(m['tool'],old_obs,grid,original_options)
 hashes={key:digest(v['data']) for key,v in expected['layers'].items()};metrics=expected['metrics'];series=expected['series'];old_paths=[o['path'] for o in old_obs]
 old_array_hashes=[digest(o['array']) for o in old_obs]
 del expected,old_obs;gc.collect()
 obs=[load_observation(item,r.context.bbox,grid,new_options,lambda:False) for item in payload['items']]
 assert [digest(o['array']) for o in obs]==old_array_hashes,'Reader measurements changed'
 assert [o['path'] for o in obs]==old_paths,'Reader path changed'
 actual=process(r,obs,grid);comparisons={}
 trace=actual['extra']['processing_trace'];assert trace['version']=='1.0.0'
 assert len(trace['stages'])==len(r.steps)
 for stage,step in zip(trace['stages'],r.steps):
  assert stage['operation']==step.operation and (stage['maps'] or stage['diagnostic_keys'] or stage['unavailable_reason'])
  for link in stage['maps']:
   assert link['id'] in actual['layers'] and link['unit']==actual['layers'][link['id']]['unit']
   assert actual['layers'][link['id']]['data'].shape==tuple(grid['shape'])
 trace_summary={'version':trace['version'],'stages':len(trace['stages']),'captured_maps':trace['snapshot_maps'],'stage_evidence':[{k:v for k,v in stage.items() if k in ['step','operation','maps','diagnostic_keys','unavailable_reason']} for stage in trace['stages']]}
 mapping={key:key for key in hashes}
 if m['tool']=='P04':
  mapping={key:key for key in hashes if key.startswith('observation_')};mapping.update(los_rate_year='summary',los_change='change',los_fit_residual='trend_residual',los_pair_residual='network_residual')
 for old,new in mapping.items():
  assert new in actual['layers'],(ident,'missing layer',new)
  equal=hashes[old]==digest(actual['layers'][new]['data']);comparisons[old]={'editable_layer':new,'identical':equal,'sha256':hashes[old]};assert equal,(ident,old,new)
 if m['tool']!='P04':
  assert actual['metrics']==metrics,(ident,'metrics differ')
  assert actual['series']==series,(ident,'dated series differ')
 else:
  assert actual['extra']['los_series']==[{'date':x['date'],'median_cm':x['median']} for x in actual['series']]
 prior=json.loads((ROOT/'Examples'/ident/'verification.json').read_text()).get('metrics',{})
 historical={k:{'previous':v,'current':metrics.get(k),'unchanged':bool(k in metrics and np.isclose(metrics[k],v,rtol=1e-6,atol=1e-6))} for k,v in prior.items() if isinstance(v,(int,float))}
 receipt={'application_version':APP_VERSION,'processing_trace':trace_summary,'metrics':metrics,'historical_metric_comparison':historical,'case':ident,'method':m['tool'],'source_count':len(obs),'grid_shape':list(grid['shape']),'resolution':grid['resolution'],'steps':[s.model_dump() for s in r.steps],'reader_arrays_identical':True,'engine_version':'1.1.0','comparisons':comparisons,'metrics_identical':actual['metrics']==metrics,'series_identical':actual['series']==series,'verification_scope':'All existing numeric layers, metrics and dated series' if m['tool']!='P04' else 'Annualized rate, accumulated change, all reconstructed dates and fit/network residual maps; elementary result uses its own statistics schema','result':'PASS','remote_science_bytes':sum(o.get('bytes_transferred',0) for o in obs)}
 browser_file=OUT/'browser.json'
 if browser_file.is_file():
  browser=next((v for v in reversed(json.loads(browser_file.read_text())['checks']) if v['case']==ident),None)
  if browser:receipt.update(compare_saved_browser(ROOT,browser,mapping,hashes))
 OUT.mkdir(parents=True,exist_ok=True);(OUT/(ident+'.json')).write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(ident,'PASS',len(comparisons),'maps',flush=True)
 (ROOT/'Recipes').mkdir(exist_ok=True);(ROOT/'Recipes'/(ident+'.json')).write_text(json.dumps(r.model_dump(mode='json'),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--case',choices=CASES);args=parser.parse_args()
 if args.case:
  from backend.access import DATA
  from backend.runtime_storage import RuntimeLease
  with RuntimeLease(DATA):verify(args.case)
 else:
  for ident in CASES:subprocess.run([sys.executable,str(Path(__file__).resolve()),'--case',ident],cwd=ROOT,check=True)
