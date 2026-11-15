"""Synthetic suitability rules are engineering checks, never stable-ground truth."""
import json,time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.reference import reference_assistant,reference_fingerprint,rectangle_mask
from backend.science import target_grid
from backend import app as module
from test_processing_maturity import scene,options,BBOX


def observations():
    grid=target_grid(BBOX,100,max_dimension=900)
    seq=scene('GUNW',grid,[0,0,0])
    for o in seq:o['aux']={'coherence':np.full(grid['shape'],.92)}
    return grid,seq


def test_candidates_are_inside_bounds_separated_and_not_certified_stable():
    grid,seq=observations();r=reference_assistant(seq,grid,{})
    assert len(r['candidates'])==3
    previous=[]
    for c in r['candidates']:
        assert all(BBOX[i]<=c['bbox'][i] for i in [0,1])
        assert all(BBOX[i]>=c['bbox'][i] for i in [2,3])
        assert c['shared_cells']>=25 and c['shared_fraction']>=.8
        assert c['worst_pair_median_coherence']==pytest.approx(.92)
        assert c['stability']=='not independently established'
        mask=rectangle_mask(c['bbox'],grid)
        assert not any(np.any(mask&p) for p in previous);previous.append(mask)
    assert all(c['relative_rate_to_candidate_1_cm_year']==pytest.approx(0) for c in r['candidates'])


def test_strong_coherent_moving_patch_is_never_called_stable():
    grid,seq=observations();h,w=grid['shape']
    for o in seq:
        o['array'][:,:w//2]=3 # spatially uniform motion can be coherent
        o['aux']['coherence'][:,:w//2]=.99
    r=reference_assistant(seq,grid,{})
    c=r['candidates'][0]
    assert np.median(seq[0]['array'][rectangle_mask(c['bbox'],grid)])==3
    assert 'may be moving' in r['stability']
    assert c['data_suitability']=='strong shared data'
    assert 'stationary' in r['relative_rate_meaning']


def test_reference_rate_shift_matches_known_phase_difference():
    grid,seq=observations()
    for o in seq:
        o['array'][:]=np.arange(grid['shape'][1])[None,:]*.2
        o['aux']['coherence'][:]=np.linspace(.99,.8,grid['shape'][1])[None,:]
    r=reference_assistant(seq,grid,{})
    a,b=r['candidates'][:2]
    difference=b['pair_reference_phase_rad'][0]-a['pair_reference_phase_rad'][0]
    # Constant 12-day pair change -> exact linear rate.
    expected=-.24*difference/(4*np.pi)*100*365.25/12
    assert b['relative_rate_to_candidate_1_cm_year']==pytest.approx(expected,abs=1e-5)


@pytest.mark.parametrize('mode',['no_common','missing_coherence','too_small'])
def test_unusable_data_does_not_silently_relax_thresholds(mode):
    grid,seq=observations()
    if mode=='no_common':
        for i,o in enumerate(seq):o['array'][:]=np.nan;o['array'][i,:]=0
    elif mode=='missing_coherence':
        for o in seq:o['aux']={}
    else:
        for o in seq:o['array'][:]=np.nan;o['array'][:2,:2]=0
    r=reference_assistant(seq,grid,{})
    assert r['candidates']==[] and r['status']=='no suitable candidate found'


def test_current_reference_is_assessed_even_if_invalid():
    grid,seq=observations()
    r=reference_assistant(seq,grid,{**options(),'reference_bbox':BBOX})
    assert any('No comparison ground' in w for w in r['current_reference']['warnings'])
    for o in seq:o['array'][:]=np.nan
    r=reference_assistant(seq,grid,options())
    assert r['current_reference']['shared_cells']==0
    assert r['current_reference']['data_suitability']=='review needed'


def test_supplied_affected_area_is_excluded():
    grid,seq=observations()
    w,s,e,n=BBOX;mid=(w+e)/2
    context={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'affected'},'geometry':{'type':'Polygon','coordinates':[[[w,s],[mid,s],[mid,n],[w,n],[w,s]]]}}]}
    r=reference_assistant(seq,grid,{'spatial_context':context})
    assert r['candidates'] and all(c['bbox'][0]>=mid-.0001 for c in r['candidates'])


def test_assessment_fingerprint_tracks_inputs_but_not_new_spatial_zero():
    grid,seq=observations();items=[o['item'] for o in seq]
    a=reference_fingerprint(items,BBOX,{})
    assert a==reference_fingerprint(list(reversed(items)),BBOX,{'reference_bbox':BBOX})
    assert a!=reference_fingerprint(items,BBOX,{'coherence':.9})
    assert a!=reference_fingerprint(items[:2],BBOX,{})


