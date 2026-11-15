"""Known-answer tests for the completed analysis modules; not field accuracy claims."""
import numpy as np
import pytest
from datetime import datetime,timedelta,timezone
from rasterio.transform import from_origin
from backend.advanced import network_solution,seasonal_solution,robust_baseline
from backend.spatial import patch_history,validate_context
from backend.validation import water_calibration,continuous_validation
from backend.processors import process,region_mask
from test_processing_maturity import scene,grid,BBOX,REFERENCE,options


def test_tracking_preserves_split_and_merge_relationships():
    g={'shape':(5,5),'transform':from_origin(0,1000,100,100),'crs':'EPSG:6933'}
    a=np.zeros((5,5),bool);a[1:4,1:4]=True;b=a.copy();b[:,2]=False
    t=patch_history([a,b,a],['a','b','c'],g,0)
    assert len(t['objects'])==4
    assert len(t['objects'][0]['children'])==2
    assert len(t['objects'][-1]['parents'])==2
    assert 'merge' in t['objects'][-1]['event']
    assert len(t['geometry']['features'])==4


def test_network_recovers_known_epoch_values_and_zero_residual(grid):
    seq=scene('GUNW',grid,[0,0,0]);dates=['2026-08-01T00:00:00Z','2026-08-13T00:00:00Z','2026-08-25T00:00:00Z']
    for o,(i,j) in zip(seq,[(0,1),(1,2),(0,2)]):o['item'].update(start=dates[i],end=dates[j])
    values=np.stack([np.full(grid['shape'],v) for v in [10,20,30]])
    fitted,meta=network_solution(seq,values)
    assert meta['status'].startswith('fitted')
    assert fitted['cube'][:,0,0]==pytest.approx([0,10,30])
    assert np.max(fitted['rms'])<1e-10
    missing,metadata=network_solution(seq[:2],values[:2]);assert missing is None and 'redundant' in metadata['reason']


def test_annual_model_recovers_injected_signal_and_rejects_short_season():
    start=datetime(2024,1,1,tzinfo=timezone.utc);dates=[(start+timedelta(days=i*45)).isoformat() for i in range(12)]
    t=np.arange(12)*45/365.25;signal=2+3*t+5*np.sin(2*np.pi*t)
    cube=np.broadcast_to(signal[:,None,None],(12,2,2))
    fitted,meta=seasonal_solution(cube,dates)
    assert np.allclose(fitted['amplitude'],5)
    assert np.max(fitted['rms'])<1e-10
    assert seasonal_solution(cube[:5],dates[:5])[0] is None


def test_held_out_water_labels_calibrate_separately():
    db=np.array([[[-12,-12,-4,-4],[-12,-12,-4,-4]]],dtype='float32');contexts=[]
    for row,split in [(0,'train'),(1,'test')]:
        for sl,role in [(slice(0,2),'water'),(slice(2,4),'dry')]:
            mask=np.zeros((2,4),bool);mask[row,sl]=True
            contexts.append({'role':role,'mask':mask,'properties':{'date':'2026-08-01','split':split,'source':'independent synthetic truth'}})
    threshold,report=water_calibration(db,['2026-08-01'],contexts,-17)
    assert -12<threshold<=-4
    assert report['test_cells']==4 and report['calibration_cells']==4
    assert report['precision']==report['recall']==report['iou']==1
    conflict={**contexts[0],'role':'dry'}
    with pytest.raises(ValueError,match='conflicting'):water_calibration(db,['2026-08-01'],contexts+[conflict],-17)




def test_fire_map_and_chart_use_same_pixel_departure_statistic(grid):
    ref=region_mask(REFERENCE,grid);a=np.full(grid['shape'],.1);b=a.copy()
    coords=np.argwhere(~ref)
    # A heterogeneous trajectory where difference-of-medians need not equal median difference.
    for i,(y,x) in enumerate(coords):
        a[y,x]=10**([1,2,100][i%3]/10);b[y,x]=10**([2,100,1][i%3]/10)
    r=process('P03',scene('GCOV',grid,[a,b,b]),grid,options())
    assert r['series'][-1]['relative_trajectory_db']==pytest.approx(float(np.median(r['layers']['relative_change']['data'][~ref])),abs=1e-4)


def test_exact_event_timestamp_supports_same_day_pair_boundary(grid):
    obs=scene('GUNW',grid,[0]);obs[0]['item'].update(start='2026-08-01T00:00:00Z',end='2026-08-02T00:00:00Z')
    r=process('P05',obs,grid,{'reference_bbox':REFERENCE,'event_timestamp':'2026-08-01T12:00:00Z'})
    assert r['extra']['event_selection']['timing_precision']=='timestamp'


def test_regional_reference_metrics_are_matched_and_not_invented():
    series=[{'date':'2026-08-01','median':.3},{'date':'2026-08-13','median':.5}]
    references=[{'date':'2026-08-01','end':None,'value':.2,'source':'sensor record'},{'date':'2026-08-13','value':.4,'source':'sensor record'}]
    r=continuous_validation(series,references,'m³/m³')
    assert r['bias']==pytest.approx(.1) and r['rmse']==pytest.approx(.1) and r['unbiased_rmse']<1e-15
    assert continuous_validation(series,[],'m³/m³')['status'].startswith('not evaluated')


