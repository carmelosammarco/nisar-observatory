"""Known-value synthetic fixtures verify transformations, not scientific accuracy."""
from datetime import datetime,timedelta
import numpy as np
import pytest
import h5py
from backend.science import target_grid,read_window,load_observation
from backend.processors import process
from backend.exports import export_result

@pytest.fixture
def grid():return target_grid([-114.76,36.12,-114.70,36.18],200)

def observations(product,grid,n=4):
 h,w=grid['shape'];yy,xx=np.indices((h,w));obs=[]
 for i in range(n):
  if product=='GCOV':
   a=np.full((h,w),.1,'float32');a[(xx>w*.3)&(xx<w*(.5+.05*i))]=.001
   if i>0:a[(xx>w*.7)&(yy>h*.6)]=.3
  elif product=='SME2':a=np.full((h,w),.2+i*.03,'float32')
  else:a=(xx/w*.5+i*.1).astype('float32')
  start=f'2026-09-{1+12*i:02}T00:00:00Z' if i<3 else '2026-10-07T00:00:00Z'
  from datetime import datetime,timedelta
  start=(datetime(2026,8,1)+timedelta(days=12*i)).isoformat()+'Z';end=(datetime(2026,8,13)+timedelta(days=12*i)).isoformat()+'Z'
  obs.append({'array':a,'item':{'id':str(i),'name':'SYNTHETIC TEST FIXTURE','product':product,'start':start,'end':end,'group':'one'},'path':'/science/LSAR/'+product+'/grids/frequencyA/test','attrs':{'units':'radians' if product=='GUNW' else 'm'},'quality_paths':[],'warnings':['SYNTHETIC TEST FIXTURE — NOT NASA OBSERVATIONS'],'bytes_transferred':0,'wavelength':.24})
 return obs

def test_all_seven_workflows_and_exports(grid,tmp_path):
 obs=sum([observations(p,grid) for p in ['GCOV','GUNW','GOFF','SME2']],[])
 options={'reference_bbox':[-114.76,36.12,-114.75,36.18],'event_date':'2026-08-05','water_threshold':-17,'change_threshold':3}
 for i in range(1,8):
  pid=f'P{i:02}';result=process(pid,obs,grid,options)
  assert result['layers'] and result['sources']
  exported=export_result(result,grid,tmp_path/pid)
  assert (tmp_path/pid/'result.json').exists()
  assert all((tmp_path/pid/l['raster']).exists() for l in exported['layers'])
  assert exported['validation_status'].startswith('Exploratory')

def test_known_water_area_and_change(grid):
 obs=observations('GCOV',grid,2);obs[0]['array'][:]=.1;obs[1]['array'][:]=.001
 r=process('P01',obs,grid,{})
 assert r['metrics']['baseline_water_candidate_km2']==0
 assert r['metrics']['latest_water_candidate_km2']==pytest.approx(np.prod(grid['shape'])*grid['resolution']**2/1e6)
 assert np.nanmedian(r['layers']['change']['data'])==pytest.approx(-20)

def test_phase_reference_and_conversion(grid):
 obs=observations('GUNW',grid,1)
 r=process('P04',obs,grid,{'reference_bbox':[-114.76,36.12,-114.75,36.18]})
 a=r['layers']['range']['data'];assert np.nanmin(a)<-5
 assert np.nanmax(a)<5
 with pytest.raises(ValueError,match='reference'):process('P04',obs,grid,{})

def test_missing_event_and_incompatible_groups(grid):
 obs=observations('GUNW',grid,2)
 with pytest.raises(ValueError,match='brackets'):process('P05',obs,grid,{'reference_bbox':[-114.76,36.12,-114.75,36.18],'event_date':'2020-01-01'})
 obs=observations('GCOV',grid,2);obs[1]['item']['group']='different'
 with pytest.raises(ValueError,match='track'):process('P01',obs,grid,{})

