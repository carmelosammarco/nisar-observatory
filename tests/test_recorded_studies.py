"""Recorded examples must remain reproducible, clearly labelled and read-only."""
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import app as service
from backend.examples import CASES
from backend.recorded_studies import recorded,recipe_identity


@pytest.mark.parametrize('case',CASES)
def test_every_recorded_case_matches_its_recipe_and_renders_without_login(case):
 manifest,result,directory=recorded(case)
 assert manifest['remote_science_bytes']==0 and manifest['numeric_replay_maps']>0
 assert manifest['recipe_sha256']==recipe_identity(case)
 opening=result['display_preferences'];pid=result['project'];ident='example-'+case
 client=TestClient(service.app)
 response=client.get('/api/examples/'+case+'/recorded')
 assert response.status_code==200 and response.json()['kind']=='recorded'
 assert 'Previously computed' in response.json()['message']
 before=hashlib.sha256((directory/'result.json').read_bytes()).hexdigest()
 view=client.get(f'/api/visualization/{ident}/{pid}/{opening["layer"]}',params={k:opening[k] for k in ('mode','palette','low','high') if opening.get(k) is not None})
 assert view.status_code==200 and view.json().get('available') is not False
 if opening['mode']=='custom':assert [view.json()['min'],view.json()['max']]==[opening['low'],opening['high']]
 asset=client.get(f'/api/artifacts/{ident}/{pid}/result.json');assert asset.status_code==200
 assert client.put(f'/api/jobs/{ident}/display/{pid}',json=opening).status_code==409
 assert client.delete('/api/jobs/'+ident).status_code==404
 assert hashlib.sha256((directory/'result.json').read_bytes()).hexdigest()==before
 assert client.get(f'/api/artifacts/{ident}/{pid}/manifest.json').status_code==404


def test_recorded_identifiers_cannot_escape_into_inputs_or_other_products():
 client=TestClient(service.app)
 for path in ['/api/examples/unknown/recorded','/api/artifacts/example-P01_Mozambique/P07/result.json','/api/visualization/example-P08_removed/P01/event']:
  assert client.get(path).status_code==404


def test_recorded_reference_can_be_used_as_an_experiment_baseline(tmp_path,monkeypatch):
 import json,shutil
 monkeypatch.setattr(service,'JOBS_DIR',tmp_path)
 _,result,original=recorded('P01_Mozambique');directory=tmp_path/('c'*32)/'P01';directory.mkdir(parents=True)
 (directory/'result.json').write_text(json.dumps({**result,'layers':[l for l in result['layers'] if l['id']=='event']}))
 shutil.copyfile(original/'event.tif',directory/'event.tif')
 response=TestClient(service.app).post('/api/studies/compare',json={'before':'example-P01_Mozambique','before_product':'P01','after':'c'*32,'after_product':'P01'})
 assert response.status_code==200 and response.json()['layers'][0]['changed_cells']==0
