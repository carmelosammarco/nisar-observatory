"""Independent synthetic scenes with known changes and intentional failure cases.
These fixtures establish numerical behavior, not environmental accuracy.
"""
from datetime import datetime,timedelta,timezone
import numpy as np
import pytest
import h5py
from pyproj import Transformer
from rasterio.transform import from_origin
from backend import science
from backend.engines import PRODUCT_FOR,MINIMUM,pair_network
from backend.processors import process,region_mask

BBOX=[-114.76,36.12,-114.70,36.18]
REFERENCE=[-114.76,36.12,-114.75,36.18]

@pytest.fixture
def grid():return science.target_grid(BBOX,200)

def scene(product,grid,values):
    out=[]
    for i,v in enumerate(values):
        a=np.full(grid['shape'],v,dtype='float32') if np.isscalar(v) else np.array(v,dtype='float32')
        start=datetime(2026,8,1,tzinfo=timezone.utc)+timedelta(days=i*12)
        end=start+timedelta(days=12) if product in ['GUNW','GOFF'] else start+timedelta(seconds=30)
        out.append({'array':a,'item':{'id':str(i),'name':'SYNTHETIC KNOWN TRUTH','product':product,'start':start.isoformat(),'end':end.isoformat(),'group':'synthetic'},'path':'/science/'+product+'/frequencyA/test','attrs':{},'quality_paths':[],'warnings':['SYNTHETIC FIXTURE — NOT NASA DATA'],'bytes_transferred':0,'wavelength':.24})
    return out

def options():return {'reference_bbox':REFERENCE,'event_date':'2026-08-05'}

@pytest.mark.parametrize('pid',list(PRODUCT_FOR))
def test_no_change_null_scene_all_seven(grid,pid):
    product=PRODUCT_FOR[pid];value={'GCOV':.1,'SME2':.2,'GUNW':0.,'GOFF':0.}[product]
    r=process(pid,scene(product,grid,[value]*max(3,MINIMUM[pid])),grid,options())
    assert r['algorithm_version']==('0.4.3' if pid=='P05' else '0.4.2' if pid=='P07' else '0.4.0')
    assert r['report']['findings'] and r['extra']['support']['common_pixels']==np.prod(grid['shape'])
    # A null scene cannot produce fabricated first-to-last change, water gains or motion.
    for key in ['change','range','interval_rate','margin','surface','persistent','patches','moisture_anomaly']:
        if key in r['layers']:
            assert np.nanmax(np.abs(r['layers'][key]['data']))==pytest.approx(0),(pid,key)
    if 'water_gain_km2' in r['metrics']:assert r['metrics']['water_gain_km2']==0

@pytest.mark.parametrize('pid',list(PRODUCT_FOR))
def test_disjoint_coverage_is_missing_not_zero_for_every_tool(grid,pid):
    product=PRODUCT_FOR[pid];n=max(2,MINIMUM[pid]);obs=scene(product,grid,[.2]*n)
    for i,o in enumerate(obs):o['array'][:]=np.nan;o['array'][i,:]=.2
    with pytest.raises(ValueError,match='common valid footprint'):process(pid,obs,grid,options())

