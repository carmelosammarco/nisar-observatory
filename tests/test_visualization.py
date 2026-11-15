"""Display-only range and playback data checks, using synthetic rasters."""
import json,hashlib
import numpy as np
import rasterio
from rasterio.transform import from_origin
from fastapi.testclient import TestClient
from backend import app as module


def test_display_ranges_preserve_numeric_rasters(monkeypatch,tmp_path):
 monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
 ident='a'*32;directory=tmp_path/ident/'P07';directory.mkdir(parents=True)
 arrays=[np.arange(100,dtype='float32').reshape(10,10),np.arange(100,dtype='float32').reshape(10,10)+100]
 layers=[]
 for i,a in enumerate(arrays):
  name=f'observation_{i}'
  with rasterio.open(directory/(name+'.tif'),'w',driver='GTiff',height=10,width=10,count=1,dtype='float32',crs='EPSG:6933',transform=from_origin(0,1000,100,100),nodata=np.nan) as ds:ds.write(a,1)
  layers.append({'id':name,'unit':'m³/m³','kind':'continuous'})
 (directory/'result.json').write_text(json.dumps({'layers':layers}))
 path=directory/'observation_0.tif';before=hashlib.sha256(path.read_bytes()).hexdigest();client=TestClient(module.app)
 def get(name,query=''):return client.get(f'/api/visualization/{ident}/P07/{name}'+query)
 shared=[get(f'observation_{i}').json() for i in range(2)]
 assert shared[0]['min']==shared[1]['min'] and shared[0]['max']==shared[1]['max']
 assert shared[0]['shared_frames']==2
 assert shared[0]['image'].startswith('data:image/png;base64,')
 full=get('observation_0','?mode=full').json();assert full['min']==0 and full['max']==99
 robust=get('observation_0','?mode=robust').json();assert robust['min']>0 and robust['max']<99
 custom=get('observation_0','?mode=custom&low=10&high=20').json();assert custom['min']==10 and custom['max']==20
 assert get('observation_0','?mode=custom&low=20&high=10').status_code==422
 assert get('missing').status_code==404
 assert client.get('/api/visualization/invalid/P07/observation_0').status_code==404
 assert before==hashlib.sha256(path.read_bytes()).hexdigest()


def test_download_batch_model_accepts_more_than_eight():
 assert len(module.DownloadQuery(granules=[f'id{i}' for i in range(100)]).granules)==100


def test_class_and_patch_colors_do_not_depend_on_contrast():
 from backend.exports import colorize
 a=np.array([[0,1,2,np.nan]],dtype='float32')
 first,_,_=colorize(a,'categorical',(-100,100))
 second,_,_=colorize(a,'categorical',(0,1))
 assert np.array_equal(first,second)
 assert first[0,3,3]==0
 binary=np.array([[0,1]],dtype='float32')
 first,lo,hi=colorize(binary,'binary',(-100,100))
 second,_,_=colorize(binary,'binary',(0,1))
 assert np.array_equal(first,second) and (lo,hi)==(0,1)


def test_mexico_palette_presets_and_custom_ranges_are_display_only(monkeypatch,tmp_path):
 monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
 ident='b'*32;directory=tmp_path/ident/'P04';directory.mkdir(parents=True)
 layers=[]
 for name,unit,kind in [('los_rate_year','cm/year','diverging'),('los_rate_month','cm/month','diverging'),('observation_0','cm','diverging'),('observation_1','cm','diverging'),('reference_support','class','binary'),('quality_coherence_0','score','continuous')]:
  a=np.linspace(-40,40,100,dtype='float32').reshape(10,10)
  if name=='observation_1':a=a*2
  if unit=='class':a=(a>0).astype('float32')
  if unit=='score':a=np.abs(a)/40
  a[0,0]=np.nan
  with rasterio.open(directory/(name+'.tif'),'w',driver='GTiff',height=10,width=10,count=1,dtype='float32',crs='EPSG:6933',transform=from_origin(0,1000,100,100),nodata=np.nan) as ds:ds.write(a,1)
  layers.append({'id':name,'unit':unit,'kind':kind})
 (directory/'result.json').write_text(json.dumps({'layers':layers}))
 before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')};client=TestClient(module.app)
 def get(name,query):
  r=client.get(f'/api/visualization/{ident}/P04/{name}?'+query);assert r.status_code==200,r.text;return r.json()
 annual=get('los_rate_year','mode=mexico&palette=mexico');monthly=get('los_rate_month','mode=mexico&palette=mexico')
 assert (annual['min'],annual['max'])==(-30,30)
 assert (monthly['min'],monthly['max'])==(-2.5,2.5)
 assert annual['palette_name']=='mexico' and len(annual['palette'])==256
 standard=get('los_rate_year','mode=mexico&palette=standard')
 assert standard['image']!=annual['image'] and (standard['min'],standard['max'])==(-30,30)
 custom=get('los_rate_year','mode=custom&low=-12&high=3&palette=mexico')
 assert (custom['min'],custom['max'])==(-12,3) and custom['clipped_percent']>0
 shared=[get(n,'palette=mexico') for n in ['observation_0','observation_1']]
 assert shared[0]['min']==shared[1]['min'] and shared[0]['max']==shared[1]['max']
 assert all(v['shared_frames']==2 for v in shared)
 fallback=get('observation_0','mode=mexico&palette=mexico')
 assert fallback['mode']=='shared' and 'rate maps' in fallback['range_note']
 quality=get('quality_coherence_0','palette=mexico')
 assert quality['palette_name']=='standard' and 'Quality' in quality['palette_note']
 binary=get('reference_support','mode=custom&low=-9&high=9&palette=mexico')
 assert (binary['min'],binary['max'])==(0,1) and binary['palette_name']=='standard'
 assert client.get(f'/api/visualization/{ident}/P04/los_rate_year?palette=unrecognized').status_code==422
 assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}


