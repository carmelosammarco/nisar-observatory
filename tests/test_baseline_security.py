"""Baseline safeguards. Only invented credentials and bounded synthetic responses."""
import io,json,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest,requests
from fastapi.testclient import TestClient
from backend import app as module,access,catalog
from test_access import Response,Session

client=TestClient(module.app)

@pytest.mark.parametrize('payload',[
 {'username':'synthetic-audit-user','password':'synthetic-audit-secret'*30},
 {'username':{'wrong':'synthetic-audit-user'},'password':'synthetic-audit-secret'},
 {'username':'synthetic-audit-user','password':{'wrong':'synthetic-audit-secret'}},
])
def test_auth_validation_never_echoes_submitted_fields(payload):
 response=client.post('/api/auth',json=payload)
 assert response.status_code==422
 assert 'synthetic-audit-secret' not in response.text
 assert 'synthetic-audit-user' not in response.text
 assert 'input' not in response.json()


def test_secret_model_repr_and_logout(monkeypatch):
 login=module.Login(username='synthetic',password='invented-private-value')
 assert 'invented-private-value' not in repr(login)
 credentials=access.Credentials();session=access.EarthdataSession('synthetic','invented-private-value')
 credentials.session=session;credentials.verified=True
 credentials.logout()
 assert credentials.session is None and credentials.verified is False
 assert session._credential is None


def test_failed_new_login_cannot_reuse_previous_account(monkeypatch):
 credentials=access.Credentials();old=access.EarthdataSession('previous-test-user','invented')
 credentials.session=old;credentials.verified=True
 monkeypatch.setattr(access,'search',lambda *args,**kwargs: (_ for _ in ()).throw(ValueError('Synthetic failure')))
 with pytest.raises(ValueError):credentials.login('next-test-user','invented')
 assert credentials.session is None and not credentials.verified
 assert old._credential is None


@pytest.mark.parametrize('url',[
 'http://urs.earthdata.nasa.gov/oauth/authorize',
 'https://embedded:secret@urs.earthdata.nasa.gov/oauth/authorize',
 'https://urs.earthdata.nasa.gov:8443/oauth/authorize',
])
def test_auth_rejects_insecure_or_embedded_credential_routes(url):
 session=access.EarthdataSession('synthetic','invented')
 with pytest.raises(ValueError):session.prepare_request(requests.Request('GET',url))
 with pytest.raises(ValueError):session.rebuild_auth(requests.Request('GET',url).prepare(),None)
 session.close()


@pytest.mark.parametrize('url',[
 'https://embedded:secret@datapool.asf.alaska.edu/file.h5',
 'https://datapool.asf.alaska.edu:1234/file.h5',
 'https://datapool.asf.alaska.edu:notaport/file.h5',
 'http://datapool.asf.alaska.edu/file.h5',
 'https://[bad/file.h5',
])
def test_asset_url_boundary(url):assert not catalog.allowed_url(url)


def test_single_action_admission_prevents_login_and_run_races():
 module.ACTION_LOCK.acquire()
 try:
  assert client.post('/api/auth',json={'username':'synthetic','password':'invented'}).status_code==409
  assert client.post('/api/run',json={'bbox':[0,0,1,1],'granules':[],'projects':['P01']}).status_code==409
 finally:module.ACTION_LOCK.release()


@pytest.mark.parametrize('options',[
 {'rainfall':None},{'rainfall':[{'date':'not-a-date','mm':2}]},
 {'rainfall':[{'date':'2026-01-01','mm':-1}]},
 {'rainfall':[{'date':'2026-01-01','mm':1},{'date':'2026-01-01','mm':2}]},
 {'soil_allow_unrecommended':'false'},{'component':'unsupported'},
 {'password':'invented-private-value'}, {'event_date':'2026-02-31'},
 {'reference_bbox':'not a rectangle'}, {'graph_distance':-1},
])
def test_invalid_options_fail_before_creating_a_job(options):
 response=client.post('/api/run',json={'bbox':[0,0,1,1],'granules':[],'projects':['P01'],'options':options})
 assert response.status_code==422
 assert 'invented-private-value' not in response.text


