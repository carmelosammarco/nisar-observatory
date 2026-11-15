"""Fresh-process RSS comparison of an exact 32-date shared colour range.

Synthetic replayable chunks isolate range calculation from GDAL caching, warp,
PNG encoding and scientific processing. This is not a total application limit.
"""
import argparse, hashlib, json, platform, resource, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def measure(method):
    import numpy as np
    from backend.display_range import exact_percentiles
    passes=[0]
    def blocks():
        passes[0]+=1
        for date in range(32):
            for start in range(0,1_000_000,65_536):
                a=np.arange(start,min(start+65_536,1_000_000),dtype='float32')
                a/=1000;a+=date;np.sin(a,out=a);a[::97]=np.nan
                yield a
    start=time.perf_counter()
    if method=='legacy':
        chunks=[a[np.isfinite(a)] for a in blocks()]
        result=np.percentile(np.concatenate(chunks),[2,98])
    else:result=exact_percentiles(blocks,'float32')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'method':method,'range':result.tolist(),'range_sha256':hashlib.sha256(result.tobytes()).hexdigest(),'passes':passes[0],'seconds':time.perf_counter()-start,'peak_rss_bytes':int(rss if sys.platform=='darwin' else rss*1024)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--method',choices=['legacy','bounded']);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.method:print(json.dumps(measure(args.method)))
    else:
        measurements=[json.loads(subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--method',method],cwd=ROOT,check=True,text=True,capture_output=True,timeout=120).stdout) for method in ['legacy','bounded']]
        assert measurements[0]['range_sha256']==measurements[1]['range_sha256'],'Shared percentile result changed'
        receipt={'scope':__doc__.strip(),'platform':platform.platform(),'python':platform.python_version(),'frames':32,'cells_per_frame':1_000_000,'input_block_values':65_536,'exact_range_identity':True,'measurements':measurements,'peak_rss_reduction_fraction':1-measurements[1]['peak_rss_bytes']/measurements[0]['peak_rss_bytes']}
        if args.output:args.output.write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2))
