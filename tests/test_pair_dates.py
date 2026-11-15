from datetime import datetime
import pytest
from backend.catalog import filename_interval,search
from backend import catalog

PAIR='NISAR_L2_PR_GOFF_031_170_D_053_032_7700_SH_20260929T235201_20260929T235237_20261011T235201_20261011T235237_P05023_N_P_J_001.h5'

def test_offset_interval_is_twelve_days_not_thirty_six_seconds():
 start,end=filename_interval(PAIR,'GOFF')
 assert (datetime.fromisoformat(end)-datetime.fromisoformat(start)).total_seconds()/86400==12


def test_invalid_import_dates_are_rejected_before_writing(monkeypatch,tmp_path):
 from fastapi.testclient import TestClient
 from backend import app as module
 monkeypatch.setattr(module,'DATA',tmp_path)
 client=TestClient(module.app)
 for name in [PAIR.replace('20260929','20260231'),PAIR.replace('_20261011T235201_20261011T235237','')]:
  response=client.post('/api/import',headers={'X-Filename':name},content=b'ignored')
  assert response.status_code==422
 assert not (tmp_path/'raw').exists()


def test_catalog_preserves_raw_dates_while_normalizing_pair_interval(monkeypatch):
 class Response:
  headers={'CMR-Hits':'1'};url='https://cmr.earthdata.nasa.gov/search/granules.json'
  def raise_for_status(self):pass
  def json(self):return {'feed':{'entry':[{'id':'G-test','producer_granule_id':PAIR,'time_start':'2026-09-29T23:52:01Z','time_end':'2026-10-11T23:52:37Z','links':[{'href':'https://datapool.asf.alaska.edu/file.h5'}]}]}}
 monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:Response())
 item=search('GOFF',[0,0,1,1],'2025-07-30','2026-10-16')['items'][0]
 assert item['end']=='2026-10-11T23:52:01Z'
 assert item['catalog_end']=='2026-10-11T23:52:37Z'
