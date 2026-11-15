from backend import catalog


def test_discovery_preserves_polygon_footprints_without_fabricating_boxes(monkeypatch):
 class Response:
  headers={'CMR-Hits':'1'}
  url='https://cmr.earthdata.nasa.gov/search/granules.json'
  def raise_for_status(self):pass
  def json(self):return {'feed':{'entry':[{
   'id':'G-test','producer_granule_id':'NISAR_L2_PR_GCOV_023_101_A_023_2005_DHDH_A_20260621T044315_20260621T044332_P05023_N_P_J_001',
   'time_start':'2026-06-21T04:43:15Z','time_end':'2026-06-21T04:43:32Z','granule_size':'100',
   'polygons':[['42.9 6.1 43.9 5.6 43.2 2.7 42.1 3.2 42.9 6.1']],
   'links':[{'href':'https://datapool.asf.alaska.edu/scene.h5'}]
  }]}}
 monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:Response())
 result=catalog.search('GCOV',[4.52,43.47,4.58,43.53],'2025-07-30','2026-10-16')
 assert result['items'][0]['polygons']==[['42.9 6.1 43.9 5.6 43.2 2.7 42.1 3.2 42.9 6.1']]
 assert result['items'][0]['boxes']==[]
