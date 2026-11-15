"""RAM-only Earthdata session and bounded HTTP range access to science files."""
from .execution import checkpoint
import io, threading, re, json
from pathlib import Path
import requests
from .catalog import allowed_url,search
from urllib.parse import urlparse
from datetime import datetime,timedelta,timezone
from requests.auth import HTTPBasicAuth
from .runtime_storage import runtime_directory
DATA=runtime_directory(Path(__file__).resolve().parents[1]/'data')
class EarthdataSession(requests.Session):
 """Send Basic credentials only to Earthdata Login, including redirect authentication.
 NASA cookies are kept in RAM. No legacy ASF cookie gate or persistent API token.
 """
 def __init__(self,username,password):
  super().__init__();self.trust_env=False;self._credential=HTTPBasicAuth(username,password)
 def prepare_request(self,request):
  self._https_only(request.url)
  prepared=super().prepare_request(request)
  if urlparse(prepared.url).hostname=='urs.earthdata.nasa.gov':self._credential(prepared)
  return prepared
 def rebuild_auth(self,prepared,response):
  self._https_only(prepared.url)
  prepared.headers.pop('Authorization',None)
  if urlparse(prepared.url).hostname=='urs.earthdata.nasa.gov':self._credential(prepared)
 @staticmethod
 def _https_only(url):
  p=urlparse(url)
  if p.scheme!='https' or p.username or p.password or p.port not in (None,443):raise ValueError('NASA authentication and file transfers require HTTPS without embedded credentials.')
 def close(self):
  self._credential=None;self.cookies.clear();super().close()
class ScienceAccessError(ValueError):
 def __init__(self,message,status_code=503):
  super().__init__(message);self.status_code=status_code

def verification_urls():
 """Keep login usable during a CMR outage without skipping a real archive check."""
 now=datetime.now(timezone.utc);end=now.strftime('%Y-%m-%d');start=(now-timedelta(days=120)).strftime('%Y-%m-%d')
 urls=[]
 try:
  found=search('GCOV',[-114.76,36.12,-114.70,36.18],start,end,limit=1)
  urls=[item['url'] for item in found['items'] if allowed_url(item['url'])]
 except requests.RequestException:
  pass # Catalog discovery is public and must not be mistaken for bad credentials.
 probes=Path(__file__).resolve().parents[1]/'docs/science-access-probes.json'
 if probes.is_file():
  urls.extend(item['url'] for item in json.loads(probes.read_text())['sources'] if allowed_url(item['url']))
 return list(dict.fromkeys(urls))

class Credentials:
 def __init__(self):self.session=None;self.lock=threading.Lock();self.verified=False
 def login(self,username,password):
  self.logout()
  candidate=EarthdataSession(username,password)
  try:
   urls=verification_urls()
   if not urls:raise ScienceAccessError('NASA catalog discovery is unavailable and no verification file is configured. Your credentials could not be checked. Try again later.')
   failure=None
   for url in urls[:3]:
    try:
     with candidate.get(url,headers={'Range':'bytes=0-7','Accept-Encoding':'identity'},stream=True,timeout=(15,30)) as response:
      status=response.status_code
      if status in (401,403):
       raise ScienceAccessError('NASA did not authorize science-file access (HTTP '+str(status)+'). Check your Earthdata credentials and authorize the ASF/NASA data application in Earthdata Login. A browser sign-in alone may not grant archive access.',401)
      if status in (404,410,408,429) or status>=500:
       failure=ScienceAccessError('NASA science-file verification is temporarily unavailable (HTTP '+str(status)+'). Your credentials could not be verified. Try again later; local files and Examples remain usable.')
       continue
      if status!=206:
       raise ScienceAccessError('NASA did not return the requested science-file header. Complete any required application authorization at Earthdata Login, then try again. No complete file was downloaded.',502)
      if not re.fullmatch(r'bytes 0-7/\d+',response.headers.get('Content-Range','')) or response.raw.read(9)!=b'\x89HDF\r\n\x1a\n':
       raise ScienceAccessError('NASA returned an invalid science-file verification response. No session was established. Try again later.',502)
     break
    except ScienceAccessError:
     raise
    except requests.exceptions.SSLError:
     failure=ScienceAccessError('A secure connection to NASA could not be verified. Check your computer clock and network/VPN certificate configuration; certificate checking remains enabled.',502)
    except requests.exceptions.Timeout:
     failure=ScienceAccessError('The NASA science-access check timed out. Your credentials could not be verified. Check your connection and try again.')
    except requests.exceptions.ConnectionError:
     failure=ScienceAccessError('The app could not reach NASA Earthdata Login or its science archive. Check your internet connection, VPN or firewall and try again. Your credentials could not be verified.')
    except requests.RequestException:
     failure=ScienceAccessError('NASA science-access verification was interrupted. Your credentials could not be verified. Try again; local files and Examples remain usable.')
   else:
    raise failure or ScienceAccessError('No NASA verification file is currently available. Try again later.')
   with self.lock:
    if self.session:self.session.close()
    self.session=candidate;self.verified=True
  except Exception:
   candidate.close();raise
 def logout(self):
  with self.lock:
   if self.session:self.session.close()
   self.session=None;self.verified=False
