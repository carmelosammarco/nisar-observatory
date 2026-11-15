"""Inspectable NISAR adapters: native window reads, common equal-area grid, explicit quality."""
from .execution import checkpoint
from pathlib import Path
from contextlib import contextmanager
import math, json,hashlib
import h5py,numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin,from_bounds
from rasterio.warp import reproject,Resampling,transform_bounds
from .access import RangeReader,DATA
from .engines import READER_VERSION
from .subset_storage import subset_file

def source_file(item,root=None):
 root=DATA if root is None else root
 if item.get('subset'):
  return subset_file(root,item)
 return root/'raw'/f"{item['id']}.h5"

@contextmanager
def open_science(item,cancel):
 local=source_file(item)
 if local.exists():
  with h5py.File(local,'r') as f:yield f,None
 else:
  if item.get('subset'):raise ValueError('Saved area file is missing. Find and save the NASA source again.')
  stream=RangeReader(item['url']);stream.cancel=cancel
  try:
   with h5py.File(stream,'r') as f:yield f,stream
  finally:stream.close()

def decode(v):
 if isinstance(v,bytes):return v.decode(errors='replace')
 if isinstance(v,np.ndarray):return [decode(x) for x in v.tolist()] if v.ndim else decode(v.item())
 if isinstance(v,np.generic):return decode(v.item())
 if isinstance(v,float) and not np.isfinite(v):return None
 return v

def target_grid(bbox,resolution=100,max_dimension=384):
 bounds=transform_bounds('EPSG:4326','EPSG:6933',*bbox,densify_pts=21)
 w,s,e,n=bounds;res=max(float(resolution),(e-w)/max_dimension,(n-s)/max_dimension)
 width=max(2,math.ceil((e-w)/res));height=max(2,math.ceil((n-s)/res))
 return {'crs':'EPSG:6933','transform':from_origin(w,n,res,res),'shape':(height,width),'resolution':res,'bbox':bbox}

def datasets(f):
 found=[]
 def visit(name,obj):
  if isinstance(obj,h5py.Dataset) and obj.ndim==2 and min(obj.shape)>1:found.append('/'+name)
 f.visititems(visit);return found

def grid_for(ds):
 g=ds.parent
 while g.name!='/':
  if 'xCoordinates' in g and 'yCoordinates' in g:return g
  g=g.parent
 raise ValueError(f'No supported geocoded grid found for {ds.name}. Range-Doppler products require a different processor.')

def native_window(f,path,bbox,preserve_integer=False):
 ds=f[path];g=grid_for(ds)
 x=np.asarray(g['xCoordinates'][:]);y=np.asarray(g['yCoordinates'][:])
 if len(x)!=ds.shape[1] or len(y)!=ds.shape[0]:raise ValueError('Layer and coordinate dimensions disagree.')
 proj=g['projection'];epsg=proj.attrs.get('epsg_code',proj[()]);epsg=int(np.asarray(epsg).item())
 w,s,e,n=transform_bounds('EPSG:4326',f'EPSG:{epsg}',*bbox,densify_pts=21)
 dx=float(np.median(np.diff(x)));dy=float(np.median(np.diff(y)))
 if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or dx==0 or dy==0 or not np.allclose(np.diff(x),dx,rtol=1e-5,atol=1e-5) or not np.allclose(np.diff(y),dy,rtol=1e-5,atol=1e-5):raise ValueError('Native coordinates must be finite, regular and strictly monotonic.')
 ix=np.where((x>=w-abs(dx))&(x<=e+abs(dx)))[0];iy=np.where((y>=s-abs(dy))&(y<=n+abs(dy)))[0]
 if not len(ix) or not len(iy):raise ValueError('This science layer has no pixels in the selected area.')
 a,b=int(iy.min()),int(iy.max())+1;c,d=int(ix.min()),int(ix.max())+1
 if (b-a)*(d-c)>8_000_000:raise ValueError('The native window exceeds 8 million pixels. Narrow the area to keep processing bounded.')
 data=np.asarray(ds[a:b,c:d],dtype='float64' if preserve_integer else 'float32')
 attrs={k:decode(v) for k,v in ds.attrs.items()}
 for key in ['_FillValue','missing_value']:
  if key in attrs:
   try:data[data==float(attrs[key])]=np.nan
   except (ValueError,TypeError):pass
 data[~np.isfinite(data)]=np.nan
 attrs['native_spacing_source_crs']=[abs(dx),abs(dy)];attrs['native_epsg']=epsg
 if dx<0:data=data[:,::-1]
 if dy>0:data=data[::-1,:]
 left=min(x[c],x[d-1])-abs(dx)/2;top=max(y[a],y[b-1])+abs(dy)/2
 return data,attrs,from_origin(left,top,abs(dx),abs(dy)),epsg

