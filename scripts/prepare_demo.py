"""Prepare three saved demonstration runs using protected local inputs only.

Creates a NEW isolated runtime; never connects to the user's running app and
never downloads science data. Existing directories are refused, not overwritten.
"""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from verify_release import IsolatedServer,ROOT

CASES=('P03_Timber_Fire','P01_Mozambique','P04_Mexico_City')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True,help='New directory for rehearsal runs, separate from personal data')
    args=parser.parse_args();runtime=args.runtime.resolve()
    runtime.mkdir(parents=True,exist_ok=False)
    server=IsolatedServer(runtime);rows=[]
    try:
        health=server.start()
        assert not health['earthdata_connected']
        for case in CASES:
            setup=server.request('/api/examples/'+case+'/setup')
            assert all(i.get('protected_example') for i in setup['items'])
            job,_=server.wait(server.request('/api/run',setup['request']))
            pid=setup['example']['tool'];entry=job['results'][pid]
            assert entry['status']=='exploratory',entry
            result=server.request(entry['url'])
            assert all(s.get('bytes_transferred',0)==0 for s in result['sources'])
            result_path=runtime/'jobs'/job['id']/pid/'result.json'
            rows.append({'case':case,'job':job['id'],'tool':pid,'status':job['status'],
                         'display':result['display_preferences'],
                         'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest(),
                         'remote_science_bytes':0})
            print(case,job['id'],'ready',flush=True)
        report={'prepared_utc':datetime.now(timezone.utc).isoformat(),'application_version':health['version'],
                'runtime':str(runtime),'status':'prepared_saved_runs',
                'claim':'Local engineering rehearsal, not new independent validation. Results were computed before the presentation.',
                'runs':rows}
        (runtime/'demo-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:server.stop()
    print('Saved rehearsal results retained at',runtime,flush=True)

if __name__=='__main__':main()
