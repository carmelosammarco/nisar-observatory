from fastapi.testclient import TestClient
from backend.app import app
from backend.catalog import allowed_url,validate_bbox
client=TestClient(app)
def test_public_contracts():
 assert client.get('/api/health').json()['runtime']=='project .venv'
 assert len(client.get('/api/projects').json())==7
 assert client.get('/api/library').json()['essentials']
 assert client.get('/').status_code==200
 assert 'password' not in client.get('/api/health').text

def test_local_boundary():
 assert client.get('/api/health',headers={'Host':'evil.example'}).status_code==403
 assert client.post('/api/auth',headers={'Origin':'https://evil.example'},json={'username':'x','password':'x'}).status_code==403
 assert not allowed_url('https://example.com/file.h5')
 assert not allowed_url('https://asf.alaska.edu.evil.com/file.h5')
 assert allowed_url('https://datapool.asf.alaska.edu/file.h5')

def test_invalid_requests():
 assert client.post('/api/run',json={'bbox':[1,1,0,0],'granules':[],'projects':['P01']}).status_code==422
 assert client.post('/api/run',json={'bbox':[0,0,1,1],'granules':['madeup'],'projects':['P01']}).status_code==422
 assert client.get('/api/artifacts/no/P01/result.json').status_code==404

def test_credentials_only_sent_to_earthdata():
 from backend.access import EarthdataSession
 import requests
 session=EarthdataSession('synthetic-user','synthetic-password')
 nasa=session.prepare_request(requests.Request('GET','https://nisar.asf.earthdatacloud.nasa.gov/file.h5'))
 urs=session.prepare_request(requests.Request('GET','https://urs.earthdata.nasa.gov/oauth/authorize'))
 assert 'Authorization' not in nasa.headers
 assert urs.headers.get('Authorization','').startswith('Basic ')
 session.rebuild_auth(urs,None)
 assert 'Authorization' in urs.headers
 session.rebuild_auth(nasa,None)
 assert 'Authorization' not in nasa.headers
 session.close();assert session._credential is None
