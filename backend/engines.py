"""Shared, bounded product calculations. These are measurements, not causal classifiers."""
from .execution import cancellable,checkpoint
from .processing_trace import snapshot
from datetime import datetime,timezone
import numpy as np

PRODUCT_FOR = {'P01':'GCOV','P02':'GCOV','P03':'GCOV','P04':'GUNW','P05':'GUNW','P06':'GCOV','P07':'GOFF'}
MINIMUM = dict(zip(PRODUCT_FOR, [2,3,3,1,1,2,1]))
READER_VERSION = '0.3.3'
ALGORITHM_VERSION = '0.4.0'

def instant(value):
    from datetime import timezone
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

def days_between(start,end):return (instant(end)-instant(start)).total_seconds()/86400

def summary(array):
    v=np.asarray(array);v=v[np.isfinite(v)]
    return {'valid_pixels':int(v.size),'valid_fraction':float(v.size/array.size) if array.size else 0.,
            **{name:float(np.percentile(v,p)) if len(v) else None for name,p in [('median',50),('p10',10),('p90',90)]}}

def support(values):
    finite=np.isfinite(values);common=finite.all(axis=0)
    return common,finite.sum(axis=0)

def water_evidence(db,common,threshold,area):
    water=(db<threshold)&np.isfinite(db)
    rows=[]
    # A sensitivity bracket, NOT an uncertainty interval or accuracy estimate.
    for t in [threshold-2,threshold-1,threshold,threshold+1,threshold+2]:
        rows.append({'threshold_db':float(t),'area_km2':[float(((x<t)&common).sum()*area) for x in db]})
    gain=(~water[0])&water[-1]&common;loss=water[0]&(~water[-1])&common
    return water,rows,{'water_gain_km2':float(gain.sum()*area),'water_loss_km2':float(loss.sum()*area),
                       'net_water_change_km2':float((gain.sum()-loss.sum())*area)}

@cancellable
def phase_engine(arr,seq,reference,comparison=None):
    common,_=support(arr);fixed=reference&common
    study=common if comparison is None else common&np.asarray(comparison,dtype=bool)
    if not study.any():raise ValueError('No common valid phase pixels remain inside the study domain. Reference coverage outside it is not study coverage. Revise the domain or select overlapping pairs.')
    if not fixed.any():raise ValueError('Reference needs the same coherent pixels valid on every selected pair. Redraw it, or select fewer overlapping pairs.')
    if not (study&~reference).any():raise ValueError('No common comparison pixels remain inside the study domain outside the reference. Draw a smaller reference or revise the study domain.')
    values=[];rates=[];diagnostics=[]
    for a,o in zip(arr,seq):
        checkpoint()
        wavelength=o.get('wavelength')
        if wavelength is None or not np.isfinite(wavelength) or wavelength<=0:raise ValueError('Center-frequency metadata is missing; wavelength will not be guessed.')
        days=days_between(o['item']['start'],o['item']['end'])
        if days<=0:raise ValueError('Phase pair interval must be positive.')
        phase_reference=float(np.median(a[fixed]));v=-wavelength*(a-phase_reference)/(4*np.pi)*1000
        v[~common]=np.nan;values.append(v);rates.append(v/days)
        q=np.percentile(a[fixed],[10,50,90])
        diagnostics.append({'source':o['item']['id'],'reference_pixels':int(fixed.sum()),'reference_phase_rad':phase_reference,
                            'reference_phase_p10_rad':float(q[0]),'reference_phase_p90_rad':float(q[2]),'interval_days':days})
    return np.stack(values),np.stack(rates),fixed,diagnostics

@cancellable
def pair_network(seq,values):
    normalized=[(instant(o['item']['start']).astimezone(timezone.utc).isoformat(),instant(o['item']['end']).astimezone(timezone.utc).isoformat()) for o in seq]
    epochs=sorted({e for endpoints in normalized for e in endpoints});index={e:i for i,e in enumerate(epochs)}
    matrix=np.zeros((len(seq),len(epochs)));edge={}
    for i,(start,end) in enumerate(normalized):
        a,b=index[start],index[end];matrix[i,a]=-1;matrix[i,b]=1;edge[a,b]=i
    rank=int(np.linalg.matrix_rank(matrix));triangles=[]
    for a,b in edge:
        for c in range(b+1,len(epochs)):
            if (b,c) in edge and (a,c) in edge:
                closure=values[edge[a,b]]+values[edge[b,c]]-values[edge[a,c]];v=closure[np.isfinite(closure)]
                triangles.append({'epochs':[epochs[a],epochs[b],epochs[c]],'common_pixels':int(v.size),
                                  'median_closure_mm':float(np.median(v)) if v.size else None,
                                  'rms_closure_mm':float(np.sqrt(np.mean(v.astype('float64')**2))) if v.size else None})
    return {'epochs':len(epochs),'pairs':len(seq),'connected_components':len(epochs)-rank,
            'cycle_rank':len(seq)-rank,'triangle_closures':triangles,'inversion_performed':False,
            'interpretation':'Closure is an internal consistency check, not proof of displacement accuracy. Pair endpoints must match exactly; no interpolation or time-series inversion is performed.'}

@cancellable
def offset_engine(arr,seq,options,trace_component=None,domain=None):
    result=arr.copy();diagnostics=[]
    for i,o in enumerate(seq):
        checkpoint()
        days=days_between(o['item']['start'],o['item']['end'])
        if days<=0:raise ValueError('Offset pair interval must be positive.')
        population=np.isfinite(arr[i])&(domain if domain is not None else True)
        v=arr[i][population]
        if not len(v):raise ValueError('Offset interval has no valid samples.')
        med=float(np.median(v));mad=float(np.median(np.abs(v-med)))
        cutoff=max(float(options.get('offset_mad_multiplier',8))*1.4826*mad,float(options.get('offset_min_cutoff_m',1)))
        reject=population&(np.abs(arr[i]-med)>cutoff)
        if options.get('offset_filter',True):result[i,reject]=np.nan
        diagnostics.append({'source':o['item']['id'],'interval_days':days,'native_screened_grid_pixels':len(v),
                            'spatial_median_offset_m':med,'mad_m':mad,'cutoff_m':cutoff,
                            'candidate_outlier_pixels':int(reject.sum()),'removed_pixels':int(reject.sum()) if options.get('offset_filter',True) else 0,**({'population_scope':'study domain; auxiliary stable samples retain native-quality screening'} if domain is not None else {})})
        component=trace_component or 'selected_component'
        snapshot('offset_screen',component,result[i],component.replace('Offset',' offset')+' after spatial screening, before time normalization','m','diverging',group=o['item']['group'],start=o['item']['start'],end=o['item']['end'])
        result[i]/=days
    return result,diagnostics