def test_invalid_search_dates_are_request_errors():
 for start,end in [('2026-02-31','2026-03-01'),('2026-10-16','2025-01-01')]:
  assert client.post('/api/search',json={'bbox':[0,0,1,1],'start':start,'end':end}).status_code==422


def test_header_probe_is_bounded_and_bad_ranges_rejected(monkeypatch):
 signature=b'\x89HDF\r\n\x1a\n'
 class BadSession:
  def get(self,*args,**kwargs):return Response(signature+b'x'*100,206,{'Content-Range':'bytes 0-7/1000'})
 monkeypatch.setattr(access.AUTH,'session',BadSession())
 with pytest.raises(ValueError,match='bounded'):access.RangeReader('https://datapool.asf.alaska.edu/file.h5')
 class WrongRange(Session):
  def get(self,*args,**kwargs):
   response=super().get(*args,**kwargs)
   if self.calls>1:response.headers['Content-Range']='bytes 8-15/1000'
   return response
 monkeypatch.setattr(access.AUTH,'session',WrongRange(signature+b'x'*100))
 with access.RangeReader('https://datapool.asf.alaska.edu/file.h5') as reader:
  with pytest.raises(ValueError,match='different byte range'):reader.read(10)


def test_incomplete_download_is_never_published(monkeypatch,tmp_path):
 class Truncated(Session):
  def get(self,*args,**kwargs):
   response=super().get(*args,**kwargs);response.headers['Content-Length']='10000';return response
 monkeypatch.setattr(access,'DATA',tmp_path);monkeypatch.setattr(access.AUTH,'session',Truncated(b'\x89HDF\r\n\x1a\n'))
 with pytest.raises(ValueError,match='complete file'):access.download({'id':'test','url':'https://datapool.asf.alaska.edu/file.h5'},lambda:False,lambda *args:None)
 assert not list((tmp_path/'raw').iterdir())


def test_existing_import_does_not_need_credentials_to_keep_original(monkeypatch,tmp_path):
 raw=tmp_path/'raw';raw.mkdir();(raw/'local-test.h5').write_bytes(b'original')
 monkeypatch.setattr(access,'DATA',tmp_path);monkeypatch.setattr(access.AUTH,'session',None)
 assert access.download({'id':'local-test','url':''},lambda:False,lambda *args:None)==str(raw/'local-test.h5')


def test_saved_jobs_are_independent_snapshots_and_concurrent_writes_are_atomic(monkeypatch,tmp_path):
 ident='d'*32;j={'id':ident,'status':'running','created_at':'2026-10-16T00:00:00Z','results':{},'progress':0}
 monkeypatch.setattr(module,'JOBS',{ident:j});monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
 with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda n:module.update(j,progress=n),range(20)))
 record=json.loads((tmp_path/ident/'job.json').read_text());assert record['progress']==j['progress']
 snapshot=module.job(ident);snapshot['results']['fake']={};assert not j['results']


def test_corrupt_local_record_does_not_break_catalog(monkeypatch,tmp_path):
 from backend import examples
 monkeypatch.setattr(examples,'saved_inputs',lambda:iter(()))
 raw=tmp_path/'raw';raw.mkdir();(raw/'broken.json').write_text('not json')
 monkeypatch.setattr(module,'DATA',tmp_path)
 assert client.get('/api/local').json()==[]


def test_security_headers_and_no_browser_credential_defaults():
 response=client.get('/api/health')
 assert response.headers['cache-control']=='no-store'
 assert response.headers['x-frame-options']=='DENY'
 html=client.get('/').text
 assert 'id="password" type="password" autocomplete="off"' in html
 assert 'id="username" autocomplete="off"' in html
