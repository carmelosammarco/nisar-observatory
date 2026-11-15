"""Native geocoded area extracts; never presented as complete NASA products."""
from .execution import checkpoint
import hashlib,json
from datetime import datetime,timezone
import h5py,numpy as np
from rasterio.warp import transform_bounds
from . import science
from .catalog import validate_bbox
from .subset_storage import saved_items,new_folder,filename,digest,describe_folder

VERSION='area-1'
MAX_ARRAY_BYTES=512*1024**2

def contains(outer,inner):
 return outer[0]<=inner[0]<inner[2]<=outer[2] and outer[1]<=inner[1]<inner[3]<=outer[3]

def subset_id(item,bbox):
 source=item.get('source_id',item['id'])
 digest=hashlib.sha256(json.dumps([VERSION,source,[float(v) for v in bbox]],separators=(',',':')).encode()).hexdigest()[:32]
 return 'subset-'+digest

def saved_subset(item,bbox):
 ident=subset_id(item,bbox)
 exact=next(saved_items(science.DATA,ident),None)
 if exact and exact.get('subset_bbox')==[float(v) for v in bbox]:return exact
 # Imported self-contained files use a content identity but keep their original source.
 return next((s for s in saved_items(science.DATA) if s.get('source_id')==item.get('source_id',item['id']) and s.get('subset_bbox')==[float(v) for v in bbox] and s.get('subset_version')==VERSION),None)

def _attrs(source,dest):
 # HDF5 references point into the source file and must not be copied as references.
 for key,value in source.attrs.items():
  if key in ['DIMENSION_LIST','REFERENCE_LIST','CLASS','NAME']:continue
  dtype=np.asarray(value).dtype
  if h5py.check_dtype(ref=dtype) or dtype.kind=='O' and not isinstance(value,(str,bytes)):continue
  dest.attrs[key]=value

