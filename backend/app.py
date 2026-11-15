from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from urllib.parse import urlparse
import json,uuid,threading,re,shutil,functools,copy,tempfile
from contextlib import asynccontextmanager
import asyncio
from .runtime_storage import RuntimeLease,atomic_json,guarded_json,load_jobs,JOB_ID
from .execution import execution_scope,ProcessingCancelled,checkpoint
from .render_admission import render_admission
from datetime import date
from typing import Literal
from fastapi.exceptions import RequestValidationError
import numpy as np
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,SecretStr,ConfigDict,StrictBool,AwareDatetime,field_validator,model_validator
from .catalog import search,validate_bbox,group_key,PRODUCTS,filename_interval,CatalogError
from .access import AUTH,DATA,download,ScienceAccessError
from .science import load_observation,target_grid,open_science,datasets,decode,grid_for,source_file
from .processors import process
from .engines import PRODUCT_FOR
from .los import phase_group
from .spatial import validate_context
from .exports import export_result
from .map_styles import is_category,validate_colors,validate_opacity,category_entries
from .reference import reference_assistant,reference_fingerprint,REFERENCE_PRODUCTS
from .subsets import extract as extract_subset,saved_subset,contains
from .subset_storage import saved_items,new_folder
from .subset_import import metadata as subset_import_metadata,store as store_imported_subset
ROOT=Path(__file__).resolve().parents[1]
PLANS=json.loads((ROOT/'docs/tools.json').read_text())
APP_VERSION='0.9.0'
POOL=ThreadPoolExecutor(max_workers=1);CATALOG={};JOBS={};LOCK=threading.RLock()

@asynccontextmanager
async def lifespan(application):
 global POOL
 from .storage_budget import disk_reserve_bytes
 disk_reserve_bytes()
 from .resource_budget import memory_budget_bytes
 memory_budget_bytes()
 lease=RuntimeLease(DATA).acquire()
 application.state.runtime_owner=True
 try:
  recovered,issues=load_jobs(JOBS_DIR,recover=True)
  with LOCK:JOBS.clear();JOBS.update(recovered)
  application.state.storage_issues=issues
  if getattr(POOL,'_shutdown',False):POOL=ThreadPoolExecutor(max_workers=1)
  yield
 finally:
  def persist_shutdown(pending):
   try:savejob(pending)
   except (OSError,ValueError):application.state.storage_issues=getattr(application.state,'storage_issues',[])+['A shutdown job record could not be persisted; its files were preserved.']
  try:
   with LOCK:
    for pending in JOBS.values():
     if pending['status'] in ['queued','running']:pending.update(cancelled=True,message='Server shutdown requested; stopping safely at the next processing boundary.');persist_shutdown(pending)
   await asyncio.get_running_loop().run_in_executor(None,lambda:POOL.shutdown(wait=True,cancel_futures=True))
   with LOCK:
    for pending in JOBS.values():
     if pending['status'] in ['queued','running']:pending.update(status='interrupted',message='Server stopped before completion; saved inputs and committed outputs were preserved.');persist_shutdown(pending)
  finally:
   AUTH.logout();application.state.runtime_owner=False;lease.release()

app=FastAPI(title='NISAR Observatory',version=APP_VERSION,docs_url='/api/reference',redoc_url=None,lifespan=lifespan)
ACTION_LOCK=threading.Lock()
def exclusive_action(function):
 @functools.wraps(function)
 def guarded(*args,**kwargs):
  if not ACTION_LOCK.acquire(blocking=False):raise HTTPException(409,'Another data or connection request is being prepared. Try again shortly.')
  try:return function(*args,**kwargs)
  finally:ACTION_LOCK.release()
 return guarded

@app.exception_handler(RequestValidationError)
async def invalid_request(request,error):
 # FastAPI's default errors include raw submitted input, potentially including passwords.
 if any('reference_observations' in entry.get('loc',()) for entry in error.errors()):return JSONResponse({'detail':'Regional reference fields are invalid. Supply ordered date/end, a finite value, a source citation, and both quantity and unit for a new check. Use los_displacement, radar_component_rate or horizontal_speed; see Area & analysis settings for the allowed units and component names.'},status_code=422)
 return JSONResponse({'detail':'Invalid request. Check the required fields, dates, types and allowed ranges.'},status_code=422)

JOBS_DIR=DATA/'jobs';JOBS_DIR.mkdir(exist_ok=True)
JOBS.update(load_jobs(JOBS_DIR,recover=False)[0])

@app.middleware('http')
async def local_only(request,call_next):
 host=request.headers.get('host','').split(':')[0]
 if host not in ['127.0.0.1','localhost','testserver']:return JSONResponse({'detail':'This service is local only.'},403)
 origin=request.headers.get('origin')
 if origin and (urlparse(origin).hostname not in ['127.0.0.1','localhost','testserver'] or urlparse(origin).netloc!=request.headers.get('host')):return JSONResponse({'detail':'Cross-origin requests are disabled.'},403)
 response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';response.headers['X-Frame-Options']='DENY';response.headers.setdefault('Content-Security-Policy',"frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
 if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
 elif request.url.path=='/' or request.url.path.endswith(('.html','.js','.css')):response.headers['Cache-Control']='no-cache'
 return response

class Login(BaseModel):
 model_config=ConfigDict(extra='forbid')
 username:str=Field(min_length=1,max_length=100)
 password:SecretStr=Field(min_length=1,max_length=200)
class SearchQuery(BaseModel):
 bbox:list[float];start:str;end:str;products:list[str]=['GCOV']
 maturity:Literal['VALIDATED','PROVISIONAL','BETA']='PROVISIONAL'
 @field_validator('start','end')
 @classmethod
 def valid_date(cls,value):
  if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Use an ISO calendar date.')
  date.fromisoformat(value);return value
 @model_validator(mode='after')
 def ordered_dates(self):
  if self.start>self.end:raise ValueError('Start must precede end.')
  return self
from .analysis_options import AnalysisOptions,RegionalReference

from .display_settings import DisplaySettings

class RunQuery(BaseModel):
 bbox:list[float];granules:list[str]=Field(max_length=32);projects:list[str]=Field(max_length=10);options:dict=Field(default_factory=dict);display:DisplaySettings|None=None
 @field_validator('options')
 @classmethod
 def typed_options(cls,value):return AnalysisOptions.model_validate(value).model_dump(mode='json',exclude_unset=True)
class DownloadQuery(BaseModel):granules:list[str]=Field(min_length=1)
class AreaDownloadQuery(BaseModel):
 model_config=ConfigDict(extra='forbid')
 bbox:list[float]
 granules:list[str]=Field(min_length=1)

def savejob(j):
 with LOCK:
  if not JOB_ID.fullmatch(j['id']):raise ValueError('Invalid job identifier.')
  directory=JOBS_DIR/j['id']
  if directory.is_symlink():raise ValueError('Job folders cannot be symbolic links.')
  directory.mkdir(exist_ok=True)
  atomic_json(directory/'job.json',j)
def update(j,**values):
 with LOCK:j.update(values);savejob(j)
