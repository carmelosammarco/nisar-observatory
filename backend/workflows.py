"""Versioned, declarative recipes. No uploaded executable code or arbitrary paths."""
from .execution import cancellable,checkpoint
from typing import Literal
from pydantic import Field,model_validator
from pathlib import Path
import json,uuid,hashlib
import numpy as np
from scipy import ndimage
from .engines import summary,phase_engine,offset_engine,instant
from .science import load_observation
from . import workflow_templates as templates

VERSION='1.1.0'
CATALOG=[
 {'id': 'db', 'name': 'Power to decibels', 'description': '10 log10 of accepted positive calibrated power. A dB difference is a power ratio, not environmental attribution.'},
 {'id': 'los', 'name': 'Phase to relative LOS change', 'description': 'Use one fixed common reference and source wavelength to convert phase to cm. Positive is toward the satellite; this is not vertical motion.'},
 {'id': 'rate', 'name': 'Displacement to interval rate', 'description': 'Divide displacement by exact pair duration. Each pair remains its own interval; rates are not accumulated motion.'},
 {'id': 'network', 'name': 'Reconstruct connected acquisition dates', 'description': 'Solve connected referenced LOS pairs for acquired dates, fixing the first date to zero. A tree has no independent closure check.'},
 {'id': 'trend', 'name': 'Fit a movement trend', 'description': 'Fit an intercept and linear slope to at least three reconstructed dates. Annualization does not mean a year was observed.'},
 {'id': 'baseline', 'name': 'Subtract an observed baseline', 'description': 'Subtract the per-cell median of the first N observations. Every baseline observation must be valid. The first N frames are the declared baseline, not a climate normal.'},
 {'id': 'smooth', 'name': 'Smooth without filling gaps', 'description': 'Normalized Gaussian smoothing with reflected edges and at least 30% finite kernel support. Missing central cells remain missing. Sigma uses actual analysis-cell spacing; smoothing changes spatial support, not sensor resolution.'},
 {'id': 'threshold', 'name': 'Make a labelled candidate mask', 'description': 'Apply a declared threshold in the current units. Categories are candidate conditions, not confirmed environmental classes.'},
 {'id': 'patches', 'name': 'Keep connected candidate patches', 'description': 'Remove four-connected candidate patches smaller than a physical area on the equal-area analysis grid. Only valid after a threshold.'},
 {'id': 'summary', 'name': 'Summarize the observed record', 'description': 'Create mean, median, spread or observed candidate frequency on cells valid at every selected date. Dates remain discrete observations.'}]
CATALOG+=templates.catalog()
from .workflow_parameters import StrictModel,PARAMS,parameter_defaults,parameter_schemas
from .workflow_contract import inspect_sequence,RULES
RULES['titles'].update({op['id']:op['name'] for op in CATALOG})
for _operator in CATALOG:
 if _operator['id'] in RULES['elementary']:_operator.update(products=RULES['elementary'][_operator['id']]['products'],defaults=parameter_defaults()[_operator['id']])

class Step(StrictModel):
 operation:Literal[tuple(PARAMS)]
 parameters:dict=Field(default_factory=dict)
 @model_validator(mode='after')
 def valid_params(self):
  self.parameters=PARAMS[self.operation].model_validate(self.parameters).model_dump();return self
class Source(StrictModel):
 name:str=Field(max_length=400);catalog_id:str=Field(max_length=200);start:str=Field(max_length=50);end:str=Field(max_length=50);group:str=Field(max_length=300)
class Context(StrictModel):
 bbox:list[float]|None=Field(default=None,min_length=4,max_length=4)
 sources:list[Source]=Field(default_factory=list,max_length=32)
class Recipe(StrictModel):
 format:Literal['nisar-observatory-workflow']='nisar-observatory-workflow'
 schema_version:Literal[1]=1
 engine_version:Literal['1.0.0','1.1.0']=VERSION
 name:str=Field(default='Untitled experiment',min_length=1,max_length=100)
 description:str=Field(default='',max_length=2000)
 product:Literal['GCOV','GUNW','GOFF']='GCOV'
 method:Literal['custom','P01','P02','P03','P04','P05','P06','P07']='custom'
 steps:list[Step]=Field(default_factory=list,max_length=16)
 options:dict=Field(default_factory=dict)
 display:dict|None=None
 context:Context=Field(default_factory=Context)
 @model_validator(mode='after')
 def compatible(self):
  if not self.name.strip():raise ValueError('Give the workflow a name.')
  from .engines import PRODUCT_FOR
  if self.method!='custom':
   if PRODUCT_FOR[self.method]!=self.product:raise ValueError('The guided method uses a different product.')
   if self.steps:raise ValueError('Guided methods keep their tested internal order; choose Custom steps to compose operators.')
   return self
  if templates.is_scientific(self.steps):
   templates.compile_plan(self.product,self.steps,self.options);return self
  report=inspect_sequence(self.product,self.steps,defaults=parameter_defaults())
  if report['issue']:raise ValueError(report['issue'])
  if not report['complete']:raise ValueError('End the workflow with Summarize the observed record.')
  return self

