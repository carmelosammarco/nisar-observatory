"""Read-only comparison of saved run previews with the former range algorithm."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def verify():
    import numpy as np
    import rasterio
    from backend import app, display_range
    original=display_range.raster_percentiles
    def legacy(paths,quantiles=(2,98),max_cells=4_000_000):
        chunks=[]
        for path in paths:
            with rasterio.open(path) as source:
                a=source.read(1);chunks.append(a[np.isfinite(a)])
        return np.percentile(np.concatenate(chunks),quantiles)
    rows=[]
    for path in sorted(app.JOBS_DIR.glob('*/*/result.json')):
        result=json.loads(path.read_text());pid=path.parent.name;ident=path.parent.parent.name
        # One actual shared-range preview per distinct observation quantity in
        # each saved run. Other palette/range behaviour has endpoint unit tests.
        quantities=set()
        for layer in result['layers']:
            quantity=(layer.get('unit'),layer.get('kind'))
            if not layer['id'].startswith('observation_') or quantity in quantities:continue
            quantities.add(quantity)
            paths=[path.parent/(peer['id']+'.tif') for peer in result['layers'] if peer['id'].startswith('observation_') and (peer.get('unit'),peer.get('kind'))==quantity]
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,*paths]}
            try:
                display_range.raster_percentiles=legacy
                expected=app.visualization(ident,pid,layer['id'])
            finally:display_range.raster_percentiles=original
            actual=app.visualization(ident,pid,layer['id'])
            assert actual==expected,(ident,pid,layer['id'])
            assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,*paths]},'Saved result changed'
            rows.append({'run':ident,'tool':pid,'layer':layer['id'],'frames':len(paths),'exact_response_identity':True,'source_hashes_unchanged':True,'range':[actual.get('min'),actual.get('max')],'png_sha256':hashlib.sha256(actual.get('image','').encode()).hexdigest()})
    return {'scope':'Read-only rendering of one saved observation per distinct unit/kind per saved run, comparing complete display responses against the former concatenated finite-value percentile path. Includes range, PNG, category metadata, clipping and bounds. This is display regression evidence, not scientific transfer validation.','version':app.APP_VERSION,'runs':len({r['run'] for r in rows}),'previews':len(rows),'checks':rows}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    receipt=verify()
    if args.output:args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'runs':receipt['runs'],'previews':receipt['previews'],'all_exact':True}))
