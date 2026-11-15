from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds,reproject,Resampling
from PIL import Image
from .execution import checkpoint,cancellable

COLOR_BLOCK_PIXELS=65536

@cancellable
def colorize(a,kind,limits=None,palette=None,category_colors=None,category_opacity=None):
 """Preserve exact global ranges; bound temporary RGB/interpolation arrays.

 The input and final RGBA image remain in memory. Global percentiles still use
 all finite values. Only colour interpolation is streamed, in C-order blocks.
 """
 a=np.asarray(a)
 if a.ndim!=2:raise ValueError('Map colour rendering requires a two-dimensional raster.')
 v=a[np.isfinite(a)]
 lo,hi=(float(np.percentile(v,2)),float(np.percentile(v,98))) if v.size else (0.,1.)
 del v
 if limits is not None:lo,hi=map(float,limits)
 elif kind=='diverging':hi=max(abs(lo),abs(hi),1e-6);lo=-hi
 if kind=='binary':lo,hi=0.,1.
 if kind=='water_state':lo,hi=0.,2.
 if hi<=lo:hi=lo+1
 stops=np.array([[24,45,61],[41,155,165],[231,230,166]]) if kind!='diverging' else np.array([[61,137,205],[242,239,222],[229,102,76]])
 if palette is not None:stops=np.array(palette)
 if kind=='water_state':stops=np.array([[225,220,198],[49,143,191],[142,143,151]])
 if kind=='binary':stops=np.array([[225,220,198],[49,143,191],[20,88,151]])
 rgba=np.empty((*a.shape,4),dtype='uint8');output=rgba.reshape(-1,4);offset=0
 # buffered external_loop also bounds contiguous inputs and avoids copying a
 # whole transposed/strided raster just to flatten it.
 for block in np.nditer(a,flags=['external_loop','buffered','zerosize_ok'],op_flags=['readonly'],order='C',buffersize=COLOR_BLOCK_PIXELS):
  checkpoint()
  z=np.clip((np.nan_to_num(block,nan=lo)-lo)/(hi-lo),0,1)
  c=z*(len(stops)-1);i=np.minimum(c.astype(int),len(stops)-2);f=(c-i)[...,None]
  rgb=(stops[i]*(1-f)+stops[i+1]*f).astype('uint8')
  alpha=np.where(np.isfinite(block),255 if category_opacity is not None else 210,0).astype('uint8')
  if kind=='categorical':
   ids=np.nan_to_num(block,nan=0).astype('int64')
   rgb=np.stack([55+(ids*67)%175,65+(ids*103)%160,65+(ids*43)%175],axis=-1).astype('uint8')
   rgb[ids==0]=[225,220,198]
  if category_colors:
   for value,color in category_colors.items():rgb[block==float(value)]=[int(color[i:i+2],16) for i in (1,3,5)]
  if category_opacity:
   for value,opacity in category_opacity.items():alpha[block==float(value)]=round(255*opacity)
  end=offset+block.size;output[offset:end,:3]=rgb;output[offset:end,3]=alpha;offset=end
 return rgba,lo,hi

