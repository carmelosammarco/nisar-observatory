"""Checksummed, read-only example outputs. These are previously computed results."""
import hashlib
import json
import re
from pathlib import Path

from fastapi import HTTPException

_CHECKS={}
SAFE_FILE=re.compile(r'^[a-z0-9_]+\.(?:json|png|tif)$')


def recipe_identity(case):
 from .examples import definition
 m=definition(case)
 return hashlib.sha256(json.dumps({'request':m['request'],'sources':m['sources']},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def recorded(case):
 from .examples import directory,definition
 from .subset_storage import digest
 try:
  base=directory(case)/'recorded'
  if base.is_symlink():raise ValueError('Invalid recorded study directory.')
  manifest=base/'manifest.json'
  if manifest.is_symlink() or manifest.stat().st_size>1024**2:raise ValueError('Invalid manifest.')
  record=json.loads(manifest.read_text())
  if record.get('format')!='nisar-recorded-study-1' or record.get('case')!=case or record.get('recipe_sha256')!=recipe_identity(case):raise ValueError('Recorded recipe does not match the tutorial.')
  files=record['files']
  if not isinstance(files,dict) or not files or len(files)>1000 or 'result.json' not in files:raise ValueError('Missing recorded result files.')
  for name,checksum in files.items():
   if not SAFE_FILE.fullmatch(name) or not re.fullmatch('[a-f0-9]{64}',checksum):raise ValueError('Invalid recorded filename or digest.')
   path=base/name
   if path.is_symlink() or not path.is_file():raise ValueError('Missing recorded file.')
   stat=path.stat();key=(str(path),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,checksum)
   if key not in _CHECKS:_CHECKS[key]=digest(path)==checksum
   if not _CHECKS[key]:raise ValueError('Recorded file checksum mismatch.')
  result=json.loads((base/'result.json').read_text())
  if result.get('project')!=definition(case)['tool']:raise ValueError('Recorded tool mismatch.')
  for layer in result['layers']:
   if layer['id']+'.tif' not in files or layer['id']+'.png' not in files:raise ValueError('Incomplete recorded maps.')
  return record,result,base
 except (OSError,ValueError,KeyError,TypeError):
  raise HTTPException(404,'The recorded result is missing, outdated or damaged. The tutorial remains available; run it yourself using its protected inputs.') from None


def result_directory(root,ident,pid):
 if ident.startswith('example-'):
  case=ident[len('example-'):]
  _,result,base=recorded(case)
  if result['project']!=pid:raise HTTPException(404,'Recorded product does not match this example.')
  return base
 if not re.fullmatch(r'[a-f0-9]{32}',ident) or pid not in ('LAB','P01','P02','P03','P04','P05','P06','P07'):raise HTTPException(404,'Saved result not found.')
 base=Path(root)/ident/pid
 if base.is_symlink() or not base.resolve().is_relative_to(Path(root).resolve()):raise HTTPException(404,'Saved result not found.')
 return base


def install(api):
 from .examples import definition

 @api.get('/api/examples/{case}/recorded')
 def detail(case:str):
  record,result,_=recorded(case);m=definition(case);ident='example-'+case
  return {'id':ident,'kind':'recorded','status':'completed','created_at':record['computed_at'],
          'message':'Previously computed from protected example inputs. Opening this view does not run processing.',
          'request':m['request'],'recorded_case':case,
          'results':{result['project']:{'status':'exploratory','title':result['title'],'url':f'/api/artifacts/{ident}/{result["project"]}/result.json'}},
          'receipt':{'application_version':record.get('application_version'),'recipe_sha256':record['recipe_sha256'],'file_count':len(record['files'])}}
