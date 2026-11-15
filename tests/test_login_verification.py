"""Bounded login probes, catalog outages and safe actionable messages."""
import io
import pytest,requests
from backend import access,app as module
from fastapi.testclient import TestClient
from test_access import Response

URL='https://nisar.asf.earthdatacloud.nasa.gov/known.h5'
class Candidate:
 def __init__(self,responses):self.responses=iter(responses);self.closed=False;self.calls=[]
 def get(self,url,**kwargs):
  self.calls.append((url,kwargs));value=next(self.responses)
  if isinstance(value,Exception):raise value
  return value
 def close(self):self.closed=True

def valid():return Response(b'\x89HDF\r\n\x1a\n',headers={'Content-Range':'bytes 0-7/12345678'})
def prepare(monkeypatch,responses,urls=None):
 candidate=Candidate(responses);monkeypatch.setattr(access,'EarthdataSession',lambda *a:candidate)
 monkeypatch.setattr(access,'verification_urls',lambda:urls or [URL])
 return access.Credentials(),candidate

def test_catalog_500_uses_retained_catalog_resolved_probes(monkeypatch):
 calls=[]
 def unavailable(*args,**kwargs):calls.append(kwargs);raise requests.HTTPError('sensitive upstream content never shown')
 monkeypatch.setattr(access,'search',unavailable)
 urls=access.verification_urls();assert len(urls)>=2
 assert calls==[{'limit':1}]
 assert all(access.allowed_url(url) and url.endswith('.h5') for url in urls)

def test_login_reads_only_verified_eight_byte_header(monkeypatch):
 auth,candidate=prepare(monkeypatch,[valid()]);auth.login('invented','invented')
 assert auth.verified and auth.session is candidate
 assert candidate.calls[0][1]['headers']['Range']=='bytes=0-7'
 assert candidate.calls[0][1]['stream'] is True

def test_missing_or_busy_probe_tries_next_known_file(monkeypatch):
 auth,candidate=prepare(monkeypatch,[Response(b'',503),valid()],[URL,URL+'?second'])
 auth.login('invented','invented');assert auth.verified and len(candidate.calls)==2

@pytest.mark.parametrize('status',[401,403])
def test_credentials_rejection_is_distinct_and_not_retried(monkeypatch,status):
 auth,candidate=prepare(monkeypatch,[Response(b'',status)],[URL,URL+'?second'])
 with pytest.raises(access.ScienceAccessError,match='did not authorize') as failure:auth.login('invented','invented')
 assert failure.value.status_code==401 and not auth.verified and candidate.closed and len(candidate.calls)==1

@pytest.mark.parametrize('exception,fragment',[(requests.Timeout('private URL'), 'timed out'),(requests.ConnectionError('private credential'), 'could not reach'),(requests.exceptions.SSLError('private certificate'), 'secure connection')])
def test_network_failures_explain_cause_without_echoing_secrets(monkeypatch,exception,fragment):
 auth,candidate=prepare(monkeypatch,[exception])
 with pytest.raises(access.ScienceAccessError,match=fragment) as failure:auth.login('invented','invented')
 assert 'private' not in str(failure.value) and not auth.verified and candidate.closed

def test_oversized_or_invalid_header_never_connects(monkeypatch):
 auth,candidate=prepare(monkeypatch,[Response(b'\x89HDF\r\n\x1a\nEXTRA',headers={'Content-Range':'bytes 0-7/12345678'})])
 with pytest.raises(access.ScienceAccessError,match='invalid science-file'):auth.login('invented','invented')
 assert candidate.closed and not auth.verified

def test_api_reports_service_failure_without_claiming_invalid_password(monkeypatch):
 monkeypatch.setattr(module,'busy',lambda:False)
 def unavailable(*args):raise access.ScienceAccessError('NASA service unavailable. Your credentials could not be verified.')
 monkeypatch.setattr(module.AUTH,'login',unavailable)
 r=TestClient(module.app).post('/api/auth',json={'username':'invented','password':'invented-private-password'})
 assert r.status_code==503 and 'credentials could not be verified' in r.text
 assert 'invented' not in r.text
