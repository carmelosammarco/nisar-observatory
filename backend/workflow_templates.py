"""Typed scientific block plans compiled to the existing, tested product kernels.

A compound stage is labelled as such; its parameters control real reader/kernel
operations. Optional source/output transforms execute explicitly. No user code.
"""
from .execution import cancellable,checkpoint
from dataclasses import dataclass
import copy
from .analysis_options import AnalysisOptions,positive_smoothing_field
import numpy as np
from pydantic import BaseModel,ConfigDict,Field,field_validator
from typing import Literal

class Model(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 @field_validator('*')
 @classmethod
 def calendar_parameters(cls,value,info):
  from datetime import date,datetime
  import re
  form=(cls.model_fields[info.field_name].json_schema_extra or {}).get('format')
  if not form or value is None:return value
  if value=='':return None
  if form=='date':
   if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Use a real calendar date in YYYY-MM-DD form.')
   date.fromisoformat(value)
  elif form=='date-time':
   if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})',value):raise ValueError('Event timestamp needs ISO date/time with an explicit timezone.')
   if value[-1]!='Z' and (int(value[-5:-3])>23 or int(value[-2:])>59):raise ValueError('Event timezone offset is outside its valid range.')
   if datetime.fromisoformat(value.replace('Z','+00:00')).tzinfo is None:raise ValueError('Event timestamp needs an explicit timezone.')
  return value
def option_field(name,default=None,**overrides):
 """Copy the authoritative shared bounds; block defaults may differ deliberately."""
 field=copy.deepcopy(AnalysisOptions.model_fields[name])
 if default is not None:field.default=default
 for key,value in overrides.items():setattr(field,key,value)
 return field

class Water(Model):
 method:Literal['single','hh_hv']='single'
 threshold_db:float=option_field('water_threshold')
 hh_db:float=option_field('water_hh_threshold')
 hv_db:float=option_field('water_hv_threshold')
