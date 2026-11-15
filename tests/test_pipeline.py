"""Exercise import → HDF5 adapters → all seven processors → export via the real API.
All inputs are explicitly synthetic. This is engineering validation only.
"""
import io,time,json
import h5py,numpy as np
from datetime import datetime,timedelta
from fastapi.testclient import TestClient
from pyproj import Transformer
from backend import app as module,science,access

def fixture_bytes(product,date):
 memory=io.BytesIO();x,y=Transformer.from_crs(4326,32611,always_xy=True).transform(-114.73,36.15)
 with h5py.File(memory,'w') as f:
  parent=f'/science/LSAR/{product}/grids/frequencyA'
  if product=='GUNW':parent+='/unwrappedInterferogram/HH'
  if product=='GOFF':parent+='/pixelOffsets/HH/layer1'
  g=f.create_group(parent);g['xCoordinates']=x+np.arange(-50,50)*100;g['yCoordinates']=y-np.arange(-50,50)*100;g['projection']=32611
  a=np.full((100,100),.1,'float32');a[:,45:55]=.001
  if date>0:a[60:70,60:70]=.3
  if product=='GCOV':g['HHHH']=a;g['mask']=np.ones(a.shape,'uint8')
  elif product=='GUNW':
   g['unwrappedPhase']=np.tile(np.linspace(0,1,100),(100,1));g['coherenceMagnitude']=np.full(a.shape,.9,'float32');g['connectedComponents']=np.ones(a.shape,'uint8')
   f[f'/science/LSAR/{product}/metadata/processingInformation/parameters/frequencyA/centerFrequency']=1.25e9
  elif product=='GOFF':g['slantRangeOffset']=np.full(a.shape,2.4,'float32');g['slantRangeOffset'].attrs['units']='meters';g['snr']=np.full(a.shape,10,'float32')
  else:
   g['volumetricSoilMoisture']=np.full(a.shape,.2+date*.01,'float32');g['qualityFlag']=np.zeros(a.shape,'uint8');g['qualityFlag'].attrs['flag_values']=np.array([0,1]);g['qualityFlag'].attrs['flag_meanings']='good bad'
 return memory.getvalue()

def test_end_to_end_all_seven(monkeypatch,tmp_path):
 for m in [module,science,access]:monkeypatch.setattr(m,'DATA',tmp_path)
 jobs=tmp_path/'jobs';jobs.mkdir();monkeypatch.setattr(module,'JOBS_DIR',jobs);monkeypatch.setattr(module,'JOBS',{});monkeypatch.setattr(module,'CATALOG',{})
 client=TestClient(module.app);ids=[]
 for product in ['GCOV','GUNW','GOFF','SME2']:
  for i in range(4):
   d=datetime(2026,8,1)+timedelta(days=i*12);end=d+timedelta(days=12) if product in ['GUNW','GOFF'] else d+timedelta(seconds=30)
   name=f'NISAR_L2_PR_{product}_001_001_A_001_4005_DHDH_A_{d:%Y%m%dT%H%M%S}_{end:%Y%m%dT%H%M%S}_M00100_P_F_J_001.h5'
   if product in ['GUNW','GOFF']:name=f'NISAR_L2_PR_{product}_001_001_A_001_002_4005_DH_{d:%Y%m%dT%H%M%S}_{d+timedelta(seconds=30):%Y%m%dT%H%M%S}_{end:%Y%m%dT%H%M%S}_{end+timedelta(seconds=30):%Y%m%dT%H%M%S}_M00100_P_F_J_001.h5'
   response=client.post('/api/import',headers={'X-Filename':name,'Content-Type':'application/octet-stream'},content=fixture_bytes(product,i))
   assert response.status_code==200,response.text
   item=response.json();item['group']='synthetic-one';module.CATALOG[item['id']]['group']='synthetic-one';ids.append(item['id'])
 request={'bbox':[-114.76,36.12,-114.70,36.18],'granules':ids,'projects':[f'P{i:02}' for i in range(1,8)],'options':{'reference_bbox':[-114.76,36.12,-114.75,36.18],'event_date':'2026-08-05'}}
 r=client.post('/api/run',json=request);assert r.status_code==200,r.text
 ident=r.json()['id']
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  j=client.get('/api/jobs/'+ident).json()
  if j['status'] not in ['queued','running']:break
  time.sleep(.03)
 assert j['status']=='completed',j
 assert len(j['results'])==7,j
 assert not j.get('source_errors'),j
 assert all(v['status']=='exploratory' for v in j['results'].values()),j
 result=client.get(j['results']['P01']['url']);assert result.status_code==200
 assert len(result.json()['sources'])==4
 frames=[l for l in result.json()['layers'] if l['id'].startswith('observation_')]
 assert len(frames)==4 and all(l['kind']=='binary' and l['start'] for l in frames)
 for pid in ['P04','P07']:
  r=client.get(j['results'][pid]['url']).json();assert len([l for l in r['layers'] if l['id'].startswith('observation_')])==(5 if pid=='P04' else 4)
 raster=client.get(f'/api/artifacts/{ident}/P01/water.tif');assert raster.status_code==200
 pixel=client.get(f'/api/pixel/{ident}/P01/water?lat=36.15&lon=-114.73');assert pixel.status_code==200
 assert pixel.json()['value'] in [0,1]

 # Verify each tool's real exported observation supports preview, inspection and download.
 for pid,entry in j['results'].items():
  result=client.get(entry['url']).json()
  candidates=[l for l in result['layers'] if l['id']=='observation_0' or l['id']=='variability']
  presentation=client.get(f"/api/map-image/{ident}/{pid}/{candidates[0]['id']}")
  assert presentation.status_code==200,(pid,presentation.text[:200] if presentation.status_code!=200 else '')
  assert presentation.headers['content-type']=='image/png'
  from PIL import Image
  printed=json.loads(Image.open(io.BytesIO(presentation.content)).info['NISAR_Observatory'])
  assert printed['layer']['unit']==candidates[0]['unit'] and len(printed['sources'])==4
  for layer in candidates:
   view=client.get(f"/api/visualization/{ident}/{pid}/{layer['id']}")
   assert view.status_code==200,(pid,layer['id'],view.text)
   assert view.json()['image'].startswith('data:image/png;base64,')
   assert client.get(f"/api/pixel/{ident}/{pid}/{layer['id']}?lat=36.15&lon=-114.73").status_code==200
   assert client.get(f"/api/artifacts/{ident}/{pid}/{layer['raster']}").status_code==200
 margin=client.get(f'/api/visualization/{ident}/P06/change_direction?mode=custom&low=-100&high=100').json()
 assert margin['min']==-1 and margin['max']==1