def record_result(j,pid,result):
 with LOCK:j['results'][pid]=result;savejob(j)
def busy():
 with LOCK:return any(j['status'] in ['queued','running'] for j in JOBS.values())
def array_cache_files():
 directory=DATA/'arrays'
 if directory.is_symlink():raise HTTPException(409,'The array cache must be a regular folder.')
 if not directory.exists():return []
 return [p for p in directory.iterdir() if not p.is_symlink() and p.is_file()]
def cache_status():
 files=array_cache_files()
 return {'files':len(files),'bytes':sum(p.stat().st_size for p in files),'can_clear':not busy()}
@app.get('/api/cache')
def get_cache():
 with LOCK:return cache_status()
@app.delete('/api/cache')
@exclusive_action
def clear_cache():
 with LOCK:
  if busy():raise HTTPException(409,'Finish or cancel the active job before clearing the array cache.')
  removed=freed=failed=0
  for path in array_cache_files():
   try:
    size=path.stat().st_size;path.unlink();removed+=1;freed+=size
   except OSError:failed+=1
  return {**cache_status(),'removed_files':removed,'freed_bytes':freed,'failed_files':failed}
@app.get('/api/health')
def health():return {'status':'ok','earthdata_connected':AUTH.verified,'version':APP_VERSION,'runtime':'project .venv','science_validation':'exploratory; see docs/VALIDATION.md','runtime_owner':getattr(app.state,'runtime_owner',False),'storage_warning_count':len(getattr(app.state,'storage_issues',[]))}
@app.post('/api/auth')
@exclusive_action
def login(body:Login):
 if busy():raise HTTPException(409,'Wait for the active job before changing Earthdata sessions.')
 try:AUTH.login(body.username,body.password.get_secret_value())
 except ScienceAccessError as e:raise HTTPException(e.status_code,str(e))
 except ValueError as e:raise HTTPException(401,str(e))
 except Exception:raise HTTPException(502,'NASA science-access verification could not finish. No session was established. Please try again; local files and Examples remain usable.')
 return {'connected':True,'storage':'RAM only; erased when this service stops.'}
@app.delete('/api/auth')
@exclusive_action
def logout():
 if busy():raise HTTPException(409,'Cancel or finish the active job first.')
 AUTH.logout();return {'connected':False}
@app.get('/api/projects')
def projects():return PLANS
@app.get('/api/library')
def library():return json.loads((ROOT/'docs/mission.json').read_text())
@app.post('/api/search')
def discover(body:SearchQuery):
 try:
  validate_bbox(body.bbox)
  if not body.products or any(p not in PRODUCTS for p in body.products):raise ValueError('Choose supported products.')
 except ValueError as e:raise HTTPException(422,str(e))
 saved={i['name']:i for i in local() if not i.get('subset')}
 results={}
 def one(p):
  try:return p,search(p,body.bbox,body.start,body.end,**({'maturity':body.maturity} if body.maturity!='PROVISIONAL' else {}))
  except CatalogError as e:return p,e.result()
  except ValueError as e:return p,{'error':str(e),'items':[],'hits':None,'availability':'unknown'}
  except Exception:return p,{'error':'The app could not interpret the catalog response. Availability is unknown; report this error if retrying does not help.','error_details':{'code':'unexpected_app_error'},'items':[],'hits':None,'availability':'unknown'}
 with ThreadPoolExecutor(max_workers=4) as pool:
  for p,r in pool.map(one,body.products):
   results[p]=r
   for item in r.get('items',[]):
    stored=saved.get(item['name'])
    if stored:
     item.update(catalog_id=item['id'],id=stored['id'],local=True)
    CATALOG[item['id']]=item
 return results
class InspectQuery(BaseModel):granule:str
@app.post('/api/inspect')
@exclusive_action
def inspect(body:InspectQuery):
 if body.granule not in CATALOG:raise HTTPException(404,'Search or import this file first.')
 if busy():raise HTTPException(409,'Wait for the current transfer or processing job before inspecting another file.')
 try:
  with open_science(CATALOG[body.granule],lambda:False) as (f,stream):
   inventory=[]
   for path in datasets(f):
    ds=f[path]
    entry={'path':path,'shape':list(ds.shape),'units':decode(ds.attrs.get('units','not declared')),'description':decode(ds.attrs.get('description','')),'flag_values':decode(ds.attrs.get('flag_values',[])),'flag_meanings':decode(ds.attrs.get('flag_meanings',''))}
    try:
     g=grid_for(ds);projection=g['projection'];entry['epsg']=int(projection.attrs.get('epsg_code',projection[()]))
    except (ValueError,KeyError,TypeError):entry['epsg']=None
    inventory.append(entry)
   return {'granule':CATALOG[body.granule]['name'],'layers':inventory,'bytes_transferred':stream.bytes if stream else 0}
 except ValueError as e:raise HTTPException(422,str(e))
 except Exception:raise HTTPException(502,'Science inventory could not be read. Check connection or local file schema.')

@app.get('/api/local')
def local():
 items=[]
 for path in (DATA/'raw').glob('*.json') if (DATA/'raw').exists() else []:
  try:
   item=json.loads(path.read_text())
   if not re.fullmatch(r'(?:local-[a-f0-9]{16}|G[0-9]+-[A-Za-z0-9_-]+)',item['id']):continue
   if not (DATA/'raw'/(item['id']+'.h5')).is_file():continue
   item['start'],item['end']=filename_interval(item['name'],item['product'])
   item['local']=True
   CATALOG[item['id']]=item;items.append(item)
  except (ValueError,KeyError,TypeError,OSError):continue
 from .examples import saved_inputs
 for item in [*saved_items(DATA),*saved_inputs()]:
  item['local']=True;CATALOG[item['id']]=item;items.append(item)
 return list({item['id']:item for item in items}.values())
@app.get('/api/examples')
def examples_list():
 from .examples import CASES,inspect
 return [{k:v for k,v in inspect(i).items() if k not in ['inputs','sources','request']} for i in CASES]

@app.get('/api/examples/{ident}')
def example_detail(ident:str):
 from .examples import inspect
 try:return {k:v for k,v in inspect(ident).items() if k!='inputs'}
 except ValueError as error:raise HTTPException(404,str(error))

@app.get('/api/examples/{ident}/setup')
def example_setup(ident:str):
 from .examples import setup,CASES
 if ident not in CASES:raise HTTPException(404,'Example not found.')
 try:payload=setup(ident)
 except ValueError as error:raise HTTPException(422,str(error))
 for item in payload['items']:CATALOG[item['id']]=item
 return payload

@app.get('/api/examples/{ident}/files/{filename:path}')
def example_asset(ident:str,filename:str):
 from .examples import directory
 try:base=directory(ident)
 except ValueError:raise HTTPException(404,'Example not found.')
 # Raw HDF5 and sidecars are not exposed as arbitrary static files.
 target=base/filename
 if filename not in ['README.md'] and not (filename.startswith(('figures/','references/')) and target.suffix.lower() in ['.png','.jpg','.jpeg','.md','.csv','.json','.geojson']):raise HTTPException(404,'Example asset not found.')
 if not target.resolve().is_relative_to(base.resolve()) or not target.is_file():raise HTTPException(404,'Example asset not found.')
 return FileResponse(target)