class Flood(Model):comparison_date:str|None=Field(default=None,max_length=10,json_schema_extra={'format':'date'});ambiguity_db:float=option_field('water_unknown_db')
class Wetland(Model):ambiguity_db:float=option_field('water_unknown_db')
class Tracking(Model):minimum_m2:float=option_field('patch_area_m2')
class Dual(Model):baseline_count:int=Field(default=3,ge=3,le=31);baseline_end:str|None=Field(default=None,max_length=10,json_schema_extra={'format':'date'})
class SurfaceBaseline(Model):count:int=option_field('baseline_count');end:str|None=Field(default=None,max_length=10,json_schema_extra={'format':'date'});noise_floor_db:float=option_field('baseline_noise_floor_db')
class Signed(Model):threshold_db:float=option_field('change_threshold')
class Event(Model):timestamp:str|None=Field(default=None,max_length=50,json_schema_extra={'format':'date-time'});date:str|None=Field(default=None,max_length=10,json_schema_extra={'format':'date'});mosaic:bool=True
class Screen(Model):global_filter:bool=True;local_filter:bool=False;minimum_cutoff_m:float=option_field('offset_min_cutoff_m');mad_multiplier:float=option_field('offset_mad_multiplier')
class Bias(Model):enabled:bool=False
class Horizontal(Model):height_m:float=option_field('offset_geometry_height_m');condition_limit:float=option_field('offset_condition_limit');vertical_scenario_m_year:float=option_field('offset_vertical_scenario_m_year')
class Units(Model):unit:Literal['m/day','m/year']='m/year'
class Publish(Model):layer:str=Field(min_length=1,max_length=100)
class Empty(Model):pass
class SourceSmooth(Model):sigma_m:float=positive_smoothing_field()
PARAMS={'water_rule':Water,'flood_history':Flood,'wetland_history':Wetland,'water_tracking':Tracking,'dual_change':Dual,'robust_score':Empty,'surface_baseline':SurfaceBaseline,'signed_change':Signed,'surface_history':Empty,'event_pairs':Event,'event_los':Empty,'offset_screen':Screen,'offset_bias':Bias,'horizontal_velocity':Horizontal,'radar_components':Empty,'rate_units':Units,'publish':Publish,'source_smooth':SourceSmooth}
# Field metadata is also the UI contract: no duplicated free-form executable forms.
LABELS={
'water_rule':('Classify water candidates','GCOV','Compound radiometric decision: use one gamma-zero threshold or the joint HH/HV sigma-zero rule.','Low radar brightness can also be smooth dry ground or shadow. These are candidates, not verified water.'),
'flood_history':('Compare new water and later dry observations','GCOV','Use the median pre-comparison brightness as baseline; identify new water and bounds on an observed return to dry.','No later observation means unresolved, not still flooded. Acquisition gaps remain unknown.'),
'wetland_history':('Summarize observed wetness across dates','GCOV','Compute candidate occupancy, intermittent/always-observed areas and zone trajectories on common support.','Observation frequency is not continuous hydroperiod or vegetation-specific inundation.'),
'water_tracking':('Track connected water-candidate patches','GCOV','Link candidate objects by observed overlap and retain patches above a physical area.','Links are spatial correspondences, not measured water flow or uninterrupted persistence.'),
'dual_change':('Compare HH and HV against per-view baselines','GCOV','Compound block: median linear-power baselines, separate HH/HV log ratios, absolute sum and latest-view fusion.','Each view needs at least three baseline dates and a later date. Views may be asynchronous; change is not confirmed fire.'),
'robust_score':('Normalize change with a robust score','GCOV','Subtract the scene median and divide by 1.4826 times its median absolute deviation.','This score depends on the study domain. It is not a probability or burn-severity index.'),
'surface_baseline':('Declare the observed brightness baseline','GCOV','Convert positive power to dB and calculate a median baseline and robust spread from the declared first dates.','A baseline during an eruption cannot reveal lava already unchanged at that time.'),
'signed_change':('Find brightening and dimming candidates','GCOV','Apply separate positive and negative departure thresholds, with physical patch filtering.','Moisture, snow, roughness and geometry can mimic the same changes.'),
'surface_history':('Separate new, transient and repeated changes','GCOV','Record first observed changes and consecutive latest same-sign support.','Repeated evidence needs at least two later acquisitions; it does not prove uninterrupted persistence or lava.'),
'event_pairs':('Select earthquake-bracketing measurements','GUNW','Select the shortest intervals that strictly bracket the documented event; optionally include compatible adjacent views.','Other motion within each interval is not separated from the event.'),
'event_los':('Reference, convert and combine event views','GUNW','Compound geometry block: common-reference phase-to-LOS conversion and quality-aware event coverage mosaic.','Each view retains its dates and reference evidence. LOS is not vertical motion or building damage.'),
'offset_screen':('Screen radar-offset measurements','GOFF','Apply the declared local and/or robust spatial outlier rules to both offset components.','Filtering can remove real localized motion; compare its rejection maps and an unfiltered run.'),
'offset_bias':('Optionally subtract stable-ground bias','GOFF','Subtract each component median in the supplied stable-terrain polygon when enabled.','A polygon label does not prove stability. Enabled correction requires usable stable pixels.'),
'horizontal_velocity':('Estimate horizontal velocity from viewing geometry','GOFF','Compound inversion: combine range/along-track offsets with delivered ENU viewing vectors, fixing vertical velocity to zero.','Slope-parallel and vertical motion can bias this estimate. Constant ellipsoidal height is not a terrain DEM.'),
'radar_components':('Keep radar-direction motion components','GOFF','Keep signed range/along-track rates and their filtered radar-plane magnitude.','Radar-plane magnitude is not geographic horizontal speed.'),
'rate_units':('Choose daily or annualized motion units','GOFF','Use each exact pair duration, with optional multiplication by 365.25.','An annualized interval rate is not a full year of observations.'),
'publish':('Choose the opening result map','GCOV GUNW GOFF','Keep the method maps, dated observations, diagnostics and exports; choose the main map to inspect.','Changing presentation or selecting a map does not establish environmental accuracy.'),
'source_smooth':('Smooth quality-screened input measurements','GCOV GUNW GOFF','Optional Gaussian smoothing on the analysis grid before the compound method, preserving missing central cells and quality evidence.','This is an added experiment: it changes inputs, can blend real features and does not improve native resolution.')}

COMPOUND={'water_rule','dual_change','surface_baseline','signed_change','event_los','horizontal_velocity'}
from .workflow_contract import RULES
RULES['titles']={key:value[0] for key,value in LABELS.items()}

