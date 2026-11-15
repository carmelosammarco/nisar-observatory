"""Create, verify or restore an offline NISAR runtime snapshot. Run --help first."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.workspace_backup import backup_runtime,verify_backup,restore_backup,LIMIT


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 commands=parser.add_subparsers(dest='command',required=True)
 create=commands.add_parser('create',help='Stop the app first; protect its ordinary inputs, workflows and runs.')
 create.add_argument('--runtime',required=True,type=Path);create.add_argument('--output',required=True,type=Path);create.add_argument('--include-cache',action='store_true',help='Also copy regenerable array caches; excluded by default.')
 verify=commands.add_parser('verify',help='Verify every member size and SHA-256 without writing files.');verify.add_argument('archive',type=Path)
 restore=commands.add_parser('restore',help='Verify then restore into a new folder; existing profiles cannot be overwritten.');restore.add_argument('archive',type=Path);restore.add_argument('--destination',required=True,type=Path)
 for sub in [verify,restore]:sub.add_argument('--max-gib',type=int,default=LIMIT//1024**3,help='Maximum total uncompressed payload (default 32 GiB).')
 args=parser.parse_args()
 try:
  if args.command=='create':report=backup_runtime(args.runtime,args.output,args.include_cache)
  elif args.command=='verify':report=verify_backup(args.archive,args.max_gib*1024**3);report.pop('manifest',None)
  else:report=restore_backup(args.archive,args.destination,args.max_gib*1024**3)
 except (ValueError,RuntimeError,OSError) as error:parser.exit(1,str(error)+'\n')
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
