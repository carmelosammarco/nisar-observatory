"""Verify protected HDF5 provenance and compute one/all ready example recipes locally."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np,h5py
from backend.examples import CASES,inspect
from backend.science import load_observation,target_grid
from backend.subset_import import metadata
from backend.subset_storage import subset_file
from backend.processors import process
from backend.app import RunQuery,processing_grid
for ident in sys.argv[1:] or CASES:
 m=inspect(ident)
 if not m['ready']:print(ident+': awaiting required subsets',flush=True);continue
 req=m['request'];opt=req['options'];pid=m['tool'];grid=processing_grid(RunQuery.model_validate({**req,'granules':[i['id'] for i in m['inputs']]}),m['product'])
 for item in m['inputs']:
  with h5py.File(subset_file(ROOT/'data',item),'r') as h:native=metadata(h)
  assert native['name']==item['name'] and native['subset_bbox']==req['bbox'] and native['group']==item['group']
 observations=[load_observation(i,req['bbox'],grid,opt,lambda:False) for i in m['inputs']]
 assert all(o['bytes_transferred']==0 for o in observations)
 result=process(pid,observations,grid,opt);metrics=result['metrics']
 if pid=='P01':assert abs(metrics['new_water_candidate_km2']-90.47)<.011
 if pid=='P02':assert np.allclose([r['water_candidate_km2'] for r in result['series']],[.2548,.5064,.6784,.3044,.1228,.2460],atol=1e-6)
 if pid=='P07':
  assert result['extra']['horizontal_velocity'] and metrics['valid_pixels']==6703
  assert np.isclose(metrics['median'],21.787776947021484)
  assert np.isclose(np.nanmax(result['layers']['horizontal_speed']['data']),144.93783569335938)
 if pid=='P04':assert result['extra']['los_model']['epoch_count']==7
 if pid=='P05':assert metrics['event_groups']==3 and metrics['reference_pixels']>=25
 if pid in ['P04','P05']:
  archive=ROOT/('docs/validation/browser-workflow/mexico-restored-run.json' if pid=='P04' else 'docs/validation/p06-overlap/verification.json')
  expected_metrics=json.loads(archive.read_text())['metrics']
  for key,value in expected_metrics.items():assert np.isclose(metrics[key],value,rtol=1e-6,atol=1e-6),(pid,key,metrics[key],value)
 receipt={'tool':pid,'provenance_verified':True,'protected_input_count':len(observations),'reader_versions':sorted({o['reader_version'] for o in observations}),'processing_remote_bytes':0,'metrics':metrics,'series':result['series'],'scientific_accuracy':'Not established; numerical replay check only.'}
 (ROOT/'Examples'/ident/'verification-direct.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'example':ident,'metrics':metrics,'protected_input_count':len(observations),'processing_remote_bytes':0}),flush=True)
