"""Exact, bounded shared ranges: compare against the former concatenated path."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from backend import display_range as module
from backend.execution import execution_scope, ProcessingCancelled


@pytest.mark.parametrize('dtype',['float32','float64'])
@pytest.mark.parametrize('population',['random','repeated','extreme','constant'])
def test_external_selection_matches_numpy_exactly(monkeypatch,dtype,population):
    monkeypatch.setattr(module,'IN_MEMORY_VALUES',7)
    rng=np.random.default_rng(547)
    a=rng.normal(size=(47,43)).astype(dtype)
    if population=='repeated':a=np.round(a)
    if population=='extreme':a*=np.array(1e30,dtype=dtype)
    if population=='constant':a[:]=1.25
    a[0,:5]=[np.nan,np.inf,-np.inf,0.,-0.]
    # Include subnormals and values on opposite sides of zero.
    a[1,:3]=[np.nextafter(np.array(0,dtype=dtype),np.array(1,dtype=dtype)),1.,-1.]
    a=a.T[:,::2]
    calls=[]
    def blocks():
        calls.append(1)
        for row in a:yield row
    qs=[0,.01,2,25,50,75,98,99.99,100]
    actual=module.exact_percentiles(blocks,dtype,qs)
    expected=np.percentile(a[np.isfinite(a)],qs)
    np.testing.assert_array_equal(actual,expected)
    assert len(calls)==np.dtype(dtype).itemsize


@pytest.mark.parametrize('count',[1,2,7,8,11])
def test_small_large_boundary_empty_blocks_and_missing_values(monkeypatch,count):
    monkeypatch.setattr(module,'IN_MEMORY_VALUES',7)
    a=np.arange(count,dtype='float32')
    def blocks():
        yield np.array([np.nan,np.inf],dtype='float32')
        yield np.array([],dtype='float32')
        yield a
    np.testing.assert_array_equal(module.exact_percentiles(blocks,a.dtype),np.percentile(a,[2,98]))


def test_invalid_empty_population_and_cooperative_cancellation(monkeypatch):
    with pytest.raises(ValueError,match='No finite'):module.exact_percentiles(lambda:[np.array([np.nan])],'float32')
    with pytest.raises(ValueError,match='float32 or float64'):module.exact_percentiles(lambda:[],'int32')
    with pytest.raises(ValueError,match='Percentiles'):module.exact_percentiles(lambda:[],'float32',[101])
    monkeypatch.setattr(module,'IN_MEMORY_VALUES',1)
    calls=[0]
    def cancel():calls[0]+=1;return calls[0]>=5
    with execution_scope(cancel),pytest.raises(ProcessingCancelled):
        module.exact_percentiles(lambda:[np.arange(100,dtype='float32') for _ in range(3)],'float32')


def test_mixed_raster_dtypes_windows_missing_frames_and_unchanged_files(monkeypatch,tmp_path):
    import hashlib
    monkeypatch.setattr(module,'IN_MEMORY_VALUES',7)
    arrays=[np.arange(517*263,dtype='float32').reshape(517,263)/7,np.full((3,5),np.nan,dtype='float32'),np.array([[-100.,.123456789,4.]],dtype='float64')]
    paths=[]
    for i,a in enumerate(arrays):
        path=tmp_path/f'{i}.tif';paths.append(path)
        with rasterio.open(path,'w',driver='GTiff',height=a.shape[0],width=a.shape[1],count=1,dtype=a.dtype,crs='EPSG:6933',transform=from_origin(0,6000,10,10)) as ds:ds.write(a,1)
    before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    result=module.raster_percentiles(paths)
    values=np.concatenate([a[np.isfinite(a)] for a in arrays])
    np.testing.assert_array_equal(result,np.percentile(values,[2,98]))
    assert before==[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    with pytest.raises(ValueError,match='too large'):module.raster_percentiles(paths,max_cells=10)


def test_selected_order_statistic_disappearing_is_rejected(monkeypatch):
    monkeypatch.setattr(module,'IN_MEMORY_VALUES',1)
    passes=[0]
    def blocks():
        passes[0]+=1
        yield np.array([1.,2.,3.] if passes[0]==1 else [],dtype='float32')
    with pytest.raises(ValueError,match='changed'):module.exact_percentiles(blocks,'float32')
