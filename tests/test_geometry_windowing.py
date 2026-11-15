"""Bound native geometry reads before allocation; retain the former interpolant."""
import numpy as np
import pytest
from rasterio.transform import from_origin
from backend import glacier_geometry as geometry


class Coordinate:
    def __init__(self,values):
        self.values=np.asarray(values);self.attrs={};self.shape=self.values.shape;self.ndim=self.values.ndim;self.size=self.values.size;self.dtype=self.values.dtype
    def __getitem__(self,key):return self.values[key]


class VirtualCube:
    """A roughly 10 GB logical source. A full read fails without allocating it."""
    def __init__(self,axes,index,reads):
        self.axes=axes;self.index=index;self.reads=reads;self.shape=tuple(len(a) for a in axes);self.dtype=np.dtype('float32');self.chunks=(2,32,32)
        self.attrs={'units':'degrees' if index==4 else '1','description':('East' if geometry.FIELDS[index].endswith('X') else 'North')+' component'}
    def __getitem__(self,key):
        assert isinstance(key,tuple) and len(key)==3 and all(isinstance(k,slice) for k in key),'Full geometry-cube read attempted'
        axes=[a[k] for a,k in zip(self.axes,key)];shape=tuple(len(a) for a in axes)
        assert np.prod(shape)<1_000_000,'Unbounded geometry window attempted'
        self.reads.append({'field':self.index,'shape':shape,'key':key})
        z,y,x=np.ix_(*axes)
        return ([-.6,0,0,1,36.87][self.index]+z*1e-5+(x+y)*1e-6).astype('float32')


def virtual_source():
    axes=[np.array([-1000.,0.,1000.,2000.,3000.]),np.linspace(2000,-2000,10001),np.linspace(-2000,2000,10001)];reads=[]
    group={name:Coordinate(axis) for name,axis in zip(['heightAboveEllipsoid','yCoordinates','xCoordinates'],axes)};group['projection']=Coordinate(6933)
    for i,name in enumerate(geometry.FIELDS):group[name]=VirtualCube(axes,i,reads)
    return {geometry.ROOT:group,**{geometry.ROOT+'/'+name:ds for name,ds in group.items()}},reads


def test_large_original_geometry_is_windowed_in_space_and_height_before_reading():
    source,reads=virtual_source();target={'crs':'EPSG:6933','shape':(20,25),'transform':from_origin(-25,20,2,2)}
    out,meta=geometry.interpolate(source,target,500)
    assert len(reads)==5 and all(r['shape'][0]==2 for r in reads)
    assert all(r['shape'][1]<120 and r['shape'][2]<140 for r in reads)
    assert np.isfinite(out['losUnitVectorX']).all()
    assert np.max(abs(out['losUnitVectorX']-(-.6+.005)))<1e-4