@app.post('/api/import')
async def import_file(request:Request):
 name=Path(request.headers.get('x-filename','')).name
 if not name.endswith('.h5'):raise HTTPException(422,'Import a NISAR original or Observatory saved-area .h5 file.')
 hint=next((p for p in PRODUCTS if '_'+p+'_' in name),None)
 if hint and name.startswith('NISAR_') and '__subset_' not in name:
  try:filename_interval(name,hint)
  except ValueError as error:raise HTTPException(422,str(error))
 from .storage_budget import require_space,InsufficientStorage
 try:require_space(DATA,operation='Importing a science file')
 except InsufficientStorage as error:raise HTTPException(507,str(error))
 ident='local-'+uuid.uuid4().hex[:16];raw=DATA/'raw';raw.mkdir(exist_ok=True);temp=raw/(ident+'.part');size=0
 try:
  with temp.open('wb') as f:
   async for chunk in request.stream():
    size+=len(chunk)
    if size>8*1024**3:raise HTTPException(413,'Local file exceeds 8 GiB.')
    try:require_space(raw,len(chunk)+65536,operation='Importing a science file')
    except InsufficientStorage as error:raise HTTPException(507,str(error))
    f.write(chunk)
  with temp.open('rb') as f:
   if f.read(8)!=b'\x89HDF\r\n\x1a\n':raise HTTPException(422,'File is not HDF5.')
  import h5py
  try:
   with h5py.File(temp,'r') as h:
    is_subset=any(k.startswith('observatory_subset') or k=='observatory_requested_bbox' for k in h.attrs)
    if is_subset:
     try:subset_metadata=subset_import_metadata(h)
     except (ValueError,KeyError,TypeError) as error:raise HTTPException(422,'Saved-area import rejected: '+str(error))
    else:
     if '__subset_' in name or name.startswith('subset-'):raise HTTPException(422,'This saved-area file is missing its required subset metadata; it cannot be imported as an original.')
     product=next((p for p in PRODUCTS if '_'+p+'_' in name),None)
     if not product or f'/science/LSAR/{product}' not in h:raise HTTPException(422,'Import an original named NISAR GCOV, GUNW, GOFF or SME2 .h5 file, or a self-describing Observatory area extract.')
     try:acquisition_start,acquisition_end=filename_interval(name,product)
     except ValueError as error:raise HTTPException(422,str(error))
  except HTTPException:raise
  except Exception:raise HTTPException(422,'The file could not be read as a supported NISAR HDF5 product.')
  if is_subset:
   try:item=store_imported_subset(temp,subset_metadata,DATA)
   except ValueError as error:raise HTTPException(422,str(error))
   CATALOG[item['id']]=item;return item
  temp.replace(raw/(ident+'.h5'))
  item={'id':ident,'name':name,'product':product,'start':acquisition_start,'end':acquisition_end,'size_mb':size/1e6,'url':'','group':group_key(name,product),'local':True}
  (raw/(ident+'.json')).write_text(json.dumps(item));CATALOG[ident]=item;return item
 finally:
  if temp.exists():temp.unlink()

@app.get('/api/jobs')
def jobs():
 with LOCK:return copy.deepcopy(sorted(JOBS.values(),key=lambda j:j['created_at'],reverse=True))
@app.get('/api/jobs/{ident}')
def job(ident:str):
 with LOCK:
  if ident not in JOBS:raise HTTPException(404,'Run not found.')
  return copy.deepcopy(JOBS[ident])
@app.delete('/api/jobs/{ident}')
def delete_job(ident:str):
 if not re.fullmatch(r'[a-f0-9]{32}',ident):raise HTTPException(404,'Run not found.')
 with LOCK:
  if ident not in JOBS:raise HTTPException(404,'Run not found.')
  if JOBS[ident]['status'] in ['queued','running']:raise HTTPException(409,'Finish or cancel this run before deleting it.')
  directory=JOBS_DIR/ident
  if directory.is_symlink():raise HTTPException(409,'The run directory is not a regular saved-run folder.')
  try:
   if directory.exists():shutil.rmtree(directory)
  except OSError:raise HTTPException(500,'The saved run could not be fully removed. Check file permissions and try again.')
  del JOBS[ident]
 return {'deleted':ident}
@app.post('/api/jobs/{ident}/cancel')
def cancel(ident:str):
 with LOCK:
  if ident not in JOBS:raise HTTPException(404,'Run not found.')
  if JOBS[ident]['status'] not in ['queued','running']:raise HTTPException(409,'This run has already finished.')
  update(JOBS[ident],cancelled=True,message='Cancellation requested; the current calculation or network read may finish before the next safe stopping point.')
 return {'ok':True}
def newjob(kind,**fields):
 with LOCK:
  j={'id':uuid.uuid4().hex,'kind':kind,'status':'queued','created_at':datetime.now(timezone.utc).isoformat(),'message':'Queued','progress':0,'results':{},'cancelled':False,**fields}
  try:savejob(j)
  except OSError:raise HTTPException(507,'The new run could not be saved. Check runtime folder permissions and free disk space. No job was started.') from None
  JOBS[j['id']]=j;return j
def submit_job(function,job,*args):
 def stopped(message):
  with LOCK:
   if job['status'] not in ['queued','running']:return
   job.update(status='cancelled' if job.get('cancelled') else 'failed',message=message)
   try:savejob(job)
   except (OSError,ValueError):app.state.storage_issues=getattr(app.state,'storage_issues',[])+['A stopped job could not be persisted; saved files were preserved.']
 def guarded(job,*values):
  try:
   with execution_scope(lambda:job.get('cancelled',False)):
    return function(job,*values)
  except ProcessingCancelled:
   job['cancelled']=True
   stopped('Cancelled at a safe processing boundary. Completed results and downloaded inputs were preserved.')
  finally:stopped('The worker stopped before recording completion. Saved files were preserved; check free disk space and the run details before starting a new run.')
 try:return POOL.submit(guarded,job,*args)
 except RuntimeError:
  stopped('The server could not start this job. Saved files were preserved. Restart the app and start a new run when ready.')
  raise HTTPException(503,'The processing worker is shutting down or unavailable. No task was automatically retried.')

