"""Dated scattering evidence, explicitly allowing late-onset and transient change."""
from .execution import cancellable,checkpoint
from .processing_trace import snapshot,enabled
import math
import numpy as np
from .raster_methods import smooth,candidate_mask
from .spatial import optional_patch_history as patch_history

@cancellable
def evolving_surface(db,baseline,baseline_indices,common,dates,grid,opt):
 post=[i for i in range(len(db)) if i>max(baseline_indices)]
 if not post:raise ValueError('Keep at least one later observation after the declared baseline.')
 threshold=float(opt.get('change_threshold',3));sigma_m=float(opt.get('smoothing_m',40));sigma=sigma_m/grid['resolution'];cell=abs(grid['transform'].a*grid['transform'].e);minimum=max(1,math.ceil(float(opt.get('patch_area_m2',30000))/cell))
 departures=np.stack([smooth(np.where(common,a-baseline,np.nan),sigma) for a in db]);states=np.zeros(db.shape,dtype='int8')
 for i in post:
  checkpoint()
  states[i]=candidate_mask(departures[i],threshold,minimum).astype('int8')-candidate_mask(-departures[i],threshold,minimum).astype('int8')
 if enabled('signed_change'):
  raw=(departures[-1]>=threshold).astype('int8')-(-departures[-1]>=threshold).astype('int8')
  snapshot('signed_change','signed_before_patches',np.where(common,raw,np.nan),'Latest signed threshold before patch filtering','class','diverging',start=dates[-1],end=dates[-1],classes={'-1':'Dimming candidate','0':'Threshold not met','1':'Brightening candidate'},interpretation='Signed threshold only, before removing small patches: −1 dimming, 0 threshold not met, +1 brightening. None identifies lava or a physical cause.')
 latest=states[-1];consecutive=np.zeros(grid['shape'],dtype='int16');active=(latest!=0)&common
 # Count only a trailing run of the same sign, not every earlier date.
 still=active.copy()
 for i in reversed(post):still&=(states[i]==latest);consecutive[still]+=1
 repeated=(consecutive>=2)&active
 first=np.full(grid['shape'],np.nan,'float32')
 for i in post:
  checkpoint()
  pick=np.isnan(first)&(states[i]!=0)&common;first[pick]=i
 layers={}
 def layer(k,a,label,unit='class',kind='binary'):layers[k]={'data':np.asarray(a,dtype='float32'),'label':label,'unit':unit,'kind':kind}
 layer('latest_departure',departures[-1],'Latest smoothed change from the declared baseline','dB','diverging')
 layer('surface',np.where(common,active,np.nan),'Changed patches at the latest observation')
 layer('confirmed_change',np.where(common,repeated,np.nan),'Latest same-sign change observed on at least two consecutive later dates')
 layer('change_direction',np.where(common,latest,np.nan),'Latest qualifying brightness increase (+1) or decrease (−1)','class','diverging')
 layer('first_change',first,'First acquired date meeting the signed change and patch rules','observation index','continuous')
 layer('repeat_count',np.where(common,consecutive,np.nan),'Consecutive latest observations supporting the same change direction','count','continuous')
 for i in post:layer('dated_departure_'+str(i),departures[i],f'Smoothed baseline departure · {dates[i][:10]}','dB','diverging')
 steps=np.diff(db,axis=0);idx=np.argmax(np.abs(steps),axis=0)
 layer('largest_step',np.where(common,idx+1,np.nan),'Index of observation ending the largest unsmoothed brightness step','observation index','continuous')
 area=cell/1e6;updates=[]
 for i,date in enumerate(dates):
  updates.append({'change_candidate_km2':float(np.count_nonzero(states[i])*area),'brightening_candidate_km2':float(np.count_nonzero(states[i]>0)*area),'dimming_candidate_km2':float(np.count_nonzero(states[i]<0)*area)})
 metrics={'latest_change_area_km2':float(active.sum()*area),'repeated_latest_change_area_km2':float(repeated.sum()*area),'increasing_area_km2':float(np.count_nonzero(latest>0)*area),'decreasing_area_km2':float(np.count_nonzero(latest<0)*area),'common_valid_area_km2':float(common.sum()*area)}
 tracking=patch_history((states!=0)&common,dates,grid,float(opt.get('patch_area_m2',30000)))
 extra={'surface_method':{'id':'evolving','version':'0.7.1','smoothing_m':sigma_m,'change_threshold_db':threshold,'minimum_patch_area_m2':float(opt.get('patch_area_m2',30000)),'minimum_patch_cells':minimum,'post_baseline_dates':[dates[i] for i in post],'repeated_latest_available':len(post)>=2,'meaning':'Change since the declared observed baseline, with late-onset, transient and repeated evidence separated. Neither lava attribution nor uninterrupted persistence is established.'},'first_change_calendar':[{'index':i,'date':dates[i]} for i in post],'step_calendar':[{'index':i,'start':dates[i-1],'end':dates[i]} for i in range(1,len(dates))],'tracking':tracking}
 notes=['Latest changed patches can first appear on any later acquisition; absence on an earlier date no longer removes a late-growing patch.','Repeated latest change requires at least two consecutive post-baseline observations in the same direction. It is not proof of uninterrupted change between passes.','First-change indices identify sampled acquisition dates; onset lies in an unobserved interval, and may predate this record.','Smoothing uses a normalized Gaussian and preserves missing cells. Small signed patches are filtered in physical square metres.','Snowmelt, surface wetness, terrain effects and viewing geometry can change brightness. Candidate patches are not validated lava, temperature, volume or eruption probability.','A baseline acquired during an ongoing eruption measures later change only; existing lava with stable brightness may remain undetected.']
 return layers,metrics,extra,updates,notes