AUTH=Credentials()
class RangeReader(io.RawIOBase):
 """HDF5 file object backed by 1 MiB blocks. Never silently downloads a full file."""
 def __init__(self,url,budget=256*1024**2):
  if not allowed_url(url):raise ValueError('The asset is not an approved NASA/ASF catalog URL.')
  if not AUTH.session:raise ValueError('Connect Earthdata in Settings before reading science data.')
  self.url=url;self.pos=0;self.bytes=0;self.budget=budget;self.block=1024**2;self.cache={};self.cancel=lambda:False
  r=AUTH.session.get(url,headers={'Range':'bytes=0-7','Accept-Encoding':'identity'},stream=True,timeout=60)
  try:
   if r.status_code!=206:raise ValueError(f'NASA did not accept range access (HTTP {r.status_code}). Check Earthdata authorization or use a downloaded file.')
   match=re.fullmatch(r'bytes 0-7/(\d+)',r.headers.get('Content-Range',''))
   if not match or int(match[1])<8:raise ValueError('NASA returned an invalid file-size range header.')
   self.size=int(match[1])
   if r.raw.read(9)!=b'\x89HDF\r\n\x1a\n':raise ValueError('The response is not a bounded HDF5 science-file header.')
  finally:r.close()
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
  if self.pos<0:raise ValueError('Negative seek.')
  return self.pos
 def readinto(self,b):
  v=self.read(len(b));b[:len(v)]=v;return len(v)
 def read(self,n=-1):
  checkpoint(self.cancel)
  if n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos)
  if n<=0:return b''
  parts=[];stop=self.pos+n
  while self.pos<stop:
   key=self.pos//self.block
   if key not in self.cache:
    a=key*self.block;z=min(a+self.block,self.size)-1
    if self.bytes+z-a+1>self.budget:raise ValueError('The 256 MiB per-file transfer limit was reached. Narrow the area or use a local file.')
    r=AUTH.session.get(self.url,headers={'Range':f'bytes={a}-{z}','Accept-Encoding':'identity'},stream=True,timeout=90)
    try:
     if r.status_code!=206:raise ValueError(f'Range transfer failed (HTTP {r.status_code}).')
     if r.headers.get('Content-Range')!=f'bytes {a}-{z}/{self.size}':raise ValueError('NASA returned a different byte range than requested.')
     content=r.raw.read(z-a+2)
     if len(content)!=z-a+1:raise ValueError('Incomplete range response.')
     self.cache[key]=content;self.bytes+=len(content)
    finally:r.close()
   content=self.cache[key];off=self.pos%self.block;take=min(stop-self.pos,len(content)-off)
   parts.append(content[off:off+take]);self.pos+=take
  return b''.join(parts)
 def close(self):
  self.cache.clear();super().close()

def download(item,cancel,progress,max_bytes=8*1024**3):
 target=DATA/'raw'/f"{item['id']}.h5";target.parent.mkdir(exist_ok=True)
 if target.exists():return str(target)
 from .storage_budget import require_space
 require_space(target,operation='Full-original download')
 if not AUTH.session:raise ValueError('Connect Earthdata first.')
 if not allowed_url(item['url']):raise ValueError('Unapproved asset URL.')
 temp=target.with_suffix('.part')
 try:
  with AUTH.session.get(item['url'],headers={'Accept-Encoding':'identity'},stream=True,timeout=90) as r:
   r.raise_for_status();total=int(r.headers.get('Content-Length',0))
   if total>max_bytes:raise ValueError('File exceeds the 8 GiB full-download limit; use area streaming.')
   require_space(target,total+65536,operation='Full-original download')
   count=0
   with temp.open('wb') as f:
    for chunk in r.iter_content(1024**2):
     checkpoint(cancel)
     count+=len(chunk)
     if count>max_bytes:raise ValueError('Download limit exceeded.')
     require_space(target,len(chunk)+65536,operation='Full-original download')
     f.write(chunk);progress(count,total)
   if total and count!=total:raise ValueError('The download ended before the complete file arrived. Try again.')
   with temp.open('rb') as f:
    if f.read(8)!=b'\x89HDF\r\n\x1a\n':raise ValueError('NASA returned a login page instead of HDF5. Review Earthdata application authorization.')
  checkpoint(cancel)
  temp.replace(target);return str(target)
 finally:
  if temp.exists():temp.unlink()
