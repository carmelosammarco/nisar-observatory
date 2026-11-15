"""Isolated browser + real-data verification for guided discovery and experiments.

Requires node, Playwright and installed Google Chrome. Set NODE_PATH if using a
separate tooling installation. No satellite downloads or Earthdata session.
Failure preserves its temporary profile and logs; successful profiles are removed.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from verify_release import IsolatedServer,verify_result,ROOT
sys.path.insert(0,str(ROOT))


def verify_browser_outputs(server,output,runtime):
 from backend.display_settings import DisplaySettings
 browser=json.loads((output/'browser.json').read_text());checks=[]
 assert browser['passed'] and len(browser['cases'])==7
 for row in browser['cases']:
  case=row['case'];baseline=json.loads((ROOT/'docs/validation/workflows/seven-examples'/(case+'.json')).read_text())
  definition=server.request('/api/examples/'+case)
  for mode in ('guided','editable'):
   display=definition['request']['display'] if mode=='guided' else server.request('/api/examples/'+case+'/workflow')['display']
   expected=DisplaySettings.model_validate(display).model_dump(mode='json')
   run=row[mode];job=server.request('/api/jobs/'+run['job'])
   check=verify_result(server,job,run['pid'],case,mode,baseline,runtime,expected)
   checks.append({k:v for k,v in check.items() if k!='result'})
 receipt={'passed':True,'scope':'Isolated real Chrome journeys, guided/editable protected replay, all saved previews and opening-map exports. Not independent environmental accuracy or a novice-user study.','browser':'browser.json','runs':checks,'numeric_maps':sum(c['original_numeric_maps'] for c in checks),'saved_preview_checks':sum(len(c['all_saved_map_checks']) for c in checks)}
 (output/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('Scenario B verified:',receipt['numeric_maps'],'numeric map replays;',receipt['saved_preview_checks'],'saved previews.',flush=True)
 return receipt


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True,help='Evidence directory outside personal runtime storage.')
 args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
 runtime=Path(tempfile.mkdtemp(prefix='nisar-scenario-b-gate-'));server=IsolatedServer(runtime);passed=False
 try:
  server.start()
  subprocess.run(['node',str(ROOT/'scripts/verify_study_browser.cjs'),server.base,str(output)],check=True,cwd=ROOT)
  verify_browser_outputs(server,output,runtime)
  passed=True
 finally:
  server.stop()
  if passed:shutil.rmtree(runtime)
  else:print('Verification profile retained for inspection:',runtime)


if __name__=='__main__':main()
