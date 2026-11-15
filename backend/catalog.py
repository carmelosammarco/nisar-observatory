"""Public CMR discovery. Only catalog-resolved NASA/ASF assets may be fetched."""
from datetime import datetime,timezone
import re,math
from urllib.parse import urlparse
import requests
PRODUCTS={'GCOV':2,'GUNW':2,'GOFF':2,'SME2':3}
ARCHIVE_MATURITIES=('VALIDATED','PROVISIONAL','BETA')
def validate_bbox(bbox):
 if len(bbox)!=4: raise ValueError('Use west, south, east, north coordinates.')
 w,s,e,n=map(float,bbox)
 if not all(math.isfinite(v) for v in (w,s,e,n)) or not(-180<=w<e<=180 and -85<=s<n<=85): raise ValueError('Select an ordered rectangle between 85°S and 85°N; split dateline areas.')
 if (e-w)*(n-s)>100: raise ValueError('Start with an area smaller than 100 square degrees.')
 return [w,s,e,n]
def allowed_url(url):
 try:
  p=urlparse(url)
  return bool(p.scheme=='https' and not p.username and not p.password and p.port in (None,443) and p.hostname and (p.hostname.endswith('.asf.alaska.edu') or p.hostname.endswith('.earthdatacloud.nasa.gov') or p.hostname=='datapool.asf.alaska.edu'))
 except (ValueError,TypeError):return False

def filename_interval(name,product):
 stamps=re.findall(r'\d{8}T\d{6}',name)
 count=4 if product in ('GUNW','GOFF') else 2
 if len(stamps)!=count:raise ValueError('Use an original NISAR filename with all acquisition timestamps (four for GUNW/GOFF).')
 try:times=[datetime.strptime(t,'%Y%m%dT%H%M%S') for t in stamps]
 except ValueError:raise ValueError('The filename contains an invalid acquisition timestamp.') from None
 if any(times[j]>times[j+1] for j in range(0,count,2)):raise ValueError('Acquisition start must precede its end.')
 if count==4 and times[2]<=times[0]:raise ValueError('The secondary acquisition must follow the reference acquisition.')
 # Pair rates use reference start -> secondary start, not the duration of one pass.
 return times[0].isoformat()+'Z',times[2 if count==4 else 1].isoformat()+'Z'

def group_key(name,product):
 p=name.split('_')
 try:
  return '_'.join((p[5:10] if product in ('GCOV','SME2') else [p[5],p[6],p[7],p[9],p[10]])+[p[-5]])
 except IndexError:return name


class CatalogError(RuntimeError):
 """Safe discovery diagnostics; never includes authentication or raw server HTML."""
 def __init__(self,message,code,*,status=None,request_id=None,retryable=True):
  super().__init__(message)
  self.diagnostics={'service':'NASA CMR','code':code,'http_status':status,
                    'request_id':request_id,'retryable':retryable}
 def result(self):
  return {'error':str(self),'error_details':self.diagnostics,'items':[],
          'hits':None,'availability':'unknown'}

def catalog_page(params):
 try:
  response=requests.get('https://cmr.earthdata.nasa.gov/search/granules.json',params=params,timeout=45)
 except requests.Timeout:
  raise CatalogError('NASA’s catalog did not respond in time. File availability is unknown; retry the search later.','timeout') from None
 except requests.ConnectionError:
  raise CatalogError('The app could not reach NASA’s catalog. File availability is unknown; check network access and retry.','connection') from None
 request_id=str(response.headers.get('CMR-Request-Id','')).split(',')[0].strip()
 request_id=request_id if re.fullmatch(r'[A-Za-z0-9_-]{1,100}',request_id) else None
 status=getattr(response,'status_code',200)
 try:payload=response.json()
 except (ValueError,requests.exceptions.JSONDecodeError):
  raise CatalogError('NASA’s catalog returned an unreadable response. File availability is unknown; retry later.','invalid_response',status=status,request_id=request_id) from None
 errors=payload.get('errors') if isinstance(payload,dict) else None
 if status>=400 or errors:
  detail=str(errors or '')
  if 'index_closed_exception' in detail:
   message='NASA’s catalog search index is temporarily closed. File availability is unknown; retry later. Your Earthdata sign-in is not used for this public search.';code='index_closed'
  elif 'Elasticsearch' in detail:
   message='NASA’s catalog reported an internal search-index error. File availability is unknown; retry later.';code='search_index'
  elif status in (429,500,502,503,504):
   message=f'NASA’s catalog is temporarily unavailable (HTTP {status}). File availability is unknown; retry later.';code='service_unavailable'
  else:
   message=f'NASA’s catalog rejected the search (HTTP {status}). Availability is unknown; report the diagnostics if retrying does not help.';code='request_rejected'
  raise CatalogError(message,code,status=status,request_id=request_id,retryable=code!='request_rejected')
 if not isinstance(payload,dict) or not isinstance(payload.get('feed'),dict) or not isinstance(payload['feed'].get('entry'),list):
  raise CatalogError('NASA’s catalog returned an unexpected response. File availability is unknown; retry later.','invalid_response',status=status,request_id=request_id)
 return response,payload['feed']['entry']

