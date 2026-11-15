"""Study statistics must not absorb auxiliary reference/stable-ground samples."""
import copy
import numpy as np
import pytest
from backend.processors import process,region_mask
from backend.science import target_grid
from backend.spatial import context_masks,union_role,role_mask
from test_processing_maturity import scene,BBOX,REFERENCE,options


def feature(role,left,right):
    _,south,_,north=BBOX
    return {'type':'Feature','properties':{'role':role},'geometry':{'type':'Polygon','coordinates':[[[left,south],[right,south],[right,north],[left,north],[left,south]]]}}


def context(auxiliary=True,narrow=False):
    west,_,east,_=BBOX
    features=[feature('domain',west+(.05 if narrow else .035),east)]
    if auxiliary:features += [feature('reference',west,west+.01),feature('stable',west+.012,west+.025)]
    return {'type':'FeatureCollection','features':features}


def masks(ctx,grid):return {f['role']:f['mask'] for f in context_masks(ctx,grid)}


@pytest.mark.parametrize('pid,dual',[('P01',False),('P02',False),('P02',True)])
def test_water_measurements_and_counts_stay_inside_domain(pid,dual):
    grid=target_grid(BBOX,200);ctx=context();domain=masks(ctx,grid)['domain']
    obs=scene('GCOV',grid,[.1,.01] if pid=='P01' else [.1,.01,.01])
    opt={'spatial_context':ctx,'water_method':'hh_hv' if dual else 'single'}
    if dual:
        for i,o in enumerate(obs):o['aux']={'water_hh_sigma_power':o['array'].copy(),'water_hv_sigma_power':o['array']*.01,'cross_copol_ratio_db':np.full(grid['shape'],i,dtype='float32')}
    original=[o['array'].copy() for o in obs];result=process(pid,obs,grid,opt)
    assert result['extra']['support']['common_pixels']==int(domain.sum())
    assert result['metrics']['common_valid_area_km2']==pytest.approx(domain.sum()*.04)
    for info in result['layers'].values():
        if info.get('spatial_scope')=='study domain':assert np.isnan(info['data'][~domain]).all(),info['label']
    assert all(row['comparison_pixels']==domain.sum() for row in result['series'])
    if dual:
        assert result['layers']['polarization_ratio_change']['spatial_scope']=='source diagnostic'
        assert np.isfinite(result['layers']['polarization_ratio_change']['data'][~domain]).all()
    for o,before in zip(obs,original):np.testing.assert_array_equal(o['array'],before)


def test_relative_fire_reference_can_lie_outside_domain_without_entering_measurement_maps():
    grid=target_grid(BBOX,200);ctx=context(False);domain=masks(ctx,grid)['domain'];ref=region_mask(REFERENCE,grid)
    obs=scene('GCOV',grid,[.01,.04,.16])
    for o in obs:o['array'][ref]=.01
    result=process('P03',obs,grid,{**options(),'spatial_context':ctx,'baseline_count':1})
    expected=10*np.log10(16)
    assert result['metrics']['relative_trajectory_db']==pytest.approx(expected,abs=1e-5)
    assert result['extra']['support']['common_pixels']==domain.sum()
    assert np.isnan(result['layers']['relative_change']['data'][~domain]).all()
    assert np.all(result['layers']['reference_support']['data'][ref]==1)


def test_legacy_surface_change_ignores_reference_and_stable_polygons_outside_domain():
    grid=target_grid(BBOX,200);ctx=context();domain=masks(ctx,grid)['domain']
    result=process('P06',scene('GCOV',grid,[.01,.1]),grid,{'spatial_context':ctx,'surface_method':'legacy'})
    assert result['metrics']['persistent_change_area_km2']==pytest.approx(domain.sum()*.04)
    assert np.isnan(result['layers']['surface']['data'][~domain]).all()


@pytest.mark.parametrize('pid',['P04','P05'])
def test_reference_and_stable_coverage_cannot_hide_missing_study_coverage(pid):
    grid=target_grid(BBOX,200);ctx=context();domain=masks(ctx,grid)['domain'];obs=scene('GUNW',grid,[0.,0.])
    for o in obs:o['array'][domain]=np.nan
    with pytest.raises(ValueError,match='inside the study domain'):process(pid,obs,grid,{**options(),'spatial_context':ctx,'phase_network':False})


@pytest.mark.parametrize('pid',['P04','P05'])
def test_only_actual_reference_is_retained_and_valid_comparison_must_be_in_domain(pid):
    grid=target_grid(BBOX,200);ctx=context();m=masks(ctx,grid);obs=scene('GUNW',grid,[1.,1.])
    for o in obs:o['array'][m['reference']]=0
    # Reference polygons take precedence over an old, larger rectangle.
    result=process(pid,obs,grid,{**options(),'reference_bbox':BBOX,'spatial_context':ctx,'phase_network':False})
    assert result['extra']['spatial_support']['processing_footprint_pixels']==int((m['domain']|m['reference']).sum())
    assert result['extra']['reference_diagnostics']['fixed_pixels']==m['reference'].sum()
    assert np.isfinite(result['layers']['range']['data'][m['domain']]).all()
    assert np.isnan(result['layers']['range']['data'][~m['domain']]).all()
    # A reference covering the entire study cannot borrow comparison samples
    # from a separate stable polygon outside the study.
    ctx['features'][1]=copy.deepcopy(ctx['features'][0]);ctx['features'][1]['properties']['role']='reference'
    with pytest.raises(ValueError,match='outside the reference'):process(pid,obs,grid,{**options(),'spatial_context':ctx,'phase_network':False})


