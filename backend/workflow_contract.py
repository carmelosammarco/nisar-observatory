"""Authoritative declarative sequence rules, also interpreted by the browser.

Only a small data-expression vocabulary is used. Recipes never carry executable rules.
Parameter types/ranges remain the published Pydantic schemas.
"""
import copy
from .engines import MINIMUM

VERSION='1.0.0'
def var(name):return {'var':name}
def expr(op,*args):return {op:list(args)}
def check(condition,message):return {'condition':condition,'message':message}
U=var('unit');D=var('domain');P=var('product');I=var('index');S=var('seen')
FAMILIES={
 'P01':{'product':'GCOV','detect':['flood_history'],'stages':[['water_rule'],['flood_history'],['water_tracking','?']],'minimum':2},
 'P02':{'product':'GCOV','detect':['water_rule','wetland_history','water_tracking'],'stages':[['water_rule'],['wetland_history'],['water_tracking','?']],'minimum':MINIMUM['P02']},
 'P03':{'product':'GCOV','detect':['dual_change','robust_score'],'stages':[['dual_change'],['smooth','?'],['robust_score'],['threshold'],['patches','?']],'minimum':4},
 'P06':{'product':'GCOV','detect':['surface_baseline','signed_change','surface_history'],'stages':[['surface_baseline'],['smooth','?'],['signed_change'],['patches','?'],['surface_history']],'minimum':2},
 'P05':{'product':'GUNW','detect':['event_pairs','event_los'],'stages':[['event_pairs'],['event_los']],'minimum':1},
 'P07':{'product':'GOFF','detect':['offset_screen','offset_bias','horizontal_velocity','radar_components','rate_units'],'stages':[['offset_screen','?'],['offset_bias','?'],['horizontal_velocity','radar_components'],['rate_units']],'minimum':1}}
ELEMENTARY={
 'db':{'products':['GCOV'],'checks':[check(expr('all',expr('eq',U,'power'),expr('eq',I,0)),'Decibels can only be added first to unchanged GCOV power.')],'set':{'unit':'dB'}},
 'los':{'products':['GUNW'],'checks':[check(expr('all',expr('eq',U,'rad'),expr('eq',I,0)),'Convert phase to relative movement first, once only.')],'set':{'unit':'cm'}},
 'network':{'products':['GUNW'],'checks':[check(expr('all',expr('eq',D,'pairs'),expr('eq',U,'cm'),expr('subset',S,['los','smooth'])),'First reconstruct connected LOS dates after phase-to-LOS, optionally smoothed, before baselines, rates or masks.')],'set':{'domain':'epochs'}},
 'trend':{'products':['GUNW'],'checks':[check(expr('all',expr('eq',D,'epochs'),expr('eq',U,'cm')),'First reconstruct connected LOS acquisition dates before fitting a trend.')],'set':{'domain':'map','unit':{'if':[var('parameters.annualized'),'cm/year','cm/day']}}},
 'rate':{'products':['GOFF','GUNW'],'checks':[check(expr('all',expr('eq',D,'pairs'),expr('in',U,['m','cm']),expr('subset',S,['los'])),'Add a rate immediately after displacement, before other calculations.')],'set':{'unit':{'concat':[U,{'if':[var('parameters.annualized'),'/year','/day']}]}}},
 'baseline':{'products':['GCOV','GUNW','GOFF'],'checks':[check(expr('not',expr('eq',D,'map')),'A single fitted map has no time baseline to subtract.'),check(expr('not',expr('eq',U,'class')),'A baseline requires measurements, not candidate labels.')],'set':{}},
 'smooth':{'products':['GCOV','GUNW','GOFF'],'checks':[check(expr('not',expr('eq',U,'class')),'Smooth measurements before creating category labels.')],'set':{}},
 'threshold':{'products':['GCOV','GUNW','GOFF'],'checks':[check(expr('not',expr('eq',U,'class')),'Choose a numeric output before adding a threshold.'),check(expr('any',expr('not',expr('eq',var('parameters.direction'),'absolute')),expr('gte',var('parameters.value'),0)),'An absolute-magnitude threshold must be nonnegative.')],'set':{'unit':'class'}},
 'patches':{'products':['GCOV','GUNW','GOFF'],'checks':[check(expr('eq',U,'class'),'First mark values that meet a condition, then filter candidate patches.')],'set':{}},
 'summary':{'products':['GCOV','GUNW','GOFF'],'checks':[check(expr('any',expr('not',expr('eq',D,'map')),expr('in',var('parameters.statistic'),['mean','frequency'])),'Keep the single fitted map with Mean, or use frequency for a candidate mask.'),check(expr('eq',expr('eq',U,'class'),expr('eq',var('parameters.statistic'),'frequency')),'Use candidate frequency for labels; use a measurement statistic for numeric values.')],'set':{'unit':{'if':[expr('eq',var('parameters.statistic'),'frequency'),'fraction',U]}}}}
