"""Shared reference suitability. Data-only candidates never certify stable terrain."""
from .execution import cancellable,checkpoint
import hashlib,json
import numpy as np
from pyproj import Transformer
from .spatial import context_masks,union_role
from .los import los_trend

REFERENCE_PRODUCTS={'P03':'GCOV','P04':'GUNW','P05':'GUNW'}
SCIENCE_OPTIONS={'resolution':100,'coherence':.4,'min_valid_fraction':.5,'apply_ionosphere':False,'channel':'auto','phase_allow_mixed_revisions':False,'quake_mosaic':False,'event_timestamp':None,'event_date':None,'baseline_count':1,'baseline_end':None}


def reference_fingerprint(items,bbox,options,project='P04'):
    context=options.get('spatial_context') or {}
    from .engines import READER_VERSION
    key={'project':project,'assistant':'2.1','reader':READER_VERSION,'bbox':bbox,'sources':sorted((i['id'],i['name']) for i in items),
         'options':{k:options.get(k,v) for k,v in SCIENCE_OPTIONS.items()},
         'context':[f for f in context.get('features',[]) if (f.get('properties') or {}).get('role','zone') in ['domain','affected']]}
    return hashlib.sha256(json.dumps(key,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def rectangle_mask(bbox,grid):
    h,w=grid['shape'];t=grid['transform'];xs=t.c+(np.arange(w)+.5)*t.a;ys=t.f+(np.arange(h)+.5)*t.e
    west,south,east,north=bbox
    x0,y0=Transformer.from_crs(4326,grid['crs'],always_xy=True).transform(west,south)
    x1,y1=Transformer.from_crs(4326,grid['crs'],always_xy=True).transform(east,north)
    return (ys[:,None]>=y0)&(ys[:,None]<=y1)&(xs[None,:]>=x0)&(xs[None,:]<=x1)


@cancellable
def reference_assistant(seq,grid,options,project='P04'):
    if project not in REFERENCE_PRODUCTS:raise ValueError('This tool does not use a reference area.')
    brightness=project=='P03'
    seq=sorted(seq,key=lambda o:(o['item']['group'],o['item']['start'],o['item']['end']))
    if not seq:raise ValueError('Select compatible observations first.')
    if any(o['item']['product']!=REFERENCE_PRODUCTS[project] for o in seq):raise ValueError('Select the product used by this tool.')
    if project=='P05':
        from .quake import brackets_event,validate_mosaic_groups
        if not options.get('event_timestamp') and not options.get('event_date'):raise ValueError('Enter the documented event time before checking earthquake references.')
        groups={o['item']['group'] for o in seq}
        if len(groups)>1:
            if not options.get('quake_mosaic'):raise ValueError('Select one compatible acquisition group or explicitly enable event coverage.')
            validate_mosaic_groups([o['item'] for o in seq])
        for group in groups:
            if not any(brackets_event(o['item'],options) for o in seq if o['item']['group']==group):raise ValueError(f'{group}: no selected pair brackets the event; check the event time and selected files.')
    if len({(o['item']['group'],o['item']['start'],o['item']['end']) for o in seq})!=len(seq):raise ValueError('Choose one version per pair; duplicate intervals cannot be assessed.')
    if len({o['path'].split('/frequencyA/')[-1] for o in seq})>1:raise ValueError('Selected science channels differ. Choose one compatible science channel.')
    from .resource_budget import require_resources
    require_resources([o['item'] for o in seq],grid)
    arr=np.stack([o['array'] for o in seq]);h,w=grid['shape']
    if brightness:arr=10*np.log10(np.where(arr>0,arr,np.nan))
    common=np.isfinite(arr).all(axis=0)
    if brightness:
        from .advanced import robust_baseline
        baseline,_,_=robust_baseline(arr,[o['item']['start'] for o in seq],options)
        departures=arr-baseline
    contexts=context_masks(options.get('spatial_context'),grid)
    domain=union_role(contexts,'domain',grid['shape'])&rectangle_mask(grid['bbox'],grid);affected=union_role(contexts,'affected',grid['shape'],np.zeros((h,w),bool))
    # No land-cover, elevation or stable-ground inference is made from coherence.
    eligible=domain&~affected;common&=rectangle_mask(grid['bbox'],grid)
    comparison_support=common&domain
    if project=='P05' and options.get('quake_mosaic'):
        comparison_support=domain&np.logical_or.reduce([np.isfinite(np.stack([o['array'] for o in seq if o['item']['group']==group])).all(axis=0) for group in {o['item']['group'] for o in seq}])
    has_coherence=all('coherence' in o.get('aux',{}) for o in seq)
    coherence=np.stack([o['aux']['coherence'] for o in seq]) if has_coherence else None
    if not brightness and any(o.get('wavelength') is None or not np.isfinite(o['wavelength']) or o['wavelength']<=0 for o in seq):raise ValueError('Source wavelength is required to compare reference choices.')
    wavelengths=np.array([o.get('wavelength',0) for o in seq])
    def assess(mask):
        total=int(mask.sum());support=mask&common;n=int(support.sum());fraction=n/total if total else 0
        medians=[float(np.median(a[support])) for a in arr] if n else []
        q=[float(np.median(a[support])) if np.isfinite(a[support]).all() else None for a in coherence] if n and has_coherence else []
        worst=min(q) if q and all(v is not None for v in q) else None
        spread=max(float(np.median(abs(a[support]-m))) for a,m in zip(arr,medians)) if n else None
        warnings=[]
        if 25<=n<100:warnings.append('Fewer than 100 shared analysis cells: this is a small reference sample; inspect larger alternatives when available.')
        if n<25:warnings.append('Fewer than 25 shared analysis cells; choose a larger or better-covered patch.')
        if fraction<.8:warnings.append('Less than 80% of this patch is usable on every selected pair.')
        if worst is None and not brightness:warnings.append('Comparable coherence evidence is unavailable.')
        elif worst is not None and worst<.7:warnings.append('Worst-pair median accepted-sample coherence is below 0.70; inspect the quality maps.')
        if (mask&affected).any():warnings.append('This patch intersects your supplied affected area; avoid it unless independently justified.')
        if not (mask&common).any():warnings.append('No shared finite reference cells: this reference cannot be used.')
        if n and not (comparison_support&~mask).any():warnings.append('No comparison ground remains outside this reference.')
        return {'patch_cells':total,'shared_cells':n,'shared_fraction':fraction,'worst_pair_median_coherence':worst,
                'maximum_pair_spatial_mad_rad':None if brightness else spread,'spatial_spread':spread,'spread_unit':'dB' if brightness else 'rad','pair_reference_phase_rad':medians if not brightness else [],
                'reference_values':([float(np.median(a[support])) for a in departures] if n else []) if brightness else medians,
                'data_suitability':'strong shared data' if not warnings else 'review needed',
                'stability':'not independently established','warnings':warnings}
    candidates=[]
    base_size=max(12,min(48,int(min(h,w)*.06)))
    sizes=sorted({min(base_size,h,w),min(max(6,base_size//2),h,w),min(6,h,w)},reverse=True)
    def window_counts(values,size):
        integral=np.pad(np.cumsum(np.cumsum(values.astype('float64'),axis=0),axis=1),((1,0),(1,0)))
        return integral[size:,size:]-integral[:-size,size:]-integral[size:,:-size]+integral[:-size,:-size]
    if (has_coherence or brightness) and common.any():
        for size in sizes:
            checkpoint()
            if size<5:continue
            counts=window_counts(common&eligible,size)
            available=(counts>=max(25,.8*size*size))&(window_counts(eligible,size)==size*size)
            coverage=counts/(size*size)
            quality=np.ones(counts.shape,dtype='float64')
            if not brightness:
                for plane in coherence:
                    means=window_counts(np.where(common&eligible&np.isfinite(plane),plane,0),size)/np.maximum(counts,1)
                    quality=np.minimum(quality,means)
            scores=np.where(available,quality+coverage*.0001,-np.inf)
            positions=[]
            # Sample the full study grid. Equal-coverage ties previously exhausted
            # the budget at the northern edge before visiting the rest of the area.
            for rows in np.array_split(np.arange(scores.shape[0]),9):
                for cols in np.array_split(np.arange(scores.shape[1]),8):
                    if not rows.size or not cols.size:continue
                    block=scores[np.ix_(rows,cols)];best=np.max(block)
                    if not np.isfinite(best):continue
                    rr,cc=np.where(block==best)
                    distance=(rr-(len(rows)-1)/2)**2+(cc-(len(cols)-1)/2)**2
                    k=np.argmin(distance);positions.append((int(rows[rr[k]]),int(cols[cc[k]])))
            remaining=scores.copy()
            for row,col in positions:
                checkpoint()
                radius=max(1,size//2);remaining[max(0,row-radius):row+radius+1,max(0,col-radius):col+radius+1]=-np.inf
            for _ in range(3):
                row,col=np.unravel_index(np.argmax(remaining),remaining.shape)
                if not np.isfinite(remaining[row,col]):break
                positions.append((int(row),int(col)));radius=max(1,size//2)
                remaining[max(0,row-radius):row+radius+1,max(0,col-radius):col+radius+1]=-np.inf
            for row,col in positions:
                checkpoint()
                t=grid['transform'];left=t.c+col*t.a;right=left+size*t.a;top=t.f+row*t.e;bottom=top+size*t.e
                convert=Transformer.from_crs(grid['crs'],4326,always_xy=True)
                west,south=convert.transform(left,bottom);east,north=convert.transform(right,top)
                bounds=grid['bbox'];bbox=[max(west,bounds[0]),max(south,bounds[1]),min(east,bounds[2]),min(north,bounds[3])]
                actual=rectangle_mask(bbox,grid)
                if not actual.any() or not eligible[actual].all() or not (comparison_support&~actual).any():continue
                q=assess(actual)
                if q['shared_cells']<25 or q['shared_fraction']<.8:continue
                if not brightness and q['worst_pair_median_coherence'] is None:continue
                candidates.append({**q,'bbox':bbox,'_row':int(row),'_col':int(col),'_size':size})
    candidates.sort(key=lambda c:(0 if brightness else -int(c['worst_pair_median_coherence']>=.7),-int(c['shared_cells']>=100),0 if brightness else -c['worst_pair_median_coherence'],-c['shared_fraction'],-c['shared_cells'],c['spatial_spread']))
    chosen=[]
    for c in candidates:
        if all(abs((c['_row']+c['_size']/2)-(p['_row']+p['_size']/2))>=.75*(c['_size']+p['_size']) or abs((c['_col']+c['_size']/2)-(p['_col']+p['_size']/2))>=.75*(c['_size']+p['_size']) for p in chosen):chosen.append(c)
        if len(chosen)==3:break
    for i,c in enumerate(chosen):
        c.update(id=f'candidate_{i+1}',name=f'Candidate {i+1}',area_km2=c['patch_cells']*abs(grid['transform'].a*grid['transform'].e)/1e6)
        c.pop('_row');c.pop('_col');c.pop('_size')
    def relative_rate(values,baseline):
        if not values or not baseline:return None
        mm=-wavelengths*(np.array(values)-baseline)/(4*np.pi)*1000
        fit,_=los_trend(seq,mm[:,None,None])
        return float(fit['rate_year'][0,0]) if fit is not None else None
    baseline=chosen[0]['pair_reference_phase_rad'] if chosen else []
    for c in chosen:c['relative_rate_to_candidate_1_cm_year']=relative_rate(c['pair_reference_phase_rad'],baseline) if project=='P04' else None
    current=None
    if any(f['role']=='reference' for f in contexts):
        current=assess(union_role(contexts,'reference',grid['shape']));current['origin']='supplied reference polygons'
    elif options.get('reference_bbox'):
        current=assess(rectangle_mask(options['reference_bbox'],grid));current['origin']='current reference rectangle'
    if current:current['relative_rate_to_candidate_1_cm_year']=relative_rate(current['pair_reference_phase_rad'],baseline) if project=='P04' else None
    network={}
    if project=='P04':_,network=los_trend(seq,np.zeros((len(seq),1,1),dtype='float32'))
    # Per-observation offsets exactly match the spatial origin used by each processor.
    base=chosen[0]['reference_values'] if chosen else []
    for c in chosen+([current] if current else []):
        values=c['reference_values']
        if not base or not values:c['relative_reference_offsets']=[];continue
        offsets=np.array(values)-base
        if not brightness:offsets=-wavelengths*offsets/(4*np.pi)*100
        c['relative_reference_offsets']=offsets.tolist()
    comparison_unit='dB' if brightness else 'cm'
    spans=[max(c['relative_reference_offsets'][i] for c in chosen)-min(c['relative_reference_offsets'][i] for c in chosen) for i in range(len(seq))] if chosen else []
    shifts=[c['relative_rate_to_candidate_1_cm_year'] for c in chosen if c['relative_rate_to_candidate_1_cm_year'] is not None]
    return {'assistant_version':'2.1','project':project,'product':REFERENCE_PRODUCTS[project],'comparison_unit':comparison_unit,'maximum_candidate_offset_span':max(spans) if spans else None,'comparison_meaning':'Offsets relative to Candidate 1 for each selected observation, in source order. Switching reference subtracts these offsets from the corresponding map. They describe sensitivity of the spatial origin, not accuracy. For GCOV these are departures from the declared per-cell median baseline; phase tools use converted LOS pair changes.','status':'candidates available' if chosen else 'no suitable candidate found',
            'fingerprint':reference_fingerprint([o['item'] for o in seq],grid['bbox'],options,project),
            'candidates':chosen,'current_reference':current,'sources':[{'id':o['item']['id'],'name':o['item']['name'],'start':o['item']['start'],'end':o['item']['end'],'group':o['item']['group'],'bytes_transferred':o['bytes_transferred'],'quality_paths':o['quality_paths'],'correction_manifest':o.get('attrs',{}).get('correction_manifest',[])} for o in seq],
            'grid':{'bbox':grid['bbox'],'resolution_m':grid['resolution'],'shape':list(grid['shape']),'crs':grid['crs']},
            'network':network,'rate_comparison_status':'Annualized reference-choice comparison available; not absolute stability.' if shifts else network.get('reason','No candidate comparison is available.'),'common_cells':int((common&domain).sum()),'pair_count':len(seq),'relative_candidate_rate_span_cm_year':max(shifts)-min(shifts) if shifts else None,
            'selection_method':'Up to 225 bounded windows at up to three sizes (minimum 6 × 6 cells), sampled across a 9 × 8 spatial stratification plus up to three global quality seeds per size; at least 25 shared cells and 80% shared coverage; exclude supplied affected areas; retain up to three separated patches. '+('GCOV: prefer at least 100 shared cells when available, then rank by shared coverage and spatial dB uniformity, without coherence or unaffected-ground inference.' if brightness else 'Phase: prefer coherence at least 0.70, then at least 100 shared cells, then worst-pair median accepted-sample coherence, coverage, cell count and spatial phase MAD. These are data-suitability preferences, never ground-stability tests.'),
            'threshold_meaning':('GCOV screening uses 25 shared cells and 80% support; these are engineering rules, not calibrated reliability thresholds.' if brightness else 'Candidate patches require at least 25 shared cells and 80% shared coverage. Coherence of 0.70 is preferred for ranking; lower-coherence candidates can appear with review warnings. These are engineering rules, not calibrated reliability thresholds. Coherence is aggregated over already accepted native samples.'),
            'stability':('Unaffected status is not independently established. Spatially uniform brightness can still change; no fire perimeter, land-cover or independent validation is inferred.' if brightness else 'Not independently established. A coherent, uniform patch may be moving. No land-cover or elevation classification, stable-ground map, GNSS, atmospheric or DEM-error validation is available.'),
            'relative_rate_meaning':'Candidate rates are relative to Candidate 1, which is zero by definition. They describe sensitivity of the spatial origin, not proof that any candidate is stationary. Switching from Candidate 1 to a candidate subtracts that candidate’s relative rate from the map. None is a probability or measurement uncertainty.',
            'next_step':'Inspect candidate locations on the basemap and choose ground outside suspected change, preferably nearby and at similar elevation when known. You may draw your own reference. If no candidate passes, review coverage or choose another area/date set; thresholds are not silently relaxed.',
            'warnings':(['No independent unaffected-area evidence was supplied.'] if brightness else ['No independent stable-ground evidence was supplied.','A connected chain has no redundant closure check; zero residual cannot establish unwrapping accuracy.'])+(['Processing revisions differ; artifacts may mimic motion.'] if len({o['item']['group'].split('_')[-1] for o in seq})>1 else [])}
