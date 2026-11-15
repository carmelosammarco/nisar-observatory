from backend import catalog
from backend.app import SearchQuery
import pytest

def test_beta_is_explicit_and_default_stays_provisional(monkeypatch):
 calls=[]
 class Response:
  headers={'CMR-Hits':'0'}
  url='https://cmr.earthdata.nasa.gov/search/granules.json'
  def raise_for_status(self):pass
  def json(self):return {'feed':{'entry':[]}}
 def get(url,params,**kwargs):calls.append(params.copy());return Response()
 monkeypatch.setattr(catalog.requests,'get',get)
 catalog.search('GUNW',[-100,19,-99,20],'2025-10-25','2026-01-17',maturity='BETA')
 assert calls[-1]['short_name']=='NISAR_L2_GUNW_BETA_V1'
 catalog.search('GUNW',[-100,19,-99,20],'2025-10-25','2026-01-17')
 assert calls[-1]['short_name']=='NISAR_L2_GUNW_PROVISIONAL_V1'
 with pytest.raises(ValueError):catalog.search('GUNW',[-100,19,-99,20],'2025-10-25','2026-01-17',maturity='other')
 assert SearchQuery(bbox=[0,0,1,1],start='2025-10-25',end='2026-01-17').maturity=='PROVISIONAL'


@pytest.mark.parametrize('product,name',[
 ('GCOV','NISAR_L2_PR_GCOV_033_143_D_069_4005_DHDH_A_20261022T030424_20261022T030459_P05036_N_F_J_001'),
 ('GUNW','NISAR_L2_PR_GUNW_033_143_D_069_4005_DHDH_A_20261010T030424_20261010T030459_20261022T030424_20261022T030459_P05036_N_F_J_001'),
 ('GOFF','NISAR_L2_PR_GOFF_033_143_D_069_4005_DHDH_A_20261010T030424_20261010T030459_20261022T030424_20261022T030459_P05036_N_F_J_001'),
])
def test_validated_collection_omits_maturity_suffix(monkeypatch,product,name):
 def page(params):
  assert params['short_name']==f'NISAR_L2_{product}_V1'
  response=type('Response',(),{'headers':{'CMR-Hits':'1'},'url':'https://cmr.earthdata.nasa.gov/search/granules.json'})()
  return response,[{'id':'G4411127425-ASF','producer_granule_id':name,'links':[{'href':f'https://datapool.asf.alaska.edu/{name}.h5'}]}]
 monkeypatch.setattr(catalog,'catalog_page',page)
 query=SearchQuery(bbox=[0,0,1,1],start='2026-10-21',end='2026-11-14',maturity='VALIDATED')
 result=catalog.search(product,query.bbox,query.start,query.end,maturity=query.maturity)
 assert result['collection']==f'NISAR_L2_{product}_V1'
 assert result['items'][0]['maturity']=='VALIDATED'
 assert result['items'][0]['group'].endswith('_P05036')


def test_validated_soil_moisture_collection_is_not_queried(monkeypatch):
 def unexpected(params):
  pytest.fail('Validated soil moisture should not reach the catalog')
 monkeypatch.setattr(catalog,'catalog_page',unexpected)
 with pytest.raises(ValueError,match='Level 2'):
  catalog.search('SME2',[0,0,1,1],'2026-10-21','2026-11-14',maturity='VALIDATED')