def catalog():
 out=[]
 for key,(name,products,why,limit) in LABELS.items():
  fields=[]
  schema=PARAMS[key].model_json_schema()
  for field,meta in schema.get('properties',{}).items():
   choices=meta.get('enum');types=meta.get('anyOf',[meta]);primary=next((m for m in types if m.get('type')!='null'),meta)
   if not choices:choices=primary.get('enum')
   fields.append({'key':field,'label':field.replace('_',' '),'type':primary.get('type','string'),'choices':choices,'minimum':meta.get('minimum',meta.get('exclusiveMinimum')),'maximum':meta.get('maximum'),'default':meta.get('default')})
  defaults={k:v.get('default') for k,v in schema.get('properties',{}).items() if 'default' in v}
  out.append({'id':key,'name':name,'products':products.split(),'description':why,'limitation':limit,'defaults':defaults,'fields':fields,'group':'Scientific blocks','compound':key in COMPOUND})
 return out

# Curated scalar maps: available before processing, so post-transform units are checked.
OUTPUTS={
'P01':{'event':('class','New water candidates'),'occupancy':('fraction','Observed water-candidate fraction'),'event_baseline_departure':('dB','Comparison minus pre-comparison baseline'),'change':('dB','Last minus first brightness')},
'P02':{'occupancy':('fraction','Observed water-candidate fraction'),'water':('class','Latest water candidates'),'change':('dB','Last minus first brightness'),'hh_sigma':('dB','Latest HH sigma-zero'),'hv_sigma':('dB','Latest HV sigma-zero')},
'P03':{'fire_score':('z','Combined HH/HV surface-change score'),'fire_candidate':('class','Candidate changed patches'),'change_intensity':('dB','Combined absolute HH/HV change'),'smoothed_intensity':('dB','Smoothed change magnitude')},
'P05':{'event_displacement_cm':('cm','Event-interval relative LOS displacement'),'range':('mm','Event-interval phase-equivalent change')},
'P06':{'latest_departure':('dB','Latest smoothed baseline departure'),'surface':('class','Latest changed patches'),'confirmed_change':('class','Repeated latest changes'),'change_direction':('class','Latest signed change direction')},
'P07':{'horizontal_speed':('motion','Estimated horizontal speed'),'radar_magnitude':('motion','Filtered radar-plane magnitude'),'value':('motion','Signed selected radar-component rate')}}
SPECIAL=set(PARAMS)-{'publish','source_smooth'}
@dataclass
class Plan:
 method:str
 options:dict
 post:list
 output:str
 unit:str
 source_smoothing:float|None=None

def is_scientific(steps):return any(s.operation in SPECIAL for s in steps)
def compile_plan(product,steps,options):
 """Compile the shared validated stage contract into existing scientific kernels."""
 from .workflow_contract import inspect_sequence
 from .workflow_parameters import parameter_defaults
 report=inspect_sequence(product,steps,OUTPUTS,parameter_defaults())
 if not report['complete']:raise ValueError(report['issue'] or 'Finish this scientific block plan with Choose the opening result map.')
 method=report['method'];indices=report['stage_indices'];opt=copy.deepcopy(options)
 p={s.operation:s.parameters for s in steps if s.operation not in ['smooth','threshold','patches']}
 if method in ['P01','P02']:
  w=p['water_rule'];opt.update(water_method=w['method'],water_threshold=w['threshold_db'],water_hh_threshold=w['hh_db'],water_hv_threshold=w['hv_db'])
  q=p['flood_history' if method=='P01' else 'wetland_history'];opt['water_unknown_db']=q['ambiguity_db']
  if method=='P01':opt['flood_date']=q['comparison_date']
  opt['patch_area_m2']=p.get('water_tracking',{}).get('minimum_m2',0);opt['water_tracking_enabled']='water_tracking' in indices
 elif method=='P03':
  q=p['dual_change'];opt.update(fire_method='combined',channel='HHHH',baseline_count=q['baseline_count'],baseline_end=q['baseline_end'],compare_polarizations=True)
  opt['score_threshold']=steps[indices['threshold']].parameters['value']
 elif method=='P06':
  q=p['surface_baseline'];opt.update(surface_method='evolving',baseline_count=q['count'],baseline_end=q['end'],baseline_noise_floor_db=q['noise_floor_db'],change_threshold=p['signed_change']['threshold_db'])
 elif method=='P05':
  q=p['event_pairs'];opt.update(event_timestamp=q['timestamp'],event_date=q['date'],quake_mosaic=q['mosaic'])
 elif method=='P07':
  solution='horizontal_velocity' if 'horizontal_velocity' in indices else 'radar_components'
  q=p.get('offset_screen',{});opt.update(offset_filter=q.get('global_filter',False),offset_local_filter=q.get('local_filter',False),offset_min_cutoff_m=q.get('minimum_cutoff_m',1),offset_mad_multiplier=q.get('mad_multiplier',8),offset_stable_bias=p.get('offset_bias',{}).get('enabled',False),offset_solution='horizontal' if solution=='horizontal_velocity' else 'radar',offset_rate_unit=p['rate_units']['unit'])
  if solution=='horizontal_velocity':
   q=p[solution];opt.update(offset_geometry_height_m=q['height_m'],offset_condition_limit=q['condition_limit'],offset_vertical_scenario_m_year=q['vertical_scenario_m_year'])
 if method in ['P03','P06']:
  opt['smoothing_m']=steps[indices['smooth']].parameters['sigma_m'] if 'smooth' in indices else 0
  opt['patch_area_m2']=steps[indices['patches']].parameters['minimum_m2'] if 'patches' in indices else 0
 source_smoothing=p.get('source_smooth',{}).get('sigma_m')
 return Plan(method,opt,[steps[i] for i in report['post_indices']],report['output'],report['unit'],source_smoothing)