RULES={'version':VERSION,'initial_units':{'GCOV':'power','GUNW':'rad','GOFF':'m'},'initial_domains':{'GCOV':'observations','GUNW':'pairs','GOFF':'pairs'},'max_steps':16,'families':FAMILIES,'elementary':ELEMENTARY,'repeatable':['smooth','threshold','patches'],'scientific_ids':[name for name in dict.fromkeys(n for f in FAMILIES.values() for stage in f['stages'] for n in stage if n not in ('?','smooth','threshold','patches'))],'entry_ids':['water_rule','dual_change','surface_baseline','event_pairs','offset_screen','horizontal_velocity','radar_components'],'block_units':{'water_rule':'class','flood_history':'class','wetland_history':'fraction','water_tracking':'class','dual_change':'dB','robust_score':'z','surface_baseline':'dB','signed_change':'class','surface_history':'class','event_pairs':'rad','event_los':'cm','offset_screen':'m','offset_bias':'m','horizontal_velocity':'m/day','radar_components':'m/day','rate_units':var('parameters.unit')},'post_ids':['smooth','threshold','patches'],'semantic_checks':{'P01':{'water_rule':[check(expr('eq',var('parameters.method'),'single'),'The flood baseline requires the single-channel rule. Use Wetland history for joint HH/HV.')]},'P03':{'threshold':[check(expr('all',expr('eq',var('parameters.direction'),'above'),expr('gt',var('parameters.value'),0),expr('lte',var('parameters.value'),20)),'The combined-score classifier needs an at-or-above threshold greater than 0 and at most 20 in z units.')]},'P05':{'event_pairs':[check(expr('any',var('parameters.timestamp'),var('parameters.date')),'Supply the documented event timestamp or date.')]}}}


RULES['method_order']=list(FAMILIES)
RULES['common_checks']=[check(expr('not',expr('in','summary',S)),'The summary must be last. Move new calculations before it.'),check(expr('any',expr('not',expr('eq',P,'GUNW')),expr('not',expr('eq',U,'rad')),expr('eq',var('operation'),'los')),'First convert phase to relative ground movement.')]
RULES['elementary']['baseline']['minimum_sources']={'max':[var('minimum_sources'),{'add':[var('parameters.count'),{'if':[expr('eq',D,'epochs'),0,1]}]}]}
RULES['elementary']['network']['minimum_sources']={'max':[var('minimum_sources'),{'if':[var('parameters.require_cycles'),3,1]}]}
RULES['elementary']['trend']['minimum_sources']={'max':[var('minimum_sources'),2]}
RULES['families']['P03']['minimum_parameter']={'operation':'dual_change','field':'baseline_count','default':3,'unless':'baseline_end'}
RULES['families']['P06']['minimum_parameter']={'operation':'surface_baseline','field':'count','default':1,'unless':'end'}
RULES['output_filters']={'P02':{name:expr('eq',var('by_operation.water_rule.method'),'hh_hv') for name in ['hh_sigma','hv_sigma']},'P07':{'horizontal_speed':expr('in','horizontal_velocity',var('operations'))}}
RULES['output_units']={'P07':{'motion':{'fallback':[var('by_operation.rate_units.unit'),'m/year']}}}
RULES['patch_prohibited_outputs']=['change_direction']


