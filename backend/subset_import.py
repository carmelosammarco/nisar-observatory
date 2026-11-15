"""Import self-describing native extracts without mistaking them for originals."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .catalog import ARCHIVE_MATURITIES,PRODUCTS,validate_bbox,filename_interval,group_key
from . import science
from .subset_storage import saved_items,new_folder,filename,digest,describe_folder,subset_file

def metadata(h):
 from .subsets import VERSION
 version=science.decode(h.attrs.get('observatory_subset_version',''))
 if version!=VERSION:raise ValueError('Unsupported or incomplete Observatory area extract.')
 bbox=validate_bbox(science.decode(h.attrs.get('observatory_requested_bbox',[])))
 name=science.decode(h.attrs.get('observatory_source_name',''))
 if not isinstance(name,str) or Path(name).name!=name or len(name)>240:raise ValueError('Invalid original source name in saved area.')
 product=next((p for p in PRODUCTS if '_'+p+'_' in name),None)
 if not product or f'/science/LSAR/{product}' not in h:raise ValueError('The saved area does not identify a supported NISAR product.')
 start,end=filename_interval(name,product);layers=science.datasets(h);science.select_path(layers,product)
 portable={}
 if 'observatory_subset_manifest' in h.attrs:
  raw=science.decode(h.attrs['observatory_subset_manifest'])
  if not isinstance(raw,str) or len(raw)>2*1024**2:raise ValueError('Invalid saved-area provenance size.')
  portable=json.loads(raw)
  if not isinstance(portable,dict) or portable.get('format')!='nisar-observatory-area' or portable.get('product')!=product or portable.get('subset_version')!=version or portable.get('source_name')!=name or portable.get('subset_bbox')!=bbox:raise ValueError('Saved-area metadata and embedded provenance disagree.')
 source_id=portable.get('source_id')
 source_id_known=isinstance(source_id,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,128}',source_id))
 if not source_id_known:source_id='imported-source-'+hashlib.sha256(name.encode()).hexdigest()[:32]
 original_size=portable.get('original_size_mb')
 if original_size is not None and (not isinstance(original_size,(int,float)) or not np.isfinite(original_size) or original_size<0):raise ValueError('Invalid original size in saved-area provenance.')
 geometry=portable.get('viewing_geometry',{})
 if not isinstance(geometry,dict):raise ValueError('Invalid viewing-geometry manifest.')
 omitted=portable.get('omitted_layers',[])
 if not isinstance(omitted,list):raise ValueError('Invalid omitted-layer manifest.')
 maturity=portable.get('maturity')
 return {**({'maturity':maturity} if maturity in ARCHIVE_MATURITIES else {}),'name':name,'product':product,'start':start,'end':end,'group':group_key(name,product),'subset':True,'subset_bbox':bbox,'subset_version':version,'subset_created_at':portable.get('subset_created_at'),'source_id':source_id,'source_id_origin':'embedded original identity' if source_id_known else 'derived from original filename; archive identity unavailable','catalog_id':portable.get('catalog_id') if isinstance(portable.get('catalog_id'),str) else None,'retained_layers':layers,'viewing_geometry':geometry,'omitted_layers':omitted,'original_size_mb':original_size,'bbox':bbox,'bounds':bbox,'polygons':[],'boxes':[f'{bbox[1]} {bbox[0]} {bbox[3]} {bbox[2]}'],'url':'','local':True}

def store(temp,item,root):
 checksum=digest(temp)
 for existing in saved_items(root):
  same=existing.get('content_sha256')==checksum
  if not existing.get('content_sha256') and existing['name']==item['name'] and existing['subset_bbox']==item['subset_bbox']:
   same=digest(subset_file(root,existing))==checksum
  if same:return existing
 ident='subset-'+checksum[:32];directory=new_folder(root,item['product'])
 target=directory/filename(item['name'],ident);manifest=directory/(ident+'.json')
 result={**item,'id':ident,'size_mb':temp.stat().st_size/1e6,'content_sha256':checksum,'subset_path':str(target.relative_to(root/'subsets')),'download_folder':directory.name,'imported_at':datetime.now(timezone.utc).isoformat()}
 try:
  if target.exists():raise ValueError('A different file already occupies this saved-area path.')
  metadata_temp=manifest.with_suffix('.tmp');metadata_temp.write_text(json.dumps(result,allow_nan=False))
  temp.replace(target);metadata_temp.replace(manifest);describe_folder(directory)
  return result
 finally:
  try:directory.rmdir()
  except OSError:pass