def legacy_interpolate(*args):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('geometry_0_8_11',Path(__file__).parent/'fixtures/geometry_0_8_11.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.interpolate(*args)


def create_fixture(path,directions):
    import h5py
    axes=[np.array([-1000.,0.,400.,1000.,4000.]),np.array([-1000.,-700.,-280.,-120.,0.,22.,55.,250.,390.,700.,1000.]),np.array([-1000.,-700.,-300.,-100.,-40.,0.,23.,150.,400.,500.,750.,1000.])]
    axes=[a[::direction] for a,direction in zip(axes,directions)]
    with h5py.File(path,'w') as f:
        g=f.create_group(geometry.ROOT)
        for name,a in zip(['heightAboveEllipsoid','yCoordinates','xCoordinates'],axes):g[name]=a
        g['projection']=6933;rng=np.random.default_rng(834)
        for i,name in enumerate(geometry.FIELDS):
            data=rng.normal(size=tuple(len(a) for a in axes)).astype('float32');data[rng.random(data.shape)<.02]=np.nan;data.ravel()[17]=-9999
            ds=g.create_dataset(name,data=data,chunks=(2,4,4));ds.attrs['_FillValue']=-9999;ds.attrs['units']='degrees' if i==4 else '1';ds.attrs['description']=('East' if name.endswith('X') else 'North')+' component'
    return path


@pytest.mark.parametrize('directions',[(z,y,x) for z in [-1,1] for y in [-1,1] for x in [-1,1]])
@pytest.mark.parametrize('height',[-1000.,0.,500.,4000.])
def test_exact_full_cube_oracle_including_descending_axes_nan_neighbours_and_height_boundaries(tmp_path,monkeypatch,directions,height):
    import h5py
    path=create_fixture(tmp_path/'source.h5',directions);target={'crs':'EPSG:6933','shape':(12,13),'transform':from_origin(-550,550,100,100)}
    monkeypatch.setattr(geometry,'MAX_POINT_BATCH',17)
    with h5py.File(path,'r') as f:
        expected,_=legacy_interpolate(f,target,height);actual,meta=geometry.interpolate(f,target,height)
    for name in geometry.FIELDS:
        assert np.isfinite(expected[name]).any()
        np.testing.assert_array_equal(actual[name],expected[name],err_msg=name)
    assert meta['maximum_point_batch']==17 and meta['read_window_shape'][0]==2


def test_outside_geometry_returns_missing_without_reading_a_cube():
    source,reads=virtual_source();target={'crs':'EPSG:6933','shape':(4,4),'transform':from_origin(10000,12000,10,10)}
    out,meta=geometry.interpolate(source,target,500)
    assert not reads and meta['read_window_shape']==[0,0,0]
    assert all(np.isnan(a).all() for a in out.values())


def test_native_window_budget_is_checked_before_cube_or_output_allocation():
    source,reads=virtual_source();target={'crs':'EPSG:6933','shape':(1000,1000),'transform':from_origin(-2000,2000,.4,.4)}
    with pytest.raises(ValueError,match='window exceeds 64 MiB'):geometry.interpolate(source,target,500)
    assert not reads


def test_oversized_hdf5_chunk_is_rejected_before_source_reads():
    source,reads=virtual_source();source[geometry.ROOT][geometry.FIELDS[0]].chunks=(5,10001,10001)
    with pytest.raises(ValueError,match='chunk exceeds 64 MiB'):geometry.interpolate(source,{'crs':'EPSG:6933','shape':(2,2),'transform':from_origin(0,0,10,10)},500)
    assert not reads


@pytest.mark.parametrize('axis',[[0.],[0.,0.,1.],[0.,2.,1.],[0.,np.nan,1.]])
def test_bad_axes_fail_before_cube_reads(axis):
    source,reads=virtual_source();source[geometry.ROOT]['xCoordinates']=Coordinate(axis)
    with pytest.raises(ValueError,match='strictly monotonic'):geometry.interpolate(source,{'shape':(2,2)},500)
    assert not reads


def test_target_limit_is_checked_before_any_source_metadata_access():
    source,_=virtual_source()
    with pytest.raises(ValueError,match='4 million'):geometry.interpolate(source,{'shape':(2048,2048)},500)


def test_cancellation_stops_before_another_geometry_field(monkeypatch):
    from backend.execution import execution_scope,ProcessingCancelled
    source,reads=virtual_source();target={'crs':'EPSG:6933','shape':(20,25),'transform':from_origin(-25,20,2,2)}
    with pytest.raises(ProcessingCancelled),execution_scope(lambda:bool(reads)):
        geometry.interpolate(source,target,500)
    assert len(reads)==1


def test_only_horizontal_geometry_cache_identity_changes_with_adapter_version(monkeypatch):
    from backend.science import cache_identity
    item={'id':'unit-source','product':'GOFF'};grid={'crs':'EPSG:6933','bbox':[0,0,.1,.1],'shape':(4,4),'resolution':100,'transform':from_origin(0,400,100,100)}
    radar=cache_identity(item,grid['bbox'],grid,{});old=cache_identity(item,grid['bbox'],grid,{'offset_solution':'horizontal'})
    monkeypatch.setattr(geometry,'INTERPOLATION_VERSION','test-next')
    assert cache_identity(item,grid['bbox'],grid,{})==radar
    assert cache_identity(item,grid['bbox'],grid,{'offset_solution':'horizontal'})!=old


def test_oversized_axis_metadata_is_rejected_without_reading_it():
    source,reads=virtual_source()
    class OversizedAxis:
        ndim=1;size=geometry.MAX_AXIS_SAMPLES+1
        def __getitem__(self,key):pytest.fail('An over-budget axis was read')
    source[geometry.ROOT]['xCoordinates']=OversizedAxis()
    with pytest.raises(ValueError,match='one million'):geometry.interpolate(source,{'shape':(2,2)},500)
    assert not reads


def test_bad_cube_dimensions_fail_before_any_field_is_read():
    source,reads=virtual_source();source[geometry.ROOT][geometry.FIELDS[-1]].shape=(1,2,3)
    with pytest.raises(ValueError,match='dimensions disagree'):geometry.interpolate(source,{'shape':(2,2)},500)
    assert not reads


def test_target_affine_uses_both_row_and_column_vectors():
    from affine import Affine
    source,_=virtual_source();target={'crs':'EPSG:6933','shape':(5,6),'transform':Affine(2,.5,-8,.25,-2,7)}
    actual,_=geometry.interpolate(source,target,500);row,col=np.indices(target['shape']);x=2*(col+.5)+.5*(row+.5)-8;y=.25*(col+.5)-2*(row+.5)+7
    expected=-.6+.005+(x+y)*1e-6
    np.testing.assert_allclose(actual['losUnitVectorX'],expected,rtol=0,atol=1e-7)