def selected_run_items(body):
 try:validate_bbox(body.bbox)
 except ValueError as e:raise HTTPException(422,str(e))
 if busy():raise HTTPException(409,'One processing job can run at a time. Cancel or finish the current run.')
 if not body.projects or any(p not in [x['id'] for x in PLANS] for p in body.projects):raise HTTPException(422,'Choose at least one recognized project.')
 if not body.granules or any(g not in CATALOG for g in body.granules):raise HTTPException(422,'Search or import data before selecting observations.')
 required_products={PRODUCT_FOR[pid] for pid in body.projects}
 items=[CATALOG[g].copy() for g in body.granules if CATALOG[g]['product'] in required_products]
 for item in items:
  if item.get('subset') and not contains(item['subset_bbox'],body.bbox):raise HTTPException(422,'The analysis rectangle extends beyond a saved area. Choose a smaller rectangle or find and save new NASA data.')
 if any(not source_file(item,DATA).exists() for item in items) and not AUTH.session:raise HTTPException(401,'Connect Earthdata in Connection, or import original NISAR files before processing.')
 for prod in PRODUCTS:
  allow=prod=='GUNW' and body.projects==['P04'] and body.options.get('phase_allow_mixed_revisions',False)
  group={phase_group(i['group'],allow) for i in items if i['product']==prod}
  if prod=='GUNW' and body.options.get('quake_mosaic'):
   if body.projects!=['P05']:raise HTTPException(422,'Event mosaic is available for a P05-only run. Switch back to one group for other tools.')
   from .quake import validate_mosaic_groups
   try:validate_mosaic_groups([i for i in items if i['product']=='GUNW'])
   except ValueError as error:raise HTTPException(422,str(error))
   continue
  if len(group)>1 and not (prod=='GCOV' and body.projects==['P03'] and body.options.get('fire_method')=='combined'):raise HTTPException(422,f'{prod}: select one compatible acquisition group.')
 for key,low,high in [('resolution',20,2000),('water_threshold',-40,0),('change_threshold',.1,20),('coherence',0,1),('snr',0,100)]:
  if key in body.options:
   try:v=float(body.options[key])
   except (ValueError,TypeError):raise HTTPException(422,f'Invalid {key}.')
   if not np.isfinite(v) or not low<=v<=high:raise HTTPException(422,f'{key} must be between {low} and {high}.')
 if body.options.get('reference_bbox'):
  try:
   r=validate_bbox(body.options['reference_bbox']);w,s,e,n=body.bbox
   if not(w<=r[0]<r[2]<=e and s<=r[1]<r[3]<=n):raise ValueError('Reference must lie inside the analysis area.')
  except ValueError as e:raise HTTPException(422,str(e))
 return items

def assistant_report(ident):
 if not re.fullmatch(r'[a-f0-9]{32}',ident):raise HTTPException(422,'Invalid reference assessment.')
 if ident not in JOBS or JOBS[ident]['kind']!='reference' or JOBS[ident]['status']!='completed':raise HTTPException(422,'Reference assessment is not completed. Run the assistant again.')
 try:return json.loads((JOBS_DIR/ident/JOBS[ident]['request']['projects'][0]/'reference_assistant.json').read_text())
 except (OSError,ValueError):raise HTTPException(422,'Reference assessment is unavailable. Run the assistant again.')

def check_assistant_choice(body,items):
 ident=body.options.get('reference_assistant_id');candidate_id=body.options.get('reference_candidate_id')
 if not ident and not candidate_id:return None
 if not ident or not candidate_id or (len(body.projects)!=1 or body.projects[0] not in REFERENCE_PRODUCTS):raise HTTPException(422,'Reference candidate provenance requires one supported tool and both assessment and candidate identifiers.')
 report=assistant_report(ident)
 if report.get('project','P04')!=body.projects[0] or report['fingerprint']!=reference_fingerprint(items,body.bbox,body.options,body.projects[0]):raise HTTPException(422,'Tool, area, files or processing settings changed. Run the reference assistant again, or draw your own reference.')
 if candidate_id=='current':
  current=report.get('current_reference');saved=JOBS[ident]['request']['options']
  reference_features=lambda opts:[f for f in (opts.get('spatial_context') or {}).get('features',[]) if (f.get('properties') or {}).get('role')=='reference']
  if not current or current['shared_cells']<25 or any('No comparison ground' in w for w in current['warnings']):raise HTTPException(422,'The checked reference has insufficient shared support. Choose another patch and recheck.')
  if body.options.get('reference_bbox')!=saved.get('reference_bbox') or reference_features(body.options)!=reference_features(saved):raise HTTPException(422,'Your drawn reference changed after assessment. Check it again.')
  chosen={**current,'id':'current','name':'Your checked reference','bbox':saved.get('reference_bbox')}
 else:
  chosen=next((c for c in report['candidates'] if c['id']==candidate_id),None)
  if not chosen or body.options.get('reference_bbox')!=chosen['bbox']:raise HTTPException(422,'The reference differs from the selected candidate. Review it or draw your own reference without candidate provenance.')
  if any((f.get('properties') or {}).get('role')=='reference' for f in (body.options.get('spatial_context') or {}).get('features',[])):raise HTTPException(422,'Reference polygons override the rectangle. Remove them explicitly before adopting this candidate.')
 return {'assessment_id':ident,'candidate':chosen,'stability':report['stability'],'relative_rate_meaning':report['relative_rate_meaning'],'comparison_meaning':report.get('comparison_meaning'),'project':body.projects[0],'assistant_version':report['assistant_version'],'comparison_unit':report.get('comparison_unit'),'sources':report['sources'],'maximum_candidate_offset_span':report.get('maximum_candidate_offset_span')}

@app.post('/api/run')
@exclusive_action
def run(body:RunQuery):
 items=selected_run_items(body)
 if body.options.get('surface_method')=='evolving' and body.projects!=['P06']:raise HTTPException(422,'Evolving surface change requires a P06-only run.')
 if body.options.get('fire_method')=='combined' or body.projects==['P06'] and body.options.get('surface_method')=='evolving':
  try:processing_grid(body,'GCOV')
  except ValueError as error:raise HTTPException(422,str(error))
 if body.options.get('fire_method')=='combined' and body.projects!=['P03']:raise HTTPException(422,'Combined HH/HV change requires a P03-only run.')
 try:
  from .readiness import assess,require
  for pid in body.projects:
   product=PRODUCT_FOR[pid]
   require(assess([i for i in items if i['product']==product],body.bbox,processing_grid(body,product),pid,body.options,product=product))
 except ValueError as e:raise HTTPException(422,str(e))
 choice=check_assistant_choice(body,items)
 j=newjob('analysis',request=body.model_dump(),reference_selection=choice);submit_job(work,j,items,body);return j

@app.post('/api/reference-assistant')
@exclusive_action
def start_reference_assistant(body:RunQuery):
 if len(body.projects)!=1 or body.projects[0] not in REFERENCE_PRODUCTS:raise HTTPException(422,'Choose one reference-based tool: P03, P04, P05.')
 items=selected_run_items(body)
 if len({i['id'] for i in items})!=len(items):raise HTTPException(422,'Choose each science file only once.')
 from .resource_budget import require_resources
 try:resources=require_resources(items,processing_grid(body,REFERENCE_PRODUCTS[body.projects[0]]),root=DATA)
 except ValueError as error:raise HTTPException(422,str(error))
 j=newjob('reference',request=body.model_dump(),resource_preflight=resources);submit_job(reference_work,j,items,body);return j