@pytest.mark.parametrize('product',['GCOV','GUNW','GOFF','SME2'])
def test_native_rejected_values_never_enter_coarse_average(tmp_path,monkeypatch,product):
    monkeypatch.setattr(science,'DATA',tmp_path);(tmp_path/'raw').mkdir()
    x,y=Transformer.from_crs(4326,6933,always_xy=True).transform(-114.73,36.15)
    xs=x+np.arange(8)*100;ys=y-np.arange(8)*100
    to_geo=Transformer.from_crs(6933,4326,always_xy=True)
    west,south=to_geo.transform(xs[0]-50,ys[-1]-50);east,north=to_geo.transform(xs[-1]+50,ys[0]+50)
    bbox=[west,south,east,north]
    target={'crs':'EPSG:6933','shape':(4,4),'transform':from_origin(xs[0]-50,ys[0]+50,200,200),'resolution':200,'bbox':bbox}
    with h5py.File(tmp_path/'raw'/'native.h5','w') as f:
        root=f'/science/LSAR/{product}/grids'
        if product!='SME2':root+='/frequencyA'
        if product=='GUNW':root+='/unwrappedInterferogram/HH'
        if product=='GOFF':root+='/pixelOffsets/HH/layer1'
        g=f.create_group(root);g['xCoordinates']=xs;g['yCoordinates']=ys;g['projection']=6933
        accepted={'GCOV':.01,'GUNW':1.,'GOFF':2.,'SME2':.2}[product]
        rejected={'GCOV':10.,'GUNW':9.,'GOFF':100.,'SME2':.8}[product]
        data=np.full((8,8),accepted,'float32');data[:,1::2]=rejected
        name={'GCOV':'HHHH','GUNW':'unwrappedPhase','GOFF':'slantRangeOffset','SME2':'soilMoisture'}[product]
        g[name]=data
        q=np.ones((8,8),'uint8');q[:,1::2]=0
        if product=='GCOV':g['mask']=q
        if product=='GUNW':
            g['coherenceMagnitude']=q*.9;g['connectedComponents']=np.ones((8,8),'uint8')
        if product=='GOFF':g['snr']=q*10;g[name].attrs['units']='meters'
        if product=='SME2':
            g['retrievalQualityFlag']=1-q;g['retrievalQualityFlag'].attrs['description']='The least significant bit indicates whether the retrieval is recommended (0 = recommended, 1 = not recommended).'
    item={'id':'native','product':product,'url':''}
    r=science.load_observation(item,bbox,target,{},lambda:False)
    assert np.allclose(r['array'],accepted,atol=1e-6)
    assert r['attrs']['native_quality_before_aggregation'] is True
    assert r['attrs']['native_accepted_fraction']==pytest.approx(.5)
    assert r['reader_version']=='0.3.3'
    with pytest.raises(ValueError,match='survived'):
        science.load_observation(item,bbox,target,{'min_valid_fraction':.75},lambda:False)

@pytest.mark.parametrize('pid',['P06'])
def test_alternating_change_is_not_persistence(grid,pid):
    r=process(pid,scene('GCOV',grid,[.1,1.,.01]),grid,{})
    layer='surface'
    assert not np.any(r['layers'][layer]['data'])
    signed=process(pid,scene('GCOV',grid,[.1,1.,1.]),grid,{})
    assert np.all(signed['layers']['change_direction']['data']==1)


def test_flood_auto_selection_recovery_bounds_and_no_followup(grid):
    r=process('P01',scene('GCOV',grid,[.1,.1,.001,.1]),grid,{})
    assert r['extra']['event_selection']['index']==2
    assert np.all(r['layers']['recovery_lower_days']['data']==0)
    assert np.all(r['layers']['recovery_upper_days']['data']==12)
    assert r['metrics']['observed_dry_again_km2']==pytest.approx(r['metrics']['new_water_candidate_km2'])
    last=process('P01',scene('GCOV',grid,[.1,.1,.001]),grid,{})
    assert np.isnan(last['layers']['recovery']['data']).all()
    assert last['metrics']['unresolved_water_candidate_km2']==pytest.approx(last['metrics']['new_water_candidate_km2'])


def test_flood_explicit_date_needs_baseline_and_uses_earlier_median(grid):
    obs=scene('GCOV',grid,[.1,.001,.001,.1])
    r=process('P01',obs,grid,{'flood_date':'2026-08-13'})
    assert r['extra']['event_selection']['index']==1
    with pytest.raises(ValueError,match='baseline'):process('P01',obs,grid,{'flood_date':'2026-08-01'})


def test_water_gain_loss_conservation_and_threshold_scenarios(grid):
    first=np.full(grid['shape'],.1,'float32');first[:,:3]=.001
    last=np.full(grid['shape'],.1,'float32');last[:,2:6]=.001
    r=process('P01',scene('GCOV',grid,[first,last]),grid,{})
    m=r['metrics']
    assert m['latest_water_candidate_km2']-m['baseline_water_candidate_km2']==pytest.approx(m['water_gain_km2']-m['water_loss_km2'])
    scenarios=r['extra']['threshold_sensitivity']['scenarios']
    for i in range(2):assert [s['area_km2'][i] for s in scenarios]==sorted(s['area_km2'][i] for s in scenarios)



def test_fire_normalization_cancels_shared_brightness_change(grid):
    ref=region_mask(REFERENCE,grid)
    first=np.where(ref,.1,.2)
    r=process('P03',scene('GCOV',grid,[first,first*2,first*3]),grid,options())
    assert r['metrics']['relative_trajectory_db']==pytest.approx(0,abs=1e-5)
    assert np.nanmax(np.abs(r['layers']['relative_change']['data']))<1e-5


