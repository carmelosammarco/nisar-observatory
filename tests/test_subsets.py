"""Native area extraction, equality, persistence, cancellation and access control."""
from backend.execution import ProcessingCancelled
import io,json
from types import SimpleNamespace
import h5py,numpy as np,pytest
from fastapi.testclient import TestClient
from backend import app as module,science,subsets
from test_pipeline import fixture_bytes

BBOX=[-114.74,36.14,-114.72,36.16]

def setup(monkeypatch,tmp_path,product='GCOV'):
 from backend import examples
 monkeypatch.setattr(examples,'saved_inputs',lambda:iter(()))
 for m in [module,science]:monkeypatch.setattr(m,'DATA',tmp_path)
 (tmp_path/'raw').mkdir();(tmp_path/'jobs').mkdir()
 monkeypatch.setattr(module,'JOBS_DIR',tmp_path/'jobs');monkeypatch.setattr(module,'JOBS',{});monkeypatch.setattr(module,'CATALOG',{})
 item={'id':'local-'+'a'*16,'name':f'NISAR_L2_PR_{product}_001_001_A_001_4005_DHDH_A_20260801T000000_20260801T000030_M00100_P_F_J_001.h5','product':product,'group':'synthetic-one','start':'2026-08-01T00:00:00Z','end':'2026-08-01T00:00:30Z','url':'','size_mb':1}
 (tmp_path/'raw'/(item['id']+'.h5')).write_bytes(fixture_bytes(product,0));module.CATALOG[item['id']]=item
 return item,TestClient(module.app)

@pytest.mark.parametrize('product',['GCOV','GUNW','GOFF','SME2'])
def test_subset_matches_native_and_processed_values_for_every_product(monkeypatch,tmp_path,product):
 item,client=setup(monkeypatch,tmp_path,product)
 result,transferred,reused=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 assert result['subset'] and transferred==0 and not reused
 assert result['size_mb']>0 and result['source_id']==item['id']
 grid=science.target_grid(BBOX,100)
 a=science.load_observation(item,BBOX,grid,{},lambda:False)
 b=science.load_observation(result,BBOX,grid,{},lambda:False)
 np.testing.assert_allclose(a['array'],b['array'],equal_nan=True)
 assert a['wavelength']==b['wavelength']
 assert a['quality_paths']==b['quality_paths']
 assert b['attrs']['source_subset']['bbox']==BBOX
 for key in a['aux']:np.testing.assert_allclose(a['aux'][key],b['aux'][key],equal_nan=True)
 with h5py.File(science.source_file(item)) as full,h5py.File(science.source_file(result)) as cropped:
  for path in result['retained_layers']:
   assert cropped[path].shape[0]<full[path].shape[0] and cropped[path].shape[1]<full[path].shape[1]
   assert cropped[path].dtype==full[path].dtype
  assert cropped.attrs['observatory_subset_version']=='area-1'
 # Reuse returns without opening any source and inventory survives a fresh catalog.
 monkeypatch.setattr(science,'open_science',lambda *a:pytest.fail('duplicate should not reopen source'))
 again,count,hit=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 assert again['id']==result['id'] and count==0 and hit
 module.CATALOG.clear();inventory=client.get('/api/local').json()
 assert any(i['id']==result['id'] for i in inventory)
 assert result['id'] in module.CATALOG


def test_range_backed_source_is_subset_without_full_download(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path)
 content=science.source_file(item).read_bytes();science.source_file(item).unlink()
 from contextlib import contextmanager
 reads=[]
 @contextmanager
 def remote(selected,cancel):
  reads.append(selected['id'])
  with h5py.File(io.BytesIO(content),'r') as f:yield f,SimpleNamespace(bytes=4096)
 monkeypatch.setattr(science,'open_science',remote)
 result,count,hit=subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 assert count==4096 and reads==[item['id']] and not hit
 assert not list((tmp_path/'raw').glob('*.h5'))
 assert science.source_file(result).exists()


def test_cancel_leaves_no_partial_subset(monkeypatch,tmp_path):
 item,_=setup(monkeypatch,tmp_path)
 with pytest.raises(ProcessingCancelled,match='Cancelled'):subsets.extract(item,BBOX,lambda:True,lambda *a:None)
 assert not list((tmp_path/'subsets').glob('*'))


def test_rejects_outside_area_and_disconnected_remote(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path)
 result,_,_=subsets.extract(item,BBOX,lambda:False,lambda *a:None);module.CATALOG[result['id']]=result
 with pytest.raises(ValueError,match='extends beyond'):subsets.extract(result,[-115,36,-114,37],lambda:False,lambda *a:None)
 request={'bbox':[-115,36,-114,37],'granules':[result['id']],'projects':['P01'],'options':{}}
 assert client.post('/api/run',json=request).status_code==422
 assert client.post('/api/download-area',json={'bbox':request['bbox'],'granules':[result['id']]}).status_code==422
 science.source_file(item).unlink();monkeypatch.setattr(module.AUTH,'session',None)
 assert client.post('/api/download-area',json={'bbox':[-114.75,36.13,-114.71,36.17],'granules':[item['id']]}).status_code==401
 assert client.post('/api/download-area',json={'bbox':[0,0,0,0],'granules':[item['id']]}).status_code==422
 assert client.post('/api/download-area',json={'bbox':BBOX,'granules':['unknown']}).status_code==422


def test_api_worker_queues_unique_files_and_retains_actual_sizes(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path);calls=[]
 monkeypatch.setattr(module,'POOL',SimpleNamespace(submit=lambda *a:calls.append(a)))
 response=client.post('/api/download-area',json={'bbox':BBOX,'granules':[item['id'],item['id']]})
 assert response.status_code==200,response.text
 worker,job,items,bbox=calls[0];assert len(items)==1
 worker(job,items,bbox)
 assert job['status']=='completed' and len(job['saved_areas'])==1
 assert job['bytes_transferred']==0 and 'MB on disk' in job['message']
 # Offline processing authorization uses the saved subset, not the original HDF5 path.
 saved=job['saved_areas'][0];monkeypatch.setattr(module.AUTH,'session',None)
 monkeypatch.setattr(module,'JOBS',{})
 response=client.post('/api/run',json={'bbox':BBOX,'granules':[saved['id']],'projects':['P01'],'options':{}})
 # Offline authorization succeeded; readiness correctly rejects the single-date flood comparison.
 assert response.status_code==422 and 'at least 2' in response.json()['detail'],response.text


def test_oversize_no_overlap_and_failed_worker_are_explicit(monkeypatch,tmp_path):
 item,client=setup(monkeypatch,tmp_path)
 with pytest.raises(ValueError,match='overlap'):subsets.extract(item,[10,10,11,11],lambda:False,lambda *a:None)
 assert not list((tmp_path/'subsets').glob('*.part'))
 monkeypatch.setattr(subsets,'MAX_ARRAY_BYTES',1)
 with pytest.raises(ValueError,match='512 MiB'):subsets.extract(item,BBOX,lambda:False,lambda *a:None)
 job=module.newjob('area_download');module.area_download_work(job,[item],BBOX)
 assert job['status']=='needs_input' and not job['saved_areas'] and job['source_errors']
 assert not list((tmp_path/'subsets').glob('*.h5'))