def smooth_array(a,sigma):
 from .raster_methods import smooth
 return smooth(a,sigma).astype('float32')

@cancellable
def execute(recipe,observations,grid,plan):
 from .processors import process
 from .engines import summary
 from scipy.ndimage import label
 obs=observations
 if plan.source_smoothing is not None:
  from .processing_trace import snapshot
  obs=copy.deepcopy(observations)
  for o in obs:
   checkpoint()
   o['array']=smooth_array(o['array'],plan.source_smoothing/grid['resolution'])
   snapshot('source_smooth','primary',o['array'],'Smoothed input measurement · '+o['item']['group'],{'GCOV':'power','GUNW':'rad','GOFF':'m'}[recipe.product],group=o['item']['group'],start=o['item']['start'],end=o['item']['end'])
   for key in ['cross_power','water_hh_sigma_power','water_hv_sigma_power','other_offset']:
    if key in o.get('aux',{}):
     o['aux'][key]=smooth_array(o['aux'][key],plan.source_smoothing/grid['resolution'])
     snapshot('source_smooth',key,o['aux'][key],'Smoothed input '+key.replace('_',' ')+' · '+o['item']['group'],'m' if key=='other_offset' else 'power',group=o['item']['group'],start=o['item']['start'],end=o['item']['end'])
 result=process(plan.method,obs,grid,plan.options)
 # All native maps and diagnostics are preserved. Added operations have a separately labelled output.
 if plan.post:
  selected=result['layers'][plan.output];a=selected['data'].copy();unit=selected['unit']
  for i,step in enumerate(plan.post):
   checkpoint()
   q=step.parameters
   if step.operation=='smooth':a=smooth_array(a,q['sigma_m']/grid['resolution'])
   elif step.operation=='threshold':
    condition=a>=q['value'] if q['direction']=='above' else a<=q['value'] if q['direction']=='below' else np.abs(a)>=q['value'];a=np.where(np.isfinite(a),condition,np.nan).astype('float32');unit='class'
   else:
    labs,n=label(a==1);sizes=np.bincount(labs.ravel())*abs(grid['transform'].a*grid['transform'].e);keep=sizes>=q['minimum_m2'];keep[0]=False;a=np.where(np.isfinite(a),keep[labs],np.nan).astype('float32')
   result['layers']['workflow_post_'+str(i)]={'data':a.copy(),'label':'Added '+step.operation+' · '+selected['label'],'unit':unit,'kind':'binary' if unit=='class' else 'continuous',**({'classes':{'0':'Condition not met','1':'Condition met'}} if unit=='class' else {})}
  result['layers']['workflow_output']={'data':a,'label':'Experimental output · '+selected['label'],'unit':unit,'kind':'binary' if unit=='class' else 'continuous',**({'classes':{'0':'Condition not met','1':'Condition met'}} if unit=='class' else {})}
  result['extra']['workflow_output_statistics']=summary(a)
  result['notes'].append('Added map operations affect Experimental output only. Original method maps, timeline and method statistic cards retain their own meaning; use the added-output statistics for this new map.')
  result['report']['findings'].append('Extra map operations produced a separately labelled experimental output. The original method findings do not describe its modified values.')
  result['display_preferences']=None
 if 'water_tracking' not in [s.operation for s in recipe.steps] and plan.method in ['P01','P02']:
  result['extra'].pop('tracking',None)
 selected=result['layers']['workflow_output' if plan.post else plan.output]
 saved=recipe.display or {}
 opening='workflow_output' if plan.post else plan.output
 result['_workflow_display']=saved if saved.get('layer')==opening and saved.get('unit')==selected['unit'] else {'layer':opening,'unit':selected['unit'],'palette':'standard','mode':'shared'}
 result['extra']['workflow_method']=plan.method
 history=[{'step':i+1,'operation':s.operation,'parameters':s.parameters} for i,s in enumerate(recipe.steps)]
 result['extra']['step_history']=history
 result['extra']['scientific_blocks']={'compiled_method':plan.method,'compound_blocks':[s.operation for s in recipe.steps if s.operation in COMPOUND],'source_smoothing':plan.source_smoothing,'post_operations':len(plan.post),'opening_layer':'workflow_output' if plan.post else plan.output,'interpretation':'Typed scientific blocks compile to the shared tested kernels. Source/grid/quality and context are shared settings. Added input or output transforms are new experiments.'}
 return result


