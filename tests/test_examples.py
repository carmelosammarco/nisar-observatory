"""Examples must fail closed on missing/tampered inputs and keep disposable data separate."""
import json,shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend import examples
from backend.app import app,RunQuery
from backend.subset_storage import subset_file,digest

def test_seven_recipes_have_exact_scientific_inputs():
 expected={'P01':2,'P02':6,'P03':8,'P04':6,'P05':3,'P06':5,'P07':1}
 for ident in examples.CASES:
  m=examples.definition(ident);assert len(m['sources'])==expected[m['tool']]
  assert len({i['id'] for i in m['sources']})==len(m['sources'])
  RunQuery.model_validate({**m['request'],'granules':['test']})
  assert m['references'] and m['gallery'] and m['comparison'] and len(m['limits'])>100
  for g in m['gallery']:assert (examples.directory(ident)/g['file']).is_file()
  assert all(s['url'].startswith('https://nisar.asf.earthdatacloud.nasa.gov/') for s in m['sources'])
 p02=examples.definition('P02_Wheeler_Marsh')['request']['options']
 assert p02['water_method']=='hh_hv' and p02['spatial_context']['features']
 assert p02['resolution']==20 and p02['water_hh_threshold']==-14 and p02['water_hv_threshold']==-23
 p04=examples.definition('P04_Mexico_City')['request']
 assert p04['options']['phase_allow_mixed_revisions'] and p04['options']['phase_network']
 assert p04['display']=={'palette':'rainbow','mode':'custom','layer':'los_rate_year','unit':'cm/year','low':-30,'high':30}
 p05=examples.definition('P05_Venezuela')
 assert p05['request']['options']['quake_mosaic']
 assert not any(s['group'].startswith('061_A_006') for s in p05['sources'])
 assert p05['request']['options']['reference_bbox']==[-68.9,9.85,-66.45,10.15]

def fixture_case(tmp_path,monkeypatch):
 source=examples.definition('P01_Mozambique');source['sources']=source['sources'][:1]
 root=tmp_path/'Examples';d=root/'P01_Mozambique';(d/'inputs').mkdir(parents=True)
 (d/'example.json').write_text(json.dumps(source));monkeypatch.setattr(examples,'ROOT',root)
 return d,source

def test_missing_and_corrupted_inputs_disable_setup(tmp_path,monkeypatch):
 d,m=fixture_case(tmp_path,monkeypatch)
 assert not examples.inspect(m['id'])['ready']
 with pytest.raises(ValueError,match='incomplete'):examples.setup(m['id'])
 p=d/'inputs'/'test.h5';p.write_bytes(b'original real-file placeholder for storage test')
 item={**m['sources'][0],'id':'subset-'+'a'*32,'source_id':m['sources'][0]['id'],'subset':True,'subset_bbox':m['request']['bbox'],'example_id':m['id'],'example_file':p.name,'content_sha256':digest(p)}
 (d/'input-manifest.json').write_text(json.dumps({'inputs':[item]}))
 assert examples.inspect(m['id'])['ready']
 assert examples.setup(m['id'])['request']['granules']==[item['id']]
 p.write_bytes(b'modified')
 assert not examples.inspect(m['id'])['ready']
 with pytest.raises(ValueError):examples.setup(m['id'])

def test_example_paths_cannot_escape_and_survive_user_data_removal(tmp_path,monkeypatch):
 d,m=fixture_case(tmp_path,monkeypatch);p=d/'inputs'/'test.h5';p.write_bytes(b'kept')
 item={'example_id':m['id'],'example_file':'test.h5'}
 data=tmp_path/'data';(data/'arrays').mkdir(parents=True);(data/'jobs').mkdir()
 shutil.rmtree(data)
 assert subset_file(data,item)==p and p.read_bytes()==b'kept'
 for bad in ['../test.h5','/tmp/test.h5','.hidden.h5','folder/file.h5']:
  with pytest.raises(ValueError):examples.protected_file(data,{**item,'example_file':bad})
 with pytest.raises(ValueError):examples.directory('../data')

def test_example_assets_only_expose_documentation():
 c=TestClient(app)
 assert len(c.get('/api/examples').json())==7
 assert c.get('/api/examples/P01_Mozambique').json()['required_count']==2
 assert c.get('/api/examples/P01_Mozambique/files/README.md').status_code==200
 assert c.get('/api/examples/P01_Mozambique/files/example.json').status_code==404
 assert c.get('/api/examples/P01_Mozambique/files/input-manifest.json').status_code==404
 assert c.get('/api/examples/P01_Mozambique/files/inputs/no.h5').status_code==404
 assert c.get('/api/examples/unknown').status_code==404
 assert c.get('/api/examples/P01_Mozambique/files/references/../../example.json').status_code==404


