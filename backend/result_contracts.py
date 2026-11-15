"""Shared, exportable meaning of numeric results. Presentation never changes science."""
import hashlib,json
import numpy as np
from functools import lru_cache
from pathlib import Path

CONTRACT_VERSION='1.1.0'
SMOOTHING={'version':'1.1.0','method':'normalized Gaussian','boundary':'reflect','minimum_finite_kernel_support':0.3,'fills_missing_centres':False}
LIMITS={
 'P01':'Dark radar returns are water candidates, not confirmed flooding. Two dates cannot establish onset, duration or recovery.',
 'P02':'Occupancy is the fraction of selected valid acquisitions meeting the rule, not continuous flooded time, depth or volume. Historical paper accuracy does not transfer to these observations.',
 'P03':'The score is relative to the selected normalization domain. It detects scattering change, not burn severity, recovery or verified burns. Views can have different latest dates.',
 'P04':'Relative line-of-sight motion mixes horizontal and vertical components. Annualized rates describe the observed span. A tree network has no independent closure check.',
 'P05':'LOS mosaics can combine viewing directions, pair intervals and reference origins. Seams need source-by-source inspection. This is not a damage map.',
 'P06':'Brightness changes can reflect lava, snowmelt, wetness or geometry. First detection is an acquired observation, not an exact onset time. Repeated detections do not establish uninterrupted persistence.',
 'P07':'Horizontal estimates fix vertical velocity to zero at a declared ellipsoidal height. Radar-plane components alone are not horizontal speed. A short-pair annualized rate is not a year of measurements.',
 'LAB':'Editable processing defines a measurement or candidate condition, not an environmental cause. A modified workflow requires new evaluation.'}

def method_for(result):
 return result.get('extra',{}).get('workflow_method') or result.get('project','LAB')

@lru_cache(maxsize=1)
def reading_guides():
 return {p['id']:p['reading_guide'] for p in json.loads((Path(__file__).resolve().parents[1]/'docs/tools.json').read_text())}

def reading_guide(result):
 """Export the same plain-language guide used by the tools; never certify a run."""
 method=method_for(result);extra=result.get('extra',{})
 base=reading_guides().get(method,{'version':'1.0','measurement':'The output of the declared editable steps, in the selected map’s units.','colours':'Read the actual output unit, threshold labels and dated map. Class numbers are labels; missing values are not zero change.','checks':'Inspect each executed step, native support, baselines and references. Changing a tested recipe creates a new experiment.','cannot':'Custom steps do not identify a physical cause or inherit the scientific accuracy of an example.'})
 guide={k:v for k,v in base.items() if k!='variants'}
 variant='relative' if method=='P03' and extra.get('fire_method',{}).get('id')!='combined' else 'pair' if method=='P04' and not extra.get('los_series') else 'radar' if method=='P07' and not extra.get('horizontal_velocity') else None
 guide.update(base.get('variants',{}).get(variant,{}))
 if extra.get('tracking',{}).get('available') is False:guide['checks']+=' Optional candidate object tracking is unavailable: '+extra['tracking']['reason']+' The core maps remain available; no partial object list is supplied.'
 guide['method']=method
 guide['validation']='Source checksums verify input integrity. Replay checks verify reproducibility. Neither establishes independent environmental accuracy for this run.'
 if extra.get('workflow_output_statistics') or extra.get('scientific_blocks',{}).get('source_smoothing') is not None:
  guide['modified_workflow']='Added transformations create a new experiment. Original method findings describe its original maps; read the separately labelled experimental output and statistics.'
 return guide

def explicit_classes(info,result=None):
 if info.get('classes'):return [(float(k),v) for k,v in info['classes'].items()]
 result=result or {};method=method_for(result);ident=info.get('id','');kind=info.get('kind');values=info.get('class_values',[])
 if info.get('unit')=='observation index':
  extra=result.get('extra',{});calendar=extra.get('recovery_calendar',[]) if ident=='recovery' else extra.get('first_change_calendar',[]) if ident=='first_change' else extra.get('step_calendar',[])
  lookup={int(row['index']):row.get('date',row.get('end',''))[:10] for row in calendar}
  return [(v,lookup.get(int(v),'Observed-date index')) for v in values] if values else None
 if kind=='water_state':return [(0,'Dry candidate'),(1,'Water candidate'),(2,'Ambiguous')]
 if ident.startswith('observation_') and kind=='binary':
  return [(0,'No open-water candidate'),(1,'Open-water candidate')] if method in ['P01','P02'] else [(0,'Condition not met'),(1,'Condition met')]
 known={
  'event':('No new water candidate','New water candidate'),
  'unresolved':('Later dry observation found','No later dry observation'),
  'water':('No open-water candidate','Open-water candidate'),
  'surface':('No latest change candidate','Latest change candidate') if result.get('extra',{}).get('surface_method',{}).get('id')=='evolving' else ('No persistent change candidate','Persistent change candidate'),
  'confirmed_change':('No repeated latest change','Repeated latest same-sign change'),
  'fire_candidate':('No changed patch candidate','Changed patch candidate'),
  'threshold_sensitive':('Stable within tested thresholds','Sensitive to tested thresholds')}
 if kind=='binary':
  if ident.endswith('reference_support'):return [(0,'Outside reference support'),(1,'Reference cells used')]
  if ident.startswith('offset_rejected_'):return [(0,'Retained by spatial filter'),(1,'Rejected by spatial filter')]
  return list(enumerate(known.get(ident,('Condition not met','Condition met'))))
 if kind=='diverging' and info.get('unit')=='class':
  if ident=='margin':return [(-1,'Water candidate lost'),(0,'Unchanged'),(1,'Water candidate gained')]
  if ident=='change_direction':return [(-1,'Dimmer'),(0,'No qualifying change'),(1,'Brighter')]
 if ident=='event_source':
  keys=result.get('extra',{}).get('event_mosaic',{}).get('source_key',{})
  return [(v,keys.get(str(int(v)),f'Source group {int(v)}')) for v in values] if values else None
 if kind=='categorical':return [(v,'No patch' if v==0 else f'Patch {int(v)}') for v in values] if values else None
 return None