def test_colorize_interpolates_full_mexico_lookup_and_preserves_missing_alpha():
 from backend.exports import colorize
 from pathlib import Path
 palette=json.loads((Path(module.ROOT)/'backend/mexico_palette.json').read_text())
 a=np.array([[0,1,2,np.nan]],dtype='float32')
 rgba,lo,hi=colorize(a,'diverging',(0,2),palette)
 assert tuple(rgba[0,0,:3])==tuple(palette[0])
 assert tuple(rgba[0,2,:3])==tuple(palette[-1])
 assert rgba[0,3,3]==0 and rgba[0,1,3]>0


def test_save_opening_view_is_validated_and_changes_only_display_metadata(monkeypatch,tmp_path):
 monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
 ident='b'*32;directory=tmp_path/ident/'P04';directory.mkdir(parents=True)
 result={'layers':[{'id':'los_rate_year','unit':'cm/year'},{'id':'los_rate_month','unit':'cm/month'}],'metrics':{'reference_pixels':2698},'processing_options':{'coherence':.3},'display_preferences':None}
 path=directory/'result.json';path.write_text(json.dumps(result))
 raster=directory/'los_rate_year.tif';raster.write_bytes(b'unchanged numeric raster')
 monkeypatch.setattr(module,'JOBS',{ident:{'status':'completed','results':{'P04':{'status':'exploratory'}}}})
 client=TestClient(module.app);url=f'/api/jobs/{ident}/display/P04'
 recipe={'palette':'rainbow','mode':'custom','layer':'los_rate_year','unit':'cm/year','low':-30,'high':30}
 assert client.put(url,json={**recipe,'unit':'cm/month'}).status_code==422
 assert client.put(url,json={**recipe,'layer':'missing'}).status_code==422
 assert client.put(url,json={**recipe,'high':-40}).status_code==422
 assert json.loads(path.read_text())==result
 response=client.put(url,json=recipe);assert response.status_code==200
 saved=json.loads(path.read_text());assert saved.pop('display_preferences')==recipe
 original=dict(result);original.pop('display_preferences');assert saved==original
 assert raster.read_bytes()==b'unchanged numeric raster'
 assert client.get(f'/api/artifacts/{ident}/P04/result.json').json()['display_preferences']==recipe
 module.JOBS[ident]['status']='running';assert client.put(url,json=recipe).status_code==409
 assert client.put(f'/api/jobs/{"c"*32}/display/P04',json=recipe).status_code==404


def test_unobserved_recovery_is_explained_without_fabricating_pixels(monkeypatch,tmp_path):
 monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
 ident='e'*32;directory=tmp_path/ident/'P01';directory.mkdir(parents=True)
 with rasterio.open(directory/'recovery.tif','w',driver='GTiff',height=2,width=2,count=1,dtype='float32',crs='EPSG:6933',transform=from_origin(0,200,100,100),nodata=np.nan) as ds:ds.write(np.full((2,2),np.nan,'float32'),1)
 result={'layers':[{'id':'recovery','unit':'observation index','kind':'continuous'}],'extra':{'recovery_calendar':[]}}
 (directory/'result.json').write_text(json.dumps(result));client=TestClient(module.app)
 response=client.get(f'/api/visualization/{ident}/P01/recovery');assert response.status_code==200
 assert response.json()['available'] is False and response.json()['valid_pixels']==0
 assert 'no acquisition after' in response.json()['reason'] and 'image' not in response.json()
 png=client.get(f'/api/map-image/{ident}/P01/recovery');assert png.status_code==422 and 'Recovery cannot be assessed' in png.json()['detail']
 result['extra']['recovery_calendar']=[{'index':2,'date':'2026-01-29'}];(directory/'result.json').write_text(json.dumps(result))
 assert 'does not prove continuous flooding' in client.get(f'/api/visualization/{ident}/P01/recovery').json()['reason']
