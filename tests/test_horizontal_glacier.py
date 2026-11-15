"""Independent known-vector and native-cube checks; no NASA observations mocked as truth."""
import numpy as np
import h5py,pytest
from backend.glacier_geometry import horizontal,interpolate,copy_cubes,FIELDS,ROOT
from backend.subsets import _attrs
from backend.science import target_grid

def geometry(shape=(4,4),angle=40):
 a=np.deg2rad(angle)
 return dict(zip(FIELDS,[np.full(shape,-np.sin(a)),np.zeros(shape),np.zeros(shape),np.ones(shape),np.full(shape,angle)]))

def test_known_horizontal_vector_signs_units_and_vertical_scenario():
 g=geometry();east=-100/365.25;north=-20/365.25
 r=-g[FIELDS[0]]*east-g[FIELDS[1]]*north;a=g[FIELDS[2]]*east+g[FIELDS[3]]*north
 sol,diag=horizontal(r,a,g,annualization=365.25)
 assert np.allclose(sol['east']*365.25,-100)
 assert np.allclose(sol['north']*365.25,-20)
 assert np.allclose(sol['speed']*365.25,np.hypot(100,20))
 assert np.allclose(sol['vertical_sensitivity'],20/np.tan(np.deg2rad(40)))
 assert np.allclose(sol['bearing'],258.6900675)
 assert diag['accepted_cells']==16

def test_nonorthogonal_enu_viewing_vectors_are_solved_not_assumed_orthogonal():
 g=geometry();g[FIELDS[2]][:]=.1;g[FIELDS[3]][:]=np.sqrt(.99)
 expected_e,expected_n=2.,-3.
 r=-g[FIELDS[0]]*expected_e-g[FIELDS[1]]*expected_n;a=g[FIELDS[2]]*expected_e+g[FIELDS[3]]*expected_n
 s,_=horizontal(r,a,g);assert np.allclose(s['east'],expected_e);assert np.allclose(s['north'],expected_n)

def test_conditioning_missing_samples_and_zero_speed_direction():
 g=geometry();a=np.zeros((4,4));r=a.copy();r[0,0]=np.nan
 s,_=horizontal(r,a,g);assert np.isnan(s['speed'][0,0]);assert np.isnan(s['bearing']).all()
 s,d=horizontal(np.ones((4,4)),np.ones((4,4)),g,max_condition=1.1)
 assert np.isnan(s['speed']).all();assert d['condition_rejected_cells']==16
 g[FIELDS[2]][:]=1;g[FIELDS[3]][:]=0
 s,_=horizontal(r,a,g);assert not s['valid'].any()

def test_invalid_vector_or_incidence_is_never_used():
 g=geometry();g['incidenceAngle'][1,1]=60
 s,_=horizontal(np.ones((4,4)),np.ones((4,4)),g);assert np.isnan(s['speed'][1,1])


def make_cube(path):
 with h5py.File(path,'w') as f:
  g=f.create_group(ROOT);g['xCoordinates']=[-2000,0,2000];g['yCoordinates']=[2000,0,-2000];g['heightAboveEllipsoid']=[0,1000];g['projection']=6933
  for name,base in zip(FIELDS,[-.6,0,0,1,36.86989765]):
   ds=g.create_dataset(name,data=np.full((2,3,3),base,dtype='float32'));ds.attrs['description']=('East' if name.endswith('X') else 'North')+' component of unit vector';ds.attrs['units']='degrees' if name=='incidenceAngle' else '1'
 return path


def test_cube_interpolation_axes_height_boundary_and_no_extrapolation(tmp_path):
 path=make_cube(tmp_path/'cube.h5');grid=target_grid([-.005,-.005,.005,.005],100)
 with h5py.File(path,'r') as f:
  out,meta=interpolate(f,grid,500);assert np.allclose(out[FIELDS[0]],-.6);assert meta['height_above_ellipsoid_m']==500
  with pytest.raises(ValueError,match='outside'):interpolate(f,grid,1001)
  distant=target_grid([1,1,1.01,1.01],100);out,_=interpolate(f,distant,500);assert np.isnan(out[FIELDS[0]]).all()


def test_missing_geometry_and_ambiguous_vector_basis_fail_explicitly(tmp_path):
 path=make_cube(tmp_path/'cube.h5');grid=target_grid([-.005,-.005,.005,.005],100)
 with h5py.File(path,'r+') as f:
  f[ROOT+'/'+FIELDS[2]].attrs['description']='UTM X component'
  with pytest.raises(ValueError,match='coordinate convention'):interpolate(f,grid,500)
  del f[ROOT+'/'+FIELDS[2]]
  with pytest.raises(ValueError,match='Prepare geometry'):interpolate(f,grid,500)


def test_native_geometry_copy_is_bounded_and_self_contained(tmp_path):
 path=make_cube(tmp_path/'cube.h5')
 with h5py.File(path,'r') as source,h5py.File(tmp_path/'subset.h5','w') as dest:
  m=copy_cubes(source,dest,[-.005,-.005,.005,.005],_attrs);assert m['available'];assert dest[ROOT+'/'+FIELDS[0]].shape==(2,3,3)
  assert dest[ROOT+'/'+FIELDS[0]].attrs['description'].startswith('East')


