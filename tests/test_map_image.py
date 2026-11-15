"""Presentation images preserve display scales and scientific numeric files."""
import hashlib,io,json
import numpy as np,pytest,rasterio
from PIL import Image
from rasterio.transform import from_origin
from fastapi.testclient import TestClient
from backend import app as module


def fixture(monkeypatch,tmp_path,pid='P04',kind='diverging',unit='cm/year'):
 monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
 ident='c'*32;directory=tmp_path/ident/pid;directory.mkdir(parents=True)
 values=np.linspace(-40,20,600,dtype='float32').reshape(20,30)
 if kind in ['water_state','categorical','binary']:values=(np.arange(600).reshape(20,30)%(3 if kind=='water_state' else 12 if kind=='categorical' else 2)).astype('float32')
 values[0,:]=np.nan
 def write(name,array):
  with rasterio.open(directory/(name+'.tif'),'w',driver='GTiff',height=20,width=30,count=1,dtype='float32',crs='EPSG:6933',transform=from_origin(-10000000,2000000,100,100),nodata=np.nan) as ds:ds.write(array,1)
 write('main',values)
 layers=[{'id':'main','label':'Synthetic engineering validation — not observed Earth change','kind':kind,'unit':unit}]
 if pid=='P04':
  ref=np.zeros_like(values);ref[8:12,10:15]=1;write('reference_support',ref);layers.append({'id':'reference_support','kind':'binary','unit':'class','label':'Actual reference cells'})
 result={'project':pid,'layers':layers,'grid':{'crs':'EPSG:6933','resolution_m':100,'bbox':[-104,15,-103,16]},'algorithm_version':'synthetic-test','sources':[{'id':'synthetic-a','name':'SYNTHETIC_GUNW_A','start':'2026-01-01T00:00:00Z','end':'2026-01-13T00:00:00Z'}],'extra':{}}
 (directory/'result.json').write_text(json.dumps(result))
 return TestClient(module.app),ident,directory

@pytest.mark.parametrize('pid',[f'P{i:02}' for i in range(1,8)])
def test_every_tool_can_export_standalone_png_without_altering_geotiffs(monkeypatch,tmp_path,pid):
 client,ident,directory=fixture(monkeypatch,tmp_path,pid)
 before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}
 response=client.get(f'/api/map-image/{ident}/{pid}/main?mode=custom&low=-10&high=5&palette='+('mexico' if pid=='P04' else 'standard'))
 assert response.status_code==200,response.text
 assert response.headers['content-type']=='image/png'
 assert response.headers['content-disposition']==f'attachment; filename="{pid.lower()}_main_map.png"'
 image=Image.open(io.BytesIO(response.content));assert image.size==(1800,1570)
 meta=json.loads(image.info['NISAR_Observatory'])
 assert meta['tool']==pid and meta['scale']['min']==-10 and meta['scale']['max']==5
 assert meta['layer']['unit']=='cm/year' and meta['sources'][0]['name']=='SYNTHETIC_GUNW_A'
 assert meta['scale']['clipped_percent']>0
 assert meta['scale']['palette_name']==('mexico' if pid=='P04' else 'standard')
 assert meta['reference_outline'] is False
 if pid=='P04':assert 'not direct vertical' in meta['interpretation']
 assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}

@pytest.mark.parametrize('kind,expected',[('binary',2),('water_state',3),('categorical',12)])
def test_class_legend_uses_class_labels_instead_of_a_continuous_gradient(monkeypatch,tmp_path,kind,expected):
 client,ident,_=fixture(monkeypatch,tmp_path,'P01',kind,'class')
 response=client.get(f'/api/map-image/{ident}/P01/main');assert response.status_code==200,response.text
 meta=json.loads(Image.open(io.BytesIO(response.content)).info['NISAR_Observatory'])
 assert len(meta['legend_classes'])==expected
 if kind=='water_state':assert meta['legend_classes']==[[0,'Dry candidate'],[1,'Water candidate'],[2,'Ambiguous']]
 if kind=='categorical':assert meta['legend_classes'][-1]==[11.0,'Patch 11']