@pytest.mark.parametrize('pid',['P03','P04','P05'])
def test_assistant_job_and_adoption_are_saved_and_stale_choices_rejected(monkeypatch,tmp_path,pid):
    grid,seq=observations()
    if pid=='P03':seq=scene('GCOV',grid,[.1,.1,.1])
    (tmp_path/'raw').mkdir();(tmp_path/'jobs').mkdir()
    monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS_DIR',tmp_path/'jobs');monkeypatch.setattr(module,'JOBS',{})
    monkeypatch.setattr(module,'CATALOG',{o['item']['id']:o['item'] for o in seq})
    for o in seq:(tmp_path/'raw'/(o['item']['id']+'.h5')).write_bytes(b'SYNTHETIC route fixture')
    def load(item,*args):return next(o for o in seq if o['item']['id']==item['id'])
    monkeypatch.setattr(module,'load_observation',load)
    client=TestClient(module.app);request={'bbox':BBOX,'granules':[o['item']['id'] for o in seq],'projects':[pid],'options':{**options(),'resolution':100}}
    response=client.post('/api/reference-assistant',json=request);assert response.status_code==200,response.text
    ident=response.json()['id'];deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        job=client.get('/api/jobs/'+ident).json()
        if job['status'] not in ['queued','running']:break
        time.sleep(.02)
    assert job['status']=='completed',job
    report=client.get(job['assistant_url']).json();candidate=report['candidates'][0]
    current_body=module.RunQuery(**{**request,'options':{**request['options'],'reference_assistant_id':ident,'reference_candidate_id':'current'}})
    checked=module.check_assistant_choice(current_body,[o['item'] for o in seq])
    assert checked['candidate']['id']=='current' and checked['candidate']['bbox']==request['options']['reference_bbox']
    current_body.options['reference_bbox']=candidate['bbox']
    with pytest.raises(module.HTTPException) as changed:module.check_assistant_choice(current_body,[o['item'] for o in seq])
    assert 'reference changed' in changed.value.detail
    request['options'].update(reference_bbox=candidate['bbox'],reference_assistant_id=ident,reference_candidate_id=candidate['id'])
    # Exercise the real processor/export path using the adopted rectangle.
    started=client.post('/api/run',json=request);assert started.status_code==200,started.text
    ident2=started.json()['id'];deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        job2=client.get('/api/jobs/'+ident2).json()
        if job2['status'] not in ['queued','running']:break
        time.sleep(.02)
    assert job2['status']=='completed',job2
    result=client.get(job2['results'][pid]['url']).json()
    assert result['extra']['reference_assistant']['assessment_id']==ident
    assert result['extra']['reference_assistant']['candidate']['bbox']==candidate['bbox']
    cross=client.post('/api/run',json={**request,'projects':['P05' if pid!='P05' else 'P04']})
    assert cross.status_code==422
    assert report['grid']['shape']==result['grid']['shape']
    request['options']['coherence']=.9
    stale=client.post('/api/run',json=request)
    assert stale.status_code==422 and 'changed' in stale.json()['detail']
    request['options']['coherence']=.4;request['options']['reference_bbox']=BBOX
    assert client.post('/api/run',json=request).status_code==422
    assert client.post('/api/reference-assistant',json={**request,'projects':['P01']}).status_code==422


def test_current_reference_outside_domain_remains_usable_like_p04():
    grid,seq=observations();w,s,e,n=BBOX;mid=(w+e)/2
    context={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'domain'},'geometry':{'type':'Polygon','coordinates':[[[mid,s],[e,s],[e,n],[mid,n],[mid,s]]]}}]}
    r=reference_assistant(seq,grid,{**options(),'spatial_context':context})
    assert r['current_reference']['shared_cells']>25
    assert not any('No shared finite' in text for text in r['current_reference']['warnings'])
    assert all(c['bbox'][0]>=mid-.0001 for c in r['candidates'])


@pytest.mark.parametrize('pid',['P03','P04','P05'])
def test_shared_assistant_offsets_match_actual_processor_reference_changes(pid):
    from backend.processors import process
    grid,seq=observations();opts=options()
    if pid=='P03':
        seq=scene('GCOV',grid,[.1,.15,.2])
        for i,o in enumerate(seq):o['array']*=np.exp(np.arange(grid['shape'][1])[None,:]*.01*i)
    else:
        for o in seq:o['array'][:]=np.arange(grid['shape'][1])[None,:]*.2
    report=reference_assistant(seq,grid,opts,pid)
    a,b=report['candidates'][:2]
    ra=process(pid,seq,grid,{**opts,'reference_bbox':a['bbox']})
    rb=process(pid,seq,grid,{**opts,'reference_bbox':b['bbox']})
    assert report['project']==pid
    assert report['comparison_unit']==('dB' if pid=='P03' else 'cm')
    key='relative_change' if pid=='P03' else 'event_displacement_cm' if pid=='P05' else 'range'
    index=-1 if pid in ['P03','P04'] else 0
    expected=b['relative_reference_offsets'][index]*(10 if pid=='P04' else 1)
    difference=ra['layers'][key]['data']-rb['layers'][key]['data']
    assert np.nanmedian(difference)==pytest.approx(expected,abs=1e-5)
    if pid!='P04':assert all(c['relative_rate_to_candidate_1_cm_year'] is None for c in report['candidates'])
    if pid=='P03':
        assert all(c['worst_pair_median_coherence'] is None for c in report['candidates'])
        assert 'Unaffected status' in report['stability']