def test_processor_pairs_geometry_units_and_component_choice():
 from backend.processors import process
 from test_science import observations
 grid=target_grid([0,0,.01,.01],100);obs=observations('GOFF',grid,1);g=geometry(grid['shape'])
 # Exactly 12 days; independent velocity [-100,-20] metres/year.
 r=(-g[FIELDS[0]]*(-100)-g[FIELDS[1]]*(-20))*12/365.25
 a=(g[FIELDS[2]]*(-100)+g[FIELDS[3]]*(-20))*12/365.25
 obs[0]['array']=r;obs[0]['aux']={'other_offset':a,**{'geometry_'+k:v for k,v in g.items()}}
 opt={'offset_solution':'horizontal','offset_filter':False,'offset_rate_unit':'m/year','offset_geometry_height_m':5000}
 result=process('P07',obs,grid,opt)
 assert np.allclose(result['layers']['horizontal_speed']['data'],np.hypot(100,20))
 assert np.allclose(result['layers']['horizontal_east_0']['data'],-100)
 assert np.allclose(result['layers']['observation_0']['data'],result['layers']['horizontal_speed']['data'])
 assert 'radar_observation_0' in result['layers']
 assert result['series'][0]['median']==pytest.approx(np.hypot(100,20))
 assert result['metrics']['median']==pytest.approx(np.hypot(100,20))
 assert result['extra']['horizontal_velocity']['height_above_ellipsoid_m']==5000
 obs[0]['array']=a;obs[0]['aux']['other_offset']=r
 alternate=process('P07',obs,grid,{**opt,'component':'alongTrackOffset'})
 np.testing.assert_allclose(alternate['layers']['horizontal_speed']['data'],result['layers']['horizontal_speed']['data'])
 daily=process('P07',obs,grid,{**opt,'component':'alongTrackOffset','offset_rate_unit':'m/day'})
 np.testing.assert_allclose(daily['layers']['horizontal_speed']['data']*365.25,result['layers']['horizontal_speed']['data'],rtol=1e-6)
 np.testing.assert_allclose(daily['layers']['horizontal_vertical_sensitivity_0']['data']*365.25,result['layers']['horizontal_vertical_sensitivity_0']['data'],rtol=1e-6)


def test_processor_never_silently_omits_missing_pair_geometry():
 from backend.processors import process
 from test_science import observations
 grid=target_grid([0,0,.01,.01],100);obs=observations('GOFF',grid,2)
 for o in obs:o['aux']={'other_offset':np.ones(grid['shape']),**{'geometry_'+k:v for k,v in geometry(grid['shape']).items()}}
 del obs[1]['aux']['geometry_incidenceAngle']
 with pytest.raises(ValueError,match='every selected pair'):process('P07',obs,grid,{'offset_solution':'horizontal','offset_filter':False})


def test_native_subset_geometry_upgrade_preserves_offsets_and_old_file(monkeypatch,tmp_path):
 import json
 from backend import science,subsets,geometry_storage
 from test_subsets import setup,BBOX
 item,client=setup(monkeypatch,tmp_path,'GOFF')
 item['url']='https://nisar.asf.earthdatacloud.nasa.gov/NISAR/synthetic.h5'
 saved,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 old=science.source_file(saved);before=old.read_bytes()
 with h5py.File(science.source_file(item),'r+') as f:
  base=f['/science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH/layer1'];g=f.create_group(ROOT)
  g['xCoordinates']=base['xCoordinates'][:];g['yCoordinates']=base['yCoordinates'][:];g['heightAboveEllipsoid']=[0,1000];g['projection']=32611
  for name,value in zip(FIELDS,[-.6,0,0,1,36.86989765]):
   d=g.create_dataset(name,data=np.full((2,100,100),value));d.attrs['units']='degrees' if name=='incidenceAngle' else '1';d.attrs['description']=('East' if name.endswith('X') else 'North')+' component'
 new,count,reused=geometry_storage.prepare(saved,BBOX,lambda:False,lambda *a:None)
 assert not reused and new['id']!=saved['id'] and new['viewing_geometry']['available']
 assert old.read_bytes()==before
 with h5py.File(old) as a,h5py.File(science.source_file(new)) as b:
  path='/science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH/layer1/slantRangeOffset'
  np.testing.assert_array_equal(a[path][:],b[path][:]);assert ROOT not in a
  assert json.loads(b.attrs['observatory_subset_manifest'])['viewing_geometry']['available']
  from backend.subset_import import metadata
  # This fixture is a synthetic, deliberately shortened filename; validate its geometry manifest via a proper pair name.
  from test_subset_folders import proper_pair
  name=proper_pair(item.copy())['name']
 with h5py.File(science.source_file(new),'r+') as b:
  b.attrs['observatory_source_name']=name;manifest=json.loads(b.attrs['observatory_subset_manifest']);manifest['source_name']=name;b.attrs['observatory_subset_manifest']=json.dumps(manifest)
  assert metadata(b)['viewing_geometry']['available']
 same,_,hit=geometry_storage.prepare(saved,BBOX,lambda:False,lambda *a:None)
 assert hit and same['id']==new['id']


def test_geometry_endpoint_requires_correct_product_and_auth(monkeypatch,tmp_path):
 from test_subsets import setup,BBOX
 from backend import app as module,subsets
 item,client=setup(monkeypatch,tmp_path,'GOFF');saved,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 module.CATALOG[saved['id']]=saved;monkeypatch.setattr(module.AUTH,'session',None)
 assert client.post('/api/download-geometry',json={'bbox':BBOX,'granules':[saved['id']]}).status_code==401
 module.CATALOG[saved['id']]['product']='GCOV'
 assert client.post('/api/download-geometry',json={'bbox':BBOX,'granules':[saved['id']]}).status_code==422