def test_export_obeys_the_same_validation_and_registered_layers_as_map_preview(monkeypatch,tmp_path):
 client,ident,_=fixture(monkeypatch,tmp_path)
 assert client.get(f'/api/map-image/{ident}/P04/main?mode=custom&low=9&high=2').status_code==422
 assert client.get(f'/api/map-image/{ident}/P04/missing').status_code==404
 assert client.get('/api/map-image/not-a-run/P04/main').status_code==404
 assert client.get(f'/api/map-image/{ident}/P04/main?palette=unknown').status_code==422


def test_observation_index_map_includes_date_key_instead_of_implying_days(monkeypatch,tmp_path):
 client,ident,directory=fixture(monkeypatch,tmp_path,'P01','binary','observation index')
 (directory/'main.tif').rename(directory/'recovery.tif')
 with rasterio.open(directory/'recovery.tif','r+') as ds:
  a=ds.read(1);a[np.isfinite(a)]+=2;ds.write(a,1)
 result=json.loads((directory/'result.json').read_text());result['layers'][0].update(id='recovery',kind='continuous')
 result['extra']['recovery_calendar']=[{'index':2,'date':'2026-01-25T00:00:00Z'},{'index':3,'date':'2026-02-06T00:00:00Z'}]
 (directory/'result.json').write_text(json.dumps(result))
 response=client.get(f'/api/map-image/{ident}/P01/recovery');assert response.status_code==200,response.text
 meta=json.loads(Image.open(io.BytesIO(response.content)).info['NISAR_Observatory'])
 assert meta['legend_classes']==[[2.0,'2026-01-25'],[3.0,'2026-02-06']]

def test_first_change_legend_maps_indices_to_acquisition_dates():
 from backend.map_image import legend_spec
 info={'id':'first_change','kind':'continuous','unit':'observation index'}
 legend=legend_spec(info,{'class_values':[1,4]},{'extra':{'first_change_calendar':[{'index':1,'date':'2026-06-30T00:00:00Z'},{'index':4,'date':'2026-08-17T00:00:00Z'}]}})
 assert legend==[(1,'2026-06-30'),(4,'2026-08-17')]

@pytest.mark.parametrize('pid',[f'P{i:02}' for i in range(1,8)])
@pytest.mark.parametrize('kind',['binary','water_state','categorical'])
def test_edited_categories_match_preview_export_and_preserve_science(monkeypatch,tmp_path,pid,kind):
 import base64
 client,ident,directory=fixture(monkeypatch,tmp_path,pid,kind,'class')
 before=hashlib.sha256((directory/'main.tif').read_bytes()).hexdigest()
 colors={'0':'#ff00aa','1':'#012345'}
 query={'category_colors':json.dumps(colors),'mode':'custom','low':-50,'high':50}
 response=client.get(f'/api/visualization/{ident}/{pid}/main',params=query)
 assert response.status_code==200,response.text
 display=response.json();assert display['appearance_type']=='categories'
 assert display['category_colors']==colors
 assert {c['value']:c['color'] for c in display['categories']}[1]=='#012345'
 image=np.array(Image.open(io.BytesIO(base64.b64decode(display['image'].split(',')[1]))))
 assert np.any(np.all(image[:,:,:3]==[1,35,69],axis=-1))
 assert np.any(image[:,:,3]==0)
 assert display['mode']=='shared'
 # One representative tool per kind verifies the complete print/export path too.
 if pid=='P01':
  exported=client.get(f'/api/map-image/{ident}/{pid}/main',params=query)
  assert exported.status_code==200,exported.text
  meta=json.loads(Image.open(io.BytesIO(exported.content)).info['NISAR_Observatory'])
  assert meta['category_colors']==colors and meta['categories']==display['categories']
  pixels=np.array(Image.open(io.BytesIO(exported.content)))
  assert np.any(np.all(pixels==[1,35,69],axis=-1))
 assert before==hashlib.sha256((directory/'main.tif').read_bytes()).hexdigest()


