"""Bounded two-polarization, per-view change magnitude. No causal burn attribution."""
from .execution import cancellable,checkpoint
from .processing_trace import snapshot,enabled
import math,warnings
import numpy as np
from .spatial import context_masks,union_role

METHOD_VERSION='0.8.0'

from .raster_methods import analysis_grid,smooth,candidate_mask,geographic_window_mask

@cancellable
def process(obs,grid,opt):
 seq=sorted([o for o in obs if o['item']['product']=='GCOV'],key=lambda o:(o['item']['start'],o['item']['group']))
 if not seq:raise ValueError('Select GCOV observations with HH and HV channels.')
 if opt.get('channel','auto') not in ['auto','HHHH']:raise ValueError('Combined change uses HH and HV together. Choose Auto or HH; a single HV input cannot substitute for both channels.')
 groups={}
 for o in seq:groups.setdefault(o['item']['group'],[]).append(o)
 if len(groups)>4:raise ValueError('Select at most four compatible viewing groups; each needs its own pre-fire baseline.')
 contexts=context_masks(opt.get('spatial_context'),grid);window=geographic_window_mask(grid);domain=union_role(contexts,'domain',grid['shape'])&window
 if not domain.any():raise ValueError('The selected land domain contains no analysis cells.')
 sigma=float(opt.get('smoothing_m',80))/grid['resolution'];threshold=float(opt.get('score_threshold',2));patch=float(opt.get('patch_area_m2',100000));cell=abs(grid['transform'].a*grid['transform'].e)
 layers={};series=[];track_info=[];components=[];counts=[];notes=[];source_records=[]
 def layer(key,a,label,unit='dB',kind='continuous',**metadata):layers[key]={'data':np.asarray(a,dtype='float32'),'label':label,'unit':unit,'kind':kind,**metadata}
 for gi,(group,items) in enumerate(sorted(groups.items())):
  checkpoint()
  dates=[o['item']['start'] for o in items]
  if len({d[:10] for d in dates})!=len(dates):raise ValueError('Duplicate date/revision in a viewing group. Select one file per acquisition per group.')
  boundary=opt.get('baseline_end')
  before=[i for i,d in enumerate(dates) if d[:10]<=str(boundary)] if boundary else list(range(min(int(opt.get('baseline_count',3)),len(items))))
  after=[i for i in range(len(items)) if i not in before]
  if len(before)<3 or not after:raise ValueError(f'{group}: need at least three baseline dates and one later date. Set the baseline end before the fire, or choose the first three baseline observations.')
  hh=[];hv=[]
  for o in items:
   checkpoint()
   if 'cross_power' not in o.get('aux',{}):raise ValueError(o['item']['start'][:10]+': HH and HV are both required; no single-channel fallback is used.')
   co=np.asarray(o['array']);cross=np.asarray(o['aux']['cross_power']);paired=(co>0)&(cross>0)&np.isfinite(co)&np.isfinite(cross)&domain
   hh.append(np.where(paired,co,np.nan));hv.append(np.where(paired,cross,np.nan))
  hh=np.stack(hh);hv=np.stack(hv)
  # Require all three (or more) declared baselines, not a silently reduced median.
  fixed=np.isfinite(hh[before]).all(0)&np.isfinite(hv[before]).all(0)
  with warnings.catch_warnings():
   warnings.simplefilter('ignore',RuntimeWarning);bh=np.nanmedian(hh[before],axis=0);bv=np.nanmedian(hv[before],axis=0)
  if not fixed.any():raise ValueError(group+': no shared HH/HV baseline support.')
  if enabled('dual_change'):
   for channel,a in [('hh',bh),('hv',bv)]:snapshot('dual_change',channel+'_baseline',np.where(fixed,a,np.nan),channel.upper()+' median linear-power baseline · '+group,'power',group=group,start=dates[before[0]],end=dates[before[-1]])
  for index in after:
   checkpoint()
   with np.errstate(divide='ignore',invalid='ignore'):
    dh=np.where(fixed,10*np.log10(hh[index]/bh),np.nan);dv=np.where(fixed,10*np.log10(hv[index]/bv),np.nan)
   intensity=np.abs(dh)+np.abs(dv);frame=len(series);date=dates[index]
   layer('observation_'+str(frame),intensity,f'HH + HV absolute change · {group} · {date[:10]}',frame_index=frame,start=date,end=items[index]['item']['end'])
   v=intensity[np.isfinite(intensity)]
   series.append({'date':date,'group':group,'median_change_db':float(np.median(v)) if len(v) else None,'valid_pixels':int(len(v))})
   if index==after[-1]:
    components.append(intensity);counts.append(np.isfinite(intensity));layer(f'view_{gi}_hh_change',dh,f'{group} latest HH minus baseline',kind='diverging');layer(f'view_{gi}_hv_change',dv,f'{group} latest HV minus baseline',kind='diverging')
  track_info.append({'group':group,'baseline_dates':[dates[i] for i in before],'comparison_dates':[dates[i] for i in after],'latest':dates[after[-1]],'baseline_shared_pixels':int(fixed.sum())})
 stack=np.stack(components)
 with warnings.catch_warnings():warnings.simplefilter('ignore',RuntimeWarning);intensity=np.nanmean(stack,axis=0)
 smoothed=smooth(intensity,sigma);valid=np.isfinite(smoothed)&domain
 if valid.sum()<25:raise ValueError('Too little valid land remains to normalize the combined change.')
 center=float(np.median(smoothed[valid]));scale=float(1.4826*np.median(np.abs(smoothed[valid]-center)))
 if not np.isfinite(scale) or scale<=1e-8:raise ValueError('The selected window has no measurable robust spread. Enlarge the land window or review observations; a standardized score cannot be defined.')
 score=(smoothed-center)/scale;minimum=max(1,math.ceil(patch/cell));mask=candidate_mask(score,threshold,minimum)
 if enabled('threshold'):snapshot('threshold','candidate_before_patches',np.where(valid,score>=threshold,np.nan),'Score threshold before removing small patches','class','binary',interpretation='1 meets the score threshold; 0 does not. Derived directly from the score used by patch filtering. Neither code is verified fire.')
 layer('fire_score',score,'Combined HH/HV surface-change score','z');layer('fire_candidate',np.where(valid,mask,np.nan),'Candidate changed patches','class','binary');layer('change_intensity',intensity,'Mean absolute HH/HV change across available views');layer('smoothed_intensity',smoothed,'Smoothed absolute HH/HV change');layer('view_count',np.where(valid,np.sum(counts,axis=0),np.nan),'Number of latest valid viewing groups','count')
 for i,o in enumerate(seq):
  for name,a in o.get('aux',{}).items():
   if 'fraction' in name or name.startswith('rejected_'):layer(f'quality_{name}_{i}',a,f"{name.replace('_',' ')} · {o['item']['start'][:10]}",'fraction')
  source_records.append({'id':o['item']['id'],'catalog_id':o['item'].get('catalog_id',o['item']['id']),'name':o['item']['name'],'start':o['item']['start'],'end':o['item']['end'],'group':o['item']['group'],'path':o['path'],'additional_paths':o.get('additional_paths',{}),'attributes':o['attrs'],'quality_paths':o['quality_paths'],'cache_identity':o.get('cache_identity'),'bytes_transferred':o['bytes_transferred'],'cache_hit':o.get('cache_hit',False),'reader_version':o.get('reader_version')})
 frames=sorted([v for k,v in layers.items() if k.startswith('observation_')],key=lambda v:(v['start'],v['label']))
 layers={k:v for k,v in layers.items() if not k.startswith('observation_')}
 for i,v in enumerate(frames):v['frame_index']=i;layers['observation_'+str(i)]=v
 series.sort(key=lambda row:(row['date'],row['group']))
 area=float((mask&valid).sum()*cell/10000);valid_area=float(valid.sum()*cell/10000)
 notes=['Candidate patches show radar surface change, not independently verified burns, severity, biomass or recovery.','HH and HV changes are computed separately against each viewing group’s median linear-power baseline; raw opposite-view powers are never averaged.','The primary map combines the latest selected post-baseline observation per group. These dates are asynchronous; time frames show individual measured views, not a synchronized fused movie.','Robust normalization depends on the entire selected land window. Cropping or changing water exclusions changes the score and threshold result.','Native sample screening is applied before averaging. No per-track DEM/LOS terrain-shadow mask is implemented.','A supplied domain can exclude water; without a justified land domain, water and other unrelated changes can affect normalization.','Grid posting is not independent spatial resolving power: Gaussian full width at half maximum is 2.355 times smoothing sigma.']
 extra={'fire_method':{'id':'combined','label':'Combined HH/HV change','version':METHOD_VERSION,'groups':track_info,'normalization':{'median_db':center,'scaled_mad_db':scale,'valid_land_ha':valid_area},'smoothing_m':float(opt.get('smoothing_m',80)),'score_threshold':threshold,'minimum_patch_ha':patch/10000,'minimum_patch_cells':minimum,'connectivity':4,'terrain_mask_applied':False,'land_domain_supplied':any(f['role']=='domain' for f in contexts)},'support':{'mode':'All declared baseline dates per view; latest valid view magnitudes averaged without filling missing pixels','common_pixels':int(valid.sum()),'common_area_km2':valid_area/100,'common_fraction':float(valid.mean()),'per_observation_valid_pixels':[int(np.isfinite(o['array']).sum()) for o in seq]},'spatial_context':[{'name':f['name'],'role':f['role'],'pixels':int(f['mask'].sum())} for f in contexts],'method_references':['https://nisar-docs.asf.alaska.edu/gcov/','https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7553393']}
 findings=[f'{len(seq)} real GCOV observations from {len(groups)} viewing group(s) produced {area:.2f} ha of candidate changed patches within {valid_area:.2f} ha of valid land.',f'Threshold z ≥ {threshold:g}; patches ≥ {patch/10000:g} ha. Spatial normalization: median {center:.4f} dB, scaled MAD {scale:.4f} dB.','This detects surface-scattering change. Independent fire evidence is required for burn attribution; no recovery or severity is measured.']
 return {'project':'P03','title':'Combined HH/HV surface-change evidence','unit':'z','layers':layers,'series':series,'metrics':{'candidate_area_ha':area,'valid_land_ha':valid_area,'candidate_fraction':area/valid_area,'viewing_groups':len(groups)},'notes':list(dict.fromkeys(notes+sum([o['warnings'] for o in seq],[]))),'extra':extra,'sources':source_records,'status':'exploratory','algorithm_version':METHOD_VERSION,'report':{'headline':'What these observations show','findings':findings,'comparison_basis':extra['support']['mode'],'next_checks':['Inspect viewing-group coverage and the declared baseline dates.','Compare candidate patches with independent fire imagery and boundaries.','Check water exclusions, terrain effects and sensitivity to the selected land window.'],'validation':'Paper-inspired change detection; case-study agreement does not establish accuracy in other regions.'}}
