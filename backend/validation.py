"""Independent label evaluation with explicit calibration/test separation."""
import numpy as np
from datetime import date,timezone

def utc_day(value):
    from .engines import instant
    return instant(str(value)).astimezone(timezone.utc).date().isoformat()

def water_calibration(db,dates,contexts,default,fixed_states=None):
    samples=[];occupied={}
    for f in contexts:
        if f['role'] not in ['water','dry']:continue
        p=f['properties'];key=p['date']
        matches=[i for i,d in enumerate(dates) if d[:10]==key]
        if not matches:raise ValueError(f'Validation date {key} does not match a selected acquisition.')
        for i in matches:
            mask=f['mask']&np.isfinite(db[i]);entry=occupied.setdefault(i,[])
            for previous,props in entry:
                if np.any(previous&mask) and (props['role']!=f['role'] or props.get('split')!=p['split']):raise ValueError('Overlapping validation polygons have conflicting classes or train/test assignments.')
            entry.append((mask,{**p,'role':f['role']}))
            # Repeated labels on the same date are de-duplicated below.
            samples.append((i,mask,f['role']=='water',p['split'],p['source']))
    def gather(split):
        data=[];truth=[];seen={}
        for i,mask,label,part,source in samples:
            if split!=part:continue
            selected=mask&~seen.setdefault(i,np.zeros(mask.shape,bool));seen[i]|=selected
            values=db[i] if fixed_states is None else np.where(fixed_states[i],0.,1.)
            data.extend(values[selected].tolist());truth.extend([label]*int(selected.sum()))
        return np.array(data),np.array(truth,dtype=bool)
    train,truth=gather('train');threshold=float(default)
    if len(train) and fixed_states is None:
        if len(np.unique(truth))<2:raise ValueError('Calibration needs independently labeled water AND dry training cells.')
        candidates=np.unique(np.r_[np.percentile(train,np.linspace(0,100,101)),float(default)])
        def score(t):
            prediction=train<t;tp=np.sum(prediction&truth);fp=np.sum(prediction&~truth);fn=np.sum(~prediction&truth)
            return 2*tp/max(2*tp+fp+fn,1)
        threshold=float(max(candidates,key=lambda t:(score(t),-abs(t-default))))
    test,target=gather('test')
    if samples and not len(train) and not len(test):raise ValueError('No supplied label cells survive the common quality-screened footprint; revise labels or the selected dates.')
    report={'threshold_db':threshold,'calibration_cells':len(train) if fixed_states is None else 0,'test_cells':len(test),'independent_sources':sorted({s[-1] for s in samples}),'status':'not evaluated: no independent test labels','sampling_note':'Metrics describe labeled analysis cells only. Correlated polygon cells are not independent samples; no global accuracy or area confidence interval is inferred.'}
    if fixed_states is not None:report.update(training_cells_not_used_for_fitting=len(train),calibration_method='Fixed declared HH/HV thresholds; training labels do not fit or change them.')
    if len(test):
        predicted=test<(.5 if fixed_states is not None else threshold);tp=int(np.sum(predicted&target));tn=int(np.sum(~predicted&~target));fp=int(np.sum(predicted&~target));fn=int(np.sum(~predicted&target))
        ratio=lambda a,b:float(a/b) if b else None
        report.update(status='evaluated against supplied held-out labels',true_positive=tp,true_negative=tn,false_positive=fp,false_negative=fn,precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),iou=ratio(tp,tp+fp+fn),specificity=ratio(tn,tn+fp),water_area_bias_cells=fp-fn)
    return threshold,report

