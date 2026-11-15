"""Auditable baseline, sensitivity and graph models with explicit identifiability gates."""
from .execution import cancellable,checkpoint
from datetime import timezone
import numpy as np
from scipy import ndimage
from .engines import instant,days_between


@cancellable
def robust_baseline(db,dates,options):
    stop=options.get('baseline_end');count=int(options.get('baseline_count',1))
    if len(dates)!=len(db):raise ValueError('Baseline dates and observations must have identical lengths.')
    if not stop and (count<1 or len(db)<=count):raise ValueError(f'Baseline needs {count} baseline observations plus at least one later observation; {len(db)} available.')
    indices=[i for i,d in enumerate(dates) if d[:10]<=str(stop)] if stop else list(range(count))
    if not indices or len(indices)==len(db):raise ValueError('Baseline must include at least one observation and leave a later comparison observation.')
    finite=np.isfinite(db[indices]);common=finite.all(axis=0);baseline=np.full(db.shape[1:],np.nan,'float32');mad=baseline.copy()
    baseline[common]=np.median(db[indices][:,common],axis=0)
    mad[common]=1.4826*np.median(np.abs(db[indices][:,common]-baseline[common]),axis=0)
    floor=float(options.get('baseline_noise_floor_db',1))
    return baseline,np.maximum(mad,floor),indices


@cancellable
def local_offset_filter(values,options,domain=None):
    """Local neighbor residuals; off by default because fast localized flow can be lost."""
    if not options.get('offset_local_filter',False):return values.copy(),np.zeros(values.shape,bool)
    if domain is not None and not np.asarray(domain).all():
        filtered,rejected=local_offset_filter(np.where(domain,values,np.nan),options)
        # Auxiliary samples stay native-quality screened for the stable-ground
        # median; they do not enter moving-domain spatial filter statistics.
        filtered[~domain]=values[~domain]
        return filtered,rejected
    def median(v):
        v=v[np.isfinite(v)];return np.median(v) if len(v) else np.nan
    local=ndimage.generic_filter(values,median,size=3,mode='constant',cval=np.nan)
    residual=values-local;spread=ndimage.generic_filter(np.abs(residual),median,size=3,mode='constant',cval=np.nan)
    cutoff=np.maximum(float(options.get('offset_min_cutoff_m',1)),float(options.get('offset_mad_multiplier',8))*1.4826*spread)
    rejected=np.isfinite(values)&np.isfinite(cutoff)&(np.abs(residual)>cutoff)
    filtered=values.copy();filtered[rejected]=np.nan
    return filtered,rejected


@cancellable
def network_solution(seq,values,require_cycles=True):
    endpoints=[(instant(o['item']['start']).astimezone(timezone.utc).isoformat(),instant(o['item']['end']).astimezone(timezone.utc).isoformat()) for o in seq]
    epochs=sorted({x for pair in endpoints for x in pair});idx={d:i for i,d in enumerate(epochs)}
    matrix=np.zeros((len(seq),len(epochs)-1))
    for i,(a,b) in enumerate(endpoints):
        if idx[a]:matrix[i,idx[a]-1]=-1
        if idx[b]:matrix[i,idx[b]-1]=1
    rank=int(np.linalg.matrix_rank(matrix));redundancy=len(seq)-rank
    metadata={'epochs':epochs,'rank':rank,'redundancy':redundancy,'reference_epoch':epochs[0],'status':'not fitted','method':'ordinary least squares on pair incidence matrix; first epoch fixed to zero'}
    if rank<len(epochs)-1:return None,{**metadata,'reason':'Pair graph is disconnected; no common reference epoch exists.'}
    if require_cycles and redundancy<1:return None,{**metadata,'reason':'No redundant pair cycle. Add overlapping pair intervals to check a network solution.'}
    common=np.isfinite(values).all(axis=0)
    if not common.any():return None,{**metadata,'reason':'No common finite network support.'}
    measured=values[:,common].astype('float64');solution=np.linalg.lstsq(matrix,measured,rcond=None)[0]
    model=np.vstack((np.zeros((1,solution.shape[1])),solution));fitted=matrix@solution;residual=measured-fitted
    cube=np.full((len(epochs),*values.shape[1:]),np.nan,'float32');cube[:,common]=model
    rms=np.full(values.shape[1:],np.nan,'float32');rms[common]=np.sqrt(np.mean(residual**2,axis=0))
    t=np.array([days_between(epochs[0],d)/365.25 for d in epochs]);fit=np.linalg.lstsq(np.column_stack([np.ones(len(t)),t]),model,rcond=None)[0]
    rate=np.full(rms.shape,np.nan,'float32');rate[common]=fit[1]
    metadata.update(closure_check_available=redundancy>0,closure_interpretation='Redundant cycles permit internal consistency checks, not independent accuracy validation.' if redundancy>0 else 'Connected tree: zero pair residual is expected by construction; no independent closure check exists.',status='fitted phase-equivalent network',common_pixels=int(common.sum()),residual_rms_mm=float(np.sqrt(np.mean(residual**2))),interpretation='A reconstruction of referenced phase-equivalent changes, not independently validated ground displacement. Atmospheric, reference and unwrapping errors can enter the fitted series.')
    return {'cube':cube,'rms':rms,'rate':rate},metadata


def seasonal_solution(cube,epochs):
    t=np.array([days_between(epochs[0],d)/365.25 for d in epochs]);span=float(t[-1])
    metadata={'status':'not fitted','span_years':span,'epochs':len(epochs),'model':'intercept + linear term + annual sine + annual cosine'}
    if len(epochs)<6 or span<1:return None,{**metadata,'reason':'At least six epochs spanning a full year are required by this model gate; shorter records remain interval observations.'}
    design=np.column_stack([np.ones(len(t)),t,np.sin(2*np.pi*t),np.cos(2*np.pi*t)])
    if np.linalg.matrix_rank(design)<4 or np.linalg.cond(design)>1e6:return None,{**metadata,'reason':'Seasonal design is rank deficient or ill-conditioned.'}
    common=np.isfinite(cube).all(axis=0);v=cube[:,common]
    fit=np.linalg.lstsq(design,v,rcond=None)[0];amplitude=np.full(cube.shape[1:],np.nan,'float32');amplitude[common]=np.hypot(fit[2],fit[3])
    rms=np.full(amplitude.shape,np.nan,'float32');rms[common]=np.sqrt(np.mean((design@fit-v)**2,axis=0))
    return {'amplitude':amplitude,'rms':rms},{**metadata,'status':'fitted annual phase-equivalent model','interpretation':'Annual amplitude describes this fitted phase series, not thaw depth or a validated permafrost process.'}


def coarsened_water_sensitivity(power,common,threshold,area_km2):
    rows=[]
    for factor in [1,2,4]:
        h,w=common.shape;hh=(h//factor)*factor;ww=(w//factor)*factor
        if hh==0 or ww==0:continue
        masks=common[:hh,:ww].reshape(hh//factor,factor,ww//factor,factor).all(axis=(1,3))
        a=power[:,:hh,:ww].reshape(len(power),hh//factor,factor,ww//factor,factor).mean(axis=(2,4))
        water=10*np.log10(np.maximum(a,1e-30))<threshold
        rows.append({'factor':factor,'common_area_km2':float(masks.sum()*factor**2*area_km2),'area_km2':[float(w[masks].sum()*factor**2*area_km2) for w in water]})
    return rows