def attach(result,grid):
 """Attach a method passport and explicit per-layer class semantics before export."""
 method=method_for(result);sources=result.get('sources',[]);extra=result.setdefault('extra',{})
 starts=[s['start'] for s in sources if s.get('start')];ends=[s.get('end',s.get('start')) for s in sources if s.get('end') or s.get('start')]
 period={'start':min(starts) if starts else None,'end':max(ends) if ends else None}
 support=extra.get('support',{});baseline=extra.get('baseline') or extra.get('fire_method',{}).get('groups')
 reference=result.get('processing_options',{}).get('reference_bbox')
 reference_features=[str(f.get('properties',{}).get('name','Reference polygon')) for f in (result.get('processing_options',{}).get('spatial_context') or {}).get('features',[]) if f.get('properties',{}).get('role')=='reference']
 passport={'contract_version':CONTRACT_VERSION,'method':method,'algorithm_version':result.get('algorithm_version'),'record':period,'baseline':baseline,'reference':{'bbox':reference,'polygon_names':reference_features,'meaning':'Data-suitable reference candidates do not independently establish stable ground. Reference changes shift relative values.' if method in ['P04','P05'] or reference or reference_features and extra.get('reference_diagnostics') else 'No spatial reference subtraction declared.'},'support':support,'interpretation':LIMITS.get(method,LIMITS['LAB']),'validation':'Engineering reproducibility and checksum checks are separate from independent scientific validation. Read the case-study comparison.','smoothing_contract':SMOOTHING,'execution_engine_version':extra.get('execution_engine_version')}
 extra['result_passport']=passport
 result['reading_guide']=reading_guide(result)
 options=result.get('processing_options',{})
 # Display styles and recipe names are deliberately excluded from scientific identity.
 recipe=extra.get('workflow',{});science={'method':method,'algorithm':result.get('algorithm_version'),'contracts':CONTRACT_VERSION,'steps':recipe.get('steps',[]),'options':options,'sources':extra.get('workflow_actual_inputs') or [{k:s.get(k) for k in ['id','catalog_id','start','end','group','cache_identity']} for s in sources],'grid':{'crs':str(grid['crs']),'transform':list(grid['transform']),'shape':list(grid['shape']),'bbox':grid['bbox']}}
 if extra.get('spatial_support',{}).get('version'):science['spatial_contract']=extra['spatial_support']['version']
 extra['execution_fingerprint']=hashlib.sha256(json.dumps(science,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
 for ident,info in result['layers'].items():
  info.setdefault('spatial_scope','processing footprint' if info.get('trace_operation') else 'source quality' if ident.startswith('quality_') else 'reference support' if ident.endswith('reference_support') else 'study domain')
  view={**info,'id':ident}
  if info.get('kind')=='categorical' or info.get('unit')=='observation index':view['class_values']=[float(v) for v in np.unique(info['data'][np.isfinite(info['data'])])]
  classes=explicit_classes(view,result)
  if classes:info['classes']={str(int(k)) if k.is_integer() else str(k):v for k,v in [(float(k),v) for k,v in classes]}
  valid=int(np.isfinite(info['data']).sum());info['valid_pixels']=valid;info['valid_fraction']=valid/info['data'].size
  if not info.get('trace_operation'):info['interpretation']=LIMITS.get(method,LIMITS['LAB'])
  if not valid:
   info['unavailable_reason']='No valid cells satisfy this layer’s measurement/support requirements. Missing results are not zero change.'
   if ident in ['recovery','recovery_lower_days','recovery_upper_days','unresolved','duration_lower_bound','duration_upper_bound']:info['unavailable_reason']='No usable return-to-dry evidence is mapped here. This can mean no later acquisition, no new-water candidates, or no accepted later dry pixels. Check the comparison and later observation dates. Missing recovery is not proof of continuing flooding.'
 return passport
