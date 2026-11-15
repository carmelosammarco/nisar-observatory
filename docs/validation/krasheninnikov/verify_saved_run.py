"""Verify the real browser-created run, display persistence and every registered map."""
from pathlib import Path
import json,io,hashlib
import requests,numpy as np,rasterio
from PIL import Image
R=Path(__file__).resolve().parent;ROOT=R.parents[2];API='http://127.0.0.1:8765'
def get(path):
 r=requests.get(API+path,timeout=120);r.raise_for_status();return r
jobs=get('/api/jobs').json();job=next(j for j in jobs if j.get('kind')=='analysis' and j.get('request',{}).get('projects')==['P06'] and j['request']['options'].get('surface_method')=='evolving')
assert job['status']=='completed',job['status'];result=get(job['results']['P06']['url']).json();expected=json.loads((R/'results/evolving/result.json').read_text());assert result['metrics']==expected['metrics'];assert len(result['sources'])==5 and sum(s['bytes_transferred'] for s in result['sources'])==0
settings={'layer':'latest_departure','unit':'dB','palette':'diverging','mode':'custom','low':-8,'high':8}
r=requests.put(API+f"/api/jobs/{job['id']}/display/P06",json=settings,timeout=120);r.raise_for_status();assert get(job['results']['P06']['url']).json()['display_preferences']==settings
checks=[]
for layer in result['layers']:
 ident=layer['id'];view=get(f"/api/visualization/{job['id']}/P06/{ident}").json();assert view.get('available') is not False,ident
 with rasterio.open(ROOT/f"data/jobs/{job['id']}/P06/{ident}.tif") as ds:assert ds.crs.to_epsg()==32657 and ds.shape==(1080,1151) and ds.dtypes==('float32',)
 checks.append({'layer':ident,'valid_pixels':view['valid_pixels'],'range':[view['min'],view['max']]})
for ident,query in [('latest_departure','?mode=custom&low=-8&high=8&palette=diverging'),('first_change','')]:
 data=get(f"/api/map-image/{job['id']}/P06/{ident}"+query).content;img=Image.open(io.BytesIO(data));meta=json.loads(img.info['NISAR_Observatory']);assert img.size==(1800,1570)
 if ident=='latest_departure':assert meta['scale']['min']==-8 and meta['scale']['max']==8
 else:assert all(row[1].startswith('2026-') for row in meta['legend_classes'])
 (R/'figures'/f'app-{ident}-with-legend.png').write_bytes(data)
# Verify a downloaded numeric file is byte-for-byte the saved scientific raster.
local=ROOT/f"data/jobs/{job['id']}/P06/latest_departure.tif";data=get(f"/api/artifacts/{job['id']}/P06/latest_departure.tif").content;assert hashlib.sha256(data).digest()==hashlib.sha256(local.read_bytes()).digest()
receipt={'job_id':job['id'],'status':job['status'],'application_version':result['application_version'],'algorithm_version':result['algorithm_version'],'local_science_bytes_transferred':0,'sources':len(result['sources']),'layers_verified':len(checks),'checks':checks,'saved_display':settings,'metrics_match_local_study':True,'existing_examples':len(get('/api/examples').json())}
(R/'results/app-verification.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='checks'},indent=2))