def reference_work(j,items,body):
 try:
  pid=body.projects[0];product=REFERENCE_PRODUCTS[pid]
  grid=processing_grid(body,product);obs=[];errors=[]
  from .resource_budget import assess_resources
  resources=assess_resources(items,grid,root=DATA)
  update(j,resource_preflight=resources)
  if not resources['ready']:raise ValueError(' '.join(resources['errors']))
  update(j,status='running',message='Checking shared coverage and coherence for reference candidates')
  for i,item in enumerate(items):
   if j['cancelled']:update(j,status='cancelled',message='Reference assessment cancelled.');return
   update(j,message=f"Reading reference evidence {i+1}/{len(items)}",progress=round(75*i/max(len(items),1)))
   try:obs.append(load_observation(item,body.bbox,grid,body.options,lambda:j['cancelled']))
   except ValueError as e:errors.append({'source':item['id'],'name':item['name'],'product':item['product'],'start':item['start'],'end':item['end'],'message':str(e)})
   except Exception as e:errors.append({'source':item['id'],'name':item['name'],'product':item['product'],'start':item['start'],'end':item['end'],'message':f'Science read failed ({type(e).__name__}). Check connection, permissions and source schema.'})
  if j['cancelled']:update(j,status='cancelled',message='Reference assessment cancelled.');return
  if errors:
   update(j,status='needs_input',progress=100,source_errors=errors,message=f'{len(errors)} selected source(s) could not supply usable measurements. Review the listed files before checking reference candidates; no selected coverage was silently omitted.');return
  update(j,message='Comparing candidate reference patches',progress=80)
  report=reference_assistant(obs,grid,body.options,pid);directory=JOBS_DIR/j['id']/pid;directory.mkdir(exist_ok=True)
  report.update(assessment_id=j['id'],created_at=datetime.now(timezone.utc).isoformat(),processing_options=body.options,resource_preflight=resources)
  guarded_json(directory/'reference_assistant.json',report)
  update(j,status='cancelled' if j['cancelled'] else 'completed',progress=100,message=f"{len(report['candidates'])} candidate reference patches assessed; stable ground is not independently established.",assistant_url=f"/api/artifacts/{j['id']}/{pid}/reference_assistant.json")
 except ValueError as e:update(j,status='cancelled' if j['cancelled'] else 'needs_input',message=str(e))
 except OSError:update(j,status='failed',message='The reference report save could not be confirmed. Check the storage drive before repeating the assessment. Saved inputs and any committed report were preserved.')
 except Exception:update(j,status='failed',message='Reference assessment failed. Check the source schema and local processing diagnostics.')

def processing_grid(body,product):
 if product=='GCOV' and (body.projects==['P03'] and body.options.get('fire_method')=='combined' or body.projects==['P06'] and body.options.get('surface_method')=='evolving'):
  from .raster_methods import analysis_grid
  return analysis_grid(body.bbox,float(body.options.get('resolution',20)),body.options.get('grid_crs'),body.options.get('grid_bounds'))
 return target_grid(body.bbox,max({'GCOV':20,'GUNW':80,'GOFF':80,'SME2':200}[product],float(body.options.get('resolution',100))),max_dimension=900 if product=='GUNW' and any(p in body.projects for p in ['P04','P05']) else 384)

def work(j,items,body):
 try:
  update(j,status='running',message='Inspecting selected science files')
  required={PRODUCT_FOR[pid] for pid in body.projects}
  items=[i for i in items if i['product'] in required]
  grids={product:processing_grid(body,product) for product in required}
  reader_options={**body.options,**({'channel':'HHHH','compare_polarizations':True} if body.projects==['P03'] and body.options.get('fire_method')=='combined' else {})}
  obs=[];errors=[]
  for i,item in enumerate(items):
   if j['cancelled']:break
   update(j,message=f"Reading {item['product']} {i+1}/{len(items)}: {item['start'][:10]}",progress=round(65*i/max(len(items),1)))
   try:
    o=load_observation(item,body.bbox,grids[item['product']],reader_options,lambda:j['cancelled']);obs.append(o)
   except ValueError as e:checkpoint();errors.append({'source':item['id'],'name':item['name'],'start':item['start'],'end':item['end'],'product':item['product'],'message':str(e)})
   except Exception as e:checkpoint();errors.append({'source':item['id'],'name':item['name'],'start':item['start'],'end':item['end'],'product':item['product'],'message':f'Science read failed ({type(e).__name__}). Check connection, permissions and supported file schema.'})
  update(j,source_errors=errors)
  for i,pid in enumerate(body.projects):
   if j['cancelled']:break
   update(j,message=f'Processing {pid}',progress=65+round(35*i/len(body.projects)))
   try:
    grid=grids[PRODUCT_FOR[pid]]
    if any(e['product']==PRODUCT_FOR[pid] for e in errors):raise ValueError(f"A selected {PRODUCT_FOR[pid]} file has no usable measurements or could not be read. See the file-specific details below. Resolve access problems, or explicitly deselect unusable files and review inputs; no selected date or coverage is silently omitted.")
    result=process(pid,obs,grid,body.options)
    from .readiness import assess
    result['extra']['readiness']=assess([i for i in items if i['product']==PRODUCT_FOR[pid]],body.bbox,grid,pid,body.options,product=PRODUCT_FOR[pid])
    product=PRODUCT_FOR[pid]
    for error in errors:
     if error['product']==product:result['notes'].append(f"Excluded source {error.get('start','')[:10]} ({error['source']}): {error['message']}")
    
    if pid in REFERENCE_PRODUCTS and j.get('reference_selection'):result['extra']['reference_assistant']=j['reference_selection']
    result['display_preferences']=body.display.model_dump(mode='json') if body.display else None;result['application_version']=APP_VERSION;result['processing_options']=body.options;result['created_at']=datetime.now(timezone.utc).isoformat()
    result=export_result(result,grid,JOBS_DIR/j['id']/pid);record_result(j,pid,{'status':'exploratory','title':result['title'],'url':f"/api/artifacts/{j['id']}/{pid}/result.json"})
   except ValueError as e:checkpoint();record_result(j,pid,{'status':'needs_input','message':str(e)})
   except Exception as e:checkpoint();record_result(j,pid,{'status':'failed','message':f'Processing failed ({type(e).__name__}). Inspect the local test and schema documentation.'})
  successes=sum(r['status']=='exploratory' for r in j['results'].values())
  update(j,status='cancelled' if j['cancelled'] else 'completed' if successes else 'needs_input',progress=100,message=f'{successes} workflow results ready; {len(j["results"])-successes} require attention.')
 except Exception as e:checkpoint();update(j,status='failed',message=f'Job stopped ({type(e).__name__}).')
@app.post('/api/download-geometry')
@exclusive_action
def geometry_download(body:AreaDownloadQuery):
 try:validate_bbox(body.bbox)
 except ValueError as error:raise HTTPException(422,str(error))
 if busy():raise HTTPException(409,'Finish the active job before preparing geometry.')
 if any(g not in CATALOG for g in body.granules):raise HTTPException(422,'Load saved GOFF observations or search their sources first.')
 items=[CATALOG[g].copy() for g in dict.fromkeys(body.granules)]
 if any(i['product']!='GOFF' for i in items):raise HTTPException(422,'Choose GOFF measurements for viewing geometry.')
 if not AUTH.session and any(not i.get('viewing_geometry',{}).get('available') for i in items):raise HTTPException(401,'Connect Earthdata to retrieve the omitted viewing geometry from the original NASA files. Existing subsets are kept.')
 j=newjob('area_download',request=body.model_dump(),geometry_preparation=True);submit_job(geometry_work,j,items,body.bbox);return j

