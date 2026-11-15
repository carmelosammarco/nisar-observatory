"""Free-space checks on the actual destination filesystem, never automatic deletion."""
import os,shutil
from pathlib import Path

MIB=1024**2
class InsufficientStorage(ValueError):pass

def disk_reserve_bytes():
 try:
  value=int(os.environ.get('NISAR_DISK_RESERVE_MB','512'))
  if value<0:raise ValueError()
 except ValueError:raise ValueError('NISAR_DISK_RESERVE_MB must be a nonnegative integer in MiB.') from None
 return value*MIB

def storage_status(path,required_bytes=0):
 if not isinstance(required_bytes,int) or required_bytes<0:raise ValueError('Required storage must be a nonnegative byte count.')
 try:
  destination=Path(path).resolve()
  while not destination.exists():destination=destination.parent
  usage=shutil.disk_usage(destination)
 except OSError:raise InsufficientStorage('Cannot check free space on the destination filesystem. Check that its drive is mounted and readable before retrying. Saved files were preserved.') from None
 reserve=disk_reserve_bytes()
 return {'free_bytes':usage.free,'required_bytes':required_bytes,'reserve_bytes':reserve,'fits':usage.free>=required_bytes+reserve,'scope':'Destination filesystem free space; estimates are not a reservation against other applications.'}

def require_space(path,required_bytes=0,operation='This operation'):
 report=storage_status(path,required_bytes)
 if not report['fits']:raise InsufficientStorage(f"{operation} needs approximately {required_bytes/MIB:.1f} MiB of additional free space, plus the {report['reserve_bytes']/MIB:.0f} MiB safety reserve; {report['free_bytes']/MIB:.1f} MiB is free. Free space outside the app, choose another NISAR_DATA_DIR, or reduce the area/data selection. No saved inputs or results were removed.")
 return report

def array_write_estimate(arrays):
 # Compressed output can be larger than input for incompressible values.
 return int(sum(a.nbytes for a in arrays)*1.05)+MIB

def export_write_estimate(result):
 # Numeric COG, overviews/staging and display PNGs; not a guaranteed peak.
 return sum(int(layer['data'].nbytes)*3 for layer in result['layers'].values())+16*MIB