def operator_registry():
 from .result_contracts import SMOOTHING,CONTRACT_VERSION
 import copy
 rules=copy.deepcopy(RULES);rules['defaults']=parameter_defaults();rules['parameter_schemas']=copy.deepcopy(parameter_schemas())
 return {'engine_version':VERSION,'contract_version':CONTRACT_VERSION,'smoothing_contract':SMOOTHING,'workflow_rules':rules,'operators':[{**op,'operator_version':CONTRACT_VERSION,'parameters_schema':rules['parameter_schemas'][op['id']],'execution':'compound scientific kernel' if op.get('compound') else 'typed scientific stage' if op['id'] in templates.SPECIAL else 'measurement map operation'} for op in CATALOG],'scientific_outputs':{key:{k:{'unit':v[0],'label':v[1]} for k,v in val.items()} for key,val in templates.OUTPUTS.items()}}

def workflow_contract_record():
 registry=operator_registry();content={'workflow_rules':registry['workflow_rules'],'scientific_outputs':registry['scientific_outputs']}
 return {'version':RULES['version'],'sha256':hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()}

def checked_recipe(value):
 from .analysis_options import AnalysisOptions
 from .display_settings import DisplaySettings
 from .catalog import validate_bbox
 recipe=Recipe.model_validate(value)
 recipe.options=AnalysisOptions.model_validate(recipe.options).model_dump(mode='json',exclude_unset=True)
 if templates.is_scientific(recipe.steps):
  plan=templates.compile_plan(recipe.product,recipe.steps,recipe.options)
  AnalysisOptions.model_validate(plan.options)
 if recipe.display is not None:recipe.display=DisplaySettings.model_validate(recipe.display).model_dump(mode='json')
 if recipe.context.bbox is not None:validate_bbox(recipe.context.bbox)
 if recipe.options.get('reference_bbox'):
  ref=validate_bbox(recipe.options['reference_bbox'])
  if recipe.context.bbox is not None:
   box=recipe.context.bbox
   if not (box[0]<=ref[0]<ref[2]<=box[2] and box[1]<=ref[1]<ref[3]<=box[3]):raise ValueError('The reference must lie inside the recorded area. Choose a new reference for another region.')
 return recipe