def read_window(f,path,bbox,target,quality=False,native_filter=None):
 """Screen source samples BEFORE averaging; invalid samples never contribute."""
 data,attrs,transform,epsg=native_window(f,path,bbox)
 raw=data.copy()
 if native_filter is not None:data=native_filter(data,attrs,transform,epsg)
 dest=np.full(target['shape'],np.nan,dtype='float32')
 reproject(data,dest,src_transform=transform,src_crs=f'EPSG:{epsg}',dst_transform=target['transform'],dst_crs=target['crs'],src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.nearest if quality else Resampling.average)
 if native_filter is not None:
  # Zeros are actual rejected source support, not nodata in the fraction raster.
  support=np.zeros(target['shape'],dtype='float32')
  reproject(np.isfinite(data).astype('float32'),support,src_transform=transform,src_crs=f'EPSG:{epsg}',dst_transform=target['transform'],dst_crs=target['crs'],dst_nodata=0,resampling=Resampling.average)
  minimum=float(getattr(native_filter,'minimum_fraction',.5))
  dest[(support<minimum)|~np.isfinite(support)]=np.nan
  attrs['minimum_native_valid_fraction']=minimum
  attrs['native_quality_before_aggregation']=True
  def aggregate(values):
   output=np.full(target['shape'],np.nan,'float32')
   reproject(values.astype('float32'),output,src_transform=transform,src_crs=f'EPSG:{epsg}',dst_transform=target['transform'],dst_crs=target['crs'],src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.average)
   return output
  native_filter.aux={'accepted_fraction':aggregate(np.isfinite(data)), 'missing_fraction':aggregate(~np.isfinite(raw))}
  for name,mask in getattr(native_filter,'rejections',{}).items():native_filter.aux['rejected_'+name]=aggregate(mask)
  for name,values in getattr(native_filter,'quality_values',{}).items():native_filter.aux[name]=aggregate(np.where(np.isfinite(data),values,np.nan))
  if 'raw_offset' in getattr(native_filter,'retain',[]):native_filter.aux['raw_offset']=aggregate(raw)
 return dest,attrs

def select_path(paths,product,channel='auto',component='slantRangeOffset',offset_layer='layer1'):
 if product=='GCOV':
  opts=['HHHH','VVVV','RHRH','RVRV'] if channel=='auto' else [channel]
  for o in opts:
   match=[p for p in paths if p.endswith('/'+o) and '/frequencyA/' in p]
   if match:return match[0]
 elif product=='GUNW':
  match=[p for p in paths if p.endswith('/unwrappedPhase') and '/frequencyA/' in p]
  if match:return sorted(match)[0]
 elif product=='GOFF':
  match=[p for p in paths if p.endswith('/'+offset_layer+'/'+component) and '/frequencyA/' in p]
  if match:return sorted(match)[0]
  raise ValueError(f'GOFF {offset_layer} {component} is unavailable. Choose a delivered offset layer; another layer is never substituted silently.')
 elif product=='SME2':
  preferred='/science/LSAR/SME2/grids/soilMoisture'
  if preferred in paths:return preferred
  match=[p for p in paths if 'soilmoisture' in p.lower().replace('_','') and not any(t in p.lower() for t in ['uncert','quality','flag','error'])]
  if match:return sorted(match)[0]
 raise ValueError(f'No supported {product} science layer found. Inspect the HDF5 layer inventory.')

