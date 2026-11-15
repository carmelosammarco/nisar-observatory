"""Bounded rendering must retain the exact frozen 0.8.3 pixel contract."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
from backend import exports
from backend.execution import execution_scope,ProcessingCancelled

spec=importlib.util.spec_from_file_location('legacy_colorize',Path(__file__).parent/'helpers/colorize_legacy.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)

@pytest.mark.parametrize('kind',['continuous','diverging','binary','water_state','categorical'])
@pytest.mark.parametrize('layout',['contiguous','transpose','stride'])
@pytest.mark.parametrize('dtype',['float32','float64'])
def test_exact_pixels_and_ranges_across_blocks(kind,layout,dtype,monkeypatch):
 # Force many block boundaries on small adversarial arrays.
 monkeypatch.setattr(exports,'COLOR_BLOCK_PIXELS',37)
 rng=np.random.default_rng(123);a=rng.normal(size=(39,41)).astype(dtype)
 if kind in ['binary','water_state','categorical']:a=np.floor(abs(a)*3)
 a[0,:4]=[np.nan,np.inf,-np.inf,0]
 a=a.T if layout=='transpose' else a[:,::2] if layout=='stride' else a
 settings=[{}, {'limits':(-2,3),'palette':[[0,0,0],[0,255,100],[255,0,200],[255,255,255]]}, {'category_colors':{'0':'#123456','1':'#abcdef'},'category_opacity':{'0':0.,'1':.37}}, {'category_opacity':{}}]
 with np.errstate(invalid='ignore',over='ignore'):
  for options in settings:
   expected,lo,hi=legacy.colorize(a,kind,**options)
   actual,new_lo,new_hi=exports.colorize(a,kind,**options)
   np.testing.assert_array_equal(actual,expected)
   assert (new_lo,new_hi)==(lo,hi)

@pytest.mark.parametrize('shape',[(0,0),(1,1),(3,5)])
def test_empty_constant_and_missing_rasters(shape):
 for value in [0.,np.nan]:
  a=np.full(shape,value,dtype='float32')
  old,lo,hi=legacy.colorize(a,'continuous');new,x,y=exports.colorize(a,'continuous')
  np.testing.assert_array_equal(new,old);assert (lo,hi)==(x,y)


def test_rendering_cancellation_between_bounded_blocks(monkeypatch):
 monkeypatch.setattr(exports,'COLOR_BLOCK_PIXELS',32)
 calls=[0]
 def cancelled():calls[0]+=1;return calls[0]>=4
 with execution_scope(cancelled),pytest.raises(ProcessingCancelled):exports.colorize(np.ones((100,100),dtype='float32'),'continuous')
 assert calls[0]==4


def test_windowed_cog_retains_numeric_values_across_tile_edges(tmp_path):
 from backend.science import target_grid
 from backend.processors import process
 from test_science import observations
 from rasterio.transform import from_origin
 import rasterio
 grid=target_grid([0,0,.01,.01],100)
 grid.update(shape=(517,603),transform=from_origin(0,51700,100,100))
 result=process('P01',observations('GCOV',grid,2),grid,{})
 expected={name:layer['data'].copy() for name,layer in result['layers'].items()}
 saved=exports.export_result(result,grid,tmp_path/'run')
 for layer in saved['layers']:
  with rasterio.open(tmp_path/'run'/layer['raster']) as src:
   np.testing.assert_array_equal(src.read(1),expected[layer['id']])
   assert src.tags(ns='IMAGE_STRUCTURE')['LAYOUT']=='COG'
