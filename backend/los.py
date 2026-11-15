"""P04 connected-pair LOS trends, with explicit identifiability and quality limits."""
from .execution import cancellable,checkpoint
import re
import numpy as np
from .advanced import network_solution
from .engines import days_between


def phase_group(group, allow_revisions=False):
    # Keep track/pass/frame/mode/polarization AND release family. Never join X and P.
    return re.sub(r'_([A-Z])\d{5}$', r'_\1', group) if allow_revisions else group


@cancellable
def los_trend(seq, changes_mm):
    if len(seq)<2:
        return None, {'status':'pair only','reason':'One pair measures one interval. For a trend select at least two connected pairs linking three acquisition dates; four or more dates over several weeks are preferable.'}
    solution, meta=network_solution(seq,changes_mm,require_cycles=False)
    if solution is None:return None,meta
    epochs=meta['epochs']
    if len(epochs)<3:return None,{**meta,'status':'pair only','reason':'At least three distinct acquisition dates are needed for a multi-date trend.'}
    cube=solution['cube'];common=np.isfinite(cube).all(axis=0)
    t=np.array([days_between(epochs[0],d)/365.25 for d in epochs])
    values=cube[:,common].astype('float64');design=np.column_stack([np.ones(len(t)),t])
    fit=np.linalg.lstsq(design,values,rcond=None)[0]
    rms=np.full(common.shape,np.nan,'float32');rms[common]=np.sqrt(np.mean((values-design@fit)**2,axis=0))/10
    rate=np.full(common.shape,np.nan,'float32');rate[common]=fit[1]/10
    meta.update(status='fitted relative LOS trend',span_days=float(t[-1]*365.25),epoch_count=len(epochs),pair_count=len(seq),
                redundancy=meta['redundancy'],closure_check_available=meta['redundancy']>0,
                method='Connected chronological pair incidence least squares; first acquisition fixed to zero; intercept + linear trend at acquired epochs, 365.25 days/year.',
                interpretation='Positive is toward the satellite, negative away. Relative to the chosen reference, not vertical subsidence. Annualized short-window trends do not measure a full year. Fit residual is internal consistency, not accuracy or a confidence interval.')
    return {'cube_cm':cube/10,'rate_year':rate,'rate_month':rate/12,'change_cm':cube[-1]/10,
            'fit_rms_cm':rms,'pair_residual_cm':solution['rms']/10},meta