def evaluate(expression,context):
 if not isinstance(expression,dict):return expression
 if 'var' in expression:
  value=context
  for part in expression['var'].split('.'):
   if not isinstance(value,dict):return None
   value=value.get(part)
  return value
 op,args=next(iter(expression.items()));values=[evaluate(a,context) for a in args]
 if op=='all':return all(values)
 if op=='any':return any(values)
 if op=='not':return not values[0]
 if op=='eq':return values[0]==values[1]
 if op=='in':return values[0] in values[1]
 if op=='subset':return set(values[0]).issubset(values[1])
 if op in ['gte','gt','lte']:
  if values[0] is None or values[1] is None:return False
  return values[0]>=values[1] if op=='gte' else values[0]>values[1] if op=='gt' else values[0]<=values[1]
 if op=='if':return values[1] if values[0] else values[2]
 if op=='concat':return ''.join(map(str,values))
 if op=='max':return max(values)
 if op=='add':return sum(values)
 if op=='fallback':return values[0] if values[0] is not None else values[1]
 raise ValueError('Unsupported workflow-rule expression.')


def method_for(steps,rules=RULES):
 ops=[s['operation'] for s in steps]
 return next((m for m in rules['method_order'] if any(n in ops for n in rules['families'][m]['detect'])),None)


def output_choices(method,steps,outputs,rules=RULES):
 choices={name:({'unit':v[0],'label':v[1]} if isinstance(v,(list,tuple)) else copy.deepcopy(v)) for name,v in outputs.get(method,{}).items()}
 context={'by_operation':{s['operation']:s.get('parameters',{}) for s in steps},'operations':[s['operation'] for s in steps]}
 for name,condition in rules['output_filters'].get(method,{}).items():
  if not evaluate(condition,context):choices.pop(name,None)
 for value in choices.values():
  replacement=rules['output_units'].get(method,{}).get(value['unit'])
  if replacement is not None:value['unit']=evaluate(replacement,context)
 return choices


def _apply(op,parameters,product,index,unit,domain,seen,rules):
 spec=rules['elementary'].get(op);context={'parameters':parameters,'product':product,'index':index,'unit':unit,'domain':domain,'seen':list(seen),'operation':op}
 if not spec or product not in spec['products']:return unit,domain,f'{op} is incompatible with {product}.'
 for rule in rules['common_checks']+spec['checks']:
  if not evaluate(rule['condition'],context):return unit,domain,rule['message']
 return evaluate(spec['set'].get('unit',unit),context),evaluate(spec['set'].get('domain',domain),context),None