def example_recipe(ident,options=None):
 from .examples import definition
 m=definition(ident);o=options if options is not None else m['request']['options'];method=m['tool'];steps=[]
 def add(op,**params):steps.append({'operation':op,'parameters':params})
 if method in ['P01','P02']:
  add('water_rule',method=o.get('water_method','single'),threshold_db=o.get('water_threshold',-17),hh_db=o.get('water_hh_threshold',-14),hv_db=o.get('water_hv_threshold',-23))
  if method=='P01':add('flood_history',comparison_date=o.get('flood_date'),ambiguity_db=o.get('water_unknown_db',1))
  else:add('wetland_history',ambiguity_db=o.get('water_unknown_db',1))
  add('water_tracking',minimum_m2=o.get('patch_area_m2',30000))
 elif method=='P03':
  add('dual_change',baseline_count=o.get('baseline_count',3),baseline_end=o.get('baseline_end'));add('smooth',sigma_m=o.get('smoothing_m',80));add('robust_score');add('threshold',value=o.get('score_threshold',2),direction='above');add('patches',minimum_m2=o.get('patch_area_m2',100000))
 elif method=='P04':
  add('los');add('network',require_cycles=False);add('trend',annualized=True);add('summary',statistic='mean')
 elif method=='P05':add('event_pairs',timestamp=o.get('event_timestamp'),date=o.get('event_date'),mosaic=o.get('quake_mosaic',False));add('event_los')
 elif method=='P06':
  add('surface_baseline',count=o.get('baseline_count',1),end=o.get('baseline_end'),noise_floor_db=o.get('baseline_noise_floor_db',1));add('smooth',sigma_m=o.get('smoothing_m',40));add('signed_change',threshold_db=o.get('change_threshold',3));add('patches',minimum_m2=o.get('patch_area_m2',30000));add('surface_history')
 elif method=='P07':
  add('offset_screen',global_filter=o.get('offset_filter',True),local_filter=o.get('offset_local_filter',False),minimum_cutoff_m=o.get('offset_min_cutoff_m',1),mad_multiplier=o.get('offset_mad_multiplier',8));add('offset_bias',enabled=o.get('offset_stable_bias',False))
  if o.get('offset_solution')=='horizontal':add('horizontal_velocity',height_m=o.get('offset_geometry_height_m',0),condition_limit=o.get('offset_condition_limit',10),vertical_scenario_m_year=o.get('offset_vertical_scenario_m_year',20))
  else:add('radar_components')
  add('rate_units',unit=o.get('offset_rate_unit','m/day'))
 display=copy.deepcopy(m['request']['display'])
 if method=='P04':display['layer']='summary'
 else:
  if method=='P07' and o.get('offset_solution')!='horizontal':display.update(layer='radar_magnitude',unit=o.get('offset_rate_unit','m/day'))
  add('publish',layer=display['layer'])
 # Source settings stay shared. Block-owned values are compiled from the cards.
 return {'format':'nisar-observatory-workflow','schema_version':1,'engine_version':'1.1.0','name':m['title']+' · editable workflow','description':'Loaded from the tested '+m['tool']+' case study. Compound blocks retain their documented geometry and radiometry assumptions. Editing creates a new experiment.','product':m['product'],'method':'custom','steps':steps,'options':copy.deepcopy(o),'display':display,'context':{'bbox':m['request']['bbox'],'sources':[{k:s.get('catalog_id',s['id']) if k=='catalog_id' else s[k] for k in ['name','catalog_id','start','end','group']} for s in m['sources']]}}
