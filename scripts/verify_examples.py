"""Run every protected real-data recipe and retain numerical/UI-export checks.
Requires complete protected inputs and an idle running app; does not download data.
"""
import json,time,sys
from datetime import date
from pathlib import Path
import requests,numpy as np,rasterio
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.examples import CASES,inspect
from backend.app import RunQuery
API='http://127.0.0.1:8765'
def call(path,body=None):
 r=requests.get(API+path,timeout=180) if body is None else requests.post(API+path,json=body,timeout=180)
 r.raise_for_status();return r.json()
def wait(job):
 while job['status'] in ['queued','running']:
  time.sleep(1);job=call('/api/jobs/'+job['id'])
 assert job['status']=='completed',job
 return job
arguments=sys.argv[1:];browser_job=None
if '--job' in arguments:
 index=arguments.index('--job');browser_job=arguments[index+1];del arguments[index:index+2]
 if len(arguments)!=1:raise ValueError('--job requires exactly one named example.')
for ident in arguments or CASES:
 m=inspect(ident);assert m['ready'],(ident,m['issues'])
 setup=call('/api/examples/'+ident+'/setup');req=RunQuery.model_validate(setup['request']).model_dump(mode='json');job=wait(call('/api/jobs/'+browser_job) if browser_job else call('/api/run',req));pid=m['tool']
 if browser_job:assert job['request']==req,'Browser run did not use the exact example recipe.'
 assert all(i.get('protected_example') for i in setup['items'])
 assert not job.get('source_errors'),job.get('source_errors')
 result=call(job['results'][pid]['url']);assert result['status']=='exploratory',result
 assert len(result['sources'])==m['required_count']
 assert all(s['bytes_transferred']==0 for s in result['sources'])
 assert result['processing_options']['resolution']==req['options']['resolution']
 for k,v in req['options'].items():
  if k not in ['spatial_context']:assert result['processing_options'][k]==v,(pid,k,result['processing_options'].get(k),v)
 metrics=result['metrics']
 if pid=='P01':assert abs(metrics['new_water_candidate_km2']-90.47)<.011
 if pid=='P02':
  expected=[.2548,.5064,.6784,.3044,.1228,.2460]
  assert np.allclose([r['water_candidate_km2'] for r in result['series']],expected,atol=1e-6)
 if pid=='P03':
  assert result['extra']['fire_method']['id']=='combined' and metrics['viewing_groups']==2
  assert abs(metrics['candidate_area_ha']-7453)<.1
 if pid=='P06':
  assert result['extra']['surface_method']['id']=='evolving'
  assert np.isclose(metrics['latest_change_area_km2'],145.6028) and np.isclose(metrics['repeated_latest_change_area_km2'],128.292)
 if pid=='P07':
  assert result['extra']['horizontal_velocity'] and metrics['valid_pixels']==6703
  assert np.isclose(metrics['median'],21.787776947021484)
 if pid=='P04':assert result['extra']['los_model']['epoch_count']==7
 if pid=='P05':assert metrics['event_groups']==3 and metrics['reference_pixels']>=25
 if pid in ['P04','P05']:
  archive=ROOT/('docs/validation/browser-workflow/mexico-restored-run.json' if pid=='P04' else 'docs/validation/p06-overlap/verification.json')
  expected_metrics=json.loads(archive.read_text())['metrics']
  for key,value in expected_metrics.items():assert np.isclose(metrics[key],value,rtol=1e-6,atol=1e-6),(pid,key,metrics[key],value)
 layer=req.get('display',{}).get('layer') if req.get('display') else {'P01':'event'}.get(pid)
 if layer not in {l['id'] for l in result['layers']}:layer='backscatter'
 folder=ROOT/'data/jobs'/job['id']/pid
 with rasterio.open(folder/(layer+'.tif')) as ds:assert np.isfinite(ds.read(1)).any()
 d=req.get('display') or {}
 for key,value in d.items():assert result['display_preferences'][key]==value,(pid,key)
 params={k:d[k] for k in ['palette','mode','low','high'] if d.get(k) is not None};r=requests.get(API+f"/api/map-image/{job['id']}/{pid}/{layer}",params=params,timeout=180);r.raise_for_status();assert r.content.startswith(b'\x89PNG')
 if d.get('mode')=='custom':
  display=requests.get(API+f"/api/visualization/{job['id']}/{pid}/{layer}",params=params,timeout=180);display.raise_for_status();view=display.json();assert view['min']==d['low'] and view['max']==d['high']
 out=ROOT/'Examples'/ident
 (out/'references/review-opening-map.png').write_bytes(r.content)
 record={'job_id':job['id'],'tool':pid,'input_count':m['input_count'],'input_bytes':m['input_bytes'],'checksums_verified':True,'browser_start_verified':bool(browser_job),'request':req,'metrics':metrics,'grid':result['grid'],'display':result.get('display_preferences'),'source_errors':job.get('source_errors',[]),'processing_remote_bytes':sum(s['bytes_transferred'] for s in result['sources']),'numeric_raster_checked':layer,'map_image_with_legend_checked':True,'opening_map_export':'references/review-opening-map.png','review_date':date.today().isoformat(),'scientific_accuracy':'Not established by engineering checks; read tutorial comparison and limitations.'}
 (out/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({'example':ident,'run':job['id'],'metrics':metrics,'protected_MiB':round(m['input_bytes']/1024**2,2),'remote_science_bytes':record['processing_remote_bytes']}),flush=True)