def geometry_work(j,items,bbox):
 from .geometry_storage import prepare
 saved=[];errors=[];transferred=0;reused=0
 try:
  update(j,status='running',message='Preparing portable GOFF viewing geometry')
  for index,item in enumerate(items):
   if j['cancelled']:break
   try:
    result,count,hit=prepare(item,bbox,lambda:j['cancelled'],lambda message:update(j,message=message,progress=round(100*index/len(items))))
    with LOCK:CATALOG[result['id']]=result
    saved.append(result);transferred+=count;reused+=int(hit)
   except ValueError as e:errors.append({'name':item['name'],'message':str(e)})
   except Exception as e:errors.append({'name':item['name'],'message':f'Geometry preparation failed ({type(e).__name__}). Check NASA access and the source schema.'})
   update(j,saved_areas=saved,source_errors=errors,bytes_transferred=transferred,reused=reused,download_folders=sorted({i['download_folder'] for i in saved}))
  update(j,status='cancelled' if j['cancelled'] else 'needs_input' if errors else 'completed',progress=100,message=f'{len(saved)}/{len(items)} inputs prepared with viewing geometry. Earlier subsets are preserved; use the prepared copies for horizontal speed.')
 except Exception:update(j,status='failed',message='Geometry preparation stopped; previous local data are unchanged.')

@app.post('/api/download-area')
@exclusive_action
def area_download(body:AreaDownloadQuery):
 try:validate_bbox(body.bbox)
 except ValueError as error:raise HTTPException(422,str(error))
 if busy():raise HTTPException(409,'Cancel or finish the active job first.')
 if any(g not in CATALOG for g in body.granules):raise HTTPException(422,'Search or load saved observations first.')
 items=[CATALOG[g].copy() for g in dict.fromkeys(body.granules)]
 for item in items:
  if item.get('subset') and not contains(item['subset_bbox'],body.bbox):raise HTTPException(422,'The selected rectangle extends beyond a saved area.')
 if any(not source_file(i,DATA).is_file() and not saved_subset(i,body.bbox) for i in items) and not AUTH.session:raise HTTPException(401,'Connect Earthdata before saving remote area data.')
 j=newjob('area_download',request=body.model_dump());submit_job(area_download_work,j,items,body.bbox);return j

def area_download_work(j,items,bbox):
 saved=[];errors=[];transferred=0;reused=0;folders={}
 try:
  update(j,status='running',message='Preparing native-grid area extracts')
  for index,item in enumerate(items):
   if j['cancelled']:break
   try:
    if item['product'] in folders and not folders[item['product']].exists():del folders[item['product']]
    if not saved_subset(item,bbox) and item['product'] not in folders:folders[item['product']]=new_folder(DATA,item['product'])
    result,count,hit=extract_subset(item,bbox,lambda:j['cancelled'],lambda layer,total,size:update(j,message=f"Saving area {index+1}/{len(items)} · layer {layer+1}/{total} · {size/1024**2:.1f} MiB read",progress=round(100*(index+layer/max(total,1))/len(items))),folder=folders.get(item['product']))
    with LOCK:CATALOG[result['id']]=result
    saved.append(result);transferred+=count;reused+=int(hit)
   except ValueError as error:errors.append({'name':item['name'],'message':str(error)})
   except Exception as error:errors.append({'name':item['name'],'message':f'Area extraction failed ({type(error).__name__}). Check connection, source schema and disk space.'})
   update(j,saved_areas=saved,source_errors=errors,bytes_transferred=transferred,reused=reused,download_folders=sorted({i.get('download_folder','') for i in saved if i.get('download_folder')}))
  size=sum(i['size_mb'] for i in saved)
  update(j,status='cancelled' if j['cancelled'] else 'needs_input' if errors else 'completed',progress=100,message=f'{len(saved)}/{len(items)} area extracts saved · {size:.1f} MB on disk · {transferred/1024**2:.1f} MiB transferred · {reused} reused.'+(' Some files need attention; see details.' if errors else ' Ready for local analysis.'))
 except Exception:update(j,status='failed',message='Area extraction stopped. Completed extracts remain available through Use saved data.')

@app.post('/api/download')
@exclusive_action
def full_download(body:DownloadQuery):
 if busy():raise HTTPException(409,'Finish or cancel the current job first.')
 if not body.granules or any(g not in CATALOG for g in body.granules):raise HTTPException(422,'Select catalog observations first.')
 selected=[CATALOG[g].copy() for g in dict.fromkeys(body.granules)]
 if any(i.get('subset') for i in selected):raise HTTPException(422,'These are saved area extracts. Search NASA to download complete originals.')
 saved_names={i['name'] for i in local() if not i.get('subset')}
 items=[i for i in selected if i['name'] not in saved_names and not (DATA/'raw'/(i['id']+'.h5')).is_file()]
 if not items:raise HTTPException(409,'All selected originals are already saved on this computer. Use them in an analysis instead.')
 if not AUTH.session:raise HTTPException(401,'Connect Earthdata in Connection before downloading NASA files.')
 j=newjob('download');submit_job(download_work,j,items);return j
def download_work(j,items):
 try:
  update(j,status='running')
  for i,item in enumerate(items):
   download(item,lambda:j['cancelled'],lambda n,total:update(j,message=f"Downloading {i+1}/{len(items)}: {n/1024**2:.1f} MiB"))
   raw=DATA/'raw';(raw/(item['id']+'.json')).write_text(json.dumps(item));update(j,progress=round(100*(i+1)/len(items)))
  update(j,status='completed',message='Selected original science files downloaded.')
 except ValueError as e:update(j,status='cancelled' if j['cancelled'] else 'failed',message=str(e))
 except Exception:update(j,status='failed',message='Download failed. Check Earthdata connection and free disk space.')
@app.get('/api/artifacts/{ident}/{pid}/{filename}')
def artifact(ident:str,pid:str,filename:str):
 if pid not in ['LAB',*[p['id'] for p in PLANS]] or not re.fullmatch(r'[a-z0-9_]+\.(json|png|tif)',filename):raise HTTPException(404)
 from .recorded_studies import result_directory,recorded
 directory=result_directory(JOBS_DIR,ident,pid)
 if ident.startswith('example-') and filename not in recorded(ident[len('example-'):])[0]['files']:raise HTTPException(404)
 path=directory/filename
 if not path.exists():raise HTTPException(404)
 return FileResponse(path,filename=filename if filename.endswith('.tif') else None)