@cancellable
def _export_result(result,grid,directory):
 from .result_contracts import attach
 attach(result,grid)
 directory.mkdir(parents=True,exist_ok=True)
 tracking=result.get('extra',{}).get('tracking')
 if tracking and 'geometry' in tracking:
  geometry=tracking.pop('geometry');(directory/'patches.json').write_text(json.dumps(geometry,allow_nan=False))
  tracking['geometry_file']='patches.json'
 h,w=grid['shape'];bounds=rasterio.transform.array_bounds(h,w,grid['transform']);public=[]
 for name,layer in result.pop('layers').items():
  checkpoint()
  arr=layer.pop('data');dest=directory/(name+'.tif')
  from .storage_budget import require_space
  require_space(directory,int(arr.nbytes)*3+65536,operation='Exporting result maps')
  with rasterio.open(dest,'w',driver='COG',height=h,width=w,count=1,dtype='float32',crs=grid['crs'],transform=grid['transform'],nodata=np.nan,compress='DEFLATE') as ds:
   for _,window in ds.block_windows(1):
    checkpoint()
    rows,cols=window.toslices();ds.write(arr[rows,cols],1,window=window)
   ds.set_band_description(1,layer['label']);ds.set_band_unit(1,layer['unit'])
   ds.update_tags(1,measurement=layer['label'],units=layer['unit'],classes=json.dumps(layer.get('classes',{})),start=layer.get('start',''),end=layer.get('end',''),interpretation=layer.get('interpretation',''))
   if layer.get('trace_operation'):ds.update_tags(1,processing_stage=layer['trace_operation'],intermediate='true',trace_group=layer.get('trace_group',''))
   if layer.get('spatial_scope'):ds.update_tags(1,spatial_scope=layer['spatial_scope'])
   workflow_contract=result['extra'].get('workflow_contract',{})
   if workflow_contract:ds.update_tags(workflow_rules_version=workflow_contract.get('version',''),workflow_rules_sha256=workflow_contract.get('sha256',''))
   ds.update_tags(algorithm_version=result.get('algorithm_version',''),contract_version=result['extra']['result_passport']['contract_version'],execution_fingerprint=result['extra']['execution_fingerprint'],reference=json.dumps(result['extra']['result_passport']['reference']),record=json.dumps(result['extra']['result_passport']['record']))
   if result['extra'].get('spatial_support',{}).get('version'):ds.update_tags(spatial_contract_version=result['extra']['spatial_support']['version'])
  merc=transform_bounds(grid['crs'],'EPSG:3857',*bounds,densify_pts=21)
  preview=np.full((h,w),np.nan,'float32');t=from_bounds(*merc,w,h)
  reproject(arr,preview,src_transform=grid['transform'],src_crs=grid['crs'],src_nodata=np.nan,dst_transform=t,dst_crs='EPSG:3857',dst_nodata=np.nan,resampling=Resampling.nearest)
  checkpoint()
  rgba,lo,hi=colorize(preview,layer['kind']);Image.fromarray(rgba).save(directory/(name+'.png'))
  checkpoint()
  lonlat=transform_bounds('EPSG:3857','EPSG:4326',*merc)
  public.append({'id':name,**layer,'min':lo,'max':hi,'bounds':[[lonlat[1],lonlat[0]],[lonlat[3],lonlat[2]]],'image':name+'.png','raster':name+'.tif'})
 result['layers']=public;result['grid']={'crs':grid['crs'],'resolution_m':grid['resolution'],'shape':list(grid['shape']),'bbox':grid['bbox']};result['validation_status']='Exploratory; independent scientific accuracy has not been established.'
 workflow=result.get('extra',{}).get('workflow')
 if workflow:(directory/'workflow.json').write_text(json.dumps(workflow,indent=2,allow_nan=False)+'\n')
 (directory/'result.json').write_text(json.dumps(result,allow_nan=False,indent=2,default=str))
 return result


def export_result(result,grid,directory):
 """Commit a complete result directory atomically; never overwrite a saved run."""
 import tempfile,shutil
 checkpoint()
 directory=Path(directory)
 if directory.is_symlink() or directory.exists() and (not directory.is_dir() or any(directory.iterdir())):raise ValueError('The result folder already contains files. Start a new run; saved outputs are not overwritten.')
 from .storage_budget import require_space,export_write_estimate
 require_space(directory,export_write_estimate(result),operation='Exporting result maps')
 directory.parent.mkdir(parents=True,exist_ok=True)
 staging=Path(tempfile.mkdtemp(prefix='.export-',dir=directory.parent))
 try:
  exported=_export_result(result,grid,staging)
  checkpoint()
  if directory.exists():directory.rmdir() # Only the verified empty placeholder.
  staging.replace(directory)
  return exported
 finally:
  if staging.exists():shutil.rmtree(staging)
