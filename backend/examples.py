"""Curated, checksummed example inputs live outside disposable user data."""
from pathlib import Path
import json,re,shutil
from .subset_storage import digest
ROOT=Path(__file__).resolve().parents[1]/'Examples'
CASES=('P01_Mozambique','P02_Wheeler_Marsh','P03_Timber_Fire','P04_Mexico_City','P05_Venezuela','P06_Krasheninnikov','P07_Samudra_Tapu')
_CHECKS={}

def directory(ident):
 if ident not in CASES:raise ValueError('Unknown example.')
 return ROOT/ident

def definition(ident):
 from .study_stories import story
 value=json.loads((directory(ident)/'example.json').read_text())
 value['story']=story(value['tool'])
 return value

def protected_file(data_root,item):
 # Only server-curated example identifiers and bounded filenames are accepted.
 ident=item.get('example_id');base=directory(ident)/'inputs'
 name=item.get('example_file','')
 if not re.fullmatch(r'[A-Za-z0-9_.-]{1,240}\.h5',name) or name.startswith('.'):raise ValueError('Invalid example input filename.')
 path=base/name
 if not path.resolve().is_relative_to(base.resolve()):raise ValueError('Example input path escapes its folder.')
 return path

def verified(path,checksum):
 if not path.is_file() or not re.fullmatch('[a-f0-9]{64}',checksum or ''):return False
 st=path.stat();key=(str(path),st.st_size,st.st_mtime_ns,st.st_ctime_ns,checksum)
 if key not in _CHECKS:_CHECKS[key]=digest(path)==checksum
 return _CHECKS[key]

def inspect(ident):
 d=directory(ident);m=definition(ident);receipt=d/'input-manifest.json';entries=[];issues=[]
 try:stored=json.loads(receipt.read_text()).get('inputs',[])
 except (OSError,ValueError):stored=[]
 for source in m['sources']:
  candidates=[i for i in stored if i.get('source_id')==source['id'] and i.get('name')==source['name']]
  if len(candidates)!=1:issues.append(source['name']+': required input is missing');continue
  item=candidates[0]
  try:
   path=protected_file(None,{**item,'example_id':ident})
   if not verified(path,item.get('content_sha256')):raise ValueError('missing or checksum mismatch')
   if item.get('product')!=m['product'] or item.get('group')!=source['group'] or item.get('subset_bbox')!=m['request']['bbox']:raise ValueError('recipe or coverage mismatch')
   entries.append({**item,'example_id':ident,'protected_example':True,'local':True})
  except (OSError,ValueError,TypeError):issues.append(source['name']+': input could not be verified')
 return {**m,'ready':not issues and len(entries)==len(m['sources']),'input_count':len(entries),'required_count':len(m['sources']),'input_bytes':sum(protected_file(None,i).stat().st_size for i in entries),'issues':issues,'inputs':entries}

def saved_inputs():
 for ident in CASES:
  yield from inspect(ident)['inputs']

def setup(ident):
 m=inspect(ident)
 if not m['ready']:raise ValueError('Example inputs are incomplete or damaged. Restore the protected subset files before running.')
 request={**m['request'],'granules':[i['id'] for i in m['inputs']]}
 return {'example':m,'request':request,'items':m['inputs']}

def install(ident,items,data_root):
 """Archive complete extracts atomically; never remove user downloads."""
 from .subset_storage import subset_file
 d=directory(ident);m=definition(ident);entries=[]
 for source in m['sources']:
  matched=[i for i in items if i.get('source_id')==source['id'] and i['name']==source['name'] and i.get('subset_bbox')==m['request']['bbox']]
  if len(matched)!=1:raise ValueError('Missing or duplicate exact example source: '+source['name'])
  item=matched[0];path=subset_file(data_root,item)
  from .subset_import import metadata
  import h5py
  with h5py.File(path,'r') as native_file:native=metadata(native_file)
  if native['name']!=source['name'] or native['product']!=m['product'] or native['group']!=source['group'] or native['subset_bbox']!=m['request']['bbox']:raise ValueError('HDF5 provenance disagrees with the example recipe.')
  name=path.name;target=d/'inputs'/name
  if not target.exists() or digest(target)!=digest(path):
   temporary=target.with_suffix('.part');shutil.copyfile(path,temporary);temporary.replace(target)
  archived={**item,'example_id':ident,'example_file':name,'protected_example':True,'content_sha256':digest(target)}
  archived.pop('subset_path',None);archived.pop('download_folder',None)
  entries.append(archived)
 receipt={'format':'nisar-observatory-example-inputs-1','example':ident,'inputs':entries}
 temp=d/'input-manifest.tmp';temp.write_text(json.dumps(receipt,indent=2)+'\n');temp.replace(d/'input-manifest.json')
 return inspect(ident)