@app.put('/api/jobs/{ident}/display/{pid}')
def save_display(ident:str,pid:str,body:DisplaySettings):
 if ident.startswith('example-'):raise HTTPException(409,'Recorded example views are read-only. Run the example to save your own opening view.')
 if not re.fullmatch(r'[a-f0-9]{32}',ident) or pid not in ['LAB',*PRODUCT_FOR]:raise HTTPException(404,'Result unavailable.')
 with LOCK:
  j=JOBS.get(ident)
  if not j or j.get('results',{}).get(pid,{}).get('status')!='exploratory':raise HTTPException(404,'Result unavailable.')
  if j['status'] in ['queued','running']:raise HTTPException(409,'Wait for this run to finish before saving its opening view.')
  path=JOBS_DIR/ident/pid/'result.json'
  if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink():raise HTTPException(409,'The result directory is not a regular saved-run folder.')
  try:result=json.loads(path.read_text())
  except (OSError,ValueError):raise HTTPException(404,'Result unavailable.')
  layer=next((l for l in result['layers'] if l['id']==body.layer),None)
  if not layer or layer.get('unit')!=body.unit:raise HTTPException(422,'Choose a saved result layer and its matching unit.')
  style_layers=set(body.category_colors)|set(body.category_opacity)
  if any(name not in {l['id'] for l in result['layers']} for name in style_layers):raise HTTPException(422,'Category colors must belong to saved result maps.')
  if any(not is_category(l) for l in result['layers'] if l['id'] in style_layers and (body.category_colors.get(l['id']) or body.category_opacity.get(l['id']))):raise HTTPException(422,'Category colors apply only to category maps.')
  result['display_preferences']=body.model_dump(mode='json',exclude={key for key in ('category_colors','category_opacity') if not getattr(body,key)})
  temp=None
  try:
   with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix='.display-',suffix='.tmp',delete=False) as stream:
    temp=Path(stream.name);stream.write(json.dumps(result))
   temp.replace(path)
  except OSError:raise HTTPException(500,'The opening view could not be saved. Check local file permissions.')
  finally:
   if temp:
    try:temp.unlink(missing_ok=True)
    except OSError:pass
 return {'display_preferences':result['display_preferences']}

@app.get('/api/pixel/{ident}/{pid}/{layer}')
def pixel(ident:str,pid:str,layer:str,lat:float,lon:float):
 if pid not in ['LAB',*[p['id'] for p in PLANS]] or not re.fullmatch(r'[a-z0-9_]+',layer):raise HTTPException(404)
 if not np.isfinite(lat) or not np.isfinite(lon) or not(-90<=lat<=90 and -180<=lon<=180):raise HTTPException(422,'Invalid coordinates.')
 from .recorded_studies import result_directory
 path=result_directory(JOBS_DIR,ident,pid)/(layer+'.tif')
 if not path.exists():raise HTTPException(404)
 import rasterio
 from pyproj import Transformer
 with rasterio.open(path) as ds:
  x,y=Transformer.from_crs('EPSG:4326',ds.crs,always_xy=True).transform(lon,lat)
  if not(ds.bounds.left<=x<=ds.bounds.right and ds.bounds.bottom<=y<=ds.bounds.top):return {'value':None}
  value=float(next(ds.sample([(x,y)]))[0]);return {'value':value if np.isfinite(value) else None}