@pytest.mark.parametrize('bias',[False,True])
def test_glacier_companions_and_spatial_filters_share_the_study_population(bias):
    from test_horizontal_glacier import geometry,FIELDS
    grid=target_grid(BBOX,200);ctx=context(narrow=True);m=masks(ctx,grid);domain=m['domain'];stable=m['stable'];g=geometry(grid['shape'])
    obs=scene('GOFF',grid,[999.]);other=np.full(grid['shape'],999.,dtype='float32')
    range_bias,along_bias=(9.,12.) if bias else (0.,0.)
    obs[0]['array'][domain]=np.sin(np.deg2rad(40))*3*12+range_bias;other[domain]=4*12+along_bias
    obs[0]['array'][stable]=range_bias;other[stable]=along_bias
    obs[0]['aux']={'other_offset':other,**{'geometry_'+k:v for k,v in g.items()}}
    before_primary=obs[0]['array'].copy();before_other=other.copy()
    result=process('P07',obs,grid,{'spatial_context':ctx,'offset_solution':'horizontal','offset_filter':True,'offset_stable_bias':bias})
    assert result['metrics']['median']==pytest.approx(5.,abs=1e-5)
    assert result['extra']['offset_filter_diagnostics'][0]['native_screened_grid_pixels']==domain.sum()
    assert np.isnan(result['layers']['horizontal_speed']['data'][~domain]).all()
    if bias:assert result['extra']['stable_terrain'][0]['stable_pixels']==stable.sum()
    np.testing.assert_array_equal(obs[0]['array'],before_primary);np.testing.assert_array_equal(other,before_other)


def test_local_offset_neighbors_do_not_reach_into_auxiliary_ground():
    from backend.advanced import local_offset_filter
    a=np.arange(120,dtype='float32').reshape(10,12);domain=np.zeros(a.shape,bool);domain[2:8,3:9]=True
    a[~domain]=10000.;opts={'offset_local_filter':True}
    actual,rejected=local_offset_filter(a,opts,domain=domain)
    expected,_=local_offset_filter(np.where(domain,a,np.nan),opts)
    np.testing.assert_array_equal(actual[domain],expected[domain]);np.testing.assert_array_equal(actual[~domain],a[~domain]);assert not rejected[~domain].any()


@pytest.mark.parametrize('product',['GCOV','GUNW','GOFF'])
def test_elementary_workflows_apply_the_same_domain_and_preserve_phase_reference(product):
    from backend.workflows import process as experimental
    from test_workflows import recipe
    grid=target_grid(BBOX,200);ctx=context();m=masks(ctx,grid);domain=m['domain'];obs=scene(product,grid,[.01,.1] if product=='GCOV' else [1.,1.])
    opts={'spatial_context':ctx}
    if product=='GUNW':
        steps=[{'operation':'los'},{'operation':'summary'}]
        for o in obs:o['array'][m['reference']]=0
    else:steps=[{'operation':'summary'}]
    result=experimental(recipe(product,steps,options=opts),obs,grid)
    assert result['extra']['support']['common_pixels']==domain.sum()
    assert np.isnan(result['layers']['summary']['data'][~domain]).all()
    if product=='GUNW':assert np.all(result['layers']['reference_support']['data'][m['reference']]==1)
    assert result['extra']['spatial_support']['version']=='1.0'


def test_role_union_matches_existing_rasterization_and_export_records_scope(tmp_path):
    from backend.exports import export_result
    from backend.result_contracts import attach
    import rasterio
    grid=target_grid(BBOX,200);ctx=context();all_masks=context_masks(ctx,grid)
    for role in ['domain','reference','stable']:np.testing.assert_array_equal(role_mask(ctx,role,grid),union_role(all_masks,role,grid['shape']))
    result=process('P01',scene('GCOV',grid,[.1,.01]),grid,{'spatial_context':ctx});result['processing_options']={'spatial_context':ctx}
    attach(result,grid);first=result['extra']['execution_fingerprint'];result['extra']['spatial_support']['version']='different-reviewed-contract';attach(result,grid);assert result['extra']['execution_fingerprint']!=first
    result['extra']['spatial_support']['version']='1.0';saved=export_result(result,grid,tmp_path/'result')
    with rasterio.open(tmp_path/'result'/'event.tif') as source:
        assert source.tags(1)['spatial_scope']=='study domain' and source.tags()['spatial_contract_version']=='1.0'
        assert np.isnan(source.read(1)[~masks(ctx,grid)['domain']]).all()