def extract(item,bbox,cancel,progress,folder=None):
 bbox=validate_bbox(bbox)
 existing=saved_subset(item,bbox)
 if existing:return existing,0,True
 if item.get('subset') and not contains(item['subset_bbox'],bbox):raise ValueError('This rectangle extends beyond the saved area. Find the original NASA source to save a larger area.')
 from .storage_budget import require_space
 require_space(science.DATA,operation='Saving an area subset')
 ident=subset_id(item,bbox);directory=folder or new_folder(science.DATA,item['product'])
 target=directory/filename(item['name'],ident);temp=directory/(ident+'.part');manifest=directory/(ident+'.json')
 created_at=datetime.now(timezone.utc).isoformat()
 copied=[];omitted=[];total=0;metadata_bytes=0;transferred=0
 try:
  with science.open_science(item,cancel) as (source,stream),h5py.File(temp,'w') as output:
   product_root=f"/science/LSAR/{item['product']}/grids"
   paths=science.datasets(source);windows={};grids={}
   for path in paths:
    if not path.startswith(product_root+'/'):continue
    ds=source[path]
    try:
     g=science.grid_for(ds)
     if g.name not in windows:
      x=np.asarray(g['xCoordinates'][:]);y=np.asarray(g['yCoordinates'][:])
      if min(len(x),len(y))<2:raise ValueError('Native grid needs two coordinates per axis.')
      dx=float(np.median(np.diff(x)));dy=float(np.median(np.diff(y)))
      if not np.isfinite(x).all() or not np.isfinite(y).all() or dx==0 or dy==0 or not np.allclose(np.diff(x),dx,rtol=1e-5,atol=1e-5) or not np.allclose(np.diff(y),dy,rtol=1e-5,atol=1e-5):raise ValueError('Native grid is not regular.')
      p=g['projection'];epsg=int(np.asarray(p.attrs.get('epsg_code',p[()])).item())
      w,s,e,n=transform_bounds('EPSG:4326',f'EPSG:{epsg}',*bbox,densify_pts=21)
      ix=np.where((x>=w-abs(dx))&(x<=e+abs(dx)))[0];iy=np.where((y>=s-abs(dy))&(y<=n+abs(dy)))[0]
      if min(len(ix),len(iy))<2:raise ValueError('No usable native window in this grid.')
      a,b,c,d=int(iy.min()),int(iy.max())+1,int(ix.min()),int(ix.max())+1
      if (b-a)*(d-c)>8_000_000:raise ValueError('Native window exceeds 8 million pixels. Select a smaller rectangle.')
      windows[g.name]=(a,b,c,d);grids[g.name]=(x,y)
     a,b,c,d=windows[g.name];x,y=grids[g.name]
     if ds.shape!=(len(y),len(x)):raise ValueError('Layer dimensions differ from its grid.')
     copied.append(path)
    except (ValueError,KeyError,TypeError) as error:
     # A supported science layer must be present below; incompatible auxiliary grids are recorded.
     omitted.append({'path':path,'reason':str(error)})
   if not copied:raise ValueError('No supported geocoded science layers overlap this rectangle. Try a smaller area inside the file footprint.')
   science.select_path(copied,item['product'])
   planned_bytes=0
   for path in copied:
    ds=source[path];a,b,c,d=windows[science.grid_for(ds).name];planned_bytes+=(b-a)*(d-c)*ds.dtype.itemsize
   if planned_bytes>MAX_ARRAY_BYTES:raise ValueError('Area extract exceeds the 512 MiB uncompressed science-layer budget. Draw a smaller rectangle.')
   require_space(directory,int(planned_bytes*1.05)+80*1024**2,operation='Saving an area subset')
   def groups(name,obj):
    if isinstance(obj,h5py.Group):_attrs(obj,output.require_group('/'+name))
   _attrs(source,output);source.visititems(groups)
   # Keep bounded scalar/1D metadata, including timestamps, units, center frequency and CRS.
   small=[]
   def collect(name,obj):
    if isinstance(obj,h5py.Dataset):
     if obj.ndim<=1:small.append('/'+name)
     elif '/'+name not in copied and not any(e['path']=='/'+name for e in omitted):omitted.append({'path':'/'+name,'reason':'Non-geocoded or multidimensional auxiliary dataset is outside this native-grid extract.'})
   source.visititems(collect)
   for path in small:
    checkpoint(cancel)
    ds=source[path];parent=path.rsplit('/',1)[0];name=path.rsplit('/',1)[-1]
    if h5py.check_dtype(ref=ds.dtype):
     omitted.append({'path':path,'reason':'HDF5 object reference cannot be reused outside the source file.'});continue
    if name in ['xCoordinates','yCoordinates'] and parent.startswith(product_root):
     if parent not in windows:continue
     a,b,c,d=windows[parent];values=ds[c:d] if name=='xCoordinates' else ds[a:b]
    else:
     size=ds.size*max(ds.dtype.itemsize,8)
     if size>1024**2 or metadata_bytes+size>16*1024**2:
      omitted.append({'path':path,'reason':'Outside bounded scalar/1D metadata budget.'});continue
     metadata_bytes+=size;values=ds[()]
    out=output.create_dataset(path,data=values);_attrs(ds,out)
   for index,path in enumerate(copied):
    checkpoint(cancel)
    ds=source[path];g=science.grid_for(ds);a,b,c,d=windows[g.name]
    total+=(b-a)*(d-c)*ds.dtype.itemsize
    if total>MAX_ARRAY_BYTES:raise ValueError('Area extract exceeds the 512 MiB uncompressed science-layer budget. Draw a smaller rectangle.')
    progress(index,len(copied),stream.bytes if stream else 0)
    require_space(directory,int((b-a)*(d-c)*ds.dtype.itemsize*1.05)+1024**2,operation='Saving an area subset')
    out=output.create_dataset(path,data=ds[a:b,c:d],compression='gzip',shuffle=True);_attrs(ds,out)
   viewing_geometry={}
   if item['product']=='GOFF':
    from .glacier_geometry import copy_cubes
    viewing_geometry=copy_cubes(source,output,bbox,_attrs,storage_path=directory)
    if viewing_geometry.get('available'):omitted=[e for e in omitted if e['path'] not in viewing_geometry['paths']]
   output.attrs['observatory_subset_version']=VERSION
   output.attrs['observatory_requested_bbox']=bbox
   output.attrs['observatory_source_name']=item['name']
   output.attrs['observatory_notice']='Local native-grid extract, not a complete official NISAR product. Includes a one-cell reading buffer; analyses use the requested WGS84 rectangle. GOFF viewing cubes are retained when delivered; other non-geocoded multidimensional auxiliary datasets are omitted.'
   portable={'format':'nisar-observatory-area','subset_version':VERSION,'source_id':item.get('source_id',item['id']),'catalog_id':item.get('catalog_id',item.get('source_id',item['id'])),'source_name':item['name'],**({'maturity':item['maturity']} if item.get('maturity') else {}),'product':item['product'],'start':item['start'],'end':item['end'],'group':item['group'],'subset_bbox':bbox,'subset_created_at':created_at,'retained_layers':copied,'viewing_geometry':viewing_geometry,'omitted_layers':omitted,'original_size_mb':item.get('original_size_mb',item.get('size_mb'))}
   output.attrs['observatory_subset_manifest']=json.dumps(portable,allow_nan=False)
   transferred=stream.bytes if stream else 0
  checkpoint(cancel)
  result={**item,'id':ident,'source_id':item.get('source_id',item['id']),'catalog_id':item.get('catalog_id',item.get('source_id',item['id'])),'subset':True,'subset_bbox':bbox,'bbox':bbox,'bounds':bbox,'local':True,'subset_version':VERSION,'subset_created_at':created_at,'subset_path':str(target.relative_to(science.DATA/'subsets')),'download_folder':directory.name,'content_sha256':digest(temp),'retained_layers':copied,'viewing_geometry':viewing_geometry,'omitted_layers':omitted,'size_mb':temp.stat().st_size/1e6,'original_size_mb':item.get('original_size_mb',item.get('size_mb'))}
  # Replace broad discovery polygons with the saved area's boundary.
  result['geometry']={'type':'Polygon','coordinates':[[[bbox[0],bbox[1]],[bbox[2],bbox[1]],[bbox[2],bbox[3]],[bbox[0],bbox[3]],[bbox[0],bbox[1]]]]}
  result.pop('geometries',None);result['polygons']=[];result['boxes']=[f'{bbox[1]} {bbox[0]} {bbox[3]} {bbox[2]}']
  checkpoint(cancel)
  target_meta=manifest.with_suffix('.tmp');target_meta.write_text(json.dumps(result,allow_nan=False));temp.replace(target);target_meta.replace(manifest);describe_folder(directory)
  return result,transferred,False
 finally:
  if temp.exists():temp.unlink()
  try:directory.rmdir() # Remove only an empty folder created for an unsuccessful extract.
  except OSError:pass