@app.get('/api/visualization/{ident}/{pid}/{layer}')
@render_admission
def visualization(ident:str,pid:str,layer:str,mode:Literal['shared','robust','full','custom','mexico','quake']='shared',low:float|None=None,high:float|None=None,palette:Literal['standard','mexico','quake','rainbow','diverging']='standard',category_colors:str|None=None,category_opacity:str|None=None):
 # Resolve only registered layers from a validated saved result, never caller-provided paths.
 if pid not in ['LAB',*[p['id'] for p in PLANS]] or not re.fullmatch(r'[a-z0-9_]+',layer):raise HTTPException(404)
 from .recorded_studies import result_directory
 directory=result_directory(JOBS_DIR,ident,pid)
 try:result=json.loads((directory/'result.json').read_text())
 except (OSError,ValueError):raise HTTPException(404,'Result unavailable.')
 layers={l['id']:l for l in result['layers']};info=layers.get(layer)
 if not info:raise HTTPException(404,'Layer unavailable.')
 try:colors=validate_colors(json.loads(category_colors)) if category_colors is not None else {}
 except (ValueError,TypeError):raise HTTPException(422,'Invalid category colors. Use a JSON object of numeric class codes and #RRGGBB colors (maximum 512).')
 try:opacities=validate_opacity(json.loads(category_opacity)) if category_opacity is not None else {}
 except (ValueError,TypeError):raise HTTPException(422,'Invalid category opacity. Use numeric class codes and opacity values from 0 to 1 (maximum 512).')
 if (colors or opacities) and not is_category(info):raise HTTPException(422,'Category styling applies only to category maps.')
 import rasterio,base64,io
 from rasterio.warp import transform_bounds,reproject,Resampling
 from rasterio.transform import from_bounds
 from PIL import Image
 from .exports import colorize
 def read(name):
  with rasterio.open(directory/(name+'.tif')) as ds:
   if ds.width*ds.height>4_000_000:raise HTTPException(422,'Preview grid is too large.')
   return ds.read(1),ds.profile,ds.bounds
 arr,profile,bounds=read(layer);values=arr[np.isfinite(arr)]
 if not values.size:
  reason=info.get('unavailable_reason') or 'This view has no mapped values on the selected observations. Missing values are not zero change.'
  if layer=='event_overlap_spread':reason='No overlapping cells have valid measurements from multiple event groups. There is no overlap difference to display; missing overlap is not zero disagreement. Inspect the source-coverage maps or select overlapping compatible sources.'
  if layer in ['first_change','largest_step']:reason='No qualifying change date or interval was mapped on the selected valid observations. This does not prove the surface was unchanged. Inspect measurement and quality maps, the selected dates and detection settings.'
  if pid=='P01' and layer in ['recovery','recovery_lower_days','recovery_upper_days']:
   calendar=result.get('extra',{}).get('recovery_calendar')
   reason=('Recovery cannot be assessed: no acquisition after the comparison date is selected. Add later compatible observations to look for a return to dry.' if calendar==[] else 'No return to dry was mapped for the new-water candidates in the selected later observations. This does not prove continuous flooding or establish flood duration.')
  return {'available':False,'reason':reason,'valid_pixels':0}

 requested_mode=mode;requested_palette=palette;range_note=''
 if is_category(info):
  mode='shared';range_note='Category numbers identify labels; numerical contrast ranges do not apply.'
 if mode=='mexico' and not(pid=='P04' and info['unit'] in ['cm/year','cm/month'] and info['kind']=='diverging'):
  mode='shared';range_note='The Mexico comparison preset applies only to P04 rate maps. This layer uses an automatic shared range in its own units.'
 if mode=='quake' and not(pid=='P05' and info['kind']=='diverging' and info['unit'] in ['cm','mm']):
  mode='shared';range_note='The Venezuela comparison range applies only to P05 displacement maps. This layer uses an automatic range in its own units.'
 peers=[layer]
 if mode=='shared' and layer.startswith('observation_'):
  peers=[k for k,l in layers.items() if k.startswith('observation_') and l['unit']==info['unit'] and l['kind']==info['kind']]
 if mode=='mexico':lo,hi=(-30.,30.) if info['unit']=='cm/year' else (-2.5,2.5)
 elif mode=='quake':lo,hi=(-50.,50.) if info['unit']=='cm' else (-500.,500.)
 elif mode=='custom':
  if low is None or high is None or not np.isfinite([low,high]).all() or high<=low:raise HTTPException(422,'Choose finite scale limits with minimum below maximum.')
  lo,hi=low,high
 else:
  if len(peers)>1:
   from .display_range import raster_percentiles
   try:limits=raster_percentiles([directory/(name+'.tif') for name in peers])
   except ValueError as error:raise HTTPException(422,str(error))
   except (OSError,rasterio.errors.RasterioError):raise HTTPException(409,'A saved map could not be read while calculating the shared range. Reopen the run and check its saved files.')
  else:limits=np.percentile(values,[0,100] if mode=='full' else [2,98])
  lo,hi=map(float,limits)
  if info['kind']=='diverging':hi=max(abs(lo),abs(hi),1e-6);lo=-hi
  if hi<=lo:
   gap=max(abs(lo)*.01,1e-6);lo=max(0.,lo-gap) if values.min()>=0 and info['kind']!='diverging' else lo-gap;hi+=gap
 if info['id'].startswith('horizontal_bearing_') and mode!='custom':lo,hi=0.,360.
 if info['kind']=='binary':lo,hi=0.,1.
 if info['kind']=='water_state':lo,hi=0.,2.
 if info['kind']=='diverging' and info['unit']=='class':lo,hi=-1.,1.
 if info['kind']=='categorical' or info['unit']=='observation index':lo,hi=float(values.min()),float(values.max())
 merc=transform_bounds(profile['crs'],'EPSG:3857',*bounds,densify_pts=21)
 preview=np.full(arr.shape,np.nan,'float32')
 reproject(arr,preview,src_transform=profile['transform'],src_crs=profile['crs'],src_nodata=np.nan,dst_transform=from_bounds(*merc,arr.shape[1],arr.shape[0]),dst_crs='EPSG:3857',dst_nodata=np.nan,resampling=Resampling.nearest)
 palette_name='standard';palette_note=''
 palette=[[24,45,61],[41,155,165],[231,230,166]]
 if info['unit']=='m³/m³':palette=[[138,82,45],[213,203,130],[29,125,115]]
 if info['kind']=='diverging':palette=[[61,137,205],[242,239,222],[229,102,76]]
 if info['kind']=='water_state':palette=[[225,220,198],[49,143,191],[142,143,151]]
 if info['kind']=='binary':palette=[[225,220,198],[49,143,191],[20,88,151]]
 if requested_palette=='mexico':
  if pid=='P04' and info['kind']=='diverging' and info['unit'] in ['cm/year','cm/month','cm','mm','mm/day']:
   palette=json.loads((ROOT/'backend/mexico_palette.json').read_text());palette_name='mexico'
  else:palette_note='Rainbow colors apply to signed P04 motion layers. Quality and class maps keep their own colors.'
 if requested_palette=='rainbow' and info['kind'] in ['continuous','diverging'] and info['unit']!='class':
  palette=json.loads((ROOT/'backend/mexico_palette.json').read_text());palette_name='rainbow'
 if requested_palette=='diverging' and info['kind'] in ['continuous','diverging'] and info['unit']!='class':
  palette=[[16,57,112],[43,112,171],[166,205,226],[255,255,255],[255,238,158],[239,139,67],[176,27,50]];palette_name='diverging'
 if requested_palette=='quake':
  if pid=='P05' and info['kind']=='diverging' and info['unit'] in ['cm','mm','mm/day']:
   palette=[[16,57,112],[43,112,171],[166,205,226],[255,255,255],[255,238,158],[239,139,67],[176,27,50]];palette_name='quake'
  else:palette_note='Earthquake colors apply to signed P05 motion layers. Quality and class maps retain their own colors.'
 rgba,lo,hi=colorize(preview,info['kind'],(lo,hi),palette,colors,opacities if is_category(info) else None);stream=io.BytesIO();Image.fromarray(rgba).save(stream,format='PNG')
 display={'image':'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode(),'min':lo,'max':hi,'palette':palette,'mode':mode,'requested_mode':requested_mode,'range_note':range_note,'palette_name':palette_name,'palette_note':palette_note,'shared_frames':len(peers),'valid_pixels':int(values.size),'clipped_percent':float(100*np.count_nonzero((values<lo)|(values>hi))/values.size),'constant':bool(values.min()==values.max()),'display_bounds_mercator':list(merc),'class_values':np.unique(values).tolist() if is_category(info) else []}
 display['category_colors']=colors
 display['category_opacity']=opacities
 if opacities:
  validity=io.BytesIO();Image.fromarray(np.where(np.isfinite(preview),255,0).astype('uint8')).save(validity,format='PNG')
  display['validity_image']='data:image/png;base64,'+base64.b64encode(validity.getvalue()).decode()
 display['categories']=category_entries(info,display,result,colors,opacities) if is_category(info) else []
 display['appearance_type']='categories' if is_category(info) else 'measurement'
 return display

@app.get('/api/map-image/{ident}/{pid}/{layer}')
@render_admission
def map_image(ident:str,pid:str,layer:str,mode:Literal['shared','robust','full','custom','mexico','quake']='shared',low:float|None=None,high:float|None=None,palette:Literal['standard','mexico','quake','rainbow','diverging']='standard',category_colors:str|None=None,category_opacity:str|None=None,basemap:Literal['satellite','light','dark','streets','plain']|None=None,place_names:bool=False,overlay_opacity:float=1,extent:Literal['result','view']='result',view_bbox:str|None=None):
 # Use exactly the display resolver, including class colors and applied units/ranges.
 display=visualization(ident,pid,layer,mode,low,high,palette,category_colors,category_opacity)
 if display.get('available') is False:raise HTTPException(422,display['reason'])
 from .recorded_studies import result_directory
 directory=result_directory(JOBS_DIR,ident,pid)
 result=json.loads((directory/'result.json').read_text());info=next(l for l in result['layers'] if l['id']==layer)
 from .map_image import render_map,parse_view_bounds
 try:view_bounds=parse_view_bounds(extent,view_bbox)
 except ValueError as error:raise HTTPException(422,str(error))
 title=result.get('title','Custom workflow') if pid=='LAB' else next(p['name'] for p in PLANS if p['id']==pid)
 if not np.isfinite(overlay_opacity) or not 0<=overlay_opacity<=1:raise HTTPException(422,'Overlay opacity must be between 0 and 1.')
 from .basemap_export import BackgroundUnavailable
 try:content=render_map(result,info,display,ident,title,directory,basemap=basemap,place_names=place_names,overlay_opacity=overlay_opacity,view_bounds=view_bounds)
 except BackgroundUnavailable:raise HTTPException(503,'Background export could not finish. Try again or turn off Include background. Your result and numeric GeoTIFF are unchanged.')
 return Response(content,media_type='image/png',headers={'Content-Disposition':f'attachment; filename="{pid.lower()}_{layer}_map.png"'})

from .workflows import install as install_workflows
install_workflows(app)

from .studies import install as install_studies
install_studies(app)
from .recorded_studies import install as install_recorded_studies
install_recorded_studies(app)

app.mount('/',StaticFiles(directory=ROOT/'frontend',html=True),name='frontend')
