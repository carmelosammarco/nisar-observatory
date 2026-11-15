"""Replay local GOFF layer/filter sensitivity; no remote science requests."""
from pathlib import Path
import json,sys
import numpy as np
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from backend.science import load_observation,target_grid
from backend.processors import process
from backend.exports import export_result
HERE=Path(__file__).parent
BBOX=[77.36,32.39,77.57,32.56]
features=json.loads((HERE/'sources/rgi-bbox.geojson').read_text())['features']
f=next(f for f in features if f['properties']['RGIID']=='RGI60-14.15613')
f['properties'].update(name='Samudra Tapu · historical RGI6 outline',role='zone',source='GLIMS WFS RGI_SouthAsiaWest; RGI60-14.15613; outline BGNDATE 20020802, not a 2026 ice boundary')
context={'type':'FeatureCollection','features':[f]}
(HERE/'sources/samudra-tapu-rgi6.geojson').write_text(json.dumps(context,indent=2))
all_items=[json.loads(p.read_text()) for folder in ['GOFF_2026-10-21_14-50-54_UTC','GOFF_2026-10-21_14-59-01_UTC'] for p in (ROOT/'data/subsets'/folder).glob('subset-*.json')]
all_items.sort(key=lambda i:i['start'])
grid=target_grid(BBOX,80)
mask=geometry_mask([transform_geom('EPSG:4326',grid['crs'],f['geometry'])],out_shape=grid['shape'],transform=grid['transform'],invert=True)
def stats(a):
 a=a[np.isfinite(a)]
 return {'cells':int(a.size),**{k:float(np.percentile(a,p)) if a.size else None for k,p in [('min',0),('p02',2),('median',50),('p90',90),('p98',98),('max',100)]}}
rows=[]
for group in sorted({i['group'] for i in all_items}):
 items=[i for i in all_items if i['group']==group]
 prefix='descending-' if '_D_' in group else ''
 for layer in ['layer1','layer2','layer3']:
  for filtering in [False,True]:
   opt={'resolution':80,'snr':5,'min_valid_fraction':.5,'offset_layer':layer,'offset_rate_unit':'m/year','offset_filter':filtering,'offset_local_filter':False,'offset_stable_bias':False,'spatial_context':context}
   obs=[load_observation(i,BBOX,grid,opt,lambda:False) for i in items]
   result=process('P07',obs,grid,opt)
   label=prefix+layer+('-filtered' if filtering else '-snr-only')
   path=HERE/'results'/label;path.mkdir(exist_ok=True)
   for index,item in enumerate(items):
    a=result['layers'][f'observation_{index}']['data'];m=result['layers'][f'radar_filtered_{index}']['data']
    rows.append({'experiment':label,'group':group,'start':item['start'],'end':item['end'],'interval_days':result['extra']['offset_filter_diagnostics'][index]['interval_days'],'glacier_grid_cells':int(mask.sum()),'range_rate_m_year':stats(a[mask]),'radar_plane_magnitude_m_year':stats(m[mask]),'valid_glacier_fraction':float(np.isfinite(m[mask]).mean()),'fraction_magnitude_over_published_max':float(np.mean(m[mask&np.isfinite(m)]>139.19))})
   export_result(result,grid,path)
   print(label,rows[-1],flush=True)
(HERE/'results/sensitivity.json').write_text(json.dumps({'bbox':BBOX,'grid_m':grid['resolution'],'glacier':'RGI60-14.15613','outline_date':'2002-08-02','published_nisar_m_year':[5.7,139.19],'published_itslive_m_year':[.7,132.53],'quantities_comparable':False,'reason':'Our maps are radar-component rates and radar-plane norms, not geographic horizontal speeds; article omits exact pair IDs and conversion details.','sources':[{k:i.get(k) for k in ['id','source_id','name','start','end','download_folder','content_sha256','size_mb']} for i in all_items],'experiments':rows},indent=2))