def test_native_hdf_window_georeferencing(tmp_path):
 from pyproj import Transformer
 fpath=tmp_path/'test.h5';x0,y0=Transformer.from_crs(4326,32611,always_xy=True).transform(-114.73,36.15)
 with h5py.File(fpath,'w') as f:
  g=f.create_group('/science/LSAR/GCOV/grids/frequencyA');g['xCoordinates']=x0+np.arange(-50,50)*100;g['yCoordinates']=y0-np.arange(-50,50)*100;g['projection']=32611
  g['HHHH']=np.full((100,100),.01,'float32');g['mask']=np.ones((100,100),'uint8')
 with h5py.File(fpath,'r') as f:
  grid=target_grid([-114.74,36.14,-114.72,36.16],100);a,_=read_window(f,'/science/LSAR/GCOV/grids/frequencyA/HHHH',grid['bbox'],grid)
 assert np.nanmedian(a)==pytest.approx(.01);assert np.isfinite(a).mean()>.9

def test_goff_interval_rate(grid):
 obs=observations('GOFF',grid,1);obs[0]['array'][:]=12
 r=process('P07',obs,grid,{})
 assert np.nanmedian(r['layers']['value']['data'])==pytest.approx(1)

def test_nonfinite_hdf_attributes_are_json_safe():
 from backend.science import decode
 import json
 assert decode(np.float32(np.nan)) is None
 json.dumps({'fill':decode(np.float32(np.nan))},allow_nan=False)

def test_real_sme2_recommendation_bit_semantics(tmp_path,monkeypatch):
 from backend import science
 from pyproj import Transformer
 monkeypatch.setattr(science,'DATA',tmp_path);(tmp_path/'raw').mkdir()
 bbox=[-93.52,42,-93.50,42.02];x,y=Transformer.from_crs(4326,6933,always_xy=True).transform(-93.51,42.01)
 with h5py.File(tmp_path/'raw'/'soil.h5','w') as f:
  g=f.create_group('/science/LSAR/SME2/grids');g['xCoordinates']=x+np.arange(-15,15)*200;g['yCoordinates']=y-np.arange(-15,15)*200;g['projection']=6933
  g['soilMoisture']=np.full((30,30),.25,'float32')
  g['retrievalQualityFlag']=np.full((30,30),2,'uint8')
  g['retrievalQualityFlag'].attrs['description']='The least significant bit indicates whether the retrieval is recommended (0 = recommended, 1 = not recommended).'
  g['soilMoisture'].attrs['_FillValue']=np.nan
 grid=science.target_grid(bbox,200)
 item={'id':'soil','product':'SME2','url':''}
 observation=science.load_observation(item,bbox,grid,{},lambda:False)
 assert np.nanmedian(observation['array'])==pytest.approx(.25)
 assert observation['quality_paths']==['/science/LSAR/SME2/grids/retrievalQualityFlag']
 again=science.load_observation(item,bbox,grid,{},lambda:False)
 assert again['cache_hit'] is True
 with h5py.File(tmp_path/'raw'/'soil.h5','a') as f:f['/science/LSAR/SME2/grids/retrievalQualityFlag'][:]=3
 # Different extraction option deliberately invalidates the area cache.
 with pytest.raises(ValueError,match='No recommended SME2'):
  science.load_observation(item,bbox,grid,{'channel':'HHHH'},lambda:False)

 diag=science.load_observation(item,bbox,grid,{'soil_allow_unrecommended':True},lambda:False)
 assert np.isfinite(diag['array']).any()
 assert diag['attrs']['diagnostic_include_unrecommended'] is True
 assert diag['attrs']['recommended_fraction_of_finite_retrievals']==0
 assert any('DIAGNOSTIC' in w for w in diag['warnings'])




def test_nonpositive_power_is_missing_not_dry(grid):
 obs=observations('GCOV',grid,3)
 obs[0]['array'][0,0]=0;obs[1]['array'][0,0]=-1
 r=process('P02',obs,grid,{})
 assert r['layers']['count']['data'][0,0]==1
 assert np.isnan(r['layers']['occupancy']['data'][0,0])
 assert np.isnan(r['layers']['observation_2']['data'][0,0])

def test_single_offset_interval_has_no_artificial_temporal_change(grid):
 r=process('P07',observations('GOFF',grid,1),grid,{})
 assert 'change' not in r['layers'] and 'variability' not in r['layers']
 assert 'observation_0' in r['layers']

