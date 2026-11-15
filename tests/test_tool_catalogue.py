"""Public tool numbers, processors and protected recipes must identify the same workflow."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
from backend.engines import PRODUCT_FOR,MINIMUM,summary
from backend.examples import CASES,inspect
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def test_public_catalogue_is_consecutive_and_has_no_withdrawn_tools():
 client=TestClient(app);tools=client.get('/api/projects').json()
 expected=['Flood Memory','Wetland Pulse','After Fire Observatory','Sinking City Atlas','Quake Evidence Explorer','Volcano Surface Diary','Glacier Motion Pulse']
 assert [t['id'] for t in tools]==[f'P{i:02}' for i in range(1,8)]
 assert [t['name'] for t in tools]==expected
 assert {t['id']:t['product'] for t in tools}==PRODUCT_FOR
 assert {t['id']:t['minimum'] for t in tools}=={**MINIMUM,'P03':4}
 reading=json.loads((ROOT/'frontend/assets/tool-reading.json').read_text())
 assert set(reading['tools'])==set(PRODUCT_FOR)
 presets=client.get('/api/library').json()['presets']
 assert all(p['id'] in PRODUCT_FOR for p in presets)
 assert not any('Costa Marques' in p['name'] for p in presets)
 assert not any('Amazon river corridor' in p['name'] for p in presets)
 assert client.post('/api/run',json={'bbox':[0,0,1,1],'granules':[],'projects':['P10']}).status_code==422
 assert client.post('/api/run',json={'bbox':[0,0,1,1],'granules':[],'projects':['P11']}).status_code==422

def test_retained_examples_use_new_tools_and_verified_original_subsets():
 assert CASES==('P01_Mozambique','P02_Wheeler_Marsh','P03_Timber_Fire','P04_Mexico_City','P05_Venezuela','P06_Krasheninnikov','P07_Samudra_Tapu')
 examples=[inspect(i) for i in CASES]
 assert all(m['ready'] for m in examples)
 assert sum(m['input_count'] for m in examples)==31
 for m in examples:
  assert m['request']['projects']==[m['tool']]
  assert PRODUCT_FOR[m['tool']]==m['product']
 assert TestClient(app).get('/api/examples/P03_Costa_Marques').status_code==404

def test_tool_numbers_never_change_the_percentile_schema():
 assert summary(np.arange(11.))['p10']==1.
 assert 'p09' not in summary(np.arange(11.))


def test_audio_feature_is_completely_removed_from_runtime():
 assert 'P11' not in PRODUCT_FOR
 assert 'audio' not in (ROOT/'backend/processors.py').read_text()
 frontend=(ROOT/'frontend/app.js').read_text()
 assert 'playAudio' not in frontend and 'sound-button' not in frontend and 'AudioContext' not in frontend




def test_retired_soil_workflow_is_absent_from_all_public_entry_points():
 client=TestClient(app)
 assert 'P08' not in PRODUCT_FOR
 assert client.get('/api/examples/P08_South_Dakota').status_code==404
 assert client.get('/api/examples/P08_South_Dakota/setup').status_code==404
 assert client.post('/api/run',json={'bbox':[0,0,1,1],'granules':[],'projects':['P08']}).status_code==422
 assert not any(p['id']=='P08' for p in client.get('/api/library').json()['presets'])
 assert not (ROOT/'Examples/P08_South_Dakota').exists()
