"""P05 earthquake-interval measurements and explicitly traceable multi-view mosaics.
No east/up decomposition, synthetic filling, or silent overlap averaging is done.
"""
from datetime import datetime
import re
import numpy as np
from .engines import instant,summary

ARTICLE='https://science.nasa.gov/earth/earth-observatory/where-venezuelas-earthquakes-shifted-the-ground/'

def brackets_event(item,options):
    """Event must follow the entire reference pass and precede the secondary pass."""
    event=options.get('event_timestamp') or options.get('event_date')
    if not event:return False
    start,end=item['start'],item['end']
    stamps=re.findall(r'\d{8}T\d{6}',item.get('name',''))
    if len(stamps)==4:
        start=datetime.strptime(stamps[1],'%Y%m%dT%H%M%S').isoformat()+'Z'
        end=datetime.strptime(stamps[2],'%Y%m%dT%H%M%S').isoformat()+'Z'
    if options.get('event_timestamp'):return instant(start)<instant(event)<instant(end)
    return start[:10]<str(event)<end[:10]

def validate_mosaic_groups(items):
    """Adjacent tracks/frames allowed, but never opposite directions or releases."""
    configurations=[]
    for item in items:
        fields=item['group'].split('_')
        if len(fields)!=6 or fields[1] not in ['A','D']:
            raise ValueError('Event mosaic needs recognized NISAR track/pass/frame/mode/release groups. Use one acquisition group for this source.')
        configurations.append((fields[1],*fields[3:]))
    if len(set(configurations))>1:
        raise ValueError('Event mosaic needs the same ascending/descending direction, bandwidth, polarization mode and processing release. Opposite views or releases must be processed separately.')


