"""Isolated seven-example API/restart release gate; never uses the live runtime.

Runs guided and editable recipes, checks exact original rasters/metrics, every
saved preview, opening PNG/scale, My Tools export/reopen, and restart recovery.
Protected inputs and tutorial assets are read-only. This is engineering replay,
not independent scientific accuracy, a browser task study or a peak-RAM quota.
"""
import argparse,base64,hashlib,io,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=('P01_Mozambique','P02_Wheeler_Marsh','P03_Timber_Fire','P04_Mexico_City','P05_Venezuela','P06_Krasheninnikov','P07_Samudra_Tapu')


def digest_array(a):
    import numpy as np
    a=np.asarray(a,dtype='float32')
    return hashlib.sha256(np.where(np.isnan(a),0,a).tobytes()+np.isnan(a).tobytes()).hexdigest()


class IsolatedServer:
    """Reserve a loopback socket and pass it directly to our owned child."""
    def __init__(self,runtime):self.runtime=Path(runtime);self.process=None;self.base=None;self.log=None
    def start(self):
        if self.process is not None and self.process.poll() is None:raise RuntimeError('The verification server is already live.')
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128);self.base='http://127.0.0.1:'+str(listener.getsockname()[1])
        self.log=open(self.runtime/'server.log','ab')
        env={**os.environ,'NISAR_DATA_DIR':str(self.runtime),'PYTHONDONTWRITEBYTECODE':'1'}
        try:
            self.process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--serve-fd',str(listener.fileno())],pass_fds=(listener.fileno(),),cwd=ROOT,env=env,stdout=self.log,stderr=subprocess.STDOUT)
            import requests
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if self.process.poll() is not None:raise RuntimeError('Verification server exited; inspect '+str(self.runtime/'server.log'))
                try:
                    health=self.request('/api/health',timeout=2)
                    if health.get('status')=='ok' and health.get('runtime_owner'):return health
                except (requests.RequestException,ValueError):pass
                time.sleep(.1)
            raise TimeoutError('Verification startup was not observed within 60 seconds; runtime retained for review.')
        finally:listener.close()
    def request(self,path,body=None,timeout=180,raw=False):
        import requests
        # Explicit loopback only; do not inherit proxy/.netrc credentials.
        with requests.Session() as client:
            client.trust_env=False
            response=client.get(self.base+path,timeout=timeout) if body is None else client.post(self.base+path,json=body,timeout=timeout)
            response.raise_for_status()
            return response if raw else response.json()
    def wait(self,job,deadline_seconds=180):
        health_times=[];deadline=time.monotonic()+deadline_seconds
        while job['status'] in ['queued','running']:
            if time.monotonic()>deadline:raise TimeoutError('Job '+job['id']+' is still nonterminal; the verifier will request graceful shutdown and retain failure evidence.')
            if self.process.poll() is not None:raise RuntimeError('Verification server exited during '+job['id'])
            begin=time.perf_counter();assert self.request('/api/health',timeout=30)['status']=='ok';health_times.append(time.perf_counter()-begin)
            time.sleep(.1);job=self.request('/api/jobs/'+job['id'])
        assert job['status']=='completed',job
        return job,max(health_times,default=0)
    def stop(self):
        if self.process is None:return
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=60)
            except subprocess.TimeoutExpired:raise RuntimeError('Verification server remains live; retain '+str(self.runtime)+' and inspect its process before cleanup.') from None
        if self.log:self.log.close();self.log=None
        if self.process.returncode not in (0,-15):raise RuntimeError('Verification server failed; inspect '+str(self.runtime/'server.log'))


