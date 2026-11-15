"""Compare geometry allocations in fresh processes, without science downloads.

The synthetic HDF5 cubes use unallocated fill values: their logical size tests
allocation, not real disk/network throughput. This is a geometry-only peak-RSS
comparison, not an end-to-end analysis quota or a performance guarantee.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def worker(mode,path):
    import resource,h5py,numpy as np
    from rasterio.transform import from_origin
    from backend import science
    from backend.glacier_geometry import interpolate,FIELDS
    spec=importlib.util.spec_from_file_location('geometry_oracle',ROOT/'tests/fixtures/geometry_0_8_11.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    target={'crs':'EPSG:6933','shape':(384,384),'transform':from_origin(-15000,15000,80,80)}
    started=time.perf_counter()
    with h5py.File(path,'r') as f:out,meta=(legacy.interpolate if mode=='legacy' else interpolate)(f,target,5000)
    peak=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if sys.platform=='darwin' else 1024)
    return {'mode':mode,'peak_rss_bytes':peak,'seconds':time.perf_counter()-started,'field_hashes':{name:hashlib.sha256(out[name].tobytes()).hexdigest() for name in FIELDS},'read_window_shape':meta.get('read_window_shape'),'retained_geometry_bytes':meta.get('retained_geometry_bytes'),'maximum_point_batch':meta.get('maximum_point_batch')}


def compare():
    import h5py,numpy as np
    from backend.glacier_geometry import ROOT as cube_root,FIELDS
    with tempfile.TemporaryDirectory(prefix='nisar-geometry-memory-') as temporary:
        base=Path(temporary);path=base/'synthetic.h5';shape=(40,600,600)
        with h5py.File(path,'w') as f:
            g=f.create_group(cube_root)
            for name,axis in [('heightAboveEllipsoid',np.linspace(-1000,9000,40)),('yCoordinates',np.linspace(300000,-300000,600)),('xCoordinates',np.linspace(-300000,300000,600))]:g[name]=axis
            g['projection']=6933
            for name,value in zip(FIELDS,[-.6,0,0,1,36.86989765]):
                ds=g.create_dataset(name,shape=shape,dtype='float32',chunks=(1,64,64),fillvalue=value);ds.attrs['units']='degrees' if name=='incidenceAngle' else '1';ds.attrs['description']=('East' if name.endswith('X') else 'North')+' component'
        before=hashlib.sha256(path.read_bytes()).hexdigest();results=[]
        for mode in ['legacy','windowed']:
            env={**os.environ,'NISAR_DATA_DIR':str(base/'runtime'),'PYTHONDONTWRITEBYTECODE':'1'}
            result=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',mode,'--source',str(path)],capture_output=True,text=True,check=True,timeout=120,env=env,cwd=ROOT)
            results.append(json.loads(result.stdout))
        assert results[0]['field_hashes']==results[1]['field_hashes'],'Interpolation output changed'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==before,'Source changed'
        old,new=results
        return {'scope':__doc__.strip(),'platform':sys.platform,'logical_cube_shape':list(shape),'logical_source_float32_bytes':int(np.prod(shape))*4*len(FIELDS),'legacy_full_float64_cubes_bytes':int(np.prod(shape))*8*len(FIELDS),'exact_field_hashes':True,'source_unchanged':True,'peak_rss_reduction_percent':100*(old['peak_rss_bytes']-new['peak_rss_bytes'])/old['peak_rss_bytes'],'results':results}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--worker',choices=['legacy','windowed']);parser.add_argument('--source',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if sys.platform not in ['darwin','linux']:parser.error('Peak-RSS measurement currently supports macOS/Linux; native interpolation remains separately tested.')
    receipt=worker(args.worker,args.source) if args.worker else compare()
    if args.output:args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