def test_category_validation_reset_and_saved_view(monkeypatch,tmp_path):
 client,ident,directory=fixture(monkeypatch,tmp_path,'P01','water_state','class')
 endpoint=f'/api/visualization/{ident}/P01/main'
 for value in ['[]','null','{"nan":"#123456"}','{"0":"red"}','{"0":"<script>"}',json.dumps({str(i):'#123456' for i in range(513)})]:
  assert client.get(endpoint,params={'category_colors':value}).status_code==422
 default=client.get(endpoint).json()
 customized=client.get(endpoint,params={'category_colors':'{"1":"#123456"}'}).json()
 assert customized['image']!=default['image']
 assert client.get(endpoint).json()['image']==default['image']
 monkeypatch.setattr(module,'JOBS',{ident:{'status':'completed','results':{'P01':{'status':'exploratory'}}}})
 recipe={'palette':'standard','mode':'shared','layer':'main','unit':'class','category_colors':{'main':{'1':'#123456'}}}
 url=f'/api/jobs/{ident}/display/P01'
 assert client.put(url,json=recipe).status_code==200
 assert json.loads((directory/'result.json').read_text())['display_preferences']['category_colors']==recipe['category_colors']
 assert client.put(url,json={**recipe,'category_colors':{'missing':{'0':'#123456'}}}).status_code==422
 assert client.put(url,json={**recipe,'category_colors':{'main':{'0':'bad'}}}).status_code==422


def test_category_overrides_do_not_apply_to_measurements(monkeypatch,tmp_path):
 client,ident,_=fixture(monkeypatch,tmp_path)
 url=f'/api/visualization/{ident}/P04/main'
 assert client.get(url,params={'category_colors':'{"0":"#123456"}'}).status_code==422
 for palette in ['standard','diverging','rainbow']:
  display=client.get(url,params={'palette':palette}).json()
  assert display['appearance_type']=='measurement' and display['categories']==[]

@pytest.mark.parametrize('layer,kind,unit,values,extra,label',[
 ('change_direction','diverging','class',[-1,0,1],{},'Dimmer'),
 ('recovery','continuous','observation index',[2,3,4],{'recovery_calendar':[{'index':2,'date':'2026-01-25'},{'index':3,'date':'2026-02-06'},{'index':4,'date':'2026-02-18'}]},'2026-01-25'),
])
def test_signed_classes_and_observed_dates_use_exact_labelled_colors(monkeypatch,tmp_path,layer,kind,unit,values,extra,label):
 import base64
 client,ident,directory=fixture(monkeypatch,tmp_path,'P06')
 array=np.tile(np.array(values,'float32'),(20,10));array[0,:]=np.nan
 with rasterio.open(directory/'main.tif','r+') as ds:ds.write(array,1)
 (directory/'main.tif').rename(directory/(layer+'.tif'))
 result=json.loads((directory/'result.json').read_text());result['layers'][0].update(id=layer,kind=kind,unit=unit);result['extra']=extra
 (directory/'result.json').write_text(json.dumps(result))
 display=client.get(f'/api/visualization/{ident}/P06/{layer}',params={'category_colors':json.dumps({str(values[0]):'#abcdef'})}).json()
 assert display['appearance_type']=='categories'
 assert display['categories'][0]=={'value':values[0],'label':label,'color':'#abcdef'}
 pixels=np.array(Image.open(io.BytesIO(base64.b64decode(display['image'].split(',')[1]))))
 assert np.any(np.all(pixels[:,:,:3]==[171,205,239],axis=-1))


