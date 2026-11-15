"""Readable per-batch storage and portable manual import; all sources are synthetic."""
import json,re
from datetime import datetime,timezone
from pathlib import Path
import h5py,numpy as np,pytest
from backend import app as module,science,subsets
from backend.subset_storage import new_folder,saved_items,FOLDER_PATTERN
from test_subsets import setup,BBOX


def proper_pair(item):
 if item['product'] in ['GUNW','GOFF']:
  item['name']=f"NISAR_L2_PR_{item['product']}_001_001_A_001_002_4005_DH_20260801T000000_20260801T000030_20260813T000000_20260813T000030_M00100_P_F_J_001.h5"
  item['end']='2026-08-13T00:00:00Z'
 return item


def test_one_product_batch_uses_one_named_folder_with_all_files(monkeypatch,tmp_path):
 first,client=setup(monkeypatch,tmp_path);second={**first,'id':'local-'+'b'*16,'name':first['name'].replace('20260801','20260813'),'start':'2026-08-13T00:00:00Z','end':'2026-08-13T00:00:30Z'}
 science.source_file(second).write_bytes(science.source_file(first).read_bytes())
 j=module.newjob('area_download');module.area_download_work(j,[first,second],BBOX)
 assert j['status']=='completed',j
 assert len(j['download_folders'])==1 and re.fullmatch(FOLDER_PATTERN,j['download_folders'][0])
 folder=tmp_path/'subsets'/j['download_folders'][0]
 assert folder.name.startswith('GCOV_') and len(list(folder.glob('*.h5')))==2 and len(list(folder.glob('subset-*.json')))==2
 assert 'Import .h5 data' in (folder/'README.txt').read_text()
 for saved in j['saved_areas']:
  assert science.source_file(saved).parent==folder
  assert '_GCOV_' in science.source_file(saved).name and '__subset_' in science.source_file(saved).name
  with h5py.File(science.source_file(saved)) as h:
   embedded=json.loads(h.attrs['observatory_subset_manifest']);assert embedded['subset_bbox']==BBOX
   assert embedded['source_name']==saved['name']
 # Inventory and duplicate reuse work recursively, without a new download folder.
 count=len(list((tmp_path/'subsets').iterdir()));again=module.newjob('area_download');module.area_download_work(again,[first,second],BBOX)
 assert again['reused']==2 and len(list((tmp_path/'subsets').iterdir()))==count
 module.CATALOG.clear();assert len(client.get('/api/local').json())==2


@pytest.mark.parametrize('product',['GCOV','GUNW','GOFF','SME2'])
def test_hdf5_alone_imports_on_another_installation_with_bounds_and_values(monkeypatch,tmp_path,product):
 item,client=setup(monkeypatch,tmp_path,product);proper_pair(item)
 saved,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 grid=science.target_grid(BBOX,100);expected=science.load_observation(saved,BBOX,grid,{},lambda:False)
 content=science.source_file(saved).read_bytes();display_name=science.source_file(saved).name
 other=tmp_path/'another-installation';other.mkdir()
 for m in [module,science]:monkeypatch.setattr(m,'DATA',other)
 module.CATALOG.clear();monkeypatch.setattr(module.AUTH,'session',None)
 response=client.post('/api/import',headers={'X-Filename':display_name},content=content)
 assert response.status_code==200,response.text
 imported=response.json();assert imported['subset'] and imported['subset_bbox']==BBOX
 assert imported['source_id']==item['id'] and imported['name']==item['name'] and imported['product']==product
 assert science.source_file(imported).is_file() and science.source_file(imported).parent.name.startswith(product+'_')
 actual=science.load_observation(imported,BBOX,grid,{},lambda:False)
 np.testing.assert_allclose(actual['array'],expected['array'],equal_nan=True)
 assert actual['wavelength']==expected['wavelength'] and actual['attrs']['source_subset']['bbox']==BBOX
 for key in expected['aux']:np.testing.assert_allclose(actual['aux'][key],expected['aux'][key],equal_nan=True)
 assert client.post('/api/run',json={'bbox':[-115,36,-114,37],'granules':[imported['id']],'projects':['P04' if product=='GUNW' else 'P07' if product=='GOFF' else 'P08' if product=='SME2' else 'P01'],'options':{}}).status_code==422
 duplicate=client.post('/api/import',headers={'X-Filename':'renamed.h5'},content=content)
 assert duplicate.status_code==200 and duplicate.json()['id']==imported['id']
 assert len(list(saved_items(other)))==1