def fingerprint(recipe):return hashlib.sha256(json.dumps(recipe.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()
@cancellable
def process(recipe,observations,grid):
 from .processing_trace import capture,attach
 with capture(recipe) as trace:
  result=_execute_recipe(recipe,observations,grid)
  attach(result,recipe,trace)
 extra=result.setdefault('extra',{});record=workflow_contract_record()
 if recipe.method=='custom':
  report=inspect_sequence(recipe.product,recipe.steps,templates.OUTPUTS,parameter_defaults())
  record.update(step_io=report['rows'],minimum_sources=report['minimum_sources'],method=report['method'],scope='Declared primary typed flow. Compound blocks can also generate other method maps and diagnostics; selected-output transforms keep those original results.')
  for row,entry in zip(report['rows'],extra.get('step_history',[])):
   if 'output_unit' in entry and entry['output_unit']!=row['output']:raise ValueError('Processing output units disagree with the declared workflow contract; no result was published.')
   entry.update(input_unit=row['input'],output_unit=row['output'],input_domain=row['domain'],output_domain=row['output_domain'],scope=row['scope'])
 extra['workflow_contract']=record
 return result

def _execute_recipe(recipe,observations,grid):
 from .processors import process as guided
 if recipe.method!='custom':
  result=guided(recipe.method,observations,grid,recipe.options)
  result['extra']['workflow_method']=recipe.method
  result['project']='LAB';result['extra']['workflow']=recipe.model_dump(mode='json');result['extra']['workflow_fingerprint']=fingerprint(recipe)
  result['extra']['execution_engine_version']=VERSION
  return result
 if templates.is_scientific(recipe.steps):
  plan=templates.compile_plan(recipe.product,recipe.steps,recipe.options);result=templates.execute(recipe,observations,grid,plan)
  result['project']='LAB';result['extra']['workflow']=recipe.model_dump(mode='json');result['extra']['workflow_fingerprint']=fingerprint(recipe);result['extra']['execution_engine_version']=VERSION;return result
 seq=sorted(observations,key=lambda o:(instant(o['item']['start']),instant(o['item']['end'])))
 if not seq:raise ValueError('Select at least one observation.')
 if len({(instant(o['item']['start']),instant(o['item']['end'])) for o in seq})!=len(seq):raise ValueError('Choose one source revision per observation or interval.')
 if len({o['path'] for o in seq})!=1:raise ValueError('Selected files resolved to different measurement arrays. Choose one consistent channel, frequency and quantity across the record.')
 cube=np.stack([o['array'] for o in seq]).astype('float32');layers={};unit={'GCOV':'power','GUNW':'rad','GOFF':'m'}[recipe.product];history=[]
 from .spatial import role_mask
 from .processors import region_mask
 context=recipe.options.get('spatial_context');domain=role_mask(context,'domain',grid);footprint=domain.copy()
 has_domain=any((f.get('properties') or {}).get('role')=='domain' for f in (context or {}).get('features',[]))
 if not domain.any():raise ValueError('The supplied study domain has no analysis-cell centers in this grid.')
 declared_reference=None
 if any(step.operation=='los' for step in recipe.steps):
  box=recipe.options.get('reference_bbox');has_reference=any((f.get('properties') or {}).get('role')=='reference' for f in (context or {}).get('features',[]))
  if not box and not has_reference:raise ValueError('Draw a reference or supply a reference polygon before converting phase to LOS.')
  declared_reference=role_mask(context,'reference',grid,region_mask(box,grid) if box else np.zeros(grid['shape'],bool));footprint|=declared_reference
 cube[:,~footprint]=np.nan
 if not (np.isfinite(cube).all(axis=0)&domain).any():raise ValueError('No common valid pixels remain inside the study domain. Auxiliary reference coverage is not study coverage.')
 def add(key,array,label,units,kind='continuous',spatial_scope='study domain',**meta):
  data=array.astype('float32')
  if spatial_scope=='study domain':data[~domain]=np.nan
  layers[key]={'data':data,'label':label,'unit':units,'kind':kind,'spatial_scope':spatial_scope,**meta}
 for i,o in enumerate(seq):
  for key,a in o.get('aux',{}).items():
   if key in ['accepted_fraction','missing_fraction'] or key.startswith('rejected_'):add(f'quality_{key}_{i}',a,key.replace('_',' ')+' · '+o['item']['start'][:10],'fraction',spatial_scope='source quality')
 reference=None;final=None;reference_diagnostics=None;rate_diagnostics=None;network_meta=None;trend_meta=None;timeline=None;epoch_records=None;raw_los_mm=None;network_mm=None;epoch_baseline=False
 for index,step in enumerate(recipe.steps):
  checkpoint()
  op,p=step.operation,step.parameters
  if op=='db':cube=np.where(cube>0,10*np.log10(np.maximum(cube,1e-30)),np.nan);unit='dB'
  elif op=='los':
   cube,_,reference,diagnostics=phase_engine(cube,seq,declared_reference,comparison=domain)
   add('reference_support',np.where(np.isfinite(cube).all(axis=0),reference,np.nan),'Shared reference cells · relative zero','class','binary',spatial_scope='reference support')
   cube[:,~domain]=np.nan;raw_los_mm=cube.copy();cube/=10;unit='cm';reference_diagnostics=diagnostics
  elif op=='network':
   from .advanced import network_solution
   for i,o in enumerate(seq):add(f'pair_{i}',cube[i],'Referenced LOS pair · '+o['item']['start'][:10]+' → '+o['item']['end'][:10],'cm','diverging')
   solution,network_meta=network_solution(seq,raw_los_mm if raw_los_mm is not None else cube*10,require_cycles=p['require_cycles'])
   if solution is None:raise ValueError(network_meta.get('reason','Connected dates could not be reconstructed.'))
   network_mm=solution['cube'];cube=network_mm/10;unit='cm'
   epoch_records=[{'item':{'start':d,'end':d}} for d in network_meta['epochs']]
   add('network_residual',solution['rms']/10,'Pair-network residual RMS · no independent check for a tree','cm')
  elif op=='trend':
   from .engines import days_between
   if len(cube)<3:raise ValueError('Fit a trend needs at least three reconstructed acquisition dates.')
   epochs=[o['item']['start'] for o in epoch_records];t=np.array([days_between(epochs[0],d)/365.25 for d in epochs])
   design=np.column_stack([np.ones(len(t)),t]);common=np.isfinite(cube).all(axis=0)
   if not common.any():raise ValueError('No common valid pixels for a trend fit.')
   scale=10 if network_mm is not None else 1
   values=(network_mm if network_mm is not None else cube)[:,common].astype('float64');fit=np.linalg.lstsq(design,values,rcond=None)[0]
   rate=np.full(grid['shape'],np.nan,'float32');rate[common]=fit[1]/scale
   residual=np.full(grid['shape'],np.nan,'float32');residual[common]=np.sqrt(np.mean((values-design@fit)**2,axis=0))/scale
   add('trend_residual',residual,'Linear-trend residual RMS · internal consistency only','cm')
   timeline=(cube.copy(),epoch_records,'cm');cube=rate[None] if p['annualized'] else (rate/365.25)[None];unit='cm/year' if p['annualized'] else 'cm/day'
   trend_meta={'epochs':epochs,'span_days':float(t[-1]*365.25),'method':'intercept + linear least-squares trend at acquired dates','unit':unit,'assumptions':'Relative LOS, not vertical movement. Annualized short records are not a year of observations. Fit residual is not independent accuracy.'}
  elif op=='rate':
   if recipe.product=='GOFF':cube,diagnostics=offset_engine(cube,seq,recipe.options);rate_diagnostics=diagnostics
   else:
    from .engines import days_between
    durations=np.array([days_between(o['item']['start'],o['item']['end']) for o in seq])
    if (durations<=0).any():raise ValueError('Pair durations must be positive.')
    cube=cube/durations[:,None,None]
   if p['annualized']:cube*=365.25
   unit+='/year' if p['annualized'] else '/day'
  elif op=='baseline':
   raw_los_mm=None;network_mm=None
   if epoch_records is not None:epoch_baseline=True
   n=p['count']
   if len(cube)<=n:raise ValueError(f'Baseline needs {n} baseline observations plus at least one later observation.')
   valid=np.isfinite(cube[:n]).all(axis=0);baseline=np.median(np.where(np.isfinite(cube[:n]),cube[:n],0),axis=0);baseline[~valid]=np.nan
   cube=cube-baseline;add(f'step_{index}_baseline',baseline,'Observed baseline · median of first '+str(n)+' frames',unit)
  elif op=='smooth':
   raw_los_mm=None;network_mm=None
   cube=np.array([templates.smooth_array(a,p['sigma_m']/grid['resolution']) for a in cube],dtype='float32')
  elif op=='threshold':
   valid=np.isfinite(cube);condition=cube>=p['value'] if p['direction']=='above' else cube<=p['value'] if p['direction']=='below' else np.abs(cube)>=p['value']
   cube=np.where(valid,condition,np.nan).astype('float32');unit='class'
  elif op=='patches':
   for i,a in enumerate(cube):
    labels,n=ndimage.label(a==1);sizes=np.bincount(labels.ravel())*abs(grid['transform'].a*grid['transform'].e);keep=sizes>=p['minimum_m2'];keep[0]=False;cube[i]=np.where(np.isfinite(a),keep[labels],np.nan)
  elif op=='summary':
   common=np.isfinite(cube).all(axis=0)
   if not common.any():raise ValueError('No cells are valid on every observation. Choose overlapping files, a smaller area or review native quality settings.')
   stat=p['statistic'];f={'mean':np.mean,'frequency':np.mean,'median':np.median,'std':np.std,'minimum':np.min,'maximum':np.max}[stat]
   final=np.full(grid['shape'],np.nan,dtype='float32');final[common]=f(cube[:,common],axis=0)
   outunit='fraction' if stat=='frequency' else unit
   add('summary',final,'Observed candidate frequency' if stat=='frequency' else 'Fitted relative LOS trend · final processed map' if trend_meta else stat.capitalize()+' of processed observations',outunit)
  history.append({'step':index+1,'operation':op,'parameters':p,'output_unit':outunit if op=='summary' else unit,'finite_cells_by_frame':[int(np.isfinite(a).sum()) for a in cube]})
  if op!='summary':add(f'step_{index}_latest',cube[-1],'Step '+str(index+1)+' · '+next(c['name'] for c in CATALOG if c['id']==op)+' · latest frame',unit,'binary' if unit=='class' else 'diverging' if op=='baseline' or unit.startswith('cm') else 'continuous')
 frame_cube,records,frame_unit=timeline if timeline is not None else (cube,epoch_records or seq,unit)
 common=np.isfinite(cube).all(axis=0);counts=np.isfinite(frame_cube).sum(axis=0)
 add('count',counts,'Usable reconstructed dates' if epoch_records else 'Usable processed observations','count')
 for i,(a,o) in enumerate(zip(frame_cube,records)):
  add(f'observation_{i}',a,('Reconstructed relative LOS · ' if epoch_records else 'Processed observation · ')+o['item']['start'][:10],frame_unit,'binary' if frame_unit=='class' else 'diverging' if epoch_records else 'continuous',frame_index=i,start=o['item']['start'],end=o['item']['end'],**({'frame_scope':'processed_epoch' if epoch_baseline else 'epoch'} if epoch_records else {}))
 if len(frame_cube)>1 and frame_unit!='class':add('change',np.where(common,frame_cube[-1]-frame_cube[0],np.nan),'Reconstructed first-to-last LOS change' if epoch_records else 'Last minus first processed observation',frame_unit,'diverging')
 series=[{'date':o['item']['start'],'end':o['item']['end'],'median':summary(a[common])['median'],**({'candidate_fraction':float(np.mean(a[common]))} if frame_unit=='class' else {})} for a,o in zip(frame_cube,records)]
 metrics={**summary(final),'common_area_km2':float(common.sum()*abs(grid['transform'].a*grid['transform'].e)/1e6),'observations':len(seq),**({'acquisition_dates':len(epoch_records)} if epoch_records else {})}
 median=metrics['median'];message=f"The {recipe.steps[-1].parameters['statistic']} summary has a spatial median of {median:.4g} {outunit} across {int(common.sum()):,} common cells."
 return {'project':'LAB','title':recipe.name,'unit':unit,'layers':layers,'series':series,'metrics':metrics,'notes':['Each saved step keeps its latest map; time exploration shows the final processed observations.','Common-support summaries exclude cells missing on any selected observation. Quality maps describe source support before the custom transformations.','Thresholds create candidate conditions. These steps alone do not identify a flood, eruption, fire, damage or a physical cause.',('The reconstructed acquisition-date maps have also had the declared observed baseline subtracted; the first date need not remain zero.' if epoch_baseline else 'The dated timeline is reconstructed relative LOS at acquired epochs. Pair residual is zero by construction for a tree and is not independent validation.' if epoch_records else 'GUNW/GOFF records are interval measurements. First-to-last differences compare intervals; they are not accumulated displacement.')], 'sources':[{**{k:o.get(k) for k in ['path','quality_paths','bytes_transferred','reader_version','cache_identity']},'id':o['item']['id'],'name':o['item']['name'],'start':o['item']['start'],'end':o['item']['end'],'group':o['item']['group'],'product':recipe.product,'attributes':o.get('attrs',{})} for o in seq],'extra':{'workflow':recipe.model_dump(mode='json'),'workflow_fingerprint':fingerprint(recipe),'execution_engine_version':VERSION,'step_history':history,'network_reconstruction':network_meta,'trend_fit':trend_meta,'timeline_unit':frame_unit,**({'spatial_support':{'version':'1.0','domain_pixels':int(domain.sum()),'processing_footprint_pixels':int(footprint.sum()),'auxiliary_pixels_outside_domain':int((footprint&~domain).sum()),'policy':'Measurements and summaries use the study domain. A phase reference outside it is retained only to establish the relative zero; other context roles are annotations in an elementary workflow.'}} if has_domain else {}),**({'los_series':[{'date':row['date'],'median_cm':row['median']} for row in series]} if trend_meta else {}),'reference_diagnostics':{'pairs':reference_diagnostics,'fixed_pixels':int(reference.sum())} if reference is not None else None,'offset_filter_diagnostics':rate_diagnostics or [],'support':{'common_pixels':int(common.sum()),'common_fraction':float(common.mean()),'common_area_km2':metrics['common_area_km2']}},'report':{'headline':'What this experiment measured','findings':[message,f"{len(seq)} discrete observations were processed through {len(recipe.steps)} declared steps. Spatial percentiles describe variability, not accuracy."],'next_checks':['Read the intermediate steps and native-quality support.','Test thresholds and references against independent evidence.'],'validation':'Custom experimental workflow; environmental accuracy is not established.'},'status':'exploratory','algorithm_version':VERSION}

def execution_setup(recipe,bbox):
 """One grid/options resolution for readiness, execution and provenance."""
 from . import app as service
 from .science import target_grid
 plan=templates.compile_plan(recipe.product,recipe.steps,recipe.options) if templates.is_scientific(recipe.steps) else None
 method=plan.method if plan else recipe.method
 options={**(plan.options if plan else recipe.options)}
 if method=='P03' and options.get('fire_method')=='combined':options.update(channel='HHHH',compare_polarizations=True)
 if method=='custom':grid=target_grid(bbox,max({'GCOV':20,'GUNW':80,'GOFF':80}[recipe.product],float(options.get('resolution',100))),max_dimension=900 if any(s.operation=='network' for s in recipe.steps) else 384)
 else:grid=service.processing_grid(service.RunQuery(bbox=bbox,granules=['metadata-only'],projects=[method],options=options),recipe.product)
 return grid,options,method


def install(api):
 from fastapi import HTTPException
 from fastapi.responses import JSONResponse
 from . import app as service
 from .catalog import validate_bbox
 from .science import target_grid,source_file
 from .exports import export_result
 from .subsets import contains
 from .access import AUTH
 from datetime import datetime,timezone
 class Launch(StrictModel):
  recipe:dict
  bbox:list[float]=Field(min_length=4,max_length=4)
  granules:list[str]=Field(min_length=1,max_length=32)
  workflow_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
 def checked(value):
  try:
   if len(json.dumps(value))>262144:raise ValueError('Workflow recipes must be smaller than 256 KiB.')
   return checked_recipe(value)
  except ValueError as e:
   from pydantic import ValidationError
   message='; '.join('.'.join(map(str,x['loc']))+': '+x['msg'] for x in e.errors(include_input=False,include_context=False)) if isinstance(e,ValidationError) else str(e)
   raise HTTPException(422,message)
 def folder():
  path=service.DATA/'workflows'
  if path.is_symlink():raise HTTPException(409,'Workflow storage must be a regular directory.')
  path.mkdir(exist_ok=True);return path
 def path_for(ident):
  import re
  if not re.fullmatch('[a-f0-9]{32}',ident):raise HTTPException(404,'Workflow not found.')
  p=folder()/(ident+'.json')
  if p.is_symlink():raise HTTPException(409,'Workflow files must be regular files.')
  return p
 class DraftInspection(StrictModel):
  product:Literal['GCOV','GUNW','GOFF']
  steps:list[Step]=Field(default_factory=list,max_length=16)
 @api.post('/api/workflows/inspect')
 def inspect_draft(body:DraftInspection):
  return inspect_sequence(body.product,body.steps,templates.OUTPUTS,parameter_defaults())
 @api.get('/api/workflow-operators')
 def operators():return operator_registry()
 class MethodTemplate(StrictModel):
  method:Literal['P01','P02','P03','P04','P05','P06','P07']
  options:dict=Field(default_factory=dict)
 @api.post('/api/workflows/from-method')
 def from_method(body:MethodTemplate):
  from .examples import CASES
  from .analysis_options import AnalysisOptions
  try:
   options=AnalysisOptions.model_validate(body.options).model_dump(mode='json',exclude_unset=True)
   if body.method=='P03' and options.get('fire_method')=='relative':raise ValueError('The editable fire blocks use the combined HH/HV method. Select that method first, or retain the guided relative-reference processor.')
   if body.method=='P06' and options.get('surface_method')=='legacy':raise ValueError('The editable surface blocks use the evolving method. Select that method first, or retain the guided legacy processor.')
   recipe=templates.example_recipe(next(i for i in CASES if i.startswith(body.method+'_')),options)
   recipe.update(name=body.method+' · editable workflow',description='Editable variant of the selected method. Review the scientific blocks and source settings for your area.',context={'sources':[]},display=None)
   return checked(recipe).model_dump(mode='json')
  except ValueError:raise HTTPException(422,'Review method settings, required event timing and the supported processing mode before creating editable blocks.')
 @api.get('/api/examples/{ident}/workflow')
 def example_workflow(ident:str):
  from .examples import setup,directory
  try:
   directory(ident);payload=setup(ident)
   for item in payload['items']:service.CATALOG[item['id']]=item
   return checked_recipe(templates.example_recipe(ident)).model_dump(mode='json')
  except ValueError as e:raise HTTPException(422,str(e))
 class Inspect(StrictModel):
  recipe:dict
  bbox:list[float]=Field(min_length=4,max_length=4)
  granules:list[str]=Field(default_factory=list,max_length=32)
 @api.post('/api/workflows/preflight')
 def preflight(body:Inspect):
  recipe=checked(body.recipe)
  try:
   validate_bbox(body.bbox)
   if len(set(body.granules))!=len(body.granules):raise ValueError('Choose each source once.')
   if any(g not in service.CATALOG for g in body.granules):raise ValueError('Search or load the selected source files again.')
   items=[service.CATALOG[g] for g in body.granules]
   if any(i['product']!=recipe.product for i in items):raise ValueError('Select only the workflow product.')
   grid,options,method=execution_setup(recipe,body.bbox)
   from .readiness import assess
   report=assess(items,body.bbox,grid,method,options,recipe.steps,recipe.product)
   for item in items:
    if item.get('subset') and not contains(item['subset_bbox'],body.bbox):report['errors'].append('The selected area extends outside a saved subset. Choose a smaller area or download a larger subset.')
   report['ready']=not report['errors']
   return report
  except ValueError as e:raise HTTPException(422,str(e))
 @api.post('/api/workflows/validate')
 def validate(value:dict):
  recipe=checked(value);return {'recipe':recipe.model_dump(mode='json'),'fingerprint':fingerprint(recipe)}
 @api.get('/api/workflows')
 def listing():
  entries=[]
  for p in folder().glob('*.json'):
   if p.is_symlink():continue
   try:entries.append({'id':p.stem,**checked_recipe(json.loads(p.read_text())).model_dump(mode='json')})
   except (ValueError,OSError):continue
  return sorted(entries,key=lambda r:r['name'].casefold())
 def persist(value,ident):
  from .runtime_storage import guarded_json
  from .storage_budget import InsufficientStorage
  recipe=checked(value)
  try:
   p=path_for(ident);guarded_json(p,recipe.model_dump(mode='json'))
  except InsufficientStorage as e:raise HTTPException(507,str(e)) from None
  except OSError:raise HTTPException(507,'The tool save could not be confirmed. Check the storage drive and reopen My Tools before retrying; the save may already be present. No downloaded inputs or runs were removed.') from None
  return {'id':ident,**recipe.model_dump(mode='json')}
 @api.post('/api/workflows')
 @service.exclusive_action
 def create(value:dict):return persist(value,uuid.uuid4().hex)
 @api.put('/api/workflows/{ident}')
 @service.exclusive_action
 def replace(ident:str,value:dict):
  if not path_for(ident).is_file():raise HTTPException(404,'Workflow not found.')
  return persist(value,ident)
 @api.get('/api/workflows/{ident}/export')
 def export(ident:str):
  p=path_for(ident)
  if not p.is_file():raise HTTPException(404,'Workflow not found.')
  recipe=checked(json.loads(p.read_text()))
  return JSONResponse(recipe.model_dump(mode='json'),headers={'Content-Disposition':f'attachment; filename="nisar-workflow-{ident[:8]}.json"'})
 @api.delete('/api/workflows/{ident}')
 @service.exclusive_action
 def delete(ident:str):
  p=path_for(ident)
  if not p.is_file():raise HTTPException(404,'Workflow not found.')
  p.unlink();return {'deleted':ident}
 def work(job,items,recipe,bbox):
  try:
   service.update(job,status='running',message='Reading the selected workflow inputs')
   grid,options,method=execution_setup(recipe,bbox)
   from .readiness import assess,require
   readiness=require(assess(items,bbox,grid,method,options,recipe.steps,recipe.product))
   obs=[]
   for i,item in enumerate(items):
    if job['cancelled']:service.update(job,status='cancelled',message='Workflow cancelled.');return
    service.update(job,message=f'Reading {i+1}/{len(items)} selected sources',progress=round(i/len(items)*65))
    try:obs.append(load_observation(item,bbox,grid,options,lambda:job['cancelled']))
    except Exception as e:
     checkpoint()
     service.record_result(job,'LAB',{'status':'needs_input','message':'A selected source could not be read. Review the file-specific access and quality details.'})
     service.update(job,status='needs_input',message='A selected source could not be read. No date or coverage was silently omitted.',source_errors=[{'source':item['id'],'product':item['product'],'start':item['start'],'name':item['name'],'message':str(e) if isinstance(e,ValueError) else 'Science read failed. Check access and source schema.'}]);return
   if job['cancelled']:service.update(job,status='cancelled',message='Workflow cancelled.');return
   service.update(job,message='Executing checked scientific steps',progress=68)
   result=process(recipe,obs,grid)
   result['extra']['readiness']=readiness
   result['extra']['execution_engine_version']=VERSION
   if recipe.engine_version!=VERSION:result['notes'].append('Imported recipe declares engine '+recipe.engine_version+'; executed with '+VERSION+'. Review the processing release notes before comparing historical results.')
   if job['cancelled']:service.update(job,status='cancelled',message='Workflow cancelled before export.');return
   result.update(display_preferences=result.pop('_workflow_display',recipe.display),processing_options=options,application_version=service.APP_VERSION,created_at=datetime.now(timezone.utc).isoformat())
   result['extra']['workflow_actual_inputs']=[{k:item.get(k) for k in ['id','catalog_id','name','start','end','group','content_sha256']} for item in items]
   result['extra']['workflow_actual_bbox']=bbox
   out=service.JOBS_DIR/job['id']/'LAB'
   export_result(result,grid,out)
   service.record_result(job,'LAB',{'status':'exploratory','title':recipe.name,'url':f"/api/artifacts/{job['id']}/LAB/result.json"})
   service.update(job,status='completed',progress=100,message='Experimental workflow complete. Inspect steps, common support and scientific limits.')
  except ValueError as e:
   checkpoint()
   service.record_result(job,'LAB',{'status':'needs_input','message':str(e)})
   service.update(job,status='needs_input',message=str(e))
  except Exception:
   checkpoint()
   service.record_result(job,'LAB',{'status':'failed','message':'Workflow processing failed. Inspect the validated recipe and source schema.'})
   service.update(job,status='failed',message='Workflow processing failed. Inspect the validated recipe and source schema.')
 @api.post('/api/workflows/run')
 @service.exclusive_action
 def launch(body:Launch):
  recipe=checked(body.recipe)
  try:validate_bbox(body.bbox)
  except ValueError as e:raise HTTPException(422,str(e))
  if service.busy():raise HTTPException(409,'Finish or cancel the current job before running a workflow.')
  if len(set(body.granules))!=len(body.granules):raise HTTPException(422,'Choose each source once.')
  if any(g not in service.CATALOG for g in body.granules):raise HTTPException(422,'Search or load saved data before running the workflow.')
  items=[service.CATALOG[g].copy() for g in body.granules]
  if any(i['product']!=recipe.product for i in items):raise HTTPException(422,'A workflow processes one product at a time. Choose matching files only.')
  plan=templates.compile_plan(recipe.product,recipe.steps,recipe.options) if templates.is_scientific(recipe.steps) else None
  from .los import phase_group
  if recipe.method=='custom' and plan is None and len({phase_group(i['group'],recipe.product=='GUNW' and recipe.options.get('phase_allow_mixed_revisions',False)) for i in items})!=1:raise HTTPException(422,'Custom steps require one compatible acquisition group. Different views must not be treated as a single time series.')
  for item in items:
   if item.get('subset') and not contains(item['subset_bbox'],body.bbox):raise HTTPException(422,'Your area extends outside a selected subset. Save a larger subset or use a smaller area.')
  if not AUTH.session and any(not source_file(i,service.DATA).is_file() for i in items):raise HTTPException(401,'Connect Earthdata or load local files before reading remote measurements.')
  if plan:service.selected_run_items(service.RunQuery(bbox=body.bbox,granules=body.granules,projects=[plan.method],options=plan.options))
  if recipe.method!='custom':service.selected_run_items(service.RunQuery(bbox=body.bbox,granules=body.granules,projects=[recipe.method],options=recipe.options))
  if recipe.options.get('reference_bbox'):
   ref=recipe.options['reference_bbox']
   try:validate_bbox(ref)
   except ValueError as e:raise HTTPException(422,str(e))
   if not (body.bbox[0]<=ref[0]<ref[2]<=body.bbox[2] and body.bbox[1]<=ref[1]<ref[3]<=body.bbox[3]):raise HTTPException(422,'The reference must lie inside the current area. Choose a new reference for a new region.')
  try:
   grid,execution_options,method=execution_setup(recipe,body.bbox)
   from .readiness import assess,require
   require(assess(items,body.bbox,grid,method,execution_options,recipe.steps,recipe.product))
  except ValueError as e:raise HTTPException(422,str(e))
  saved_id=None
  if body.workflow_id:
   saved=path_for(body.workflow_id)
   if saved.is_file() and fingerprint(checked(json.loads(saved.read_text())))==fingerprint(recipe):saved_id=body.workflow_id
  # Snapshot exact scientific identities, never passwords, URLs or local filesystem paths.
  recipe.context=Context(bbox=body.bbox,sources=[Source(**{k:str(i.get('catalog_id',i['id'])) if k=='catalog_id' else str(i[k]) for k in ['name','catalog_id','start','end','group']}) for i in items])
  job=service.newjob('analysis',request={'bbox':body.bbox,'granules':body.granules,'projects':['LAB'],'options':recipe.options,'workflow':recipe.model_dump(mode='json'),'workflow_id':saved_id})
  service.submit_job(work,job,items,recipe,body.bbox);return job