def continuous_validation(series,observations,unit,value_key=None):
    if not observations:return {'status':'not evaluated: no independent matched observations'}
    pairs=[];matched=[];excluded=[]
    for reference in observations:
        matches=[row for row in series if utc_day(row['date'])==str(reference['date']) and (not reference.get('end') or row.get('end') and utc_day(row['end'])==str(reference['end']))]
        if len(matches)!=1:raise ValueError('Each independent reference must identify exactly one observed date/pair.')
        row=matches[0];key=value_key or ('median_rate_mm_day' if unit=='mm/day' else 'median_mm' if unit=='mm' else 'median');value=row.get(key)
        target=float(reference['value'])
        if not np.isfinite(target):raise ValueError('Regional reference values must be finite.')
        if value is not None and np.isfinite(value):
            pairs.append((float(value),target));matched.append({'date':row['date'],'end':row.get('end'),'observed':float(value),'reference':target,'unit':unit,'source':reference['source']})
        else:excluded.append({'date':reference['date'],'end':reference.get('end'),'source':reference['source'],'reason':'No finite regional summary on the matched interval.'})
    counts={'requested_samples':len(observations),'excluded_samples':len(excluded),'excluded_references':excluded,'matched_pairs':matched}
    if not pairs:return {'status':'not evaluated: no matching finite measurements',**counts}
    p=np.array(pairs)
    with np.errstate(over='ignore',invalid='ignore'):error=p[:,0]-p[:,1]
    if not np.isfinite(error).all():raise ValueError('Regional reference differences exceed the finite numeric range. Check values and units.')
    scale=float(np.max(np.abs(error)));scaled=error/scale if scale else error
    center=float(scaled.mean());bias=center*scale
    rmse=float(np.sqrt(np.mean(scaled**2)))*scale
    spread=float(np.sqrt(np.mean((scaled-center)**2)))*scale if len(pairs)>1 else None
    mae=float(np.mean(np.abs(scaled)))*scale
    if not np.isfinite([bias,rmse,mae]+([] if spread is None else [spread])).all():raise ValueError('Regional reference statistics exceed the finite numeric range. Check values and units.')
    return {'status':'evaluated against supplied regional references' if not excluded else 'partially evaluated: some matched intervals have no finite regional summary','samples':len(pairs),'unit':unit,'bias':bias,'rmse':rmse,'unbiased_rmse':spread,'mae':mae,'metric_notes':['Bias-removed RMSE needs at least two compared records; with one record it would be zero by construction.'] if len(pairs)==1 else [],'references':observations,**counts,'meaning':'Regional medians require matched units, geometry, interval, reference origin and spatial support. A point sensor or regional mean is not automatically representative of this median. User-supplied source citations do not independently verify accuracy.'}


QUANTITY_LABELS={'los_displacement':'Relative LOS displacement across a measured pair','radar_component_rate':'Signed radar-component interval-average rate','horizontal_speed':'Estimated horizontal speed with zero vertical velocity'}
_DISPLACEMENT={'mm':1.,'cm':10.,'m':1000.}
_RATE={'mm/day':.001,'cm/day':.01,'m/day':1.,'mm/year':.001/365.25,'cm/year':.01/365.25,'m/year':1/365.25}


