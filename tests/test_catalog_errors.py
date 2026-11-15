"""Distinguish upstream failures from true empty discovery and keep products isolated."""
import pytest
import requests
from fastapi.testclient import TestClient
from backend import catalog,app as module

class Response:
 def __init__(self,status=200,payload=None):
  self.status_code=status
  self.payload=payload if payload is not None else {'feed':{'entry':[]}}
  self.headers={'CMR-Hits':'0','CMR-Request-Id':'request-123, request-123'}
  self.url='https://cmr.earthdata.nasa.gov/search/granules.json'
 def json(self):return self.payload

@pytest.mark.parametrize('detail,expected',[
 ('Elasticsearch index_closed_exception: closed','index_closed'),
 ('Elasticsearch illegal_argument_exception: Fielddata is disabled','search_index'),
])
def test_upstream_index_failure_is_not_a_bad_area_or_empty_result(monkeypatch,detail,expected):
 monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:Response(400,{'errors':[detail]}))
 with pytest.raises(catalog.CatalogError) as caught:
  catalog.search('GOFF',[77.36,32.39,77.57,32.56],'2025-12-01','2026-02-28')
 result=caught.value.result()
 assert result['availability']=='unknown' and result['hits'] is None and result['items']==[]
 assert result['error_details']=={'service':'NASA CMR','code':expected,'http_status':400,'request_id':'request-123','retryable':True}
 assert 'File availability is unknown' in result['error']

@pytest.mark.parametrize('status,code',[(429,'service_unavailable'),(503,'service_unavailable'),(400,'request_rejected')])
def test_other_http_failures_have_safe_diagnostics(monkeypatch,status,code):
 monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:Response(status,{'errors':['<script>server content</script>']}))
 with pytest.raises(catalog.CatalogError) as caught:catalog.catalog_page({})
 assert caught.value.diagnostics['code']==code
 assert '<script>' not in str(caught.value)

@pytest.mark.parametrize('error,code',[(requests.Timeout('secret payload'),'timeout'),(requests.ConnectionError('secret payload'),'connection')])
def test_transport_failures_do_not_expose_exception_content(monkeypatch,error,code):
 def get(*a,**kw):raise error
 monkeypatch.setattr(catalog.requests,'get',get)
 with pytest.raises(catalog.CatalogError) as caught:catalog.catalog_page({})
 assert caught.value.diagnostics['code']==code
 assert 'secret' not in str(caught.value)

@pytest.mark.parametrize('payload',[{},[],{'errors':['Elasticsearch index_closed_exception']},{'feed':{}}])
def test_success_http_without_valid_data_is_never_silent_zero(monkeypatch,payload):
 monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:Response(payload=payload))
 with pytest.raises(catalog.CatalogError):catalog.catalog_page({})

def test_genuine_empty_success_is_preserved(monkeypatch):
 monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:Response())
 result=catalog.search('GOFF',[0,0,1,1],'2026-01-01','2026-01-31')
 assert result['hits']==0 and result['items']==[] and 'error' not in result

def test_api_keeps_working_products_and_exposes_failed_product_status(monkeypatch):
 def search(product,*a,**kw):
  if product=='GOFF':raise catalog.CatalogError('NASA index closed','index_closed',status=400,request_id='id-1')
  return {'hits':0,'items':[]}
 monkeypatch.setattr(module,'search',search)
 result=TestClient(module.app).post('/api/search',json={'bbox':[0,0,1,1],'start':'2026-01-01','end':'2026-01-31','products':['GCOV','GOFF']}).json()
 assert 'error' not in result['GCOV']
 assert result['GOFF']['hits'] is None and result['GOFF']['error_details']['request_id']=='id-1'