def test_p05_assistant_supports_adjacent_frames_with_identical_dates():
    grid,seq=observations();seq=seq[:2]
    for i,o in enumerate(seq):
        o['item']['group']=f'162_A_00{i+6}_2000_SH_X05010'
        o['item']['start']=seq[0]['item']['start'];o['item']['end']=seq[0]['item']['end']
    report=reference_assistant(seq,grid,{**options(),'quake_mosaic':True},'P05')
    assert report['candidates'] and not any('revisions differ' in w for w in report['warnings'])
    with pytest.raises(ValueError,match='enable event coverage'):reference_assistant(seq,grid,options(),'P05')
    with pytest.raises(ValueError,match='documented event'):reference_assistant(seq,grid,{},'P05')


def test_fingerprint_prevents_cross_tool_and_changed_event_baseline_reuse():
    grid,seq=observations();items=[o['item'] for o in seq]
    base=reference_fingerprint(items,BBOX,{},'P05')
    assert base!=reference_fingerprint(items,BBOX,{},'P04')
    for setting in [{'event_date':'2026-08-05'},{'quake_mosaic':True},{'baseline_count':2}]:
        assert base!=reference_fingerprint(items,BBOX,setting,'P05')


def test_narrow_mosaic_overlap_is_found_and_union_is_comparison_ground():
    grid,seq=observations();seq=seq[:2];h,w=grid['shape']
    for i,o in enumerate(seq):
        o['item']['group']=f'162_A_00{i+6}_2000_SH_X05010'
        o['item']['start']=seq[0]['item']['start'];o['item']['end']=seq[0]['item']['end']
        o['array'][:]=np.nan
        if i==0:o['array'][:,:w//2]=0
        else:o['array'][:,w//2:]=0
        o['array'][20:26,20:26]=0
    opts={**options(),'quake_mosaic':True};report=reference_assistant(seq,grid,opts,'P05')
    assert report['candidates']
    c=report['candidates'][0]
    assert c['shared_cells']==36 and c['patch_cells']==36
    current=reference_assistant(seq,grid,{**opts,'reference_bbox':c['bbox']},'P05')['current_reference']
    assert not any('No comparison ground' in w for w in current['warnings'])


def test_reference_worker_reports_failed_source_without_silent_exclusion(monkeypatch,tmp_path):
    grid,seq=observations()
    monkeypatch.setattr(module,'JOBS_DIR',tmp_path);monkeypatch.setattr(module,'JOBS',{})
    calls=[]
    def load(item,*args):
        calls.append(item['id'])
        if item['id']=='0':raise ValueError('No coherent connected-component pixels survive quality screening.')
        return next(o for o in seq if o['item']['id']==item['id'])
    monkeypatch.setattr(module,'load_observation',load)
    body=module.RunQuery(bbox=BBOX,granules=[o['item']['id'] for o in seq],projects=['P05'],options=options())
    job=module.newjob('reference');job['request']=body.model_dump()
    module.reference_work(job,[o['item'] for o in seq],body)
    assert calls==['0','1','2']
    assert job['status']=='needs_input' and 'assistant_url' not in job
    assert job['source_errors'][0]['source']=='0'
    assert job['source_errors'][0]['name']==seq[0]['item']['name']
    assert 'silently omitted' in job['message']


def test_spatial_sampling_reaches_high_quality_ground_away_from_northern_edge():
    grid,seq=observations();h,w=grid['shape']
    for o in seq:
        o['aux']['coherence'][:h//2]=.96
        o['aux']['coherence'][h//2:]=.72
    report=reference_assistant(seq,grid,{},'P04')
    assert all(c['worst_pair_median_coherence']==pytest.approx(.96) for c in report['candidates'])
    assert all(c['shared_cells']>=100 for c in report['candidates'])
    for o in seq:o['aux']['coherence'][:h//2]=.72;o['aux']['coherence'][h//2:]=.96
    report=reference_assistant(seq,grid,{},'P04')
    assert all(c['worst_pair_median_coherence']==pytest.approx(.96) for c in report['candidates'])
    assert all(c['shared_cells']>=100 for c in report['candidates'])


def test_checked_reference_polygons_retain_exact_geometry(monkeypatch):
    grid,seq=observations();w,s,e,n=options()['reference_bbox']
    context={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'reference','name':'Checked ground'},'geometry':{'type':'Polygon','coordinates':[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}}]}
    opts={'spatial_context':context};report=reference_assistant(seq,grid,opts,'P04');ident='a'*32
    monkeypatch.setattr(module,'assistant_report',lambda _:report)
    monkeypatch.setattr(module,'JOBS',{ident:{'request':{'options':opts}}})
    body=module.RunQuery(bbox=BBOX,granules=[o['item']['id'] for o in seq],projects=['P04'],options={**opts,'reference_assistant_id':ident,'reference_candidate_id':'current'})
    chosen=module.check_assistant_choice(body,[o['item'] for o in seq]);assert chosen['candidate']['id']=='current' and chosen['candidate']['bbox'] is None
    body.options['spatial_context']['features'][0]['properties']['name']='Changed reference'
    with pytest.raises(module.HTTPException):module.check_assistant_choice(body,[o['item'] for o in seq])
