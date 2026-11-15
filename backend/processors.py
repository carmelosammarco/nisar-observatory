"""Seven bounded exploratory workflows; no classifier is presented as validated truth."""
from .execution import cancellable,checkpoint
from .processing_trace import snapshot,enabled
from datetime import datetime
import numpy as np
from scipy import ndimage
from pyproj import Transformer
from .spatial import context_masks,union_role,optional_patch_history as patch_history
from .los import los_trend,phase_group
from .advanced import robust_baseline,local_offset_filter,network_solution,coarsened_water_sensitivity
from .validation import water_calibration,regional_validation
from .water import joint_water_evidence,joint_grid_sensitivity
from .engines import PRODUCT_FOR,MINIMUM,ALGORITHM_VERSION,summary,support,water_evidence,phase_engine,pair_network,offset_engine,days_between

def iso(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
stats=summary
def region_mask(bbox,grid):
 h,w=grid['shape'];t=grid['transform'];xx=t.c+(np.arange(w)+.5)*t.a;yy=t.f+(np.arange(h)+.5)*t.e
 conv=Transformer.from_crs('EPSG:4326',grid['crs'],always_xy=True)
 west,south,east,north=bbox;x0,y0=conv.transform(west,south);x1,y1=conv.transform(east,north)
 return (yy[:,None]>=min(y0,y1))&(yy[:,None]<=max(y0,y1))&(xx[None,:]>=min(x0,x1))&(xx[None,:]<=max(x0,x1))
@cancellable
def process(pid,obs,grid,opt):
 if pid not in PRODUCT_FOR:raise ValueError('Unknown processing tool.')
 if pid=='P03' and opt.get('fire_method')=='combined':
  from .fire import process as combined_fire
  return combined_fire(obs,grid,opt)
 product=PRODUCT_FOR[pid]
 seq=sorted([o for o in obs if o['item']['product']==product],key=lambda o:(o['item']['start'],o['item']['end']))
 minimum=MINIMUM[pid]
 if len(seq)<minimum:raise ValueError(f'{minimum} compatible usable {product} observations required; {len(seq)} available.')
 if not (pid=='P05' and opt.get('quake_mosaic') and len({o['item']['group'] for o in seq})>1) and len({(o['item']['start'],o['item']['end'] if product in ['GUNW','GOFF'] else '') for o in seq})!=len(seq):raise ValueError('Duplicate observation intervals selected; choose one version per date or pair.')
 if pid=='P05' and opt.get('quake_mosaic') and len({o['item']['group'] for o in seq})>1:
  from .quake import event_mosaic
  return event_mosaic(seq,grid,opt,process)
 if len({phase_group(o['item']['group'],pid=='P04' and opt.get('phase_allow_mixed_revisions',False)) for o in seq})>1:raise ValueError('Select one track/pass/frame/mode group for this product.')
 if len({o['path'].split('/frequencyA/')[-1] for o in seq})>1:raise ValueError('Selected science channels or offset layers differ.')
 arr=np.stack([o['array'] for o in seq]);valid=np.isfinite(arr);dates=[o['item']['start'] for o in seq];area=abs(grid['transform'].a*grid['transform'].e)/1e6
 contexts=context_masks(opt.get('spatial_context'),grid)
 domain=union_role(contexts,'domain',grid['shape'])
 if pid=='P06' and opt.get('surface_method')=='evolving':
  from .raster_methods import geographic_window_mask
  window=geographic_window_mask(grid);domain&=window
 if not domain.any():raise ValueError('The supplied domain has no analysis-cell centers in this area.')
 footprint=domain.copy()
 # Keep only auxiliary roles actually consumed by this method. A reference may
 # set the relative zero outside the study; it must not enlarge its statistics.
 declared_reference=np.zeros(grid['shape'],bool)
 if product=='GUNW' or pid=='P03':
  fallback=region_mask(opt['reference_bbox'],grid) if opt.get('reference_bbox') else np.zeros(grid['shape'],bool)
  declared_reference=union_role(contexts,'reference',grid['shape'],fallback)
  footprint|=declared_reference
 if product=='GOFF':footprint|=union_role(contexts,'stable',grid['shape'],np.zeros(grid['shape'],bool))
 arr[:,~footprint]=np.nan;valid=np.isfinite(arr)
 arr[~valid]=np.nan
 layers={};series=[];metrics={};notes=[];unit='';title='';extra={}
 common,counts=support(arr)
 if not common.any():raise ValueError('No common valid footprint across selected observations. Choose overlapping acquisitions or a smaller area.')
 if not (common&domain).any():raise ValueError('No common valid pixels remain inside the study domain. Coverage in reference or stable-ground polygons outside it is not study coverage. Revise the domain or selected observations.')
 study_common=common&domain
 extra['support']={'mode':'fixed common footprint across all selected observations','common_pixels':int(study_common.sum()),'common_area_km2':float(study_common.sum()*area),'common_fraction':float(study_common.mean()),'per_observation_valid_pixels':[int((v&domain).sum()) for v in valid]}
 if any(f['role']=='domain' for f in contexts):
  extra['spatial_support']={'version':'1.0','domain_pixels':int(domain.sum()),'processing_footprint_pixels':int(footprint.sum()),'auxiliary_pixels_outside_domain':int((footprint&~domain).sum()),'policy':'Measurement maps and regional summaries use the study domain. Reference or stable-ground samples outside it are retained only for the correction that uses them; Source-quality, raw-source, reference-support and intermediate maps are diagnostic evidence and can retain their own wider footprints.'}
  notes.append(extra['spatial_support']['policy'])
 if pid=='P06' and opt.get('surface_method')=='evolving':extra['support'].update(requested_window_pixels=int(window.sum()),selected_window_valid_fraction=float(common.sum()/max(1,window.sum())))
 extra['spatial_context']=[{'name':f['name'],'role':f['role'],'pixels':int(f['mask'].sum()),'source':f['properties'].get('source','user supplied')} for f in contexts]
 notes.append('All plotted regional comparisons use the same pixels valid on every selected date or pair. Per-date coverage is shown separately; missing coverage is never reported as zero change.')
 outside_domain=~domain
 def layer(name,data,label,unit_,kind='continuous',scope='study domain'):
  values=data.astype('float32')
  if scope=='study domain':values[outside_domain]=np.nan
  layers[name]={'data':values,'label':label,'unit':unit_,'kind':kind,'spatial_scope':scope}
 def temporal_summary(values,units):
  finite=np.isfinite(values);count=finite.sum(axis=0)
  # Explicit infinities avoid all-NaN reducer warnings; require repeated evidence.
  low=np.min(np.where(finite,values,np.inf),axis=0)
  high=np.max(np.where(finite,values,-np.inf),axis=0)
  spread=np.full(count.shape,np.nan,dtype='float32')
  repeated=count>=2;spread[repeated]=high[repeated]-low[repeated]
  layer('variability',spread,'Observed maximum minus minimum across acquisitions',units)
  layer('count',np.where(count>0,count,np.nan),'Number of valid observations','count')
 if product=='GCOV':
  valid=valid&(arr>0)
  db=10*np.log10(np.where(arr>0,arr,np.nan));delta=db[-1]-db[0]
  layer('backscatter',db[-1],'Latest calibrated backscatter','dB')
  for i,date in enumerate(dates):
   layer(f'observation_{i}',db[i],f'Backscatter · {date[:10]}','dB')
   layers[f'observation_{i}'].update(frame_index=i,start=date,end=seq[i]['item']['end'])
  layer('change',delta,'Latest minus first backscatter','dB','diverging')
  temporal_summary(db,'dB')
  baseline_db,baseline_noise,baseline_indices=robust_baseline(db,dates,opt)
  snapshot('surface_baseline','baseline_brightness',baseline_db,'Declared median brightness baseline','dB',start=dates[baseline_indices[0]],end=dates[baseline_indices[-1]])
  snapshot('surface_baseline','baseline_spread',baseline_noise,'Baseline robust spread with the declared noise floor','dB')
  extra['baseline']={'dates':[dates[i] for i in baseline_indices],'statistic':'per-cell median dB','noise_floor_db':float(opt.get('baseline_noise_floor_db',1))}
  layer('baseline_departure',db[-1]-baseline_db,'Latest minus median of the declared baseline dates','dB','diverging')
  layer('standardized_departure',(db[-1]-baseline_db)/baseline_noise,'Baseline departure divided by robust spread with declared noise floor','ratio','diverging')
  source_common=valid.all(axis=0);common=source_common&domain
  if not common.any():raise ValueError('No common valid footprint across positive-power observations.')
  threshold=float(opt.get('water_threshold',-17))
  dual_water=pid=='P02' and opt.get('water_method','single')=='hh_hv'
  if dual_water:
   for o in seq:
    if o['attrs'].get('water_method_error'):raise ValueError(o['item']['start'][:10]+': '+o['attrs']['water_method_error'])
    if not all(k in o.get('aux',{}) for k in ['water_hh_sigma_power','water_hv_sigma_power']):raise ValueError('HH/HV converted measurements are missing. Re-read the sources with HH/HV selected; no single-channel fallback is used.')
   hh_power=np.stack([o['aux']['water_hh_sigma_power'] for o in seq]);hv_power=np.stack([o['aux']['water_hv_sigma_power'] for o in seq])
   hh_db=10*np.log10(np.where(hh_power>0,hh_power,np.nan));hv_db=10*np.log10(np.where(hv_power>0,hv_power,np.nan))
   valid=np.isfinite(hh_db)&np.isfinite(hv_db)&domain
   common=valid.all(axis=0)
   if not common.any():raise ValueError('No common valid HH/HV footprint remains after joint quality and conversion screening.')
   hh_threshold=float(opt.get('water_hh_threshold',-14));hv_threshold=float(opt.get('water_hv_threshold',-23))
   water,sensitivity,water_metrics=joint_water_evidence(hh_db,hv_db,common,hh_threshold,hv_threshold,area)
   _,validation=water_calibration(np.where(common,hh_db,np.nan),dates,contexts,hh_threshold,fixed_states=water)
   validation.pop('threshold_db',None);validation['thresholds_db']={'HH':hh_threshold,'HV':hv_threshold};extra['water_validation']=validation
   extra['water_method']={'id':'hh_hv','label':'HH/HV · sigma-zero','thresholds_db':{'HH':hh_threshold,'HV':hv_threshold},'rule':'Both HH and HV must be below their declared thresholds.','radiometry':'Native linear gamma-zero multiplied by the delivered gamma-to-sigma factor before averaging; identical joint native support for both channels.','filtering':'Valid-power averaging only; no Enhanced Lee filter.','reference':'https://doi.org/10.3390/rs17020263','calibration':'Paper-inspired fixed thresholds; not independently calibrated for these NISAR scenes.'}
   layer('hh_sigma',np.where(common,hh_db[-1],np.nan),'Latest HH sigma-zero backscatter','dB')
   layer('hv_sigma',np.where(common,hv_db[-1],np.nan),'Latest HV sigma-zero backscatter','dB')
   notes.append('HH/HV water candidates use sigma-zero after native conversion and joint screening. Both thresholds must be met. This adapts the published decision rule, not its filtering, depth, volume or validation; no environmental accuracy is implied.')
  else:
   if pid in ['P01','P02']:
    threshold,validation=water_calibration(np.where(common,db,np.nan),dates,contexts,threshold)
    extra['water_validation']=validation
   water,sensitivity,water_metrics=water_evidence(db,common,threshold,area)
   if pid=='P02':extra['water_method']={'id':'single','label':'Single-channel · gamma-zero','threshold_db':threshold,'rule':'Selected co-polarized gamma-zero below the declared threshold.'}
  extra['support'].update(common_pixels=int(common.sum()),common_area_km2=float(common.sum()*area),common_fraction=float(common.mean()),per_observation_valid_pixels=[int((v&domain).sum()) for v in valid])
  if pid in ['P06'] and not common.any():raise ValueError('No common valid footprint for scattering change. Choose overlapping acquisitions or a smaller area.')
  for i,date in enumerate(dates):
   series.append({'date':date,'median_db':stats(db[i][common])['median'],'water_candidate_km2':float(water[i,common].sum()*area),'valid_fraction':float((valid[i]&domain).mean())})
   if dual_water:series[-1].update(median_hh_sigma_db=stats(hh_db[i][common])['median'],median_hv_sigma_db=stats(hv_db[i][common])['median'])
  notes+=['Backscatter changes can reflect moisture, vegetation, roughness or geometry; they do not identify a cause by themselves.','Water candidates use a user-controlled threshold. They require local independent validation; shadow and smooth dry ground can be mistaken for water.','Area uses the common valid analysis grid; local UTM areas are approximate. Coarse analysis cells are averages, not new high-resolution observations.']
  unit='dB';title='Backscatter change'
  if pid=='P06':notes=[n for n in notes if not n.startswith('Water candidates use')]
  if pid in ['P01','P02']:
   if not common.any():raise ValueError('No common valid footprint across dates. Select overlapping acquisitions or a smaller area.')
   for i,date in enumerate(dates):
    layer(f'observation_{i}',np.where(common,water[i],np.nan),f'Open-water candidate · {date[:10]}','class','binary')
    layers[f'observation_{i}'].update(frame_index=i,start=date,end=seq[i]['item']['end'])
   notes.append('Dated water playback uses the same common valid footprint and threshold on every date; it shows candidates, not verified floods or daily water evolution.')
   layer('water',np.where(common,water[-1],np.nan),'Latest open-water candidate','class','binary')
   unknown_width=float(opt.get('water_unknown_db',1));unknown=((hh_db<hh_threshold+unknown_width)&(hv_db<hv_threshold+unknown_width)&~((hh_db<hh_threshold-unknown_width)&(hv_db<hv_threshold-unknown_width))) if dual_water else np.abs(db-threshold)<=unknown_width
   layer('water_state',np.where(common,np.where(unknown[-1],2,water[-1]),np.nan),'Latest water state · 0 dry candidate, 1 water candidate, 2 ambiguous','class','water_state')
   extra['water_states']={'codes':{'0':'dry candidate','1':'water candidate','2':'ambiguous'},'threshold_db':threshold,'ambiguity_half_width_db':unknown_width,'unknown_area_km2':[float((u&common).sum()*area) for u in unknown]}
   if dual_water:
    extra['water_states'].pop('threshold_db');extra['water_states']['thresholds_db']={'HH':hh_threshold,'HV':hv_threshold}
   extra['grid_sensitivity']=joint_grid_sensitivity(hh_power,hv_power,common,hh_threshold,hv_threshold,area) if dual_water else coarsened_water_sensitivity(arr,common,threshold,area)
   if opt.get('water_tracking_enabled',True):extra['tracking']=patch_history(water&common,dates,grid,float(opt.get('patch_area_m2',30000)))
   extra['threshold_sensitivity']={'description':'Both HH and HV thresholds shifted together by -2, -1, 0, +1, +2 dB on identical support. This does not explore every independent threshold combination or provide confidence intervals.' if dual_water else 'Five user-threshold scenarios on identical support. This is sensitivity, not a confidence interval.', 'scenarios':sensitivity}
   sensitive=((hh_db<hh_threshold+2)&(hv_db<hv_threshold+2)&~((hh_db<hh_threshold-2)&(hv_db<hv_threshold-2))) if dual_water else (db>=threshold-2)&(db<threshold+2)
   layer('threshold_sensitive',np.where(common,np.any(sensitive,axis=0),np.nan),'Classification changes within the declared 2 dB threshold scenarios','class','binary')
   wetcount=water.sum(axis=0);den=valid.sum(axis=0)
   layer('occupancy',np.where(den>=2,wetcount/np.maximum(den,1),np.nan),'Observed water-candidate fraction','fraction')
   layer('count',np.where(den>0,den,np.nan),'Number of valid observations','count')
   metrics={'common_valid_area_km2':float(common.sum()*area),'baseline_water_candidate_km2':float(water[0,common].sum()*area),'latest_water_candidate_km2':float(water[-1,common].sum()*area),**water_metrics}
   if pid=='P01':
    requested=opt.get('flood_date')
    if requested:
     candidates=[i for i,d in enumerate(dates) if d[:10]>=str(requested)]
     if not candidates or candidates[0]==0:raise ValueError('Flood comparison date needs at least one earlier baseline and one observation on or after the date.')
     event_index=candidates[0]
    else:
     gains=[int(((~water[i-1])&water[i]&common).sum()) for i in range(1,len(seq))]
     event_index=int(np.argmax(gains))+1
    baseline=np.median(db[:event_index],axis=0)<threshold
    if enabled('flood_history'):snapshot('flood_history','baseline_brightness',np.median(db[:event_index],axis=0),'Median brightness before the comparison observation','dB',start=dates[0],end=dates[event_index-1])
    extra['event_baseline']={'dates':dates[:event_index],'water_candidate_km2':float((baseline&common).sum()*area),'statistic':'median pre-comparison backscatter dB'}
    layer('event_baseline_departure',db[event_index]-np.median(db[:event_index],axis=0),'Comparison observation minus median pre-comparison baseline','dB','diverging')
    new=(~baseline)&water[event_index]&common
    recovery=np.full(common.shape,np.nan);lower=recovery.copy();upper=recovery.copy();last_wet=np.full(common.shape,event_index,dtype=int)
    for i in range(event_index+1,len(seq)):
     found=new&~water[i]&~np.isfinite(recovery)
     recovery[found]=i
     for previous in np.unique(last_wet[found]):
      cells=found&(last_wet==previous)
      lower[cells]=days_between(dates[event_index],dates[int(previous)])
      upper[cells]=days_between(dates[event_index],dates[i])
     last_wet[new&water[i]&~np.isfinite(recovery)]=i
    layer('event',np.where(common,new,np.nan),'New water candidate at the selected comparison observation','class','binary')
    layer('recovery',recovery,'First later dry observation index','observation index')
    layer('recovery_lower_days',lower,'Last wet observation before first dry state · days after comparison','days')
    layer('recovery_upper_days',upper,'First dry observation · days after comparison','days')
    layer('unresolved',np.where(new,~np.isfinite(recovery),np.nan),'New water candidate without a later dry observation','class','binary')
    metrics.update(new_water_candidate_km2=float(new.sum()*area),observed_dry_again_km2=float(np.isfinite(recovery).sum()*area),unresolved_water_candidate_km2=float((new&~np.isfinite(recovery)).sum()*area))
    extra['event_selection']={'index':event_index,'date':dates[event_index],'method':'user comparison date' if requested else 'largest consecutive new-water candidate area; earliest tie','baseline_dates':dates[:event_index]}
    extra['recovery_calendar']=[{'index':i,'date':dates[i]} for i in range(event_index+1,len(seq))]
    notes.append('Baseline is the median backscatter of observations before the comparison date. Automatic comparison selection finds the largest consecutive candidate expansion; it does not verify a flood. Last-wet and first-dry observations bound the first observed return to dry; intervening wet/dry cycles are unknown, and no later dry observation means unresolved, not still flooded.')
   elif pid=='P02':
    metrics['intermittent_water_candidate_km2']=float(((water.any(axis=0))&(~water.all(axis=0))&common).sum()*area)
    metrics['always_water_candidate_km2']=float((water.all(axis=0)&common).sum()*area)
    mid=arr.shape[2]//2
    extra['zones']=[{'name':side,'wet_fraction':[float(water[i,:,sl][common[:,sl]].mean()) if common[:,sl].any() else None for i in range(len(seq))],'valid_counts':[int(common[:,sl].sum()) for i in range(len(seq))]} for side,sl in [('West half',slice(None,mid)),('East half',slice(mid,None))]]
    named=[f for f in contexts if f['role']=='zone']
    if named:extra['zones']=[{'name':f['name'],'wet_fraction':[float(water[i][common&f['mask']].mean()) if (common&f['mask']).any() else None for i in range(len(seq))],'valid_counts':[int((common&f['mask']).sum())]*len(seq)} for f in named]
    notes.append('Zone trajectories use only pixels valid on every selected date. A zone without common coverage is missing, not zero wetness.')
    notes.append('Named polygons define comparison zones; their source and common valid coverage are recorded. They are not date-specific inundation truth.' if named else 'West/east halves are exploratory comparison zones, not wetland vegetation classes or hydraulic compartments.')
    notes.append('Open-water candidates do not capture all vegetated inundation. Observation frequency is not the proportion of continuously elapsed time flooded.')
   title={'P01':'Observed flood-change and recovery','P02':'Observed wetness occupancy'}[pid]
  elif pid=='P03':
   if not opt.get('reference_bbox') and not any(f['role']=='reference' for f in contexts):raise ValueError('Draw an unaffected reference rectangle inside the analysis area to compare trajectories.')
   reference=declared_reference;ref=reference&source_common;affected=union_role(contexts,'affected',grid['shape'],domain)&domain&(~reference)&common
   if not ref.any() or not affected.any():raise ValueError('Reference and comparison areas each need pixels valid on every date. Choose another reference or fewer overlapping acquisitions.')
   for i,row in enumerate(series):
    row['reference_median_db']=stats(db[i][ref])['median'];row['affected_median_db']=stats(db[i][affected])['median']
    if row['reference_median_db'] is None or row['affected_median_db'] is None:raise ValueError('Reference or comparison zone has no valid data.')
    difference=db[i]-baseline_db
    row['relative_trajectory_db']=float(np.median(difference[affected])-np.median(difference[ref]))
   relative_delta=db[-1]-baseline_db
   layer('relative_change',np.where(common,relative_delta-np.median(relative_delta[ref]),np.nan),'Change relative to reference median','dB','diverging');title='Reference-normalized scattering trajectory'
   layer('reference_support',np.where(source_common,reference,np.nan),'Reference cells used on every date','class','binary',scope='reference support')
   extra['reference_diagnostics']={'pixels':int(ref.sum()),'area_km2':float(ref.sum()*area),'comparison_pixels':int(affected.sum()),'latest_change_p10_db':float(np.percentile(relative_delta[ref],10)),'latest_change_median_db':float(np.median(relative_delta[ref])),'latest_change_p90_db':float(np.percentile(relative_delta[ref],90))}
   metrics={'reference_pixels':int(ref.sum()),'comparison_pixels':int(affected.sum()),'relative_trajectory_db':float(series[-1]['relative_trajectory_db'])}
   references=[f for f in contexts if f['role']=='reference']
   extra['reference_sensitivity']=[{'name':f['name'],'relative_change_db':float(np.median(relative_delta[affected])-np.median(relative_delta[source_common&f['mask']])) if (source_common&f['mask']).any() else None} for f in references]
   notes.append('Map and trajectory both use per-cell departures from the same baseline, followed by reference-median subtraction. The trajectory is the median of that normalized map within the comparison domain.')
   notes.append('Trajectories use a fixed footprint of pixels valid on every date. The complement of the reference is the comparison area. A fire perimeter and dated independent vegetation evidence are still required to attribute fire effects or recovery.')
  elif pid=='P06':
   if opt.get('surface_method','legacy')=='evolving':
    from .surface import evolving_surface
    additions,metrics,evidence,updates,surface_notes=evolving_surface(db,baseline_db,baseline_indices,common,dates,grid,opt)
    layers.update(additions);extra.update(evidence);notes.extend(surface_notes)
    for row,update_row in zip(series,updates):row.update(update_row)
    title='Evolving volcanic surface-scattering evidence'
   else:
    threshold=float(opt.get('change_threshold',3));changes=db[[i for i in range(len(db)) if i>max(baseline_indices)]]-baseline_db;increase=(changes>=threshold).all(axis=0)&common;decrease=(changes<=-threshold).all(axis=0)&common;persistent=increase|decrease
    layer('change_direction',np.where(common,increase.astype(float)-decrease.astype(float),np.nan),'Consistent brightness increase (+1) or decrease (−1)','class','diverging')
    steps=np.diff(db,axis=0);idx=np.argmax(np.abs(steps),axis=0)
    layer('largest_step',np.where(common,idx+1,np.nan),'Index of observation ending the largest brightness step','observation index')
    extra['step_calendar']=[{'index':i,'start':dates[i-1],'end':dates[i]} for i in range(1,len(seq))]
    metrics={'persistent_change_area_km2':float(persistent.sum()*area),'increasing_area_km2':float(increase.sum()*area),'decreasing_area_km2':float(decrease.sum()*area)}
    layer('surface',np.where(common,persistent,np.nan),'Persistent candidate surface change','class','binary');title='Volcano surface scattering diary'
    extra['tracking']=patch_history((np.abs(db-baseline_db)>=threshold)&common,dates,grid,float(opt.get('patch_area_m2',30000)))
    notes.append('Annotations must be checked against eruption chronology. Radar brightness is not temperature, magma volume or eruption probability.')
 elif product=='GUNW':
  if not opt.get('reference_bbox') and not any(f['role']=='reference' for f in contexts):raise ValueError('Draw a stable reference rectangle inside the selected area before phase processing.')
  ref=declared_reference
  if '_phase_reference_mask' in opt:ref=np.asarray(opt['_phase_reference_mask'],dtype=bool)&ref
  ranges,rates,fixed_reference,reference_diagnostics=phase_engine(arr,seq,ref,comparison=domain)
  ranges[:,~domain]=np.nan;rates[:,~domain]=np.nan
  phase_common=common&domain
  extra['support'].update(common_pixels=int(phase_common.sum()),common_area_km2=float(phase_common.sum()*area),common_fraction=float(phase_common.mean()))
  extra['reference_diagnostics']={'domain_reference_version':'1.1','support_scope':'Reference support is preserved independently of the analysis domain; output summaries use the domain only.','fixed_pixels':int(fixed_reference.sum()),'area_km2':float(fixed_reference.sum()*area),'pairs':reference_diagnostics}
  extra['pair_network']=pair_network(seq,ranges)
  extra['phase_reference_sensitivity']=[{'name':f['name'],'fixed_pixels':int((f['mask']&common).sum()),'pair_reference_shift_mm':[-o['wavelength']*(float(np.median(arr[i][f['mask']&common]))-float(np.median(arr[i][fixed_reference])))/(4*np.pi)*1000 if (f['mask']&common).any() else None for i,o in enumerate(seq)]} for f in contexts if f['role']=='reference']
  layer('count',np.where(counts>0,counts,np.nan),'Number of quality-screened pair observations','count')
  layer('reference_support',np.where(common,fixed_reference,np.nan),'Fixed reference support shared by every pair','class','binary',scope='reference support')
  selected=len(seq)-1
  if pid=='P05':
   event=opt.get('event_timestamp') or opt.get('event_date')
   if not event:raise ValueError('Set the independently documented earthquake date first.')
   from .quake import brackets_event
   matches=[i for i,o in enumerate(seq) if brackets_event(o['item'],opt)]
   if not matches:raise ValueError('No selected pair strictly brackets the event date. Same-day event timing requires a separate timestamp check.')
   selected=min(matches,key=lambda i:days_between(seq[i]['item']['start'],seq[i]['item']['end']))
   snapshot('event_pairs','selected_phase',arr[selected],'Selected quality-screened input phase · '+seq[selected]['item']['group'],'rad','diverging',group=seq[selected]['item']['group'],start=seq[selected]['item']['start'],end=seq[selected]['item']['end'])
   extra['event_selection']={'timing_precision':'timestamp' if opt.get('event_timestamp') else 'calendar date','matching_pairs':len(matches),'selection':'shortest pair strictly bracketing the documented date','event_date':event}
   notes.append('The shortest event-bracketing interval is selected. Any signal may also include other changes within that interval; this is not a building-damage map.')
  for i,o in enumerate(seq):
   checkpoint()
   layer(f'observation_{i}',ranges[i],f"Pair · {o['item']['start'][:10]} → {o['item']['end'][:10]}",'mm','diverging')
   layers[f'observation_{i}'].update(frame_index=i,start=o['item']['start'],end=o['item']['end'])
  layer('interval_rate',rates[selected],'Relative phase-equivalent change divided by selected pair days','mm/day','diverging')
  layer('range',ranges[selected],'Relative phase-equivalent range change','mm','diverging');title='Relative phase-equivalent range change';unit='mm'
  for i,o in enumerate(seq):series.append({'date':o['item']['start'],'end':o['item']['end'],'median_mm':stats(ranges[i])['median'],'p10_mm':stats(ranges[i])['p10'],'p90_mm':stats(ranges[i])['p90'],'valid_fraction':float((np.isfinite(arr[i])&domain).mean()),'comparison_pixels':int(phase_common.sum()),'interval_days':reference_diagnostics[i]['interval_days'],'median_rate_mm_day':stats(rates[i])['median']})
  extra['selected_interval']={'start':seq[selected]['item']['start'],'end':seq[selected]['item']['end']}
  if pid=='P05':
   extra['event_controls']=[row.copy() for i,row in enumerate(series) if i not in matches]
   for i,o in enumerate(seq):
    checkpoint()
    layers[f'pair_{i}']=layers.pop(f'observation_{i}')
    layer(f'observation_{i}',ranges[i]/10,f"Relative LOS change · {o['item']['start'][:10]} → {o['item']['end'][:10]}",'cm','diverging')
    layers[f'observation_{i}'].update(frame_index=i,start=o['item']['start'],end=o['item']['end'])
    series[i].update(median_cm=series[i]['median_mm']/10 if series[i]['median_mm'] is not None else None)
   layer('event_displacement_cm',ranges[selected]/10,'Relative LOS displacement across the earthquake interval','cm','diverging')
   layers['event_displacement_cm'].update(start=seq[selected]['item']['start'],end=seq[selected]['item']['end'])
   extra['event_measurement']={'quantity':'relative line-of-sight displacement','unit':'cm','positive':'toward the satellite','negative':'away from the satellite','conversion':'−wavelength × (phase − reference median) / (4π) × 100','geometry':'Single radar view: horizontal and vertical motion are not separated.','selected_source':seq[selected]['item']['id'],'selected_group':seq[selected]['item']['group']}
   title='Earthquake interval · relative LOS displacement';unit='cm'
  metrics={**stats(ranges[selected]),'reference_pixels':int(fixed_reference.sum()),'interval_days':reference_diagnostics[selected]['interval_days']};extra['profile']=[{'column':i,'median_mm':stats(ranges[selected][:,i])['median']} for i in range(arr.shape[2])]
  if pid=='P05':
   metrics={**stats(ranges[selected]/10),'reference_pixels':int(fixed_reference.sum()),'interval_days':reference_diagnostics[selected]['interval_days']}
   for row in extra['profile']:row['median_cm']=row['median_mm']/10 if row['median_mm'] is not None else None
   notes.append('The main earthquake map is displacement in cm across the selected interval, not a rate. Positive is toward the satellite and negative away; neither is automatically east/west or up/down. Raw measured pairs in mm and interval rates remain in Advanced maps.')
  notes+=['Each point is a separate pair interval, not a cumulative displacement time series or a fitted velocity.','Conversion is −λ × (phase − reference median)/(4π), in millimeters. Check product sign convention before assigning toward/away language.','Only the retained native connected component is used. Read the correction manifest: ionospheric subtraction is optional; tropospheric and tidal corrections are not assumed.','Reference stability is an assumption. No vertical motion, structural safety, failure probability or thaw depth is inferred.']
  extra['corrections']=[{'source':o['item']['id'],'applied':o['attrs'].get('correction_manifest',[])} for o in seq]
  if pid!='P04' and opt.get('phase_network',True):
   solution,model=network_solution(seq,ranges,require_cycles=True);extra['network_model']=model
   if solution is not None:
    layer('network_residual',solution['rms'],'Pair-network reconstruction residual RMS','mm')
    layer('network_rate',solution['rate'],'Fitted trend of the phase-equivalent network reconstruction','mm/year','diverging')
    extra['network_series']=[{'date':d,'median_mm':stats(solution['cube'][i])['median']} for i,d in enumerate(model['epochs'])]
  if pid=='P04':
   solution,model=los_trend(seq,ranges);extra['los_model']=model
   revisions=sorted({o['item']['group'] for o in seq});extra['processing_revisions']=revisions
   if len(revisions)>1:notes.append('Mixed processing revisions were explicitly accepted. Algorithm differences may mimic surface change. Compare a single-revision run; release families and viewing geometries remain separate.')
   if solution is not None:
    extra['pair_network'].update(inversion_performed=True,interpretation='Graph diagnostics and exact-endpoint closure describe the measured pairs. P04 reconstructed the connected graph; see los_model for the fit and its limits. A tree has no independent closure check.')
    extra['pair_series']=list(series)
    for i in range(len(seq)):layers[f'pair_{i}']=layers.pop(f'observation_{i}')
    for i,date in enumerate(model['epochs']):
     layer(f'observation_{i}',solution['cube_cm'][i],f'Reconstructed relative LOS change · {date[:10]}','cm','diverging')
     layers[f'observation_{i}'].update(frame_index=i,start=date,frame_scope='epoch')
    layer('los_rate_year',solution['rate_year'],'Fitted relative LOS rate · annualized','cm/year','diverging')
    layer('los_rate_month',solution['rate_month'],'Fitted relative LOS rate · per mean month','cm/month','diverging')
    layer('los_change',solution['change_cm'],'Reconstructed first-to-last relative LOS change','cm','diverging')
    layer('los_fit_residual',solution['fit_rms_cm'],'Linear-trend residual RMS · internal fit only','cm')
    layer('los_pair_residual',solution['pair_residual_cm'],'Pair-network residual RMS · zero by construction for a tree','cm')
    extra['los_series']=[{'date':d,'median_cm':stats(solution['cube_cm'][i])['median'],'p10_cm':stats(solution['cube_cm'][i])['p10'],'p90_cm':stats(solution['cube_cm'][i])['p90']} for i,d in enumerate(model['epochs'])]
    metrics={**stats(solution['rate_year']),'median_rate_cm_year':stats(solution['rate_year'])['median'],'median_rate_cm_month':stats(solution['rate_month'])['median'],'reference_pixels':int(fixed_reference.sum()),'span_days':model['span_days'],'acquisition_dates':model['epoch_count']}
    unit='cm/year';title='Relative LOS motion · fitted multi-date rate'
    extra.pop('profile',None)
    notes=[n for n in notes if not n.startswith('Each point is a separate pair interval')]
    notes+=['Rate maps fit a trend across reconstructed acquired epochs. The dated timeline shows accumulated relative LOS changes in cm, not separate pair intervals. Original pair maps remain available.',
            'cm/year is annualized from the selected record; cm/month = cm/year / 12. Positive means toward the satellite, negative away. Neither is automatically vertical sinking.',
            'A connected tree can be reconstructed but has no independent closure check: a zero pair residual is then guaranteed by the model and is not evidence of accuracy. Fit residual, phase errors and reference assumptions must be inspected.']
   else:notes.append('P04 trend not fitted: '+model.get('reason','Insufficient connected observations.'))

 else:
  unit=opt.get('offset_rate_unit','m/day');title='Screened radar-component offset rates'
  result=arr.copy()
  if product=='GOFF':
   local=[];local_rejected=[]
   for values in arr:
    filtered,rejected=local_offset_filter(values,opt,domain=domain);local.append(filtered);local_rejected.append(rejected)
   local=np.stack(local);result,diagnostics=offset_engine(local,seq,opt,trace_component=opt.get('component','slantRangeOffset'),domain=domain);extra['offset_filter_diagnostics']=diagnostics
   scale=365.25 if unit=='m/year' else 1.
   magnitudes=[];component_diagnostics=[];horizontal_frames=[];horizontal_diagnostics=[]
   stable=union_role(contexts,'stable',grid['shape'],np.zeros(grid['shape'],bool));biases=[]
   for i,o in enumerate(seq):
    checkpoint()
    days=days_between(o['item']['start'],o['item']['end'])
    layer(f'offset_raw_{i}',scale*arr[i]/days,'SNR-screened offset rate before spatial filtering · '+dates[i][:10],unit,'diverging',scope='processing footprint')
    rejected=(np.isfinite(arr[i])&~np.isfinite(result[i]))|local_rejected[i]
    layer(f'offset_rejected_{i}',np.where(np.isfinite(arr[i]),rejected,np.nan),'Spatial-filter rejection mask · '+dates[i][:10],'class','binary',scope='processing footprint')
    mask=stable&np.isfinite(result[i]);bias=float(np.median(result[i][mask])) if mask.any() else None
    if opt.get('offset_stable_bias',False):
     if bias is None:raise ValueError('Stable-terrain correction requested but the stable polygon has no usable pixels.')
     result[i]-=bias
    snapshot('offset_bias','primary_rate',result[i],'Selected radar-component rate after the bias option · '+dates[i][:10],'m/day','diverging',group=o['item']['group'],start=o['item']['start'],end=o['item']['end'],interpretation='This is the rate immediately after the optional bias correction; units are m/day before the final display-unit multiplication. Disabled correction leaves the filtered rate unchanged.')
    biases.append({'date':dates[i],'stable_pixels':int(mask.sum()),'median_rate_bias_m_day':bias,'applied':bool(opt.get('offset_stable_bias',False))})
    other=o.get('aux',{}).get('other_offset')
    if other is not None:
     layer(f'other_component_{i}',scale*other/days,'Other SNR-screened radar-component rate before spatial filtering · '+dates[i][:10],unit,'diverging',scope='source diagnostic')
     layer(f'radar_magnitude_{i}',scale*np.hypot(arr[i]/days,other/days),'Two-component radar-plane magnitude before spatial filtering · not geographic speed',unit,scope='processing footprint')
     other=np.asarray(other).copy();other[~footprint]=np.nan
     other_local,other_rejected=local_offset_filter(other,opt,domain=domain)
     if (np.isfinite(other_local)&domain).any():
      other_rate,other_info=offset_engine(other_local[None],[o],opt,trace_component='alongTrackOffset' if opt.get('component','slantRangeOffset')=='slantRangeOffset' else 'slantRangeOffset',domain=domain);other_rate=other_rate[0]
     else:
      other_rate=np.full(other.shape,np.nan);other_info=[{'source':o['item']['id'],'status':'No usable other-component samples after screening.'}]
     other_mask=stable&np.isfinite(other_rate);other_bias=float(np.median(other_rate[other_mask])) if other_mask.any() else None
     if opt.get('offset_stable_bias',False):
      if other_bias is None:raise ValueError('Stable-terrain correction requested but the other offset component has no usable stable pixels.')
      other_rate-=other_bias
     snapshot('offset_bias','other_rate',other_rate,'Other radar-component rate after the bias option · '+dates[i][:10],'m/day','diverging',group=o['item']['group'],start=o['item']['start'],end=o['item']['end'])
     shared=np.isfinite(result[i])&np.isfinite(other_rate)&domain
     magnitude=np.where(shared,np.hypot(result[i],other_rate)*scale,np.nan)
     magnitudes.append((i,magnitude))
     layer(f'other_filtered_{i}',np.where(shared,scale*other_rate,np.nan),'Other filtered radar-component rate · '+dates[i][:10],unit,'diverging')
     layer(f'radar_filtered_{i}',magnitude,'Filtered two-component radar-plane magnitude · '+dates[i][:10]+' · not horizontal speed',unit)
     component_diagnostics.append({**other_info[0],'local_removed_pixels':int(other_rejected.sum()),'joint_pixels':int(shared.sum()),'stable_pixels':int(other_mask.sum()),'median_rate_bias_m_day':other_bias,'bias_applied':bool(opt.get('offset_stable_bias',False))})
     if opt.get('offset_solution')=='horizontal':
      from .glacier_geometry import horizontal,FIELDS
      geometry={key:o.get('aux',{}).get('geometry_'+key) for key in FIELDS}
      if any(v is None for v in geometry.values()):raise ValueError('Horizontal speed needs readable viewing geometry for every selected pair. Prepare geometry first; no radar-only file is silently omitted.')
      primary=result[i].copy();secondary=other_rate.copy();primary[~domain]=np.nan;secondary[~domain]=np.nan
      rr,aa=(primary,secondary) if opt.get('component','slantRangeOffset')=='slantRangeOffset' else (secondary,primary)
      solution,diagnostic=horizontal(rr,aa,geometry,float(opt.get('offset_condition_limit',10)),float(opt.get('offset_vertical_scenario_m_year',20)),scale)
      snapshot('horizontal_velocity','speed_daily',solution['speed'],'Estimated horizontal speed before display-unit conversion · '+dates[i][:10],'m/day',group=o['item']['group'],start=o['item']['start'],end=o['item']['end'],interpretation='Delivered viewing geometry with vertical velocity fixed to zero. This is the unannualized pair-interval estimate, not a measured full year or an unconstrained 3D velocity.')
      horizontal_frames.append(solution['speed']*scale)
      for key,label_,units_,kind_ in [('east','Eastward horizontal velocity',unit,'diverging'),('north','Northward horizontal velocity',unit,'diverging'),('bearing','Horizontal flow direction clockwise from true north','degrees','continuous'),('condition','Horizontal-inversion condition number','ratio','continuous'),('vertical_sensitivity','Horizontal-vector sensitivity to the vertical-motion scenario',unit,'continuous')]:
       values=solution[key]*scale if key in ['east','north'] else solution[key]
       layer(f'horizontal_{key}_{i}',np.where(domain,values,np.nan),label_+' · '+dates[i][:10],units_,kind_)
      horizontal_diagnostics.append({'source':o['item']['id'],'start':o['item']['start'],'end':o['item']['end'],**diagnostic,'geometry':o.get('attrs',{}).get('viewing_geometry',{})})
    elif opt.get('offset_solution')=='horizontal':raise ValueError('Horizontal speed requires both delivered offset components.')
   if opt.get('offset_solution')=='horizontal':
    if len(horizontal_frames)!=len(seq):raise ValueError('Horizontal geometry did not supply every selected observation.')
    hc=np.stack(horizontal_frames);joint=np.isfinite(hc).all(axis=0)
    if not joint.any():raise ValueError('No common usable horizontal-speed support. Check geometry height, conditioning, native quality and selected intervals.')
    layer('horizontal_speed',hc[-1],'Estimated horizontal glacier speed · zero vertical velocity',unit)
    if len(hc)>1:layer('horizontal_change',np.where(joint,hc[-1]-hc[0],np.nan),'Latest minus first horizontal speed · common support',unit,'diverging')
    extra['horizontal_velocity']={'assumption':'Vertical velocity is fixed at zero in the local East/North/Up frame. This is a constrained estimate; glacier flow down a slope can violate it. No DEM surface-parallel correction is applied.','equations':'range_rate = -LOS_E * vE - LOS_N * vN - LOS_U * vU; along_rate = AT_E * vE + AT_N * vN; vU = 0. Solve the per-cell 2x2 system.','height_above_ellipsoid_m':float(opt.get('offset_geometry_height_m',0)),'height_source':'User-specified constant height used for trilinear geometry interpolation, not a per-pixel DEM','maximum_condition_number':float(opt.get('offset_condition_limit',10)),'vertical_scenario_m_year':float(opt.get('offset_vertical_scenario_m_year',20)),'vertical_scenario_meaning':'Magnitude of possible horizontal-vector bias if actual vertical velocity differs from zero by the stated value. It is a sensitivity scenario, not an error bar or confidence interval.','common_cells':int(joint.sum()),'latest_speed':stats(hc[-1]),'series':[{'date':o['item']['start'],'end':o['item']['end'],'median':stats(hc[i][joint])['median']} for i,o in enumerate(seq)],'pairs':horizontal_diagnostics,'unit':unit}
    title='Estimated horizontal glacier speed · zero vertical velocity'
    notes.append('Horizontal speed uses the delivered ENU viewing vectors and a zero-vertical-velocity constraint. Geometry is interpolated at the explicitly supplied constant ellipsoidal height without extrapolation. Ill-conditioned systems and invalid vectors are excluded. Down-slope motion, residual registration bias, snow matching and offset noise can bias this estimate. Inspect the vertical-motion sensitivity scenario; it is not a confidence interval.')
   if magnitudes and magnitudes[-1][0]==len(seq)-1:
    layer('radar_magnitude',magnitudes[-1][1],'Latest filtered radar-plane motion magnitude · not horizontal glacier speed',unit)
   result*=scale
   extra['offset_measurement']={'layer':opt.get('offset_layer','layer1'),'component':opt.get('component','slantRangeOffset'),'unit':unit,'annualization_factor':scale,'other_component_diagnostics':component_diagnostics,'meaning':'These diagnostic maps retain signed radar components and their radar-plane norm; they are not horizontal speed. Any constrained horizontal estimate is described separately. Annualized units extrapolate the pair rate, not observed annual displacement.'}
   extra['stable_terrain']=biases
   result[:,~domain]=np.nan
   notes.append('Radar diagnostic maps show range or along-track components per exact elapsed day; horizontal estimates, when requested, are reported separately. The configurable spatial MAD filter can remove real localized motion: compare a run with filtering disabled. Diagnostics give cutoff and rejected counts.')
   notes.append('The selected delivered offset layer is used consistently for both components and its own SNR. Filtered radar-plane magnitude requires both components to survive the same configured screening procedure; each component has its own cutoff and optional stable-ground bias. The raw magnitude remains an advanced diagnostic. Norms are positively biased by measurement noise and are not horizontal glacier speed. m/year = m/day × 365.25, not a year of measurements.')
   if any(f['role']=='domain' for f in contexts):notes.append('Spatial offset filters use the study domain for both radar components. Stable-ground samples outside it retain native-quality screening and are used only for the separate median bias diagnostic/correction; they do not set the moving-domain filter cutoff.')
  common,counts=support(result)
  if not common.any():raise ValueError('No common valid footprint remains after product filtering. Review quality/filter settings or select fewer overlapping observations.')
  extra['support'].update(common_pixels=int(common.sum()),common_area_km2=float(common.sum()*area),common_fraction=float(common.mean()),per_observation_valid_pixels=[int(np.isfinite(a).sum()) for a in result])
  for i,o in enumerate(seq):
   checkpoint()
   layer(f'observation_{i}',result[i],f"Observation · {o['item']['start'][:10]}",unit,'diverging' if product=='GOFF' else 'continuous')
   layers[f'observation_{i}'].update(frame_index=i,start=o['item']['start'],end=o['item']['end'])
   if product=='GOFF' and opt.get('offset_solution')=='horizontal':
    layers[f'radar_observation_{i}']=layers.pop(f'observation_{i}')
    layer(f'observation_{i}',horizontal_frames[i],'Estimated horizontal speed · '+o['item']['start'][:10]+' → '+o['item']['end'][:10],unit)
    layers[f'observation_{i}'].update(frame_index=i,start=o['item']['start'],end=o['item']['end'])
  layer('value',result[-1],'Selected radar-component rate · supporting diagnostic' if product=='GOFF' and opt.get('offset_solution')=='horizontal' else title,unit,'diverging' if product=='GOFF' else 'continuous')
  if len(result)>1:
   layer('change',result[-1]-result[0],'Difference between last and first observed values',unit,'diverging')
   temporal_summary(hc if product=='GOFF' and opt.get('offset_solution')=='horizontal' else result,unit)
  mid=arr.shape[2]//2
  for i,o in enumerate(seq):series.append({'date':o['item']['start'],'end':o['item']['end'],'median':stats(result[i][common])['median'],'west':stats(result[i,:,:mid][common[:,:mid]])['median'],'east':stats(result[i,:,mid:][common[:,mid:]])['median'],'valid_fraction':float(np.isfinite(result[i]).mean())})
  # Retain the analysis-grid denominator: slicing to common cells would make
  # valid_fraction report 100% even when most of the selected area is missing.
  metrics={**stats(np.where(common,result[-1],np.nan)),'common_valid_area_km2':float(common.sum()*area)}
  if product=='GOFF' and opt.get('offset_solution')=='horizontal':
   extra['offset_measurement']['radar_component_series']=series.copy()
   series=[{'date':o['item']['start'],'end':o['item']['end'],'median':stats(hc[i][joint])['median'],'west':stats(hc[i,:,:mid][joint[:,:mid]])['median'],'east':stats(hc[i,:,mid:][joint[:,mid:]])['median'],'valid_fraction':float(np.isfinite(hc[i]).mean()),'comparison_pixels':int(joint.sum())} for i,o in enumerate(seq)]
   extra['support'].update(basis='Estimated horizontal speed; zero vertical velocity',radar_common_pixels=int(common.sum()),common_pixels=int(joint.sum()),common_area_km2=float(joint.sum()*area),common_fraction=float(joint.mean()),per_observation_valid_pixels=[int(np.isfinite(a).sum()) for a in hc])
   metrics={**stats(np.where(joint,hc[-1],np.nan)),'common_valid_area_km2':float(joint.sum()*area)}
 if extra.get('tracking',{}).get('available') is False:notes.append('Optional candidate object tracking is unavailable. '+extra['tracking']['reason']+' Core measurement and change maps are retained without altering their values.')
 if not metrics:metrics=stats(np.where(common,delta,np.nan) if product=='GCOV' else next(iter(layers.values()))['data'])
 if product=='GCOV':
  for row in series:row['comparison_pixels']=int(common.sum())
  if pid in ['P06'] and opt.get('surface_method')!='evolving':notes.append('Persistent brightness-change candidates must keep the same direction relative to baseline; alternating brightening and darkening is not persistent change.')
 # Preserve native contribution fractions and explicit rejection diagnostics.
 for i,o in enumerate(seq):
  checkpoint()
  for name,values in o.get('aux',{}).items():
   if name in ['accepted_fraction','missing_fraction','coherence','snr','ionosphere_interpolated'] or pid=='P02' and name=='water_joint_accepted_fraction' or name.startswith('rejected_') or name.endswith('phase_correction'):
    safe=''.join(c if c in 'abcdefghijklmnopqrstuvwxyz0123456789_' else '_' for c in name.lower())
    layer(f'quality_{safe}_{i}',values,f"{name.replace('_',' ')} · {dates[i][:10]}",'fraction' if name=='ionosphere_interpolated' or 'fraction' in name or name.startswith('rejected_') else 'rad' if name.endswith('phase_correction') else 'score',scope='source quality')
 if product=='GCOV' and all('cross_copol_ratio_db' in o.get('aux',{}) for o in seq):
  ratios=np.stack([o['aux']['cross_copol_ratio_db'] for o in seq]);layer('polarization_ratio_change',ratios[-1]-ratios[0],'Latest minus first cross/co-polarized power ratio','dB','diverging',scope='source diagnostic')
 extra['observation_gaps']={'days_between_starts':[days_between(dates[i-1],dates[i]) for i in range(1,len(dates))],'longest_gap_days':max([days_between(dates[i-1],dates[i]) for i in range(1,len(dates))],default=None),'meaning':'Intervals without an acquisition are unobserved, not unchanged.'}
 if product in ['GOFF','GUNW']:
  references=opt.get('reference_observations',[]);horizontal_info=extra.get('horizontal_velocity',{})
  quantity=next((r.get('quantity') for r in references if r.get('product') in [None,product]),None)
  radar_series=extra.get('offset_measurement',{}).get('radar_component_series',series)
  validation_support=({'common_pixels':horizontal_info.get('common_cells'),'common_area_km2':horizontal_info.get('common_cells',0)*area} if quantity=='horizontal_speed' else {'common_pixels':extra['support'].get('radar_common_pixels'),'common_area_km2':extra['support'].get('radar_common_pixels',0)*area}) if horizontal_info else extra['support']
  extra['independent_validation']=regional_validation(radar_series,references,product,opt,horizontal_series=horizontal_info.get('series'),support=validation_support)
 extra['method_references']={'GCOV':['https://nisar-docs.asf.alaska.edu/gcov/','https://github.com/ASFOpenSARlab/NISAR_Cookbook/blob/main/notebooks/NISAR_GCOV_SARChangeDetectionMethods.ipynb'],'GUNW':['https://nisar-docs.asf.alaska.edu/gunw/','https://doi.org/10.1016/j.cageo.2019.104331'],'GOFF':['https://nisar-docs.asf.alaska.edu/goff/']}[product]
 report=build_report(pid,product,seq,metrics,extra,series)
 return {'project':pid,'title':title,'unit':unit,'layers':layers,'series':series,'metrics':metrics,'notes':list(dict.fromkeys(notes+sum([o['warnings'] for o in seq],[]))),'extra':extra,'sources':[{'id':o['item']['id'],'catalog_id':o['item'].get('catalog_id',o['item']['id']),'name':o['item']['name'],'start':o['item']['start'],'end':o['item']['end'],'group':o['item']['group'],'path':o['path'],'reader_version':o.get('reader_version','0.1.3'),'quality_paths':o['quality_paths'],'additional_paths':o.get('additional_paths',{}),'attributes':o['attrs'],'cache_identity':o.get('cache_identity'),'bytes_transferred':o['bytes_transferred'],'cache_hit':o.get('cache_hit',False)} for o in seq],'status':'exploratory','algorithm_version':'0.4.2' if pid=='P07' else '0.7.1' if pid=='P06' and opt.get('surface_method')=='evolving' else '0.5.0' if pid=='P02' and dual_water else '0.4.3' if pid=='P05' else ALGORITHM_VERSION,'report':report}


def build_report(pid,product,seq,metrics,extra,series):
 """Deterministic observations with traceable numbers; no generated causal claims."""
 evidence=extra['support'];first=seq[0]['item']['start'][:10];last=seq[-1]['item']['end' if product in ['GUNW','GOFF'] else 'start'][:10]
 findings=[f"{len(seq)} compatible {product} observations cover {first} to {last}. Regional comparisons use {evidence['common_pixels']:,} common analysis cells ({evidence['common_area_km2']:.3f} km²)."]
 def number(key):return f"{metrics[key]:.3f}"
 if 'water_gain_km2' in metrics:
  findings.append(f"Between first and last observations, candidate water gained {number('water_gain_km2')} km² and lost {number('water_loss_km2')} km² on the same footprint.")
 if pid=='P01':
  e=extra['event_selection'];findings.append(f"Comparison observation: {e['date'][:10]} ({e['method']}). New candidate water: {number('new_water_candidate_km2')} km²; later observed dry: {number('observed_dry_again_km2')} km²; unresolved: {number('unresolved_water_candidate_km2')} km².")
 if pid=='P02':findings.append(f"Candidate water appears intermittently over {number('intermittent_water_candidate_km2')} km² and on every observation over {number('always_water_candidate_km2')} km². These are observation frequencies, not continuous wetland hydroperiods.")
 if pid=='P02' and extra.get('water_method',{}).get('id')=='hh_hv':
  t=extra['water_method']['thresholds_db'];findings.append(f"Classification requires both HH sigma-zero below {t['HH']:g} dB and HV sigma-zero below {t['HV']:g} dB. Native conversion precedes averaging. This paper-inspired rule has not been independently calibrated or validated for this run.")
 if pid=='P03':findings.append(f"Latest reference-normalized comparison trajectory: {number('relative_trajectory_db')} dB. The comparison domain is the supplied domain excluding the reference; fire attribution requires independent context.")
 if pid=='P06' and not extra.get('surface_method'):findings.append(f"Consistent brightening covers {number('increasing_area_km2')} km² and dimming {number('decreasing_area_km2')} km². The largest-step map identifies an observed interval, not an eruption date.")
 if pid=='P06' and extra.get('surface_method'):
  findings.append(f"Latest candidate change covers {number('latest_change_area_km2')} km²; {number('repeated_latest_change_area_km2')} km² is supported on at least two consecutive later observations in the same direction. These are scattering candidates, not validated lava.")
  findings.append('The declared baseline is an observed starting state. Existing deposits may already be present; late-arriving patches and transient changes are kept separately.')
 if product=='GUNW':
  net=extra['pair_network'];findings.append(f"Reference uses {extra['reference_diagnostics']['fixed_pixels']} identical cells across pairs. Pair network: {net['epochs']} epochs, {net['connected_components']} connected component(s), {net['cycle_rank']} redundant edge(s). Read the P04 motion-model status or the other phase tools’ network-model status to see whether reconstruction was supported.")
 if pid=='P04' and extra.get('los_model',{}).get('status')=='fitted relative LOS trend':
  findings.append(f"Fitted relative LOS rate: regional median {number('median_rate_cm_year')} cm/year ({number('median_rate_cm_month')} cm per mean month), using {metrics['acquisition_dates']} acquired dates over {number('span_days')} days. Rates are relative to the saved reference, not vertical subsidence.")
  findings.append('The dated reconstruction is model-derived from measured pairs. No motion is interpolated between acquisitions. Zero pair residuals in a tree do not validate the result.')
 if pid=='P05':findings.append(f"Selected event interval: {extra['selected_interval']['start'][:10]} to {extra['selected_interval']['end'][:10]}. It strictly brackets the supplied date and is the shortest matching selected pair; other changes in that interval are not excluded.")
 if pid=='P05':findings.append(f"Relative LOS displacement across this interval: spatial median {number('median')} cm, p10 {number('p10')} cm and p90 {number('p90')} cm. Positive is toward the satellite and negative away, relative to the saved reference; these spatial percentiles are not accuracy bounds.")
 if pid=='P07' and extra.get('horizontal_velocity'):
  h=extra['horizontal_velocity'];findings.append(f"The constrained horizontal estimate retains {h['latest_speed']['valid_pixels']:,} latest-interval cells. Its median is {h['latest_speed']['median']:.3f} {h['unit']}. Vertical velocity was fixed at zero; this is not independently validated glacier speed.")
 if pid=='P07':findings.append(f"Spatial outlier filtering removed {sum(r['removed_pixels'] for r in extra['offset_filter_diagnostics'])} selected-component analysis-cell values across intervals. Supporting radar diagnostics remain component rates in {extra['offset_measurement']['unit']}; the selected motion estimate is described separately. Delivered offset layer: {extra['offset_measurement']['layer']}.")
 return {'headline':'What these observations show','findings':findings,
         'comparison_basis':evidence['mode'],
         'next_checks':['Inspect observation counts and source quality before interpreting a pattern.','Compare the map and observed dates; blank pixels are missing evidence.','Use independent observations to test environmental attribution.'],
         'validation':'Synthetic engineering tests check known calculations and missing-data behavior; independent real-world accuracy is not established.'}