def test_category_opacity_preserves_measurements_missing_pixels_and_printed_key(monkeypatch,tmp_path):
 import base64
 client,ident,directory=fixture(monkeypatch,tmp_path,'P01','binary','class')
 before=hashlib.sha256((directory/'main.tif').read_bytes()).hexdigest()
 url=f'/api/visualization/{ident}/P01/main';query={'category_opacity':json.dumps({'0':0,'1':.5}),'category_colors':json.dumps({'1':'#00aa66'})}
 display=client.get(url,params=query).json()
 pixels=np.array(Image.open(io.BytesIO(base64.b64decode(display['image'].split(',')[1]))))
 assert set(np.unique(pixels[:,:,3]))=={0,128}
 valid=np.array(Image.open(io.BytesIO(base64.b64decode(display['validity_image'].split(',')[1]))))>0
 assert np.any(valid&(pixels[:,:,3]==0)) and np.any(~valid)
 assert display['categories'][0]['opacity']==0 and display['categories'][1]['opacity']==.5
 exported=client.get(f'/api/map-image/{ident}/P01/main',params=query);assert exported.status_code==200,exported.text
 image=Image.open(io.BytesIO(exported.content));meta=json.loads(image.info['NISAR_Observatory'])
 assert meta['category_opacity']=={'0':0,'1':.5}
 assert meta['categories'][0]['opacity']==0
 assert before==hashlib.sha256((directory/'main.tif').read_bytes()).hexdigest()
 # Invalid opacity and use on a measurement must be rejected, including boolean coercion.
 for value in ['null','[]','{"0":true}','{"0":"0.5"}','{"0":-0.1}','{"0":1.1}','{"NaN":0}']:
  assert client.get(url,params={'category_opacity':value}).status_code==422
 monkeypatch.setattr(module,'JOBS',{ident:{'status':'completed','results':{'P01':{'status':'exploratory'}}}})
 recipe={'palette':'standard','mode':'shared','layer':'main','unit':'class','category_opacity':{'main':{'0':0}}}
 response=client.put(f'/api/jobs/{ident}/display/P01',json=recipe);assert response.status_code==200,response.text
 assert response.json()['display_preferences']['category_opacity']==recipe['category_opacity']
 assert client.put(f'/api/jobs/{ident}/display/P01',json={**recipe,'category_opacity':{'main':{'0':True}}}).status_code==422
 assert client.put(f'/api/jobs/{ident}/display/P01',json={**recipe,'category_opacity':{'missing':{'0':.5}}}).status_code==422


def test_measurements_reject_category_opacity(monkeypatch,tmp_path):
 client,ident,_=fixture(monkeypatch,tmp_path)
 assert client.get(f'/api/visualization/{ident}/P04/main',params={'category_opacity':'{"0":0}'}).status_code==422

@pytest.mark.parametrize('pid',['P04','P05'])
@pytest.mark.parametrize('layer',['range','interval_rate'])
def test_phase_summary_export_uses_selected_pair_not_whole_record(monkeypatch,tmp_path,pid,layer):
 client,ident,directory=fixture(monkeypatch,tmp_path,pid,unit='mm/day' if layer=='interval_rate' else 'mm')
 result=json.loads((directory/'result.json').read_text())
 result['layers'][0]['id']=layer
 (directory/'main.tif').rename(directory/(layer+'.tif'))
 result['sources'].append({'id':'later','start':'2026-02-01T00:00:00Z','end':'2026-02-13T00:00:00Z'})
 selected={'start':'2026-01-13T00:00:00Z','end':'2026-01-25T00:00:00Z'}
 result['extra']['selected_interval']=selected
 (directory/'result.json').write_text(json.dumps(result))
 before=(directory/'result.json').read_bytes()
 response=client.get(f'/api/map-image/{ident}/{pid}/{layer}')
 assert response.status_code==200,response.text
 meta=json.loads(Image.open(io.BytesIO(response.content)).info['NISAR_Observatory'])
 assert meta['layer']['start']==selected['start'] and meta['layer']['end']==selected['end']
 assert len(meta['sources'])==2
 assert (directory/'result.json').read_bytes()==before # saved science stays unchanged


def test_intermediate_phase_export_keeps_its_own_meaning_without_los_claims(monkeypatch,tmp_path):
 client,ident,directory=fixture(monkeypatch,tmp_path,pid='P05',kind='diverging',unit='rad')
 path=directory/'result.json';result=json.loads(path.read_text());result['layers'][0].update(trace_operation='event_pairs',interpretation='Quality-screened input phase in radians, before reference and LOS conversion. This is not displacement.')
 path.write_text(json.dumps(result))
 response=client.get(f'/api/map-image/{ident}/P05/main');assert response.status_code==200,response.text
 meta=json.loads(Image.open(io.BytesIO(response.content)).info['NISAR_Observatory'])
 assert meta['interpretation']==result['layers'][0]['interpretation']
 assert meta['layer']['unit']=='rad' and 'positive toward satellite' not in meta['interpretation']
