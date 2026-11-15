"""Offline backup/restore integrity, size limits, path safety and no-overwrite gates."""
import hashlib,json,os,stat,subprocess,sys,zipfile
from pathlib import Path
import pytest
from backend.workspace_backup import backup_runtime,verify_backup,restore_backup,inventory,BackupError,FORMAT
from backend.runtime_storage import RuntimeLease

ROOT=Path(__file__).resolve().parents[1]

def profile(tmp_path):
 root=tmp_path/'data';root.mkdir()
 values={'raw/source.h5':b'HDF5 fixture','subsets/GCOV_date/subset.h5':b'native subset','subsets/GCOV_date/subset.json':b'{"subset":true}','workflows/id.json':b'{"name":"my recipe"}','jobs/ab/LAB/result.json':b'{"value":1}','jobs/ab/LAB/map.tif':b'Raster fixture','arrays/cached.npz':b'regenerable','notes.txt':b'outside runtime allowlist','.env':b'not app data'}
 for name,data in values.items():
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 return root,values

def fake_archive(path,records,manifest=None,extra=()):
 files={name:{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in records.items()}
 content=manifest or {'format':FORMAT,'version':1,'files':files}
 with zipfile.ZipFile(path,'w') as archive:
  for name,data in records.items():archive.writestr(name,data)
  for info,data in extra:archive.writestr(info,data)
  archive.writestr('manifest.json',json.dumps(content))
 return files

@pytest.mark.parametrize('cache',[False,True])
def test_roundtrip_verifies_every_byte_and_keeps_ordinary_data(tmp_path,cache):
 root,values=profile(tmp_path);original={p:p.read_bytes() for p in root.rglob('*') if p.is_file()};output=tmp_path/'backup.zip'
 report=backup_runtime(root,output,cache);checked=verify_backup(output)
 assert checked['verified'] and checked['files']==report['files']
 assert ('arrays/cached.npz' in checked['manifest']['files'])==cache
 assert '.env' in report['excluded'] and 'notes.txt' in report['excluded']
 assert all(p.read_bytes()==value for p,value in original.items())
 destination=tmp_path/'restored';restored=restore_backup(output,destination)
 assert restored['restored'] and not (destination/'.restore-incomplete').exists()
 for name in checked['manifest']['files']:assert (destination/name).read_bytes()==values[name]
 assert not (destination/'.env').exists() and not (destination/'notes.txt').exists()
 assert json.loads((destination/'restore-record.json').read_text())['files']==checked['files']
 with RuntimeLease(destination):pass
 assert not list(tmp_path.glob('.nisar-*'))

def test_live_runtime_cannot_be_backed_up(tmp_path):
 root,_=profile(tmp_path)
 with RuntimeLease(root):
  with pytest.raises(RuntimeError,match='Another server owns'):backup_runtime(root,tmp_path/'backup.zip')
 assert not (tmp_path/'backup.zip').exists()

def test_no_overwrite_or_recursive_output(tmp_path):
 root,_=profile(tmp_path);output=tmp_path/'existing.zip';output.write_bytes(b'keep')
 with pytest.raises(BackupError,match='already exists'):backup_runtime(root,output)
 assert output.read_bytes()==b'keep'
 with pytest.raises(BackupError,match='outside'):backup_runtime(root,root/'snapshot.zip')
 valid=tmp_path/'valid.zip';backup_runtime(root,valid)
 with pytest.raises(BackupError,match='new folder'):restore_backup(valid,root)
 assert (root/'raw/source.h5').read_bytes()==b'HDF5 fixture'

def test_snapshot_refuses_symbolic_and_hard_links(tmp_path):
 root,_=profile(tmp_path);target=tmp_path/'external';target.write_bytes(b'private')
 link=root/'raw/link.h5';link.symlink_to(target)
 with pytest.raises(BackupError,match='symbolic'):backup_runtime(root,tmp_path/'snapshot.zip')
 link.unlink();os.link(target,link)
 with pytest.raises(BackupError,match='hard links'):backup_runtime(root,tmp_path/'snapshot.zip')
 assert target.read_bytes()==b'private'

@pytest.mark.parametrize('name',['../escape.h5','/raw/absolute.h5','raw/../escape.h5','raw\\escape.h5','raw/C:escape.h5','raw/CON.h5','raw/a.h5.','raw/a.h5 ','raw//a.h5','unknown/file.json','.env','raw/.secret.h5'])
def test_restore_rejects_unsafe_names_without_creating_destination(tmp_path,name):
 archive=tmp_path/'bad.zip';fake_archive(archive,{name:b'value'});destination=tmp_path/'new'
 with pytest.raises(BackupError):restore_backup(archive,destination)
 assert not destination.exists() and not list(tmp_path.glob('.nisar-restore-*'))

def test_corruption_and_size_limit_fail_before_writes(tmp_path):
 archive=tmp_path/'bad.zip';data={'raw/source.h5':b'good'};files=fake_archive(archive,data)
 files['raw/source.h5']['sha256']='0'*64
 fake_archive(archive,data,{'format':FORMAT,'version':1,'files':files})
 with pytest.raises(BackupError,match='checksum'):restore_backup(archive,tmp_path/'no')
 assert not (tmp_path/'no').exists()
 fake_archive(archive,data)
 with pytest.raises(BackupError,match='size limit'):restore_backup(archive,tmp_path/'no',max_bytes=3)
 assert not (tmp_path/'no').exists()

def test_manifest_mismatch_duplicates_and_archive_symlink_are_rejected(tmp_path):
 path=tmp_path/'bad.zip';fake_archive(path,{'raw/a.h5':b'a'},extra=[('raw/extra.h5',b'b')])
 with pytest.raises(BackupError,match='disagree'):verify_backup(path)
 with pytest.warns(UserWarning):fake_archive(path,{'raw/a.h5':b'a'},extra=[('raw/a.h5',b'a')])
 with pytest.raises(BackupError,match='duplicate'):verify_backup(path)
 info=zipfile.ZipInfo('raw/a.h5');info.external_attr=(stat.S_IFLNK|0o777)<<16
 fake_archive(path,{},manifest={'format':FORMAT,'version':1,'files':{'raw/a.h5':{'size':3,'sha256':hashlib.sha256(b'../').hexdigest()}}},extra=[(info,b'../')])
 with pytest.raises(BackupError,match='regular file'):verify_backup(path)

def test_failed_publication_preserves_existing_backup_and_removes_only_own_temp(tmp_path,monkeypatch):
 import backend.workspace_backup as backup
 root,_=profile(tmp_path);output=tmp_path/'snapshot.zip'
 def concurrent_writer(source,destination):
  destination.write_bytes(b'other backup');raise FileExistsError('concurrent creator')
 monkeypatch.setattr(backup.os,'link',concurrent_writer)
 with pytest.raises(FileExistsError):backup_runtime(root,output)
 assert output.read_bytes()==b'other backup' and not list(tmp_path.glob('.nisar-backup-*'))

def test_interrupted_restore_cannot_be_started_as_a_runtime(tmp_path,monkeypatch):
 import backend.workspace_backup as backup
 root,_=profile(tmp_path);archive=tmp_path/'snapshot.zip';backup_runtime(root,archive)
 original=backup.atomic_json
 def fail_record(path,data):
  if path.name=='restore-record.json':raise OSError('simulated disk fault')
  return original(path,data)
 monkeypatch.setattr(backup,'atomic_json',fail_record);destination=tmp_path/'partial'
 with pytest.raises(OSError):restore_backup(archive,destination)
 assert (destination/'.restore-incomplete').exists()
 with pytest.raises(RuntimeError,match='incomplete restore'):RuntimeLease(destination).acquire()
 assert (root/'raw/source.h5').read_bytes()==b'HDF5 fixture'
 assert not list(tmp_path.glob('.nisar-restore-*'))

def test_cli_reports_verified_count_and_error_exit(tmp_path):
 root,_=profile(tmp_path);archive=tmp_path/'snapshot.zip';script=ROOT/'scripts/workspace_backup.py'
 for args in [['create','--runtime',str(root),'--output',str(archive)],['verify',str(archive)],['restore',str(archive),'--destination',str(tmp_path/'new')]]:
  result=subprocess.run([sys.executable,'-B',str(script),*args],capture_output=True,text=True,timeout=15)
  assert result.returncode==0,result.stderr
  assert json.loads(result.stdout)['files']==6
 result=subprocess.run([sys.executable,'-B',str(script),'restore',str(archive),'--destination',str(root)],capture_output=True,text=True,timeout=15)
 assert result.returncode!=0 and 'existing runtime data is never overwritten' in result.stderr