@pytest.mark.parametrize('pid',['P04','P05'])
def test_phase_requires_identical_reference_support(grid,pid):
    obs=scene('GUNW',grid,[0.,0.]);ref=region_mask(REFERENCE,grid);coords=np.argwhere(ref)
    for i,o in enumerate(obs):
        o['array'][ref]=np.nan;y,x=coords[i];o['array'][y,x]=0
    with pytest.raises(ValueError,match='same coherent pixels'):process(pid,obs,grid,options())


def test_phase_known_conversion_fixed_reference_and_exact_days(grid):
    ref=region_mask(REFERENCE,grid);phase=np.where(ref,0.,np.pi)
    r=process('P04',scene('GUNW',grid,[phase]),grid,options())
    assert np.nanmedian(r['layers']['range']['data'][~ref])==pytest.approx(-60,abs=1e-5)
    assert np.nanmedian(r['layers']['interval_rate']['data'][~ref])==pytest.approx(-5,abs=1e-5)
    assert r['extra']['reference_diagnostics']['fixed_pixels']==int(ref.sum())


def test_pair_network_detects_broken_closure(grid):
    seq=scene('GUNW',grid,[0,0,0])
    a,b,c='2026-08-01T00:00:00Z','2026-08-13T00:00:00Z','2026-08-25T00:00:00Z'
    for o,(start,end) in zip(seq,[(a,b),(b,c),(a,c)]):o['item'].update(start=start,end=end)
    values=np.stack([np.full(grid['shape'],10.),np.full(grid['shape'],20.),np.full(grid['shape'],35.)])
    n=pair_network(seq,values)
    assert n['connected_components']==1 and n['cycle_rank']==1
    assert n['triangle_closures'][0]['median_closure_mm']==pytest.approx(-5)
    assert n['triangle_closures'][0]['rms_closure_mm']==pytest.approx(5)


def test_quake_shortest_bracketing_pair_is_selected(grid):
    obs=scene('GUNW',grid,[0,0]);obs[0]['item'].update(start='2026-08-01T00:00:00Z',end='2026-08-25T00:00:00Z');obs[1]['item'].update(start='2026-08-03T00:00:00Z',end='2026-08-10T00:00:00Z')
    r=process('P05',obs,grid,options())
    assert r['extra']['selected_interval']['start']==obs[1]['item']['start']


def test_offset_filter_is_optional_and_reports_removed_motion(grid):
    data=np.full(grid['shape'],12.);data[0,0]=1200
    obs=scene('GOFF',grid,[data]);filtered=process('P07',obs,grid,{})
    assert np.isnan(filtered['layers']['value']['data'][0,0])
    assert filtered['extra']['offset_filter_diagnostics'][0]['removed_pixels']==1
    raw=process('P07',obs,grid,{'offset_filter':False})
    assert raw['layers']['value']['data'][0,0]==pytest.approx(100)
    assert raw['extra']['offset_filter_diagnostics'][0]['removed_pixels']==0










def test_wetland_observation_fraction_is_not_elapsed_time(grid):
    r=process('P02',scene('GCOV',grid,[.1,.001,.1]),grid,{})
    area=np.prod(grid['shape'])*grid['resolution']**2/1e6
    assert np.allclose(r['layers']['occupancy']['data'],1/3)
    assert r['metrics']['intermittent_water_candidate_km2']==pytest.approx(area)
    assert r['metrics']['always_water_candidate_km2']==0
    for zone in r['extra']['zones']:assert zone['wet_fraction']==[0,1,0]




def test_volcano_largest_step_has_correct_interval_key(grid):
    r=process('P06',scene('GCOV',grid,[.1,.1,.001,.01]),grid,{})
    assert np.all(r['layers']['largest_step']['data']==2)
    key=next(row for row in r['extra']['step_calendar'] if row['index']==2)
    assert key['start'][:10]=='2026-08-13' and key['end'][:10]=='2026-08-25'




def test_offset_rate_preserves_fractional_elapsed_days(grid):
    obs=scene('GOFF',grid,[25.]);obs[0]['item']['end']='2026-08-13T12:00:00Z'
    r=process('P07',obs,grid,{})
    assert np.nanmedian(r['layers']['value']['data'])==pytest.approx(2)


def test_nonfinite_measurements_never_become_reported_water_or_change(grid):
    obs=scene('GCOV',grid,[.1,.1,.1]);obs[0]['array'][0,0]=np.inf
    r=process('P02',obs,grid,{})
    assert np.isnan(r['layers']['observation_0']['data'][0,0])
    assert r['extra']['support']['common_pixels']==np.prod(grid['shape'])-1


