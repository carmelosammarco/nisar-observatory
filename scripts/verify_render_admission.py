"""Read-only live concurrency check for saved previews and presentation PNGs.

Uses an existing completed P03 result, no science download or new analysis. One
bounded burst verifies rejection/recovery and unchanged response bytes. This is
admission evidence, not a scientific pipeline or whole-process RAM stress test.
"""
import argparse,hashlib,json,sys,threading,time,urllib.error,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse


def verify(base):
    parsed=urlparse(base)
    if parsed.scheme!='http' or parsed.hostname not in ['127.0.0.1','localhost'] or parsed.username or parsed.password or parsed.path not in ['','/'] or parsed.query or parsed.fragment:
        raise ValueError('Use a loopback HTTP app URL without credentials or extra paths.')
    base=base.rstrip('/')
    def read(path):
        start=time.perf_counter()
        try:response=urllib.request.urlopen(base+path,timeout=90)
        except urllib.error.HTTPError as error:response=error
        with response:
            data=response.read()
            return {'status':response.status,'body':data,'sha256':hashlib.sha256(data).hexdigest(),'busy':response.headers.get('X-NISAR-Render-Busy'),'retry_after':response.headers.get('Retry-After'),'seconds':time.perf_counter()-start}
    def get(path):
        response=read(path);assert response['status']==200,(path,response['status'])
        return json.loads(response['body'])
    health=get('/api/health');jobs=get('/api/jobs')
    assert not any(j['status'] in ['queued','running'] for j in jobs),'Leave an active analysis undisturbed.'
    job=next(j for j in jobs if j.get('results',{}).get('P03',{}).get('status')=='exploratory')
    result=get(f"/api/artifacts/{job['id']}/P03/result.json")
    layer=next(l for l in result['layers'] if l['id']=='fire_score')
    preview=f"/api/visualization/{job['id']}/P03/{layer['id']}"
    png=f"/api/map-image/{job['id']}/P03/{layer['id']}"
    urls=[preview,png];baseline={url:read(url) for url in urls}
    assert all(r['status']==200 for r in baseline.values())
    barrier=threading.Barrier(13)
    def request(index):
        barrier.wait(timeout=10);url=urls[index%2];response=read(url)
        if response['status']==200:assert response['sha256']==baseline[url]['sha256'],'Render output changed'
        else:
            assert response['status']==429,response['status']
            assert response['busy']=='1' and response['retry_after']=='1'
        return {'route':'preview' if index%2==0 else 'png',**{k:v for k,v in response.items() if k!='body'}}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(request,index) for index in range(12)]
        barrier.wait(timeout=10);responsive=read('/api/health')
        responses=[f.result(timeout=90) for f in futures]
    assert responsive['status']==200
    busy=sum(r['status']==429 for r in responses)
    assert busy>0,'No simultaneous work observed; this run cannot prove admission.'
    for url in urls:
        after=read(url);assert after['status']==200 and after['sha256']==baseline[url]['sha256'],'Render slot did not recover'
    after_jobs=get('/api/jobs')
    assert jobs==after_jobs,'Saved jobs changed during a read-only check'
    return {'scope':__doc__.strip(),'version':health['version'],'run':job['id'],'layer':layer['id'],'concurrent_requests':12,'accepted':12-busy,'rejected_busy':busy,'health_seconds':responsive['seconds'],'sequential_preview_and_png_recovered':True,'saved_jobs_unchanged':True,'response_identity':True,'responses':responses}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',default='http://127.0.0.1:8765');parser.add_argument('--output',type=Path);args=parser.parse_args()
    receipt=verify(args.url)
    if args.output:args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['responses','scope']}))
