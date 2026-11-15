"""Reproducible offline geometry sensitivity; reads saved native NASA subsets only."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from backend.science import load_observation,target_grid,source_file
from backend.processors import process
from backend.exports import export_result
HERE=Path(__file__).parent;BBOX=[77.36,32.39,77.57,32.56]
context=json.loads((HERE.parent/'sources/study-domain.geojson').read_text())
grid=target_grid(BBOX,80)
items=[json.loads(p.read_text()) for p in (ROOT/'data/subsets').glob('GOFF_*/*.json') if p.name.startswith('subset-')]
items=[i for i in items if i.get('viewing_geometry',{}).get('available') and i['subset_bbox']==BBOX]
items=sorted({i['source_id']:i for i in items}.values(),key=lambda i:i['start'])
if not items:raise SystemExit('Prepare the native GOFF geometry through the app first.')
def stats(a):
 a=a[np.isfinite(a)]
 return {'cells':int(a.size),**{k:float(np.percentile(a,p)) if a.size else None for k,p in [('min',0),('p02',2),('median',50),('p90',90),('p98',98),('max',100)]}}
rows=[];arrays={};baseopt={'resolution':80,'snr':5,'min_valid_fraction':.5,'offset_solution':'horizontal','offset_rate_unit':'m/year','offset_geometry_height_m':5000,'offset_condition_limit':10,'offset_vertical_scenario_m_year':20,'offset_layer':'layer3','offset_filter':False,'offset_local_filter':False,'offset_stable_bias':False,'spatial_context':context}
for item in items:
 label=('january' if item['start'][:10]=='2026-01-01' else 'adjacent' if '_A_' in item['group'] else 'descending')
 for layer,height,filtering in [('layer3',5000,False),('layer3',4500,False),('layer3',6000,False),('layer1',5000,False),('layer2',5000,False),('layer3',5000,True)]:
  opt={**baseopt,'offset_layer':layer,'offset_geometry_height_m':height,'offset_filter':filtering}
  obs=load_observation(item,BBOX,grid,opt,lambda:False);result=process('P07',[obs],grid,opt)
  experiment=f'{label}-{layer}-{height}'+('-filtered' if filtering else '')
  speed=result['layers']['horizontal_speed']['data'];arrays[experiment]=speed
  row={'experiment':experiment,'source':item['source_id'],'start':item['start'],'end':item['end'],'layer':layer,'height_m':height,'spatial_filter':filtering,'horizontal_m_year':stats(speed),'radar_norm_m_year':stats(result['layers']['radar_magnitude']['data']),'vertical_20m_year_sensitivity':stats(result['layers']['horizontal_vertical_sensitivity_0']['data']),'condition':stats(result['layers']['horizontal_condition_0']['data']),'east_m_year':stats(result['layers']['horizontal_east_0']['data']),'north_m_year':stats(result['layers']['horizontal_north_0']['data']),'bearing':stats(result['layers']['horizontal_bearing_0']['data']),'glacier_valid_fraction':int(np.isfinite(speed).sum())/12502,'diagnostics':result['extra']['horizontal_velocity']['pairs']}
  if height!=5000:
   difference=speed-arrays[f'{label}-layer3-5000'];row['height_change_m_year']=stats(difference)
  rows.append(row)
  if layer=='layer3' and height==5000 and not filtering:
   out=HERE/'results'/label;out.mkdir(parents=True,exist_ok=True);export_result(result,grid,out)
   (HERE/(label+'-request.json')).write_text(json.dumps({'bbox':BBOX,'granules':[item['id']],'projects':['P07'],'options':opt},indent=2))
  print(experiment,row['horizontal_m_year'],flush=True)
(HERE/'results').mkdir(exist_ok=True)
(HERE/'results/sensitivity.json').write_text(json.dumps({'bbox':BBOX,'options':baseopt,'sources':[{k:i.get(k) for k in ['id','source_id','start','end','content_sha256','subset_path','viewing_geometry']} for i in items],'experiments':rows},indent=2))
