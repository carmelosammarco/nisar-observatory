"""Fast, non-downloading input checks shared by guided and editable workflows.

Metadata readiness is not a native-pixel quality check or scientific validation.
"""
from datetime import timezone
from .catalog import ARCHIVE_MATURITIES
from .engines import MINIMUM,instant
from .los import phase_group


def assess(items,bbox,grid,method,options,steps=(),product=None):
 product=product or (items[0]['product'] if items else None)
 errors=[];warnings=[];checks=[];groups={}
 for item in items:
  try:
   instant(item['start']);instant(item.get('end',item['start']))
  except (KeyError,TypeError,ValueError):raise ValueError('A selected source has missing or invalid acquisition dates. Search or import it again.')
 for item in items:groups.setdefault(item.get('group','unknown'),[]).append(item)
 def check(label,value):checks.append({'label':label,'value':value})
 check('Selected sources',str(len(items)))
 check('Product',product or 'No matching data selected')
 releases={item['maturity'] for item in items if item.get('maturity') in ARCHIVE_MATURITIES}
 if releases:
  release_names=', '.join(release.title() for release in ARCHIVE_MATURITIES if release in releases)
  unknown=sum(item.get('maturity') not in ARCHIVE_MATURITIES for item in items)
  check('Archive releases',release_names+(f' · {unknown} unknown' if unknown else ''))
 if len(releases)>1:warnings.append('Selected sources mix NISAR archive releases. Processing differences can resemble surface change. Compare observations from one release where possible.')
 check('Analysis grid',f"{grid['shape'][1]} × {grid['shape'][0]} cells · {grid['resolution']:.2f} m spacing")
 minimum=MINIMUM.get(method,1)
 # Elementary baseline requirements depend on the frame domain at that stage,
 # not always the count of input pair files. See stage_baselines below.
 if method=='P03' and options.get('fire_method')=='combined':minimum=max(minimum,4)
 if len(items)<minimum:errors.append(f'Select at least {minimum} compatible {product or "product"} observations; {len(items)} selected.')
 allow_multiple=method=='P03' and options.get('fire_method')=='combined' or method=='P05' and options.get('quake_mosaic')
 normalized={phase_group(g,product=='GUNW' and options.get('phase_allow_mixed_revisions',False) and method!='P05') for g in groups}
 if len(normalized)>1 and not allow_multiple:errors.append('Choose one compatible viewing group. Different views cannot be treated as one time series by this workflow.')
 references=[r for r in options.get('reference_observations',[]) if r.get('product') in [None,product]]
 if references:
  from .validation import regional_reference_spec,utc_day
  try:
   if product not in ['GUNW','GOFF']:raise ValueError('Numeric regional reference checks support GUNW and GOFF only. GCOV water checks use dated water/dry label polygons in spatial context.')
   if method not in ['P04','P05','P07']:raise ValueError('Regional reference checks require a scientific LOS or offset workflow; elementary transformed maps do not have a matched regional evaluator.')
   if method=='P05' and len(groups)>1:raise ValueError('Check regional measurements in single-group P05 runs; mosaic groups have different support and geometry.')
   spec=regional_reference_spec(references,product,options)
   for reference in spec['references']:
    matches=[i for i in items if utc_day(i['start'])==reference['date'] and (not reference.get('end') or utc_day(i.get('end',i['start']))==reference['end'])]
    if len(matches)!=1:raise ValueError('Each regional reference must identify exactly one selected UTC acquisition interval. Check date and end.')
   check('Regional reference quantity',spec['quantity_label']+' · '+spec['unit']+((' · '+spec['component']) if spec['component'] else ''))
   warnings+=spec['assumptions']
  except ValueError as error:errors.append(str(error))
 group_rows=[]
 for group,records in sorted(groups.items()):
  records=sorted(records,key=lambda i:(instant(i['start']),instant(i.get('end',i['start']))))
  keys=[(instant(i['start']),instant(i.get('end',i['start'])) if product in ['GUNW','GOFF'] else None) for i in records]
  if len(keys)!=len(set(keys)):errors.append(group+': duplicate acquisition or pair. Keep one revision per observation.')
  row={'group':group,'count':len(records),'intervals':[{'start':i['start'],'end':i.get('end',i['start'])} for i in records]}
  if product=='GCOV' and method in ['P01','P02','P03','P06']:
   stop=options.get('baseline_end');count=int(options.get('baseline_count',1))
   baseline=[i for i in records if i['start'][:10]<=str(stop)] if stop else records[:count]
   later=[i for i in records if i not in baseline]
   row.update(baseline_dates=[i['start'] for i in baseline],comparison_dates=[i['start'] for i in later])
   combined=method=='P03' and options.get('fire_method')=='combined'
   if len(baseline)<(3 if combined else 1) or not later or not stop and len(records)<=count:
    if combined:errors.append(group+f': combined HH/HV needs at least 3 baseline observations and 1 later observation per viewing group; found {len(baseline)} baseline and {len(later)} later. Review the baseline end date and selected files.')
    else:errors.append(group+f': baseline needs {count if not stop else "the declared"} observation(s) and at least one later date. Review the baseline dates.')
   if method=='P01' and options.get('flood_date'):
    comparison=next((i for i in records if i['start'][:10]>=str(options['flood_date'])),None)
    if comparison is None or comparison==records[0]:errors.append(group+': comparison date requires an earlier baseline and an observation on or after that date.')
    elif comparison:
     at=records.index(comparison);row['context_baseline_dates']=row['baseline_dates'];row['baseline_dates']=[i['start'] for i in records[:at]];row['comparison_dates']=[comparison['start']];row['baseline_role']='Pre-comparison event baseline'
   elif method=='P01':row['baseline_role']='General context baseline; event baseline is selected from native water-change evidence during processing'
   if method=='P06' and len(later)<2:warnings.append('Only one post-baseline observation: repeated change cannot be established; a zero repeated-change map does not prove stability.')
  group_rows.append(row)
 if product=='GCOV' and (options.get('water_method')=='hh_hv' or method=='P03' and options.get('fire_method')=='combined'):
  check('Required channels','HH and HV together; availability/conversion is verified when reading')
  warnings.append('Channel availability and valid native sample overlap are not established by catalog metadata.')
 if product=='GUNW':
  roles=[f.get('properties',{}).get('role') for f in (options.get('spatial_context') or {}).get('features',[])]
  if not options.get('reference_bbox') and 'reference' not in roles:errors.append('Choose and check a reference area before processing. Data suitability does not independently establish stable ground.')
  else:check('Reference','Selected; usable pixels and sensitivity are checked from measurements. Stability remains an assumption.')
  need_network=method=='P04' or any(s.operation=='network' for s in steps)
  if need_network and items:
   pairs=[(instant(i['start']),instant(i.get('end',i['start']))) for i in items];nodes={n for pair in pairs for n in pair};seen={min(nodes)}
   while True:
    connected=seen|{v for a,b in pairs if a in seen or b in seen for v in (a,b)}
    if connected==seen:break
    seen=connected
   if seen!=nodes:errors.append('The pair graph is disconnected. Add linking pairs or select a connected subset.')
   redundancy=len(pairs)-len(nodes)+1
   check('Pair network',f'{len(nodes)} acquisition dates · {max(0,redundancy)} redundant pair(s)')
   if redundancy==0:warnings.append('Connected tree: zero pair residual is expected by construction and is not an independent accuracy check.')
   if any(s.operation=='network' and s.parameters.get('require_cycles') for s in steps) and redundancy<1:errors.append('This workflow requires a redundant pair cycle; add overlapping pairs.')
   if any(s.operation=='trend' for s in steps) and len(nodes)<3:errors.append('A trend needs at least three connected acquisition dates.')
  if method=='P05':
   if not options.get('event_timestamp') and not options.get('event_date'):errors.append('Supply the documented earthquake timestamp or date before choosing event-bracketing pairs.')
   else:
    from .quake import brackets_event
    for group,records in groups.items():
     if not any(brackets_event(item,options) for item in records):errors.append(group+': no selected pair brackets the documented event. Choose a before/after pair.')
   warnings.append('Event mosaics can combine different LOS directions, dates and reference origins. Read each source group before comparing colours across seams.')
 if product in ['GUNW','GOFF']:
  if any(instant(i.get('end',i['start']))<=instant(i['start']) for i in items):errors.append('Each radar pair must have a positive acquisition interval.')
 if product=='GOFF' and options.get('offset_solution')=='horizontal':
  check('Viewing geometry','Delivered ENU cubes required; availability is verified when reading')
  warnings.append('Horizontal speed assumes zero vertical velocity at the declared ellipsoidal height. It is not an unconstrained 3D measurement.')
 stage_baselines=[]
 frames=[{'start':i['start'],'end':i.get('end',i['start'])} for i in sorted(items,key=lambda i:(instant(i['start']),instant(i.get('end',i['start']))))];basis='selected observations' if product=='GCOV' else 'selected pair intervals'
 for index,step in enumerate(steps):
  if step.operation=='network':
   epochs=sorted({instant(d).astimezone(timezone.utc).isoformat() for i in items for d in [i['start'],i.get('end',i['start'])]})
   frames=[{'start':d,'end':d} for d in epochs];basis='reconstructed acquisition dates'
  elif step.operation=='baseline':
   count=step.parameters['count']
   if len(frames)<=count:errors.append(f'Step {index+1}: baseline needs {count} {basis} plus at least one later frame; {len(frames)} available.')
   stage_baselines.append({'step':index+1,'basis':basis,'requested_count':count,'available_frames':len(frames),'baseline_dates':[i['start'] for i in frames[:count]],'later_dates':[i['start'] for i in frames[count:]],'baseline_intervals':frames[:count]})
  elif step.operation=='trend':frames=frames[-1:];basis='fitted map'
 from .resource_budget import assess_resources
 resources=assess_resources(items,grid,steps)
 errors+=resources['errors'];warnings+=resources['warnings'];checks+=resources['checks']
 warnings.append('Metadata checks do not establish usable pixel coverage or environmental accuracy; those require science reads and independent evidence.')
 return {'ready':not errors,'scope':'metadata only; no data downloaded','errors':list(dict.fromkeys(errors)),'warnings':list(dict.fromkeys(warnings)),'checks':checks,'groups':group_rows,'stage_baselines':stage_baselines,**{key:resources[key] for key in ['disk_space','estimated_trace_bytes','estimated_trace_maps','estimated_grid_bytes','memory_budget_bytes']}}


def require(report):
 if not report['ready']:raise ValueError(' '.join(report['errors']))
 return report
