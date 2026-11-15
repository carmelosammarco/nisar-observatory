import pytest
from fastapi.testclient import TestClient
from backend import app as module

@pytest.fixture
def cache(tmp_path,monkeypatch):
 for folder in ['arrays','raw','subsets','jobs']:(tmp_path/folder).mkdir()
 for folder in ['raw','subsets','jobs']:(tmp_path/folder/'keep').write_bytes(b'preserve')
 (tmp_path/'arrays'/'a.npz').write_bytes(b'12345')
 (tmp_path/'arrays'/'b.tmp').write_bytes(b'123')
 (tmp_path/'arrays'/'linked.npz').symlink_to(tmp_path/'raw'/'keep')
 (tmp_path/'arrays'/'nested').mkdir()
 (tmp_path/'arrays'/'nested'/'keep').write_bytes(b'preserve')
 monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS',{})
 return TestClient(module.app),tmp_path

def test_size_and_clear_keep_sources_results_links_and_subfolders(cache):
 client,root=cache
 assert client.get('/api/cache').json()=={'files':2,'bytes':8,'can_clear':True}
 response=client.delete('/api/cache')
 assert response.status_code==200
 assert response.json()=={'files':0,'bytes':0,'can_clear':True,'removed_files':2,'freed_bytes':8,'failed_files':0}
 for folder in ['raw','subsets','jobs']:assert (root/folder/'keep').read_bytes()==b'preserve'
 assert (root/'arrays'/'linked.npz').is_symlink()
 assert (root/'arrays'/'nested'/'keep').exists()
 assert client.delete('/api/cache').json()['removed_files']==0

@pytest.mark.parametrize('status',['queued','running'])
def test_busy_cache_cannot_be_cleared(cache,status):
 client,root=cache;module.JOBS['test']={'status':status}
 assert client.get('/api/cache').json()['can_clear'] is False
 assert client.delete('/api/cache').status_code==409
 assert (root/'arrays'/'a.npz').exists()

def test_symlink_cache_directory_rejected(cache):
 client,root=cache
 (root/'arrays').rename(root/'old-arrays');(root/'arrays').symlink_to(root/'raw',target_is_directory=True)
 assert client.delete('/api/cache').status_code==409
 assert (root/'raw'/'keep').exists()

def test_cross_origin_cache_clear_is_rejected(cache):
 client,root=cache
 assert client.delete('/api/cache',headers={'Origin':'https://evil.example'}).status_code==403
 assert (root/'arrays'/'a.npz').exists()