def event_mosaic(seq,grid,options,processor):
    validate_mosaic_groups([o['item'] for o in seq])
    if len({o['path'].split('/frequencyA/')[-1] for o in seq})>1:
        raise ValueError('Event mosaic sources need the same science channel.')
    # Prefer the same physical reference cells across views; do not fit event pixels.
    from .processors import region_mask
    from .spatial import context_masks,union_role
    contexts=context_masks(options.get('spatial_context'),grid)
    fallback=region_mask(options['reference_bbox'],grid) if options.get('reference_bbox') else np.zeros(grid['shape'],bool)
    declared=union_role(contexts,'reference',grid['shape'],fallback)
    shared=declared&np.isfinite(np.stack([o['array'] for o in seq])).all(axis=0)
    reference_mode='shared physical cells' if int(shared.sum())>=25 else 'independent group references'
    internal={'_phase_reference_mask':shared} if reference_mode=='shared physical cells' else {}
    parts=[]
    for group in sorted({o['item']['group'] for o in seq}):
        observations=[o for o in seq if o['item']['group']==group]
        if not any(brackets_event(o['item'],options) for o in observations):
            raise ValueError(f'{group}: no pair brackets the event. Uncheck this group or supply the correct event time.')
        try:part=processor('P05',observations,grid,{**options,'quake_mosaic':False,**internal})
        except ValueError as error:raise ValueError(f'{group}: {error}') from error
        parts.append((group,observations,part))
    maps=[];scores=[];layers={};sources=[];series=[];notes=[];frames=0;reference=np.zeros(grid['shape'],bool);detail=[]
    for index,(group,observations,part) in enumerate(parts):
        values=part['layers']['event_displacement_cm']['data'];maps.append(values)
        source=next(o for o in observations if o['item']['id']==part['extra']['event_measurement']['selected_source'])
        coherence=np.asarray(source.get('aux',{}).get('coherence',np.zeros(grid['shape'])),dtype='float32')
        score=np.where(np.isfinite(coherence),coherence,-1.)
        scores.append(np.where(np.isfinite(values),score,-np.inf))
        fixed=part['layers']['reference_support']['data']==1;reference|=fixed
        interval=part['extra']['selected_interval']
        detail.append({'index':index+1,'group':group,'source_id':source['item']['id'],'start':interval['start'],'end':interval['end'],'reference_pixels':int(fixed.sum()),'valid_pixels':int(np.isfinite(values).sum()),'reference_diagnostics':part['extra']['reference_diagnostics'],'corrections':part['extra']['corrections'],'event_controls':part['extra']['event_controls'],'pair_network':part['extra']['pair_network'],'network_model':part['extra'].get('network_model'),'phase_reference_sensitivity':part['extra'].get('phase_reference_sensitivity',[]),'report':part['report']})
        for ident,layer in part['layers'].items():
            if ident.startswith('observation_'):
                layers[f'observation_{frames}']={**layer,'frame_index':frames,'group':group,'label':layer['label']+' · '+group};frames+=1
            elif ident.startswith('quality_'):
                layers[f'{ident}_group_{index+1}']={**layer,'label':layer['label']+' · '+group}
            else:layers[f'group_{index+1}_{ident}']={**layer,'label':layer['label']+' · '+group}
        sources+=part['sources'];series+=[{**row,'group':group} for row in part['series']];notes+=part['notes']
    dated=[layers.pop(key) for key in list(layers) if key.startswith('observation_')]
    dated.sort(key=lambda layer:(layer['start'],layer['end'],layer['group']))
    for i,layer in enumerate(dated):layers[f'observation_{i}']={**layer,'frame_index':i}
    series.sort(key=lambda row:(row['date'],row['end'],row['group']))
    cube=np.stack(maps);valid=np.isfinite(cube);count=valid.sum(axis=0);union=count>0
    chosen=np.argmax(np.stack(scores),axis=0)
    mosaic=np.take_along_axis(cube,chosen[None],axis=0)[0];mosaic[~union]=np.nan
    def put(ident,data,label,unit,kind='continuous'):
        layers[ident]={'data':np.asarray(data,dtype='float32'),'label':label,'unit':unit,'kind':kind}
    put('event_displacement_cm',mosaic,'Relative LOS displacement · event coverage mosaic','cm','diverging')
    put('event_source',np.where(union,chosen+1,np.nan),'Source group used at each cell · see source key','source index','categorical')
    put('event_coverage',np.where(union,count,np.nan),'Number of event groups with a valid measurement','count')
    put('reference_support',np.where(union|reference,reference,np.nan),'Union of reference cells used · inspect per-group references','class','binary')
    spread=np.full(grid['shape'],np.nan,'float32');overlap=count>=2
    spread[overlap]=(np.max(np.where(valid,cube,-np.inf),axis=0)-np.min(np.where(valid,cube,np.inf),axis=0))[overlap]
    put('event_overlap_spread',spread,'Difference between overlapping referenced LOS views','cm')
    area=abs(grid['transform'].a*grid['transform'].e)/1e6;common=valid.all(axis=0)
    metrics={**summary(mosaic),'mapped_area_km2':float(union.sum()*area),'event_groups':len(parts),'overlap_area_km2':float(overlap.sum()*area),'reference_pixels':int(reference.sum())}
    extra={'event_mosaic':{'groups':detail,'selection':'Highest delivered accepted-sample coherence among valid event groups at each cell; ties use sorted group order. No overlap averaging or inferred spatial filling.','quantity':'Relative LOS change; viewing directions and time windows differ between groups.','reference':('All groups use the same '+str(int(shared.sum()))+' coherent physical reference cells inside the supplied reference. No event pixels are fitted to remove differences. Stability still requires independent justification.' if internal else 'Fewer than 25 shared reference cells: groups use independent valid reference cells. Offsets and seams can remain; revise the reference if possible.'),'reference_mode':reference_mode,'shared_reference_pixels':int(shared.sum()),'source_key':{str(d['index']):d['group'] for d in detail},'overlap_difference_cm':summary(spread)},
           'event_measurement':{'quantity':'relative line-of-sight displacement','unit':'cm','positive':'toward the satellite','negative':'away from the satellite','geometry':'Multiple same-direction tracks/frames; different LOS vectors are retained, not decomposed into east/up.'},
           'event_selection':{'event_date':options.get('event_timestamp') or options.get('event_date'),'timing_precision':'timestamp' if options.get('event_timestamp') else 'calendar date','selection':'shortest strictly bracketing pair within each group','matching_pairs':sum(sum(brackets_event(o['item'],options) for o in obs) for _,obs,_ in parts)},
           'support':{'mode':'Union event mosaic; fixed common support only within each acquisition group, not across groups.','common_pixels':int(common.sum()),'common_area_km2':float(common.sum()*area),'common_fraction':float(common.mean()),'mosaic_pixels':int(union.sum()),'mosaic_area_km2':float(union.sum()*area),'per_observation_valid_pixels':[int(np.isfinite(o['array']).sum()) for o in seq]},
           'independent_validation':{'status':'not evaluated: mosaics have different spatial support and geometry; validate each group separately'},'method_references':[ARTICLE,'https://nisar-docs.asf.alaska.edu/gunw/']}
    if options.get('reference_observations'):raise ValueError('Validate independent regional observations in single-group P05 runs; mosaic groups have different spatial support.')
    if parts[0][2]['extra'].get('spatial_support'):extra['spatial_support']=parts[0][2]['extra']['spatial_support'].copy()
    notes=['Each mosaic cell comes from one event group; the selected reference mode is recorded; dates and radar look vectors vary. Inspect the source-group and overlap-difference maps. This is not a common-date time series, east/west motion decomposition or a damage map.','The overlap difference includes viewing geometry, different post-event dates, reference choices and measurement errors; it is not an accuracy estimate.']+list(dict.fromkeys(notes))
    findings=[f'{len(parts)} event groups ({reference_mode}) map {metrics["mapped_area_km2"]:.3f} km² of the selected region.',f'Relative LOS displacement median {metrics["median"]:.3f} cm; p10 {metrics["p10"]:.3f}, p90 {metrics["p90"]:.3f} cm across mapped cells. These describe this mosaic’s spatial values, not earthquake-only motion or uncertainty.','Inspect per-group dates, references and the source key before comparing this multi-view display with a published map.']
    difference=extra['event_mosaic']['overlap_difference_cm']
    if difference['valid_pixels']:findings.append(f"Overlapping referenced LOS views differ by a spatial median {difference['median']:.3f} cm and p90 {difference['p90']:.3f} cm. These are differences between views, not accuracy bounds. Check this disagreement before interpreting a mosaic seam as ground change.")
    return {'project':'P05','title':'Earthquake interval · relative LOS coverage mosaic','unit':'cm','layers':layers,'series':series,'metrics':metrics,'notes':notes,'extra':extra,'sources':sources,'status':'exploratory','algorithm_version':'0.4.3','report':{'headline':'What these observations show','findings':findings,'comparison_basis':extra['support']['mode'],'next_checks':['Check reference stability independently.','Inspect each source group and overlap differences.','Compare against georeferenced independent displacement data.'],'validation':'Engineering behavior can be tested; independent geophysical accuracy is not established.'}}