def preview_check(server,job,pid,layer,folder):
    import numpy as np,rasterio
    from PIL import Image
    with rasterio.open(folder/(layer['id']+'.tif')) as src:
        a=src.read(1,masked=True).filled(np.nan);count=int(np.isfinite(a).sum());tags=src.tags(1)
        assert src.is_tiled and src.count==1
        if layer.get('unit'):assert tags.get('unit')==layer['unit'] or src.units[0]==layer['unit'],(layer['id'],tags)
    view=server.request(f"/api/visualization/{job}/{pid}/{layer['id']}")
    if count:
        assert view.get('available') is not False and view['valid_pixels']==count,(pid,layer['id'],view)
        assert np.isfinite([view['min'],view['max']]).all()
        with Image.open(io.BytesIO(base64.b64decode(view['image'].split(',',1)[1]))) as image:image.verify()
    else:assert view.get('available') is False and view.get('reason'),(pid,layer['id'])
    return {'layer':layer['id'],'valid_pixels':count,'available':bool(count),'unavailable_reason':view.get('reason')}


def verify_result(server,job,pid,case,mode,baseline,runtime,expected_display):
    import numpy as np,rasterio
    from PIL import Image
    entry=job['results'][pid];assert entry['status']=='exploratory',entry
    result=server.request(entry['url']);assert not job.get('source_errors')
    assert all(s.get('bytes_transferred',0)==0 for s in result['sources'])
    assert result['display_preferences']==expected_display,(case,mode,'saved display differs')
    folder=runtime/'jobs'/job['id']/pid
    for old,comparison in baseline['comparisons'].items():
        ident=old if mode=='guided' else comparison['editable_layer']
        with rasterio.open(folder/(ident+'.tif')) as src:a=src.read(1,masked=True).filled(np.nan)
        assert digest_array(a)==comparison['sha256'],(case,mode,ident,'numeric map changed')
    if case!='P04_Mexico_City' or mode=='guided':assert result['metrics']==baseline['metrics'],(case,mode,'metrics changed')
    checks=[preview_check(server,job['id'],pid,l,folder) for l in result['layers']]
    display=expected_display or {};opening=display.get('layer')
    assert opening in {l['id'] for l in result['layers']},(case,'opening map missing')
    from urllib.parse import urlencode
    params={k:display[k] for k in ['mode','palette','low','high'] if display.get(k) is not None};query=urlencode(params)
    image=server.request(f"/api/map-image/{job['id']}/{pid}/{opening}?{query}",raw=True)
    with Image.open(io.BytesIO(image.content)) as png:png.verify()
    rendered=server.request(f"/api/visualization/{job['id']}/{pid}/{opening}?{query}")
    if display.get('mode')=='custom':assert rendered['min']==display['low'] and rendered['max']==display['high']
    # Public result JSON remains readable and identical when reopened after restart.
    return {'job':job['id'],'pid':pid,'case':case,'mode':mode,'original_numeric_maps':len(baseline['comparisons']),'all_saved_map_checks':checks,'opening_layer':opening,'opening_palette':rendered.get('palette_name'),'opening_range':[rendered.get('min'),rendered.get('max')],'png_with_legend':True,'remote_science_bytes':0,'result_sha256':hashlib.sha256((folder/'result.json').read_bytes()).hexdigest(),'result':result}


