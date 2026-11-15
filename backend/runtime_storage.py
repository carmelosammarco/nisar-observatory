"""Process ownership and durable job records, without storing Earthdata sessions."""
from datetime import datetime,timezone
import json,os,re,stat,tempfile
from pathlib import Path

JOB_ID=re.compile(r'^[a-f0-9]{32}$')


def runtime_directory(default):
    value=os.environ.get('NISAR_DATA_DIR')
    directory=Path(value).expanduser() if value else Path(default)
    if value and not directory.is_absolute():raise ValueError('NISAR_DATA_DIR must be an absolute directory path.')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not directory.is_dir():raise ValueError('Runtime storage must be a directory.')
    return directory.resolve()


class RuntimeLease:
    """An OS-held advisory lock. A stale PID file never decides ownership."""
    def __init__(self,directory):self.path=Path(directory)/'.runtime.lock';self.fd=None
    def acquire(self):
        if (self.path.parent/'.restore-incomplete').exists() or (self.path.parent/'.restore-incomplete').is_symlink():raise RuntimeError('This runtime folder has an incomplete restore. Keep it for review and restore the verified backup into a new folder before starting the app.')
        if self.fd is not None:raise RuntimeError('Runtime ownership is already held by this lease.')
        if self.path.is_symlink():raise RuntimeError('Runtime lock must be a regular file, not a symbolic link.')
        fd=os.open(self.path,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise RuntimeError('Runtime lock must be a regular storage file without hard links.')
            if os.name=='nt':
                import msvcrt
                if info.st_size==0:os.write(fd,b' ')
                os.lseek(fd,0,os.SEEK_SET);msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.fd=fd
            payload=json.dumps({'format':1,'pid':os.getpid(),'acquired_at':datetime.now(timezone.utc).isoformat()}).encode()
            os.lseek(fd,0,os.SEEK_SET);os.write(fd,payload);os.ftruncate(fd,len(payload));os.fsync(fd)
            return self
        except OSError as error:
            os.close(fd);self.fd=None
            if error.errno in (11,13,35,36):raise RuntimeError('Another server owns this runtime folder. Stop that instance or choose a separate NISAR_DATA_DIR; do not use multiple workers on shared storage.') from None
            raise
        except BaseException:
            os.close(fd);self.fd=None;raise
    def release(self):
        if self.fd is None:return
        fd=self.fd;self.fd=None
        try:
            if os.name=='nt':
                import msvcrt
                os.lseek(fd,0,os.SEEK_SET);msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_UN)
        finally:os.close(fd)
        # Never unlink: another process may already hold an open handle to it.
    def __enter__(self):return self.acquire()
    def __exit__(self,*exc):self.release()


def atomic_json(path,value):
    """Flush a complete job record, then replace its name atomically."""
    path=Path(path)
    if path.is_symlink():raise ValueError('Job records cannot be symbolic links.')
    payload=json.dumps(value,default=str,allow_nan=False).encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix='.job-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
        if os.name!='nt':
            directory_fd=os.open(path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
    finally:Path(name).unlink(missing_ok=True)


def guarded_json(path,value):
    """Durable ordinary metadata save; emergency job records bypass the reserve."""
    from .storage_budget import require_space
    payload=json.dumps(value,default=str,allow_nan=False).encode('utf-8')
    require_space(path,len(payload)+65536,operation='Saving application metadata')
    atomic_json(path,value)


def load_jobs(directory,recover=False):
    """Only the runtime owner may request recovery; imports are read-only."""
    result={};issues=[]
    for path in sorted(Path(directory).glob('*/job.json')):
        if path.is_symlink() or path.parent.is_symlink() or not JOB_ID.fullmatch(path.parent.name):
            issues.append('Ignored an unsafe job-record path.');continue
        try:
            job=json.loads(path.read_text())
            if not isinstance(job.get('created_at'),str):raise ValueError('Missing job creation date')
            datetime.fromisoformat(job['created_at'].replace('Z','+00:00'))
            if job.get('id')!=path.parent.name or not isinstance(job.get('results'),dict) or not isinstance(job.get('status'),str):raise ValueError('Invalid job record')
            if recover and job['status'] in ('queued','running'):
                previous=job['status'];job.update(status='interrupted',previous_status=previous,recovered_at=datetime.now(timezone.utc).isoformat(),message='The server stopped before this job finished. Saved inputs and committed outputs are kept. Review them and start a new run; no download or processing was automatically repeated.')
                atomic_json(path,job)
            result[job['id']]=job
        except (ValueError,OSError,TypeError,AttributeError):issues.append('A saved job record could not be loaded; its files were preserved.')
    return result,issues