def test_context_rejects_missing_label_provenance_and_bad_geometry():
    polygon={'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}
    f={'type':'Feature','properties':{'role':'water','date':'2026-08-01','split':'test'},'geometry':polygon}
    with pytest.raises(ValueError,match='source'):validate_context({'type':'FeatureCollection','features':[f]})


def test_two_date_flood_mode_reports_unresolved_followup(grid):
    r=process('P01',scene('GCOV',grid,[.1,.001]),grid,{})
    assert r['metrics']['new_water_candidate_km2']>0
    assert r['metrics']['unresolved_water_candidate_km2']==r['metrics']['new_water_candidate_km2']
    assert np.isnan(r['layers']['recovery']['data']).all()


def test_native_contribution_maps_survive_cache_and_ionosphere_is_explicit(tmp_path,monkeypatch):
    import h5py
    from backend import science
    from test_pipeline import fixture_bytes
    monkeypatch.setattr(science,'DATA',tmp_path);(tmp_path/'raw').mkdir()
    path=tmp_path/'raw'/'phase.h5';path.write_bytes(fixture_bytes('GUNW',0))
    with h5py.File(path,'a') as f:
        parent=f['/science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/HH']
        d=parent.create_dataset('ionospherePhaseScreen',data=np.full((100,100),.25,'float32'));d.attrs['units']='radians'
    g=science.target_grid(BBOX,200);item={'id':'phase','product':'GUNW','url':''}
    raw=science.load_observation(item,BBOX,g,{},lambda:False)
    corrected=science.load_observation(item,BBOX,g,{'apply_ionosphere':True},lambda:False)
    assert np.allclose(raw['array']-corrected['array'],.25,atol=1e-6)
    assert 'accepted_fraction' in corrected['aux'] and 'rejected_coherence' in corrected['aux']
    assert corrected['attrs']['correction_manifest'][0]['operation']=='subtract'
    cached=science.load_observation(item,BBOX,g,{'apply_ionosphere':True},lambda:False)
    assert cached['cache_hit'] and np.allclose(cached['aux']['accepted_fraction'],corrected['aux']['accepted_fraction'],equal_nan=True)


def test_catalog_custom_limit_keeps_pagination_offsets_fixed(monkeypatch):
    from backend import catalog
    calls=[]
    def get(url,params,timeout):
        start=(params['page_num']-1)*params['page_size'];calls.append(start)
        entries=[{'id':f'G{i}','producer_granule_id':'NISAR_L2_PR_GCOV_023_101_A_023_2005_DHDH_A_20260621T044315_20260621T044332_P05023_N_P_J_001.h5','links':[{'href':'https://datapool.asf.alaska.edu/a.h5'}]} for i in range(start,min(start+params['page_size'],205))]
        class Response:
            headers={'CMR-Hits':'205'};url='https://cmr.earthdata.nasa.gov/search/granules.json'
            def raise_for_status(self):pass
            def json(self):return {'feed':{'entry':entries}}
        return Response()
    monkeypatch.setattr(catalog.requests,'get',get)
    result=catalog.search('GCOV',[0,0,1,1],'2026-01-01','2026-10-17',limit=201)
    assert calls==[0,200] and len(result['items'])==201 and result['truncated']


def test_current_tool_registry_has_only_implemented_guide_fields():
    import json
    from pathlib import Path
    guides=json.loads((Path(__file__).resolve().parents[1]/'docs/tools.json').read_text())
    assert len(guides)==7
    for g in guides:
        assert g['steps'] and g['outputs'] and g['limitations'] and g['version']==('0.4.2' if g['id']=='P07' else '0.4.1' if g['id']=='P04' else '0.4.3' if g['id']=='P05' else '0.8.0' if g['id']=='P03' else '0.5.0' if g['id']=='P02' else '0.7.1' if g['id']=='P06' else '0.4.0')
        assert not any(key in g for key in ['stretch','mvp','novelty','mix','tools'])


def test_optional_tracking_limit_does_not_export_a_partial_object_list():
 from backend.spatial import optional_patch_history,CandidateTrackingLimit
 g={'shape':(5,5),'transform':from_origin(0,1000,100,100),'crs':'EPSG:6933'}
 a=np.zeros((5,5),bool);a[0,0]=a[2,2]=a[4,4]=True
 with pytest.raises(CandidateTrackingLimit):patch_history([a],['date'],g,0,max_objects=2)
 result=optional_patch_history([a],['date'],g,0,max_objects=2)
 assert result['available'] is False and result['object_limit']==2
 assert result['objects']==[] and result['links']==[] and 'geometry' not in result
 assert '2 objects' in result['reason'] and 'partial' in result['meaning']


def test_optional_tracking_propagates_unrelated_errors(monkeypatch):
 from backend import spatial
 monkeypatch.setattr(spatial,'patch_history',lambda *args:(_ for _ in ()).throw(ValueError('invalid geometry')))
 with pytest.raises(ValueError,match='invalid geometry'):spatial.optional_patch_history([],[],{},0)


@pytest.mark.parametrize('pid',['P01','P02','P06'])
def test_tracking_limit_preserves_core_maps_across_all_tracking_tools(grid,monkeypatch,pid):
 from backend import spatial
 obs=scene('GCOV',grid,[.1,.005,.1,.005]);opt={**options(),'surface_method':'evolving','smoothing_m':200}
 baseline=process(pid,obs,grid,opt)
 def limited_tracking(*args):raise spatial.CandidateTrackingLimit('Candidate tracking exceeds 1000 objects')
 monkeypatch.setattr(spatial,'patch_history',limited_tracking)
 limited=process(pid,obs,grid,opt)
 assert baseline['metrics']==limited['metrics'] and baseline['series']==limited['series']
 assert baseline['layers'].keys()==limited['layers'].keys()
 for key in baseline['layers']:np.testing.assert_array_equal(baseline['layers'][key]['data'],limited['layers'][key]['data'])
 assert limited['extra']['tracking']['available'] is False
 assert any('tracking is unavailable' in note for note in limited['notes'])
