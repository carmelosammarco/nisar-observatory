"""Add authenticated native GOFF viewing cubes to a new portable subset copy."""
from .execution import checkpoint
import hashlib,json,shutil
from datetime import datetime,timezone
import h5py
from . import science
from .subsets import _attrs,extract,contains
from .subset_storage import new_folder,filename,digest,describe_folder,saved_items
from .glacier_geometry import copy_cubes,VERSION

def prepare(item,bbox,cancel,progress):
 if item['product']!='GOFF':raise ValueError('Viewing-geometry preparation requires GOFF files.')
 if not item.get('subset'):
  item,_,_=extract(item,bbox,cancel,lambda *args:progress('Saving native GOFF measurements'))
 if not contains(item['subset_bbox'],bbox):raise ValueError('The selected area extends beyond this saved subset.')
 if item.get('viewing_geometry',{}).get('available'):return item,0,True
 source_id=item.get('source_id',item['id'])
 ident='subset-'+hashlib.sha256((item['id']+VERSION).encode()).hexdigest()[:32]
 old=next(saved_items(science.DATA,ident),None)
 if old and old.get('viewing_geometry',{}).get('available'):return old,0,True
 remote={**item,'id':source_id};remote.pop('subset',None);remote.pop('subset_path',None)
 if not remote.get('url'):raise ValueError('The imported subset has no original NASA URL. Search its source again and save a new GOFF area extract with geometry.')
 from .storage_budget import require_space
 require_space(science.DATA,science.source_file(item).stat().st_size+80*1024**2,operation='Preparing a new viewing-geometry subset')
 folder=new_folder(science.DATA,'GOFF');target=folder/filename(item['name'],ident);temp=folder/(ident+'.part')
 try:
  shutil.copyfile(science.source_file(item),temp)
  checkpoint(cancel)
  progress('Reading native viewing geometry from the original NASA product')
  with science.open_science(remote,cancel) as (src,stream),h5py.File(temp,'r+') as dst:
   manifest=copy_cubes(src,dst,item['subset_bbox'],_attrs,storage_path=folder)
   if not manifest['available']:raise ValueError(manifest['reason'])
   portable=json.loads(dst.attrs['observatory_subset_manifest']);portable['viewing_geometry']=manifest
   portable['omitted_layers']=[e for e in portable.get('omitted_layers',[]) if e['path'] not in manifest['paths']]
   dst.attrs['observatory_subset_manifest']=json.dumps(portable,allow_nan=False)
   dst.attrs['observatory_notice']='Local native-grid area extract with bounded height-dependent GOFF viewing geometry; not a complete NASA product.'
   transferred=stream.bytes if stream else 0
  checkpoint(cancel)
  result={**item,'id':ident,'subset_path':str(target.relative_to(science.DATA/'subsets')),'download_folder':folder.name,'viewing_geometry':manifest,'omitted_layers':portable['omitted_layers'],'subset_created_at':datetime.now(timezone.utc).isoformat(),'content_sha256':digest(temp),'size_mb':temp.stat().st_size/1e6}
  checkpoint(cancel)
  temp.replace(target);(folder/(ident+'.json')).write_text(json.dumps(result,allow_nan=False));describe_folder(folder)
  return result,transferred,False
 finally:
  if temp.exists():temp.unlink()