def test_same_second_batches_get_distinct_folders(monkeypatch,tmp_path):
 stamp=datetime(2026,10,18,21,45,30,tzinfo=timezone.utc)
 first=new_folder(tmp_path,'GUNW',stamp);second=new_folder(tmp_path,'GUNW',stamp)
 assert first.name=='GUNW_2026-10-18_21-45-30_UTC' and second.name==first.name+'_02'


def test_legacy_flat_extracts_remain_usable_and_can_be_imported(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path)
 saved,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 old_file=tmp_path/'subsets'/(saved['id']+'.h5');science.source_file(saved).rename(old_file)
 saved.pop('subset_path');saved.pop('download_folder');saved.pop('content_sha256')
 with h5py.File(old_file,'r+') as h:del h.attrs['observatory_subset_manifest']
 (tmp_path/'subsets'/(saved['id']+'.json')).write_text(json.dumps(saved))
 assert science.source_file(saved)==old_file and subsets.saved_subset(item,BBOX)['id']==saved['id']
 assert client.get('/api/local').json()[0]['subset_bbox']==BBOX
 response=client.post('/api/import',headers={'X-Filename':old_file.name},content=old_file.read_bytes())
 assert response.status_code==200 and response.json()['subset_bbox']==BBOX


@pytest.mark.parametrize('relative',['../outside.h5','/tmp/outside.h5','bad/any.h5','GUNW_2026-10-18_21-45-30_UTC/../../outside.h5'])
def test_subset_paths_cannot_escape_the_managed_data_directory(tmp_path,relative):
 with pytest.raises(ValueError):science.source_file({'subset':True,'id':'subset-'+'a'*32,'subset_path':relative},tmp_path)


def test_missing_or_conflicting_subset_metadata_cannot_become_an_original(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path);saved,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None);path=science.source_file(saved)
 with h5py.File(path,'r+') as h:h.attrs['observatory_requested_bbox']=[0,0,1,1]
 response=client.post('/api/import',headers={'X-Filename':path.name},content=path.read_bytes())
 assert response.status_code==422 and 'disagree' in response.json()['detail']
 with h5py.File(path,'r+') as h:
  for key in list(h.attrs):
   if key.startswith('observatory_'):del h.attrs[key]
 response=client.post('/api/import',headers={'X-Filename':path.name},content=path.read_bytes())
 assert response.status_code==422 and 'missing' in response.json()['detail']


def test_renamed_subset_folder_is_discovered_without_rewriting_metadata(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path)
 saved,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 original=science.source_file(saved);sidecar=original.parent/(saved['id']+'.json');before=sidecar.read_bytes()
 moved=original.parent.rename(tmp_path/'subsets'/'Venezuela')
 found=list(saved_items(tmp_path));assert len(found)==1 and found[0]['id']==saved['id']
 assert science.source_file(found[0])==moved/original.name
 assert (moved/sidecar.name).read_bytes()==before
 assert client.get('/api/local').json()[0]['id']==saved['id']


def test_relocated_subset_symlink_cannot_read_outside_data(tmp_path):
 from backend.subset_storage import subset_file
 ident='subset-'+'a'*32;outside=tmp_path/'outside.h5';outside.write_bytes(b'private')
 directory=tmp_path/'subsets'/'Venezuela';directory.mkdir(parents=True)
 (directory/(ident+'.json')).write_text('{}');(directory/'scene.h5').symlink_to(outside)
 item={'id':ident,'subset_path':'GUNW_2026-10-18_21-45-30_UTC/scene.h5'}
 assert not subset_file(tmp_path,item).is_file()
