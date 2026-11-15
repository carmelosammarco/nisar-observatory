"""Build read-only example outputs in an isolated runtime, without NASA downloads.

Normal downloads, runs and My Tools are never opened. Existing inputs/tutorial
definitions are read-only. Publication refuses to overwrite an existing record;
move a previous generated record aside explicitly before rebuilding it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('cases',nargs='*')
 args=parser.parse_args()
 from verify_release import IsolatedServer,CASES,digest_array
 selected=args.cases or list(CASES)
 if not selected or any(c not in CASES for c in selected):parser.error('Choose registered example folder names.')
 receipts=[]
 with tempfile.TemporaryDirectory(prefix='nisar-recorded-studies-') as temporary:
  runtime=Path(temporary);os.environ['NISAR_DATA_DIR']=temporary
  from backend.recorded_studies import recipe_identity
  from backend.subset_storage import digest
  server=IsolatedServer(runtime)
  try:
   health=server.start()
   for case in selected:
    destination=ROOT/'Examples'/case/'recorded'
    if destination.exists():raise RuntimeError('A record already exists; refusing to overwrite '+str(destination))
    payload=server.request('/api/examples/'+case+'/setup')
    if not payload['example']['ready']:raise RuntimeError('Protected inputs are incomplete for '+case)
    job,_=server.wait(server.request('/api/run',payload['request']),deadline_seconds=300)
    pid=payload['example']['tool'];folder=runtime/'jobs'/job['id']/pid
    result=server.request(job['results'][pid]['url'])
    if any(s.get('bytes_transferred',0) for s in result['sources']):raise RuntimeError('A recorded study unexpectedly read remote science bytes.')
    # Compare actual numeric maps against the protected historical replay receipt.
    baseline=json.loads((ROOT/'docs/validation/workflows/seven-examples'/(case+'.json')).read_text())
    import rasterio
    import numpy as np
    for name,row in baseline['comparisons'].items():
     with rasterio.open(folder/(name+'.tif')) as raster:array=raster.read(1,masked=True).filled(np.nan)
     if digest_array(array)!=row['sha256']:raise RuntimeError('Protected numeric replay changed: '+case+'/'+name)
    stage=Path(tempfile.mkdtemp(prefix='.recorded-',dir=destination.parent))
    try:
     files={}
     for source in sorted(folder.iterdir()):
      if source.suffix not in ('.json','.png','.tif') or not source.is_file():continue
      target=stage/source.name;shutil.copyfile(source,target);files[source.name]=digest(target)
     receipt={'format':'nisar-recorded-study-1','case':case,'computed_at':result['created_at'],'application_version':health['version'],'recipe_sha256':recipe_identity(case),'files':files,'remote_science_bytes':0,'numeric_replay_maps':len(baseline['comparisons'])}
     (stage/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
     stage.rename(destination)
     receipts.append({k:v for k,v in receipt.items() if k!='files'})
     print(case+': '+str(len(files))+' protected recorded files; '+str(receipt['numeric_replay_maps'])+' numeric maps match.',flush=True)
    finally:
     if stage.exists():shutil.rmtree(stage)
  finally:server.stop()
 print(json.dumps({'recorded':receipts},indent=2))


if __name__=='__main__':main()
