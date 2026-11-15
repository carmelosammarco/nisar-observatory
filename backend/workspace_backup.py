"""Offline, checksummed runtime snapshots. No credentials, executable restore or overwrite."""
from datetime import datetime,timezone
import hashlib,json,os,re,shutil,stat,tempfile,zipfile
from pathlib import Path,PurePosixPath
from .runtime_storage import RuntimeLease,atomic_json
from .storage_budget import require_space

FORMAT='nisar-observatory-runtime'
LIMIT=32*1024**3
ALLOW={'raw':{'.h5','.json'},'subsets':{'.h5','.json'},'jobs':{'.json','.png','.tif','.csv','.geojson','.md'},'workflows':{'.json'},'arrays':{'.npz'}}
MARKER='.restore-incomplete'
class BackupError(ValueError):pass


def safe_name(name):
 if not isinstance(name,str) or len(name)>1024 or '\\' in name or '\x00' in name:raise BackupError('Unsafe snapshot member path.')
 path=PurePosixPath(name)
 if path.is_absolute() or str(path)!=name or len(path.parts)<2 or any(p in ('','..','.') or ':' in p or p.endswith((' ','.')) or p.startswith('.') for p in path.parts):raise BackupError('Unsafe snapshot member path.')
 if any(re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?',p,re.I) for p in path.parts):raise BackupError('Snapshot contains a nonportable filename.')
 if path.parts[0] not in ALLOW or path.suffix.lower() not in ALLOW[path.parts[0]]:raise BackupError('Snapshot contains a file outside the supported runtime data types.')
 return path


def inventory(root,include_cache=False):
 root=Path(root).resolve();files=[];excluded=[]
 if not root.is_dir():raise BackupError('Runtime folder does not exist.')
 for top in sorted(root.iterdir()):
  if top.name not in ALLOW or top.name=='arrays' and not include_cache:
   if top.name not in ('.runtime.lock','.gitkeep'):excluded.append(top.name)
   continue
  if top.is_symlink() or not top.is_dir():raise BackupError('Supported runtime directories must be real directories, not links.')
  for path in sorted(top.rglob('*')):
   if path.is_symlink():raise BackupError('Snapshot refuses symbolic links; keep source data in regular files.')
   if path.is_dir():continue
   relative=path.relative_to(root).as_posix()
   if any(p.startswith('.') for p in path.relative_to(root).parts) or path.suffix.lower() not in ALLOW[top.name]:excluded.append(relative);continue
   safe_name(relative);info=path.stat()
   if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise BackupError('Snapshot refuses special files and hard links.')
   files.append((relative,path,info))
 return files,excluded


def _sync_directory(path):
 if os.name!='nt':
  fd=os.open(path,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
  try:os.fsync(fd)
  finally:os.close(fd)

def _signature(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)

def backup_runtime(root,output,include_cache=False):
 root=Path(root).expanduser().resolve();output=Path(output).expanduser().absolute()
 if not root.is_dir():raise BackupError('Runtime folder does not exist.')
 if output.exists() or output.is_symlink():raise BackupError('Backup output already exists; choose a new filename.')
 if not output.parent.is_dir():raise BackupError('Create the backup output directory first.')
 if output.resolve().is_relative_to(root):raise BackupError('Store the backup outside its runtime folder.')
 with RuntimeLease(root):
  files,excluded=inventory(root,include_cache)
  if len(files)>100000:raise BackupError('Runtime snapshot exceeds the 100,000-file limit. Split profiles or back up their filesystem separately.')
  total=sum(info.st_size for _,_,info in files)
  require_space(output,int(total*1.02)+16*1024**2,operation='Creating a workspace backup')
  fd,temp=tempfile.mkstemp(prefix='.nisar-backup-',suffix='.tmp',dir=output.parent);os.close(fd)
  manifest={'format':FORMAT,'version':1,'created_at':datetime.now(timezone.utc).isoformat(),'includes_cache':bool(include_cache),'scope':'Ordinary runtime inputs, workflows and runs. Protected Examples and application source are backed up separately. No RAM Earthdata session is included.','files':{}}
  try:
   with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
    for name,path,before in files:
     digest=hashlib.sha256();count=0
     with path.open('rb') as stream,archive.open(name,'w',force_zip64=True) as member:
      if _signature(os.fstat(stream.fileno()))!=_signature(before):raise BackupError('A runtime file changed during backup; stop other file writers and retry.')
      while chunk:=stream.read(1024**2):
       require_space(output,len(chunk)+65536,operation='Creating a workspace backup')
       member.write(chunk);digest.update(chunk);count+=len(chunk)
      if _signature(os.fstat(stream.fileno()))!=_signature(before) or count!=before.st_size:raise BackupError('A runtime file changed during backup; no snapshot was published.')
     manifest['files'][name]={'size':count,'sha256':digest.hexdigest()}
    payload=json.dumps(manifest,indent=2,allow_nan=False).encode()
    if len(payload)>16*1024**2:raise BackupError('Snapshot manifest exceeds 16 MiB; no archive was published.')
    archive.writestr('manifest.json',payload)
   with open(temp,'rb') as stream:os.fsync(stream.fileno())
   # Publish without overwriting another backup, including a concurrent creator.
   os.link(temp,output);_sync_directory(output.parent)
   return {'archive':str(output),'files':len(files),'uncompressed_bytes':total,'archive_bytes':output.stat().st_size,'excluded':excluded,'includes_cache':bool(include_cache)}
  finally:Path(temp).unlink(missing_ok=True)


def _unique_object(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise BackupError('Snapshot metadata has duplicate keys.')
  result[key]=value
 return result


def _open_manifest(archive,max_bytes):
 if not isinstance(max_bytes,int) or max_bytes<0:raise BackupError('Restore size limit must be a nonnegative byte count.')
 members=archive.infolist();names=[info.filename for info in members]
 if len(names)!=len(set(names)) or len(names)>100001:raise BackupError('Snapshot contains duplicate or too many members.')
 if names.count('manifest.json')!=1:raise BackupError('Snapshot has no unique manifest.')
 meta=archive.getinfo('manifest.json')
 if meta.file_size>16*1024**2:raise BackupError('Snapshot manifest exceeds 16 MiB.')
 manifest=json.loads(archive.read(meta),object_pairs_hook=_unique_object)
 if not isinstance(manifest,dict) or manifest.get('format')!=FORMAT or (type(manifest.get('version')) is not int or manifest['version']!=1) or not isinstance(manifest.get('files'),dict):raise BackupError('Unsupported snapshot manifest.')
 files=manifest['files']
 if set(files)!=(set(names)-{'manifest.json'}):raise BackupError('Snapshot files and manifest disagree.')
 total=0
 for name,record in files.items():
  safe_name(name);info=archive.getinfo(name);mode=info.external_attr>>16
  if info.is_dir() or stat.S_IFMT(mode) not in (0,stat.S_IFREG):raise BackupError('Snapshot member must be a regular file.')
  if not isinstance(record,dict) or type(record.get('size')) is not int or record['size']<0 or not isinstance(record.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',record['sha256']):raise BackupError('Invalid snapshot file metadata.')
  if info.file_size!=record['size']:raise BackupError('Snapshot member size disagrees with its manifest.')
  total+=record['size']
  if total>max_bytes:raise BackupError('Snapshot exceeds the configured uncompressed size limit.')
 return manifest,total


def _copy_checked(archive,name,record,destination=None):
 digest=hashlib.sha256();count=0
 with archive.open(name) as source:
  while chunk:=source.read(1024**2):
   count+=len(chunk)
   if count>record['size']:raise BackupError('Snapshot member exceeded its declared size.')
   digest.update(chunk)
   if destination is not None:destination.write(chunk)
 if count!=record['size'] or digest.hexdigest()!=record['sha256']:raise BackupError('Snapshot checksum verification failed: '+name)


def verify_backup(path,max_bytes=LIMIT):
 try:
  with zipfile.ZipFile(path) as archive:
   manifest,total=_open_manifest(archive,max_bytes)
   for name,record in manifest['files'].items():_copy_checked(archive,name,record)
  return {'verified':True,'files':len(manifest['files']),'uncompressed_bytes':total,'manifest':manifest}
 except (zipfile.BadZipFile,KeyError,TypeError,json.JSONDecodeError,UnicodeDecodeError) as error:raise BackupError('Snapshot is malformed or unreadable.') from error


def restore_backup(path,destination,max_bytes=LIMIT):
 destination=Path(destination).expanduser().absolute()
 if destination.exists() or destination.is_symlink():raise BackupError('Restore requires a new folder; existing runtime data is never overwritten.')
 if not destination.parent.is_dir():raise BackupError('Create the restore destination parent directory first.')
 checked=verify_backup(path,max_bytes);manifest=checked['manifest']
 require_space(destination,checked['uncompressed_bytes']+16*1024**2,operation='Restoring a workspace backup')
 staging=Path(tempfile.mkdtemp(prefix='.nisar-restore-',dir=destination.parent))
 try:
  with zipfile.ZipFile(path) as archive:
   second,total=_open_manifest(archive,max_bytes)
   if second!=manifest:raise BackupError('Snapshot changed between verification and restoration.')
   for name,record in manifest['files'].items():
    target=staging.joinpath(*safe_name(name).parts);target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    require_space(destination,record['size']+65536,operation='Restoring a workspace backup')
    with target.open('xb') as output:
     _copy_checked(archive,name,record,output);output.flush();os.fsync(output.fileno())
    target.chmod(0o600)
  for folder in sorted((p for p in staging.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):_sync_directory(folder)
  _sync_directory(staging)
  # Exclusive mkdir is the no-overwrite gate. A lease blocks startup while publishing.
  destination.mkdir(mode=0o700)
  with RuntimeLease(destination):
   marker=destination/MARKER;atomic_json(marker,{'state':'incomplete','message':'Restore publication is not complete. Do not start the app with this folder.'})
   for child in staging.iterdir():child.rename(destination/child.name)
   atomic_json(destination/'restore-record.json',{'format':FORMAT,'restored_at':datetime.now(timezone.utc).isoformat(),'files':checked['files'],'uncompressed_bytes':checked['uncompressed_bytes'],'verified_file_manifest':manifest['files']})
   marker.unlink();_sync_directory(destination);_sync_directory(destination.parent)
  return {'restored':True,'runtime_directory':str(destination),'files':checked['files'],'uncompressed_bytes':checked['uncompressed_bytes']}
 finally:shutil.rmtree(staging)