def search(product,bbox,start,end,limit=5000,maturity="PROVISIONAL"):
 if maturity not in ARCHIVE_MATURITIES:raise ValueError('Choose Validated, Provisional or Beta archive release.')
 if product not in PRODUCTS:raise ValueError('Unsupported product.')
 if maturity=='VALIDATED' and PRODUCTS[product]>2:raise ValueError('Validated discovery is available for Level 2 GCOV, GUNW and GOFF.')
 release_suffix='' if maturity=='VALIDATED' else '_'+maturity
 bbox=validate_bbox(bbox)
 datetime.strptime(start,'%Y-%m-%d');datetime.strptime(end,'%Y-%m-%d')
 if start>end:raise ValueError('Start must precede end.')
 params={'short_name':f'NISAR_L{PRODUCTS[product]}_{product}{release_suffix}_V1','bounding_box':','.join(map(str,bbox)),'temporal':f'{start}T00:00:00Z,{end}T23:59:59Z','page_size':min(limit,200),'sort_key':'start_date'}
 if not isinstance(limit,int) or not 1<=limit<=5000:raise ValueError('Catalog limit must be an integer between 1 and 5000.')
 page_size=min(limit,200);entries=[];seen=set();page=1;hits=None;query=None
 while len(entries)<limit:
  params['page_num']=page;params['page_size']=page_size
  r,batch=catalog_page(params)
  hits=int(r.headers.get('CMR-Hits',len(batch))) if hits is None else hits;query=query or r.url
  fresh=[e for e in batch if e.get('id') not in seen]
  if not fresh:break
  entries.extend(fresh[:limit-len(entries)]);seen.update(e['id'] for e in fresh)
  if len(entries)>=hits or len(batch)<params['page_size']:break
  page+=1
 items=[]
 for e in entries:
  name=e.get('producer_granule_id',e.get('title',''))
  urls=[l['href'] for l in e.get('links',[]) if not l.get('inherited') and '.h5' in l.get('href','').lower() and 'QA_STATS' not in l.get('href','') and allowed_url(l['href'])]
  if not urls:continue
  try:acquisition_start,acquisition_end=filename_interval(name,product)
  except ValueError:continue
  items.append({'id':e['id'],'name':name,'product':product,'maturity':maturity,'start':acquisition_start,'end':acquisition_end,'catalog_start':e.get('time_start'),'catalog_end':e.get('time_end'),'size_mb':float(e.get('granule_size',0)),'url':urls[0],'group':group_key(name,product),'boxes':e.get('boxes',[]),'polygons':e.get('polygons',[])})
 return {'hits':hits or 0,'items':items,'query':query,'fetched_at':datetime.now(timezone.utc).isoformat(),'truncated':(hits or 0)>len(entries),'records_fetched':len(entries),'records_skipped':len(entries)-len(items),'collection':params['short_name'],'maturity':maturity,'scope_note':f'Search covers the named {maturity} V1 collection only. Other releases are searched separately. Up to 5000 catalog records per product are fetched with pagination.'}