def inspect_sequence(product,steps,outputs=None,defaults=None,rules=RULES):
 if defaults is None:
  from .workflow_parameters import parameter_defaults
  defaults=parameter_defaults()
 steps=[{'operation':s.operation,'parameters':s.parameters} if hasattr(s,'operation') else copy.deepcopy(s) for s in steps]
 for s in steps:s['parameters']={**(defaults or {}).get(s['operation'],{}),**s.get('parameters',{})}
 ops=[s['operation'] for s in steps];method=method_for(steps,rules);unit=rules['initial_units'].get(product,'unknown');domain=rules['initial_domains'].get(product,'unknown');errors=[];parameter_issues=[];missing=[];rows=[];internal=[];stage_indices={};post=[];minimum=1
 if len(steps)>rules['max_steps']:errors.append('Maximum 16 steps. Remove a step before adding another.')
 if method is None:
  seen=set()
  for i,s in enumerate(steps):
   before=unit;before_domain=domain
   minimum_rule=rules['elementary'].get(s['operation'],{}).get('minimum_sources')
   if minimum_rule:minimum=evaluate(minimum_rule,{'minimum_sources':minimum,'parameters':s['parameters'],'domain':domain})
   unit,domain,error=_apply(s['operation'],s['parameters'],product,i,unit,domain,seen,rules)
   rows.append({'input':before,'output':unit,'domain':before_domain,'output_domain':domain,'scope':'observed measurements','valid':error is None})
   if error:errors.append(error)
   seen.add(s['operation'])
  complete=bool(steps) and ops[-1]=='summary' and not errors
  return {'unit':unit,'domain':domain,'issue':next(iter(errors),None),'complete':complete,'method':None,'errors':errors,'parameter_issues':[],'missing':[],'rows':rows,'minimum_sources':minimum,'choices':{},'internal_indices':[],'stage_indices':{},'post_indices':[]}
 family=rules['families'][method];minimum=family['minimum']
 if family['product']!=product:errors.append('These scientific blocks require '+family['product']+'.')
 unique=[n for n in ops if n not in rules['repeatable']]
 if len(unique)!=len(set(unique)):errors.append('Use one instance of each compound scientific block; compatible map operations can repeat.')
 if 'publish' in ops and ops[-1]!='publish':errors.append('Choose the opening result map must be last.')
 if 'source_smooth' in ops and ops[0]!='source_smooth':errors.append('Input smoothing must be first.')
 index=1 if ops and ops[0]=='source_smooth' else 0
 for stage in family['stages']:
  alternatives=[n for n in stage if n!='?']
  if index<len(steps) and ops[index] in alternatives:
   stage_indices[ops[index]]=index
   if ops[index] in rules['repeatable']:internal.append(index)
   index+=1
  elif '?' not in stage:missing.append(' or '.join(alternatives))
 publish=next((s for s in steps if s['operation']=='publish'),None);choices=output_choices(method,steps,outputs or {},rules)
 output=publish['parameters'].get('layer') if publish else next(iter(choices),None)
 base_unit=choices.get(output,{}).get('unit','measurement')
 if publish and output not in choices:errors.append('Choose an available opening result map for this method and units.')
 post=[i for i in range(index,len(steps)) if ops[i]!='publish']
 for i in post:
  if ops[i] not in rules['post_ids']:errors.append('Restore the scientific dependency order. Only compatible map operations follow the last scientific calculation.')
 for op,checks in rules['semantic_checks'].get(method,{}).items():
  if op in stage_indices:
   for rule in checks:
    if not evaluate(rule['condition'],{'parameters':steps[stage_indices[op]]['parameters']}):parameter_issues.append(rule['message'])
 minimum_rule=family.get('minimum_parameter')
 if minimum_rule:
  q=next((s['parameters'] for s in steps if s['operation']==minimum_rule['operation']),{})
  if not q.get(minimum_rule['unless']):minimum=q.get(minimum_rule['field'],minimum_rule['default'])+1

 selected_unit=base_unit;selected_domain='map'
 for i,s in enumerate(steps):
  op=s['operation'];before=unit;before_domain=domain;scope='scientific method stage';error=None
  if i in post:
   before=selected_unit;before_domain='map';scope='selected method output'
   if op in rules['post_ids']:
    selected_unit,selected_domain,error=_apply(op,s['parameters'],product,i,selected_unit,'map',set(),rules)
    if op=='patches' and output in rules['patch_prohibited_outputs']:error='Signed direction classes are not a binary candidate mask. Choose a binary surface map for patch filtering.'
   else:error='Restore the scientific dependency order before processing.'
   if error:errors.append(error)
   row_unit=selected_unit
  elif op=='publish':before=selected_unit;before_domain='map';row_unit=selected_unit;scope='selected method output'
  elif op in rules['elementary']:
   unit,domain,error=_apply(op,s['parameters'],product,i,unit,domain,set(),rules)
   if error:errors.append(error)
   row_unit=unit
  else:
   unit=evaluate(rules['block_units'].get(op,unit),{'parameters':s['parameters']});row_unit=unit
  rows.append({'input':before,'output':row_unit,'domain':before_domain,'output_domain':'map' if scope=='selected method output' else domain,'scope':scope,'valid':error is None})
 issue=next(iter(errors),None) or next(iter(parameter_issues),None) or ('Add the missing scientific block: '+', '.join(' or '.join(rules.get('titles',{}).get(name,name) for name in group.split(' or ')) for group in missing)+'. Undo removal to restore the tested sequence.' if missing else None)
 return {'unit':selected_unit if publish or post else unit,'domain':'scientific','issue':issue,'complete':bool(publish) and ops[-1]=='publish' and not issue,'method':method,'errors':list(dict.fromkeys(errors)),'parameter_issues':parameter_issues,'missing':missing,'rows':rows,'minimum_sources':minimum,'choices':choices,'output':output,'internal_indices':internal,'stage_indices':stage_indices,'post_indices':post}