def verify(runtime,case_review=None):
    server=IsolatedServer(runtime);rows=[];recipes=[];version=None;health_max=0
    try:
        health=server.start();version=health['version'];assert health['earthdata_connected'] is False
        assert server.request('/api/jobs')==[] and server.request('/api/workflows')==[]
        examples=server.request('/api/examples');assert {e['id'] for e in examples}==set(CASES) and all(e['ready'] for e in examples)
        for case in CASES:
            setup=server.request('/api/examples/'+case+'/setup');assert all(i.get('protected_example') for i in setup['items'])
            baseline=json.loads((ROOT/'docs/validation/workflows/seven-examples'/(case+'.json')).read_text());request=setup['request'];pid=setup['example']['tool']
            job,delay=server.wait(server.request('/api/run',request));health_max=max(health_max,delay)
            guided=verify_result(server,job,pid,case,'guided',baseline,runtime,job['request'].get('display'));rows.append(guided)
            if case_review:case_review(case,guided,runtime)
            recipe=server.request('/api/examples/'+case+'/workflow');created=server.request('/api/workflows',recipe);ident=created.pop('id');exported=server.request('/api/workflows/'+ident+'/export');assert exported==created
            body={'recipe':exported,'bbox':request['bbox'],'granules':request['granules'],'workflow_id':ident}
            assert server.request('/api/workflows/preflight',{k:v for k,v in body.items() if k!='workflow_id'})['ready']
            job,delay=server.wait(server.request('/api/workflows/run',body));health_max=max(health_max,delay)
            editable=verify_result(server,job,'LAB',case,'editable',baseline,runtime,exported.get('display'));rows.append(editable)
            if case!='P04_Mexico_City':assert editable['result']['series']==guided['result']['series']
            recipes.append({'id':ident,'recipe':exported,'body':body})
            print(json.dumps({'case':case,'guided_maps':len(guided['all_saved_map_checks']),'editable_maps':len(editable['all_saved_map_checks']),'exact_original_maps_per_mode':len(baseline['comparisons']),'status':'PASS'}),flush=True)
        before=server.request('/api/jobs');assert len(before)==14 and all(j['status']=='completed' for j in before)
        server.stop();restarted=server.start();assert restarted['version']==version and restarted['earthdata_connected'] is False
        assert server.request('/api/jobs')==before
        assert len(server.request('/api/workflows'))==7
        local=server.request('/api/local');assert len([i for i in local if i.get('protected_example')])==31
        for row in rows:
            result=server.request(f"/api/artifacts/{row['job']}/{row['pid']}/result.json");assert result==row.pop('result')
            assert hashlib.sha256((runtime/'jobs'/row['job']/row['pid']/'result.json').read_bytes()).hexdigest()==row['result_sha256']
        for item in recipes:
            assert server.request('/api/workflows/'+item['id']+'/export')==item['recipe']
            assert server.request('/api/workflows/preflight',{k:v for k,v in item['body'].items() if k!='workflow_id'})['ready']
        return {'application_version':version,'scope':__doc__.strip(),'cases':len(CASES),'protected_inputs':31,'guided_and_editable_jobs':len(rows),'exact_original_map_comparisons':sum(r['original_numeric_maps'] for r in rows),'saved_map_previews_checked':sum(len(r['all_saved_map_checks']) for r in rows),'saved_recipes_reopened':7,'runs_reopened_after_restart':14,'metadata_ready_after_restart':True,'maximum_observed_health_seconds_during_jobs':health_max,'remote_science_bytes':0,'checks':rows,'status':'PASS'}
    finally:server.stop()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'docs/validation/release-integration.json');parser.add_argument('--serve-fd',type=int);args=parser.parse_args()
    if args.serve_fd is not None:
        sys.path.insert(0,str(ROOT));import uvicorn
        with socket.socket(fileno=args.serve_fd) as inherited:uvicorn.Server(uvicorn.Config('backend.app:app',log_level='warning',access_log=False)).run(sockets=[inherited])
        return
    if os.name!='posix':parser.error('This socket-isolated release verifier currently supports macOS/Linux. Native Windows delivery needs its own verification.')
    runtime=Path(tempfile.mkdtemp(prefix='nisar-release-verification-'));success=False
    try:
        receipt=verify(runtime)
        import resource
        receipt['isolated_server_peak_rss_bytes']=int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*(1 if sys.platform=='darwin' else 1024)
        receipt['resource_scope']='Peak RSS across these real protected-case API jobs/previews/restart only; not a maximum-data stress test or a quota.'
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n');success=True
        print(json.dumps({k:v for k,v in receipt.items() if k not in ['checks','scope']}),flush=True)
    finally:
        if success:
            import shutil
            shutil.rmtree(runtime)
        else:print('Failure evidence retained at '+str(runtime),file=sys.stderr)


if __name__=='__main__':main()