def _load_observation(item,bbox,target,options,cancel):
 with open_science(item,cancel) as (f,stream):
  paths=datasets(f);path=select_path(paths,item['product'],options.get('channel','auto'),options.get('component','slantRangeOffset'),options.get('offset_layer','layer1'))
  if item['product']=='SME2' and options.get('soil_method','average')!='average':
   method=options['soil_method']
   if method not in ['DSG','PMI','TSR']:raise ValueError('Choose average, DSG, PMI or TSR for SME2.')
   candidate=f'/science/LSAR/SME2/grids/algorithmCandidates/{method}/soilMoisture'
   if candidate not in paths:raise ValueError(f'{method} retrieval is absent from this file.')
   path=candidate
  warnings=[];quality_paths=[];product=item['product'];parent=path.rsplit('/',1)[0]
  if item.get('subset'):warnings.append('Input is a local native-grid area extract, not a complete original NASA product; only the saved rectangle can be analyzed.')
  def screen(data,attrs,transform,epsg):
   raw=data.copy();finite=np.isfinite(raw);screen.rejections={};screen.quality_values={};screen.retain=['raw_offset'] if product=='GOFF' else []
   def reject(name,mask):
    selected=np.asarray(mask,dtype=bool)&np.isfinite(data);screen.rejections[name]=selected;data[selected]=np.nan
   def companion(qpath,packed=False):
    q,qa,qt,qe=native_window(f,qpath,bbox,preserve_integer=packed)
    if q.shape!=data.shape or qt!=transform or qe!=epsg:
     raise ValueError('Science and quality layers have different native grids; this schema needs an explicit adapter.')
    quality_paths.append(qpath)
    return q,qa
   if product=='GCOV':
    reject('nonpositive_power',data<=0)
    mp=parent+'/mask'
    if mp in paths:
     mask,_=companion(mp);reject('source_mask',(mask==0)|(mask==255)|~np.isfinite(mask))
     warnings.append('GCOV source-sample mask is applied before averaging. It is not a terrain-shadow or water classifier.')
    else:warnings.append('No GCOV mask found; only finite positive native power is screened.')
   elif product=='GUNW':
    if 'units' in attrs and str(attrs['units']).lower() not in ['radians','radian','rad']:raise ValueError('GUNW phase units must be radians; no unit conversion is guessed.')
    cp=parent+'/coherenceMagnitude';cc=parent+'/connectedComponents'
    if cp not in paths or cc not in paths:raise ValueError('GUNW coherence and connected components are required.')
    mask_path=parent.rsplit('/',1)[0]+'/mask'
    if mask_path in paths:
     packed,ma=companion(mask_path,packed=True)
     if 'subswath' not in str(ma.get('description','')).lower():raise ValueError('Unrecognized GUNW valid-sample mask encoding; an explicit adapter is required.')
     finite_mask=np.isfinite(packed)&(packed>=0)&(packed<=4294967295)&(packed==np.floor(packed));bits=np.where(finite_mask,packed,0).astype('uint32');code=bits&255
     reject('invalid_subswath',~finite_mask|(code==255)|((code//10)%10==0)|(code%10==0))
     reject('source_anomaly',(bits&0x00ffff00)!=0)
     screen.quality_values['ionosphere_interpolated']=((bits&(1<<24))!=0).astype('float32')
     attrs['source_validity_mask']={'path':mask_path,'rule':'Both reference and secondary subswath digits nonzero; fill and anomaly bits excluded before aggregation. Bit 24 records ionospheric interpolation, not an automatic rejection.','integer_precision':'Lossless uint32 decoding through float64 native read.'}
    else:warnings.append('No delivered GUNW valid-sample mask: finite phase, coherence and connected components alone cannot screen all source-edge artifacts.')
    co,_=companion(cp);comp,_=companion(cc)
    reject('coherence',(co<float(options.get('coherence',.4)))|~np.isfinite(co))
    reject('component_missing',(comp<=0)|(comp==255)|~np.isfinite(comp));screen.quality_values['coherence']=co
    vals,counts=np.unique(comp[np.isfinite(data)],return_counts=True)
    if not len(vals):raise ValueError('No coherent connected-component pixels survive quality screening.')
    keep=vals[np.argmax(counts)];reject('other_component',comp!=keep);attrs['retained_connected_component']=int(keep)
    corrections=[]
    if options.get('apply_ionosphere',False):
     correction_path=parent+'/ionospherePhaseScreen'
     if correction_path not in paths:raise ValueError('Requested ionospheric screen is absent from this phase layer.')
     correction,ca=companion(correction_path)
     if str(ca.get('units','')).lower() not in ['rad','radian','radians']:raise ValueError('Ionospheric correction units must explicitly be radians.')
     reject('missing_correction',~np.isfinite(correction));data-=correction;screen.quality_values['ionospheric_phase_correction']=correction
     corrections.append({'path':correction_path,'operation':'subtract','units':'radians','basis':'Delivered GUNW screen is not applied by default; explicit user request.'})
    attrs['correction_manifest']=corrections
    warnings.append(f'Only native connected component {int(keep)} retained before averaging. Labels are file-local; see the correction manifest for any explicitly applied screen.')
   elif product=='GOFF':
    snr=parent+'/snr'
    if snr not in paths:raise ValueError('GOFF SNR layer is required for this offset layer.')
    q,_=companion(snr);reject('snr',(q<float(options.get('snr',5)))|~np.isfinite(q));screen.quality_values['snr']=q
    units=str(attrs.get('units','')).lower()
    if units not in ['meters','metres','m','meter','metre']:raise ValueError(f'GOFF units {units!r} require conversion not safely inferred by this processor.')
    if options.get('offset_solution')=='horizontal':
     for name in ['slantRangeOffset','alongTrackOffset']:
      pair_path=parent+'/'+name
      if pair_path not in paths:raise ValueError('Horizontal speed requires both delivered range and along-track offsets from the same layer.')
      paired,_=companion(pair_path);reject('unpaired_offset',~np.isfinite(paired))
    warnings.append('Native offsets are SNR-screened before averaging. Radar components are not horizontal flow vectors.')
   else:
    qp=[p for p in paths if p.rsplit('/',1)[0]==parent and ('quality' in p.lower() or 'flag' in p.lower())]
    applied=False
    for qpath in qp:
     q,qa=companion(qpath);description=str(qa.get('description','')).lower();good=None
     if qpath.endswith('/retrievalQualityFlag') and 'least significant bit' in description and '0 = recommended' in description:
      good=np.isfinite(q)&((np.nan_to_num(q,nan=1).astype('uint32')&1)==0)
     elif qpath.endswith('/retrievalQualityFlag') and '0 means clear' in description and 'non-zero means anomaly' in description:
      good=np.isfinite(q)&(q==0)
     elif 'flag_values' in qa and 'flag_meanings' in qa:
      meanings=str(qa['flag_meanings']).split();values=np.atleast_1d(qa['flag_values']).tolist()
      allowed=[v for v,m in zip(values,meanings) if m.lower() in ('good','valid','recommended','retrieval_success')]
      if allowed:good=np.isfinite(q)&np.isin(q,allowed)
     if good is not None:reject('quality_'+qpath.rsplit('/',1)[-1],~good);applied=True
    if not applied:raise ValueError('SME2 quality flag semantics are not recognized. Inspect the file rather than assume flag zero is valid.')
    attrs['recommended_fraction_of_finite_retrievals']=float(np.isfinite(data).sum()/max(finite.sum(),1))
    if options.get('soil_allow_unrecommended'):
     data=raw;attrs['diagnostic_include_unrecommended']=True
     warnings.append('DIAGNOSTIC: includes NASA-unrecommended retrievals; not quality-screened scientific estimates.')
    reject('physical_bounds',(data<0)|(data>1))
    warnings.append('SME2 estimates are provisional and not fully calibrated. Native recommendation flags and physical bounds are applied before averaging.')
   attrs['native_finite_samples']=int(finite.sum());attrs['native_accepted_samples']=int(np.isfinite(data).sum())
   attrs['native_accepted_fraction']=float(np.isfinite(data).sum()/max(finite.sum(),1))
   return data
  screen.minimum_fraction=options.get('min_valid_fraction',.5)
  arr,attrs=read_window(f,path,bbox,target,native_filter=screen)
  if product=='GOFF':
   attrs['offset_layer']=options.get('offset_layer','layer1')
   base='/science/LSAR/GOFF/metadata/processingInformation/parameters/pixelOffsets/frequencyA/'+attrs['offset_layer']
   attrs['correlation_window_samples']={key:decode(f[base+'/'+key][()]) for key in ['slantRangeWindowSize','alongTrackWindowSize'] if base+'/'+key in f}
  if item.get('subset'):attrs['source_subset']={'bbox':item['subset_bbox'],'source_id':item['source_id'],'version':item['subset_version']}
  aux=dict(screen.aux);additional_bytes=0;additional_paths={}
  if product=='GCOV' and options.get('water_method')=='hh_hv':
   # Keep other GCOV tools usable in a panorama; P02 explicitly stops on this error.
   from .water import read_dual_sigma
   try:
    if not path.endswith('/HHHH'):raise ValueError('HH/HV method needs HH as the primary channel. Choose Auto or HHHH, or explicitly choose Single-channel.')
    converted,manifest,used=read_dual_sigma(f,parent,bbox,target,options.get('min_valid_fraction',.5))
    aux.update(converted);attrs['water_radiometry']=manifest
    quality_paths.extend(used);additional_paths.update({k:parent+'/'+v for k,v in [('water_hh_sigma_power','HHHH'),('water_hv_sigma_power','HVHV'),('water_conversion_factor','rtcGammaToSigmaFactor')]})
   except ValueError as error:attrs['water_method_error']=str(error)
  if product=='GCOV' and options.get('compare_polarizations',False):
   attrs['polarization_comparison']='matched-cross-to-co-2'
   pair=next(((parent+'/'+co,parent+'/'+cross) for co,cross in [('HHHH','HVHV'),('VVVV','VHVH')] if path in [parent+'/'+co,parent+'/'+cross] and parent+'/'+co in paths and parent+'/'+cross in paths),None)
   if pair:
    copol,cross=pair
    values=arr if path==cross else read_window(f,cross,bbox,target,native_filter=screen)[0]
    co_values=arr if path==copol else read_window(f,copol,bbox,target,native_filter=screen)[0]
    aux['cross_power']=values
    aux['cross_copol_ratio_db']=10*np.log10(np.where((values>0)&(co_values>0),values/co_values,np.nan));additional_paths.update(cross_power=cross,copol_power=copol)
   else:warnings.append('A matching co/cross-polarization pair is absent; primary-channel processing remains available.')
  if product=='GOFF':
   other=parent+('/alongTrackOffset' if path.endswith('/slantRangeOffset') else '/slantRangeOffset')
   if other in paths:
    values,va=read_window(f,other,bbox,target,native_filter=screen);aux['other_offset']=values;additional_paths['other_offset']=other
   else:warnings.append('The other radar offset component is absent; only the selected component is processed.')
  if product=='GOFF' and options.get('offset_solution')=='horizontal':
   from .glacier_geometry import interpolate
   geometry,manifest=interpolate(f,target,float(options.get('offset_geometry_height_m',0)))
   aux.update({'geometry_'+key:value for key,value in geometry.items()});attrs['viewing_geometry']=manifest
  if product=='SME2' and options.get('compare_soil_methods',False):
   for method in ['average','DSG','PMI','TSR']:
    if method==options.get('soil_method','average'):continue
    try:
     other=_load_observation(item,bbox,target,{**options,'soil_method':method,'compare_soil_methods':False},cancel)
     aux['soil_method_'+method]=other['array'];additional_bytes+=other['bytes_transferred'];additional_paths['soil_method_'+method]=other['path']
    except ValueError as e:warnings.append(f'{method} comparison unavailable: {e}')
  if not np.isfinite(arr).any():raise ValueError('No recommended SME2 pixels survived screening. Choose another area/date/method, or explicitly enable the flagged-value diagnostic view.' if product=='SME2' else 'No valid pixels survived screening in this area.')
  wavelength=None
  freq=[]
  f.visititems(lambda name,obj:freq.append('/'+name) if isinstance(obj,h5py.Dataset) and name.lower().endswith('centerfrequency') and 'frequencyA' in name else None)
  if freq:
   value=float(np.asarray(f[freq[0]][()]).item())
   if value>1e8:wavelength=299792458/value
  return {'reader_version':READER_VERSION,'array':arr,'aux':aux,'additional_paths':additional_paths,'item':item,'path':path,'attrs':attrs,'quality_paths':quality_paths,'warnings':warnings,'bytes_transferred':(stream.bytes if stream else 0)+additional_bytes,'wavelength':wavelength}

def cache_identity(item,bbox,target,options):
 """Complete grid + source generation. Never hash a multi-GiB original per read."""
 local=source_file(item)
 try:
  stat=local.stat();generation={'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'ctime_ns':stat.st_ctime_ns,'device':stat.st_dev,'inode':stat.st_ino}
 except FileNotFoundError:generation=None
 key={'schema':2,'granule':item['id'],'product':item.get('product'),'catalog_id':item.get('catalog_id'),'content_sha256':item.get('content_sha256'),'source_generation':generation,'bbox':list(bbox),'grid':{'crs':str(target['crs']),'transform':list(target['transform']),'resolution':target['resolution'],'shape':list(target['shape'])},'options':{k:options.get(k) for k in ['channel','component','offset_layer','offset_solution','offset_geometry_height_m','coherence','snr','soil_method','soil_allow_unrecommended','min_valid_fraction','apply_ionosphere','compare_polarizations','compare_soil_methods']},'reader':READER_VERSION}
 if item['product']=='GOFF' and options.get('offset_solution')=='horizontal':
  from .glacier_geometry import INTERPOLATION_VERSION
  key['geometry_adapter']=INTERPOLATION_VERSION
 if item['product']=='GCOV' and options.get('water_method')=='hh_hv':key['water_adapter']='dual-sigma-1'
 if item['product']=='GCOV' and options.get('compare_polarizations'):key['polarization_adapter']='matched-cross-to-co-2'
 return hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()

def cache_path(item,bbox,target,options):
 return DATA/'arrays'/(cache_identity(item,bbox,target,options)+'.npz')

def load_observation(item,bbox,target,options,cancel):
 checkpoint(cancel)
 identity=cache_identity(item,bbox,target,options);cache=DATA/'arrays'/(identity+'.npz')
 if cache.exists():
  try:
   with np.load(cache,allow_pickle=False) as saved:
    meta=json.loads(str(saved['metadata'].item()))
    if meta.get('cache_identity')!=identity or saved['array'].shape!=tuple(target['shape']):raise ValueError('Cached grid/source identity does not match.')
    meta['array']=saved['array'];meta['item']=item;meta['original_stream_bytes']=meta.get('bytes_transferred',0);meta['bytes_transferred']=0;meta['cache_hit']=True;meta['reader_version']=READER_VERSION;meta['aux']={k[4:]:saved[k] for k in saved.files if k.startswith('aux_')}
    checkpoint(cancel)
    return meta
  except (ValueError,OSError,KeyError):pass
 result=_load_observation(item,bbox,target,options,cancel)
 checkpoint(cancel)
 if cache_identity(item,bbox,target,options)!=identity:raise ValueError('The selected source changed while reading. Select the source again and retry; no cache was saved.')
 result['cache_identity']=identity
 from .storage_budget import require_space,array_write_estimate
 require_space(cache,array_write_estimate([result['array'],*result.get('aux',{}).values()]),operation='Saving analysis arrays')
 cache.parent.mkdir(exist_ok=True)
 from uuid import uuid4
 temp=cache.with_name(cache.stem+'.'+uuid4().hex+'.tmp')
 try:
  with temp.open('wb') as f:np.savez_compressed(f,array=result['array'],**{'aux_'+k:v for k,v in result.get('aux',{}).items()},metadata=json.dumps({k:v for k,v in result.items() if k not in ['array','aux']},default=str,allow_nan=False))
  checkpoint(cancel)
  temp.replace(cache)
 finally:temp.unlink(missing_ok=True)
 return result