def test_real_app_cleanup_actions_keep_protected_inputs(tmp_path,monkeypatch):
 from backend import app as module
 d,m=fixture_case(tmp_path,monkeypatch);input_file=d/'inputs'/'test.h5';input_file.write_bytes(b'protected')
 data=tmp_path/'data';(data/'arrays').mkdir(parents=True);(data/'arrays'/'cache.npz').write_bytes(b'cache')
 ident='f'*32;job_dir=data/'jobs'/ident;job_dir.mkdir(parents=True);(job_dir/'result.json').write_text('{}')
 monkeypatch.setattr(module,'DATA',data);monkeypatch.setattr(module,'JOBS_DIR',data/'jobs');monkeypatch.setattr(module,'JOBS',{ident:{'status':'completed'}})
 c=TestClient(module.app)
 assert c.delete('/api/cache').json()['freed_bytes']==5
 assert c.delete('/api/jobs/'+ident).status_code==200
 assert input_file.read_bytes()==b'protected'


def test_local_catalog_deduplicates_normal_and_protected_copy(tmp_path,monkeypatch):
 from backend import app as module
 d,m=fixture_case(tmp_path,monkeypatch)
 ident='subset-'+'a'*32
 item={'id':ident,'name':m['sources'][0]['name'],'local':True,'subset':True,'subset_bbox':m['request']['bbox'],'product':'GCOV'}
 monkeypatch.setattr(module,'DATA',tmp_path/'data');monkeypatch.setattr(module,'CATALOG',{})
 monkeypatch.setattr(module,'saved_items',lambda root:iter([item]))
 monkeypatch.setattr(examples,'saved_inputs',lambda:iter([{**item,'protected_example':True,'example_id':m['id']}]))
 response=TestClient(module.app).get('/api/local').json()
 assert len(response)==1 and response[0]['protected_example']
 assert module.CATALOG[ident]['example_id']==m['id']


def test_curated_visual_evidence_is_local_distinct_and_attributed():
 import hashlib,re
 for ident in examples.CASES:
  m=examples.definition(ident);folder=examples.directory(ident)
  assert m['visual_comparison_note']
  assert m['card_image']['file'] in {g['file'] for g in m['gallery']}
  assert m['card_image']['label']
  assert len([g for g in m['gallery'] if g['role']=='result'])==1
  assert any(g['role']=='published' for g in m['gallery'])
  hashes=[]
  for g in m['gallery']:
   assert g['title'] and g['alt'] and g['caption'] and g['credit']
   assert g['width']>0 and g['height']>0
   assert g['role'] in {'published','result','context','opening'}
   if g['role']=='published':assert g['source_url'].startswith('https://')
   hashes.append(hashlib.sha256((folder/g['file']).read_bytes()).hexdigest())
  assert len(hashes)==len(set(hashes))
  readme=(folder/'README.md').read_text()
  images=re.findall(r'!\[[^\]]*\]\((figures/[^)]+)\)',readme)
  assert len(images)==len(set(images)) and set(images)=={g['file'] for g in m['gallery']}
  assert {str(f.relative_to(folder)) for f in (folder/'figures').iterdir()}==set(images)
  for report in m['reports']:assert report['file'] in {str(f.relative_to(folder)) for f in (folder/'references').rglob('*') if f.is_file()}


def test_glacier_example_bundles_native_geometry_domain_and_tested_scale():
 import h5py
 from backend.glacier_geometry import ROOT,FIELDS
 m=examples.inspect('P07_Samudra_Tapu');assert m['ready'] and m['input_count']==1
 opt=m['request']['options']
 assert opt['offset_solution']=='horizontal' and opt['offset_geometry_height_m']==5000
 assert opt['offset_layer']=='layer3' and not opt['offset_filter'] and opt['spatial_context']['features']
 assert m['request']['display']=={'palette':'rainbow','mode':'custom','layer':'horizontal_speed','unit':'m/year','low':0,'high':140}
 with h5py.File(examples.protected_file(None,m['inputs'][0])) as f:
  assert all(ROOT+'/'+name in f for name in FIELDS)
 assert m['sources'][0]['start']=='2026-01-01T00:05:27Z' and m['sources'][0]['end']=='2026-01-13T00:05:27Z'