def test_wetland_zones_use_fixed_support_and_missing_is_not_zero(grid):
 obs=observations('GCOV',grid,3);mid=grid['shape'][1]//2
 for o in obs:o['array'][:]=.001
 obs[0]['array'][:,:mid]=np.nan
 r=process('P02',obs,grid,{})
 west,east=r['extra']['zones']
 assert west['wet_fraction']==[None]*3 and west['valid_counts']==[0]*3
 assert east['wet_fraction']==[1.]*3

def test_fire_reference_requires_common_valid_support(grid):
 from backend.processors import region_mask
 obs=observations('GCOV',grid,3);bbox=[-114.76,36.12,-114.75,36.18]
 ref=region_mask(bbox,grid);coords=np.argwhere(ref)
 for i,o in enumerate(obs):
  o['array'][ref]=np.nan
  y,x=coords[i];o['array'][y,x]=.1
 with pytest.raises(ValueError,match='valid on every date'):
  process('P03',obs,grid,{'reference_bbox':bbox})

def test_empty_spatial_zone_has_missing_statistics():
 from backend.processors import stats
 assert stats(np.empty((3,0)))=={'valid_pixels':0,'valid_fraction':0.,'median':None,'p10':None,'p90':None}

def test_wetland_named_zones_do_not_claim_arbitrary_west_east_halves(grid):
 w,s,e,n=grid['bbox']
 context={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[w,s],[e,s],[e,n],[w,n],[w,s]]]},'properties':{'role':'zone','name':'Published marsh outline','source':'Independent boundary'}}]}
 result=process('P02',observations('GCOV',grid,3),grid,{'spatial_context':context})
 assert [z['name'] for z in result['extra']['zones']]==['Published marsh outline']
 assert any('Named polygons define comparison zones' in note for note in result['notes'])
 assert not any('West/east halves' in note for note in result['notes'])

@pytest.mark.parametrize('pid',['P06'])
def test_persistent_change_rejects_disjoint_coverage(grid,pid):
 obs=observations('GCOV',grid,3)
 for i,o in enumerate(obs):
  o['array'][:]=np.nan;o['array'][i,:]=.1
 with pytest.raises(ValueError,match='common valid footprint'):process(pid,obs,grid,{})

@pytest.mark.parametrize('method',['average','DSG','TSR'])
def test_sme2_quality_flags_belong_only_to_selected_retrieval(tmp_path,monkeypatch,method):
 from pyproj import Transformer
 from backend import science
 monkeypatch.setattr(science,'DATA',tmp_path);(tmp_path/'raw').mkdir()
 bbox=[-93.52,42,-93.50,42.02];x,y=Transformer.from_crs(4326,6933,always_xy=True).transform(-93.51,42.01)
 with h5py.File(tmp_path/'raw'/'soil.h5','w') as f:
  g=f.create_group('/science/LSAR/SME2/grids');g['xCoordinates']=x+np.arange(-15,15)*200;g['yCoordinates']=y-np.arange(-15,15)*200;g['projection']=6933
  for name in ['average','DSG','TSR']:
   parent=g if name=='average' else g.require_group('algorithmCandidates/'+name)
   parent['soilMoisture']=np.full((30,30),.25,'float32')
   parent['retrievalQualityFlag']=np.full((30,30),0 if name==method else 1,'uint8')
   parent['retrievalQualityFlag'].attrs['description']='The least significant bit indicates whether the retrieval is recommended (0 = recommended, 1 = not recommended).' if name=='average' else '0 means clear and non-zero means anomaly'
 grid=science.target_grid(bbox,200);item={'id':'soil','product':'SME2','url':''}
 o=science.load_observation(item,bbox,grid,{'soil_method':method},lambda:False)
 assert np.nanmedian(o['array'])==pytest.approx(.25)
 expected='/science/LSAR/SME2/grids/'+('' if method=='average' else 'algorithmCandidates/'+method+'/')+'retrievalQualityFlag'
 assert o['quality_paths']==[expected]
