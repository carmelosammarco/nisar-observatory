from backend.execution import ProcessingCancelled
import io
from types import SimpleNamespace
import pytest
from backend import access
class Response:
 def __init__(self,content,status=206,headers=None):self.content=content;self.status_code=status;self.headers=headers or {};self.raw=io.BytesIO(content)
 def close(self):pass
 def __enter__(self):return self
 def __exit__(self,*a):self.close()
 def raise_for_status(self):
  if self.status_code>=400:raise ValueError('HTTP failure')
 def iter_content(self,n):
  for i in range(0,len(self.content),n):yield self.content[i:i+n]
class Session:
 def __init__(self,content):self.content=content;self.calls=0
 def get(self,url,headers=None,**kwargs):
  self.calls+=1
  if headers and 'Range' in headers:
   a,b=map(int,headers['Range'].removeprefix('bytes=').split('-'));b=min(b,len(self.content)-1)
   return Response(self.content[a:b+1],206,{'Content-Range':f'bytes {a}-{b}/{len(self.content)}'})
  return Response(self.content,200,{'Content-Length':str(len(self.content))})
def test_range_reader_cache_and_budget(monkeypatch):
 content=b'\x89HDF\r\n\x1a\n'+b'x'*(2*1024**2)
 session=Session(content);monkeypatch.setattr(access.AUTH,'session',session)
 reader=access.RangeReader('https://nisar.asf.earthdatacloud.nasa.gov/a.h5',budget=1024**2)
 assert reader.read(8)==content[:8]
 reader.seek(10);assert reader.read(4)==b'xxxx'
 assert session.calls==2
 reader.seek(1024**2)
 with pytest.raises(ValueError,match='transfer limit'):reader.read(1)
 reader.close()
def test_download_atomicity_and_cancel(monkeypatch,tmp_path):
 content=b'\x89HDF\r\n\x1a\n'+b'x'*100
 monkeypatch.setattr(access,'DATA',tmp_path);monkeypatch.setattr(access.AUTH,'session',Session(content))
 item={'id':'test','url':'https://nisar.asf.earthdatacloud.nasa.gov/a.h5'}
 with pytest.raises(ProcessingCancelled,match='Cancelled'):access.download(item,lambda:True,lambda n,t:None)
 assert not list((tmp_path/'raw').glob('*.part'))
 path=access.download(item,lambda:False,lambda n,t:None)
 assert open(path,'rb').read()==content