@pytest.mark.parametrize('pid,product,value',[('P07','GOFF',12.)])
def test_summary_coverage_retains_missing_cells_in_its_denominator(grid,pid,product,value):
    obs=scene(product,grid,[value,value,value])
    # Later dates cover the full grid, but only half the grid supports a
    # comparable record. Summarizing a sliced array used to report 100%.
    obs[0]['array'][:,:grid['shape'][1]//2]=np.nan
    common=np.isfinite(np.stack([o['array'] for o in obs])).all(axis=0)
    r=process(pid,obs,grid,{})
    assert r['metrics']['valid_fraction']==pytest.approx(float(common.mean()))
    assert r['metrics']['valid_pixels']==int(common.sum())
    assert r['metrics']['valid_fraction']==r['extra']['support']['common_fraction']
    assert r['metrics']['median']==pytest.approx({'P07':1.}[pid])


@pytest.mark.parametrize('pid',list(PRODUCT_FOR))
def test_all_tools_report_shared_support_without_turning_missing_data_into_full_coverage(grid,pid):
    product=PRODUCT_FOR[pid];value={'GCOV':.1,'SME2':.2,'GUNW':0.,'GOFF':0.}[product]
    obs=scene(product,grid,[value]*max(3,MINIMUM[pid]))
    # Leave the left-side reference intact and remove half of the first
    # observation. Every tool must describe the same reduced comparison basis.
    obs[0]['array'][:,grid['shape'][1]//2:]=np.nan
    common=np.isfinite(np.stack([o['array'] for o in obs])).all(axis=0)
    r=process(pid,obs,grid,options())
    evidence=r['extra']['support']
    assert evidence['common_pixels']==int(common.sum())
    assert evidence['common_fraction']==pytest.approx(float(common.mean()))
    assert evidence['common_area_km2']==pytest.approx(common.sum()*grid['resolution']**2/1e6)
    if 'valid_fraction' in r['metrics']:
        assert r['metrics']['valid_fraction']==pytest.approx(float(common.mean()))


def test_pair_network_matches_exact_instants_across_equivalent_timezone_notation(grid):
    seq=scene('GUNW',grid,[0,0]);seq[0]['item'].update(start='2026-08-01T00:00:00Z',end='2026-08-13T00:00:00Z');seq[1]['item'].update(start='2026-08-13T02:00:00+02:00',end='2026-08-25T00:00:00Z')
    network=pair_network(seq,np.zeros((2,*grid['shape'])))
    assert network['epochs']==3 and network['connected_components']==1


def test_fire_reference_diagnostics_use_declared_median_baseline(grid):
    seq=scene('GCOV',grid,[.1,.4,.4])
    result=process('P03',seq,grid,{**options(),'baseline_count':2})
    assert result['extra']['reference_diagnostics']['latest_change_median_db']==pytest.approx(10*np.log10(2),abs=1e-5)
    assert result['layers']['change']['label']=='Latest minus first backscatter'

@pytest.mark.parametrize('pid',['P04','P05'])
def test_phase_reference_rectangle_survives_outside_analysis_domain(grid,pid):
    """A separate stable patch sets the zero; it is not clipped to the moving slope."""
    from backend.spatial import context_masks
    w,s,e,n=BBOX
    context={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'role':'domain'},'geometry':{'type':'Polygon','coordinates':[[[w+.025,s],[e,s],[e,n],[w+.025,n],[w+.025,s]]]}}]}
    opts={**options(),'spatial_context':context,'phase_network':False}
    obs=scene('GUNW',grid,[0.,0.])
    slope=context_masks(context,grid)[0]['mask'];ref=region_mask(REFERENCE,grid)
    for index,o in enumerate(obs):
        o['array'][:]=99 # must not enter the reference or comparison statistics
        o['array'][ref]=2
        o['array'][slope]=2+(index+1)*.5
    result=process(pid,obs,grid,opts)
    assert result['extra']['reference_diagnostics']['fixed_pixels']==int(ref.sum())
    expected=-.24*.5/(4*np.pi)*1000
    for index in range(2):
        # P04 keeps measured pairs alongside its reconstructed epochs.
        name=f'pair_{index}' if pid in ['P04','P05'] else f'observation_{index}'
        data=result['layers'][name]['data']
        assert np.allclose(data[slope],expected*(index+1),atol=1e-5)
        assert np.isnan(data[~slope]).all()
    series=result['extra']['pair_series'] if pid=='P04' else result['series']
    assert all(row['comparison_pixels']==int(slope.sum()) for row in series)


