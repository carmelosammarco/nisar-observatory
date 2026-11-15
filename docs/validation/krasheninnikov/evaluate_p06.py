"""Reproducible local-only five-date evaluation; no automatic Example installation."""
from pathlib import Path
import sys,json,hashlib,copy,csv
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import numpy as np,h5py,rasterio
from backend.raster_methods import analysis_grid
from backend.science import load_observation
from backend.processors import process
from backend.exports import export_result
R=Path(__file__).resolve().parent;O=R/'results'
def main():
 receipt=json.loads((O/'download-receipt.json').read_text());assert receipt['status']=='completed' and len(receipt['saved_areas'])==5
 bbox=receipt['request']['bbox'];items=receipt['saved_areas'];records=[]
 for i in items:
  p=ROOT/'data/subsets'/i['subset_path'];sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==i['content_sha256']
  with h5py.File(p) as h:
   g=h['science/LSAR/GCOV/grids/frequencyA'];version=h['science/LSAR/identification/productVersion'][()].decode();mask=g['mask'][:]
   records.append({'date':i['start'],'name':i['name'],'file':str(p.relative_to(ROOT)),'sha256':sha,'bytes':p.stat().st_size,'product_version':version,'spacing_m':[float(g['xCoordinateSpacing'][()]),float(g['yCoordinateSpacing'][()])],'native_shape':list(mask.shape),'mask_rejected_fraction':float(((mask==0)|(mask==255)).mean()),'exception_pixels':int(np.count_nonzero(g['inputDataExceptionMask'][:])) if 'inputDataExceptionMask' in g else None})
 options={'surface_method':'evolving','channel':'HHHH','resolution':20,'baseline_count':1,'baseline_end':'2026-06-18','change_threshold':3,'smoothing_m':40,'patch_area_m2':30000,'min_valid_fraction':.5}
 grid=analysis_grid(bbox,20);obs=[load_observation(i,bbox,grid,options,lambda:False) for i in items]
 assert all(o['bytes_transferred']==0 for o in obs),'Evaluation must use the downloaded files'
 assert len({o['item']['group'] for o in obs})==1
 verification={'input_count':len(records),'bytes':sum(x['bytes'] for x in records),'records':records,'evaluation_network_bytes':sum(o['bytes_transferred'] for o in obs),'grid_shape':list(grid['shape']),'crs':grid['crs'],'cell_spacing_m':20}
 (O/'native-input-verification.json').write_text(json.dumps(verification,indent=2));(O/'tested-options.json').write_text(json.dumps(options,indent=2))
 results={}
 for name,opts in [('evolving',options),('previous',{**options,'surface_method':'legacy'})]:
  comparison_obs=obs
  if name=='previous':
   from backend.raster_methods import geographic_window_mask
   comparison_obs=copy.deepcopy(obs);inside=geographic_window_mask(grid)
   for o in comparison_obs:o['array'][~inside]=np.nan
  try:result=process('P06',comparison_obs,grid,opts)
  except ValueError as error:
   if name!='previous' or 'tracking exceeds 1000' not in str(error):raise
   # Preserve the legacy numerical classification without weakening the app's object cap.
   db=np.stack([10*np.log10(o['array']) for o in comparison_obs]);common=np.isfinite(db).all(axis=0);d=db[1:]-db[0];up=(d>=3).all(axis=0)&common;down=(d<=-3).all(axis=0)&common;area=grid['resolution']**2/1e6
   result={'project':'P06','title':'Previous all-later-dates classification · tracking exceeded limit','unit':'dB','status':'exploratory','algorithm_version':'0.4.0','layers':{'surface':{'data':np.where(common,up|down,np.nan),'label':'Previous all-later-dates change rule','unit':'class','kind':'binary'},'change_direction':{'data':np.where(common,up.astype(float)-down,np.nan),'label':'Previous same-sign direction','unit':'class','kind':'diverging'}},'series':[],'metrics':{'persistent_change_area_km2':float((up|down).sum()*area),'increasing_area_km2':float(up.sum()*area),'decreasing_area_km2':float(down.sum()*area)},'notes':[str(error),'Comparison raster reconstructed from the exact legacy formula; the full legacy processor did not finish object tracking.'],'extra':{'tracking_status':str(error)},'sources':json.loads((O/'evolving/result.json').read_text())['sources']}
   results['previous_full_processor_status']=str(error)
  result.update(processing_options=opts,application_version='0.7.1');arrays={k:v['data'] for k,v in result['layers'].items()};results[name]=copy.deepcopy(result['metrics'])
  if name=='evolving':
   with (O/'dated-candidates.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=['date','change_candidate_km2','brightening_candidate_km2','dimming_candidate_km2']);writer.writeheader();writer.writerows({k:row[k] for k in writer.fieldnames} for row in result['series'])
  export_result(result,grid,O/name);print(name,results[name],flush=True)
 sensitivity=[]
 for threshold in [2,3,4]:
  rr=process('P06',obs,grid,{**options,'change_threshold':threshold});sensitivity.append({'threshold_db':threshold,**rr['metrics']})
 (O/'method-comparison.json').write_text(json.dumps({'same_grid_comparison':results,'threshold_sensitivity':sensitivity,'interpretation':'Candidate area and method sensitivity, not accuracy against lava ground truth. NASA frames are oblique display imagery; no quantitative lava mask is available.'},indent=2))
 print('Local-only evaluation complete; no Example installed.',flush=True)
if __name__=='__main__':main()
