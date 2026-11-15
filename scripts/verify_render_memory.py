"""Isolated, reproducible renderer RSS comparison; not a whole-pipeline benchmark."""
import argparse,hashlib,importlib.util,json,platform,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def measure(renderer):
 import numpy as np
 from backend import exports
 a=np.arange(4_000_000,dtype='float32').reshape(2000,2000)
 a/=1000;np.sin(a,out=a);a[::37,::19]=np.nan
 if renderer=='legacy':
  spec=importlib.util.spec_from_file_location('legacy',ROOT/'tests/helpers/colorize_legacy.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);render=module.colorize
 else:render=exports.colorize
 start=time.perf_counter();rgba,lo,hi=render(a,'diverging');seconds=time.perf_counter()-start
 rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 return {'renderer':renderer,'peak_rss_bytes':int(rss if sys.platform=='darwin' else rss*1024),'render_seconds':seconds,'sha256':hashlib.sha256(rgba).hexdigest(),'range':[lo,hi]}


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--renderer',choices=['legacy','streamed']);parser.add_argument('--output',type=Path);args=parser.parse_args()
 if args.renderer:print(json.dumps(measure(args.renderer)))
 else:
  results=[json.loads(subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--renderer',name],cwd=ROOT,check=True,text=True,capture_output=True,timeout=60).stdout) for name in ['legacy','streamed']]
  assert results[0]['sha256']==results[1]['sha256'] and results[0]['range']==results[1]['range'],'Renderer changed pixels or range'
  receipt={'scope':'One 2000×2000 float32 diverging map; separate fresh processes. Includes imports, input, exact percentiles and RGBA rendering. Not a full processing run or general memory limit.','platform':platform.platform(),'python':platform.python_version(),'cells':4_000_000,'colour_block_pixels':65536,'pixel_and_range_identity':True,'measurements':results,'peak_rss_reduction_fraction':1-results[1]['peak_rss_bytes']/results[0]['peak_rss_bytes']}
  if args.output:args.output.write_text(json.dumps(receipt,indent=2)+'\n')
  print(json.dumps(receipt,indent=2))