def regional_reference_spec(observations,product,options):
    """Validate quantity/unit/interval semantics before any native science read.

    Older phase/radar-mode records may omit both quantity and unit. Their old
    interpretation is retained and disclosed; horizontal runs fail closed on
    that ambiguity instead of silently comparing speed with one component.
    """
    records=[r for r in observations if r.get('product') in [None,product]]
    if not records:return None
    if product not in ['GUNW','GOFF']:raise ValueError('Regional measurement checks currently support GUNW and GOFF only.')
    default='los_displacement' if product=='GUNW' else 'radar_component_rate'
    quantities={r.get('quantity') or default for r in records}
    if len(quantities)!=1:raise ValueError('Use one physical quantity per regional reference check. Compare LOS displacement, radar components and horizontal speed separately.')
    quantity=quantities.pop()
    if quantity not in (['los_displacement'] if product=='GUNW' else ['radar_component_rate','horizontal_speed']):raise ValueError('The reference quantity is not available for this product. GUNW checks measured-pair LOS displacement; GOFF checks a radar-component rate or horizontal speed.')
    if quantity=='horizontal_speed' and options.get('offset_solution')!='horizontal':raise ValueError('Horizontal-speed references require the horizontal solution with delivered viewing geometry. Enable it or supply radar-component references.')
    unit='mm' if product=='GUNW' else options.get('offset_rate_unit','m/day')
    if unit not in (['mm'] if product=='GUNW' else ['m/day','m/year']):raise ValueError('Unsupported processing unit for a regional comparison.')
    component=options.get('component','slantRangeOffset') if quantity=='radar_component_rate' else None
    normalized=[];assumptions=[];seen=set()
    for record in records:
        start=str(record['date']);end=str(record['end']) if record.get('end') else None
        try:
            if date.fromisoformat(start).isoformat()!=start or end and date.fromisoformat(end).isoformat()!=end:raise ValueError()
        except (ValueError,TypeError):raise ValueError('Use UTC ISO calendar dates YYYY-MM-DD for regional pair references.') from None
        explicit=record.get('quantity') is not None or record.get('unit') is not None
        if explicit and (not record.get('quantity') or not record.get('unit')):raise ValueError('Each regional reference needs both quantity and unit.')
        if not explicit and product=='GOFF' and options.get('offset_solution')=='horizontal':raise ValueError('Horizontal-mode references must state quantity and unit. Choose horizontal_speed, or radar_component_rate with its component; a signed radar component is not horizontal speed.')
        if explicit and not record.get('end'):raise ValueError('Regional pair references need both date and end to identify the exact acquisition interval.')
        if end and end<=start:raise ValueError('A regional pair reference must end after its start date.')
        supplied_component=record.get('component')
        if component:
            if explicit and supplied_component!=component:raise ValueError('Radar-component references must name the selected '+component+' component; range and along-track rates cannot be interchanged.')
            if supplied_component and supplied_component!=component:raise ValueError('The reference component differs from the selected radar component.')
        elif supplied_component:raise ValueError('A component field applies only to radar_component_rate references.')
        source=str(record.get('source','')).strip()
        if not source:raise ValueError('Regional references require a source citation.')
        original_unit=record.get('unit') or unit
        factors=_DISPLACEMENT if quantity=='los_displacement' else _RATE
        if original_unit not in factors:raise ValueError('Reference units must describe the same physical quantity: displacement units for LOS pairs; rate units for radar rates or horizontal speed. No rate-to-displacement conversion is guessed.')
        value=float(record['value'])
        if not np.isfinite(value):raise ValueError('Regional reference values must be finite.')
        if quantity=='horizontal_speed' and value<0:raise ValueError('Horizontal speed is a nonnegative magnitude, not a signed radar component.')
        converted=value if original_unit==unit else value*factors[original_unit]/factors[unit]
        if not np.isfinite(converted):raise ValueError('Reference unit conversion is outside the finite numeric range.')
        identity=(start,end,converted,source,component)
        if identity in seen:raise ValueError('Duplicate regional reference record. Remove the repeated interval/value/source so it is not counted twice.')
        seen.add(identity)
        normalized.append({**record,'date':start,'end':end,'value':converted,'source':source,'quantity':quantity,'unit':unit,'input_unit':original_unit,'input_value':value,**({'component':component} if component else {})})
        if not explicit:assumptions.append('Legacy reference: quantity '+quantity+', unit '+unit+((', component '+component) if component else '')+' were assumed. Supply explicit fields for a new comparison.')
        if not record.get('end'):assumptions.append('Legacy reference omitted end; exactly one matching pair is required and its actual interval is recorded below.')
    return {'quantity':quantity,'quantity_label':QUANTITY_LABELS[quantity],'unit':unit,'component':component,'references':normalized,'assumptions':list(dict.fromkeys(assumptions))}


def regional_validation(series,observations,product,options,horizontal_series=None,support=None):
    spec=regional_reference_spec(observations,product,options)
    if spec is None:return continuous_validation(series,[], 'mm' if product=='GUNW' else options.get('offset_rate_unit','m/day'))
    selected=horizontal_series if spec['quantity']=='horizontal_speed' else series
    if selected is None:raise ValueError('No horizontal-speed regional series is available for this reference check.')
    report=continuous_validation(selected,spec['references'],spec['unit'],value_key='median_mm' if product=='GUNW' else 'median')
    report.update(quantity=spec['quantity'],quantity_label=spec['quantity_label'],unit=spec['unit'],component=spec['component'],assumptions=spec['assumptions'],comparison_basis='Regional median on the fixed common usable footprint for the named quantity; each point is its actual pair interval.',support=support or {})
    return report
