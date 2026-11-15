"""Known-answer earthquake interval tests. Synthetic truth is not NASA validation."""
import json
import numpy as np
import pytest
from backend.processors import process,region_mask
from backend.quake import brackets_event,validate_mosaic_groups
from backend.science import target_grid
from test_processing_maturity import scene,options,BBOX,REFERENCE


def test_single_pair_cm_sign_and_original_mm_preserved():
    grid=target_grid(BBOX,200);ref=region_mask(REFERENCE,grid)
    phase=np.where(ref,1.25,1.25+np.pi)
    r=process('P05',scene('GUNW',grid,[phase]),grid,options())
    assert r['unit']=='cm' and r['algorithm_version']=='0.4.3'
    assert np.nanmedian(r['layers']['event_displacement_cm']['data'][~ref])==pytest.approx(-6,abs=1e-5)
    assert np.nanmedian(r['layers']['pair_0']['data'][~ref])==pytest.approx(-60,abs=1e-4)
    assert r['layers']['observation_0']['unit']=='cm'
    assert np.allclose(r['layers']['event_displacement_cm']['data'],r['layers']['range']['data']/10,equal_nan=True)
    assert r['series'][0]['median_cm']==pytest.approx(r['series'][0]['median_mm']/10)
    assert r['extra']['event_measurement']['positive']=='toward the satellite'


def test_real_filename_windows_override_catalog_endpoints():
    item={'start':'2026-06-13T00:00:00Z','end':'2026-06-30T00:00:00Z','name':'NISAR_20260613T100000_20260613T100040_20260625T100000_20260625T100040'}
    assert brackets_event(item,{'event_timestamp':'2026-06-24T22:05:04Z'})
    assert not brackets_event(item,{'event_timestamp':'2026-06-13T10:00:20Z'})
    assert not brackets_event(item,{'event_timestamp':'2026-06-25T10:00:10Z'})
    assert not brackets_event(item,{'event_date':'2026-06-25'})
    assert not brackets_event(item,{'event_timestamp':'2026-06-25T10:00:00Z'})


def pair_groups(grid):
    ref=region_mask(REFERENCE,grid);seq=scene('GUNW',grid,[np.where(ref,0,np.pi),np.where(ref,0,-np.pi)])
    for i,o in enumerate(seq):
        o['item'].update(start='2026-08-01T00:00:00Z',end='2026-08-13T00:00:00Z',group=f'{i+1:03}_A_007_4000_SH_P05023')
        o['aux']={'coherence':np.full(grid['shape'],.7+i*.2)}
    return seq


def test_mosaic_keeps_union_when_global_common_support_is_empty():
    grid=target_grid(BBOX,200);seq=pair_groups(grid);half=grid['shape'][0]//2
    seq[0]['array'][half:]=np.nan;seq[1]['array'][:half]=np.nan
    r=process('P05',seq,grid,{**options(),'quake_mosaic':True})
    a=r['layers']['event_displacement_cm']['data'];ref=region_mask(REFERENCE,grid)
    assert np.isfinite(a).all()
    assert np.allclose(a[:half][~ref[:half]],-6)
    assert np.allclose(a[half:][~ref[half:]],6)
    assert r['extra']['support']['common_pixels']==0
    assert r['extra']['support']['mosaic_pixels']==a.size
    assert np.isnan(r['layers']['event_overlap_spread']['data']).all()
    assert len(r['sources'])==2
    assert all(x['reference_pixels']>0 for x in r['extra']['event_mosaic']['groups'])


def test_overlap_uses_highest_coherence_no_averaging_and_exposes_difference():
    grid=target_grid(BBOX,200);seq=pair_groups(grid);r=process('P05',seq,grid,{**options(),'quake_mosaic':True})
    ref=region_mask(REFERENCE,grid)
    assert np.allclose(r['layers']['event_displacement_cm']['data'][~ref],6)
    assert np.all(r['layers']['event_source']['data']==2)
    assert np.allclose(r['layers']['event_overlap_spread']['data'][~ref],12)
    assert np.all(r['layers']['event_coverage']['data']==2)
    assert set(r['extra']['event_mosaic']['source_key'])=={'1','2'}
    assert r['extra']['event_mosaic']['overlap_difference_cm']['p90']==pytest.approx(12)
    assert len([k for k in r['layers'] if k.startswith('observation_')])==2


@pytest.mark.parametrize('bad',['002_D_007_4000_SH_P05023','002_A_007_4000_SH_X05023','002_A_007_4000_SH_P05024','002_A_007_2000_SH_P05023','synthetic'])
def test_mosaic_rejects_opposite_direction_release_mode_or_unknown_group(bad):
    with pytest.raises(ValueError):validate_mosaic_groups([{'group':'001_A_007_4000_SH_P05023'},{'group':bad}])


def test_missing_reference_in_one_group_fails_explicitly():
    grid=target_grid(BBOX,200);seq=pair_groups(grid);seq[1]['array'][region_mask(REFERENCE,grid)]=np.nan
    with pytest.raises(ValueError,match='002_A_007.*same coherent pixels'):
        process('P05',seq,grid,{**options(),'quake_mosaic':True})


def test_mosaic_requires_event_bracketing_in_every_group():
    grid=target_grid(BBOX,200);seq=pair_groups(grid);seq[1]['item']['start']='2026-08-06T00:00:00Z'
    with pytest.raises(ValueError,match='no pair brackets'):
        process('P05',seq,grid,{**options(),'quake_mosaic':True})


def test_preset_covers_published_landmarks_and_sets_correct_pairs():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    p=next(x for x in json.loads((root/'docs/mission.json').read_text())['presets'] if x['id']=='P05')
    w,s,e,n=p['bbox']
    for lon,lat in [(-68.745,10.34),(-68.2,10.49),(-67.99,10.16),(-66.9,10.48),(-66.94,10.60)]:
        assert w<lon<e and s<lat<n
    assert p['selection']=='publication_extent'
    assert p['search_start']=='2026-06-13' and p['search_end']=='2026-06-30'
    assert p['event_date']=='2026-06-24'


def test_p05_palette_range_and_png_preserve_numbers(monkeypatch,tmp_path):
    import hashlib,io
    import rasterio
    from rasterio.transform import from_origin
    from fastapi.testclient import TestClient
    from PIL import Image
    from backend import app as module
    monkeypatch.setattr(module,'JOBS_DIR',tmp_path)
    ident='c'*32;d=tmp_path/ident/'P05';d.mkdir(parents=True)
    layers=[]
    for key,unit,kind,mult in [('event_displacement_cm','cm','diverging',1),('pair_0','mm','diverging',10),('reference_support','class','binary',0)]:
        a=np.linspace(-60,60,100,dtype='float32').reshape(10,10)*mult
        with rasterio.open(d/(key+'.tif'),'w',driver='GTiff',height=10,width=10,count=1,dtype='float32',crs=6933,transform=from_origin(0,1000,100,100),nodata=np.nan) as ds:ds.write(a,1)
        layers.append({'id':key,'label':key,'unit':unit,'kind':kind})
    result={'project':'P05','layers':layers,'sources':[],'grid':{'resolution_m':100},'extra':{}}
    (d/'result.json').write_text(json.dumps(result))
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.glob('*.tif')}
    c=TestClient(module.app)
    for key,limit in [('event_displacement_cm',50),('pair_0',500)]:
        r=c.get(f'/api/visualization/{ident}/P05/{key}?mode=quake&palette=quake');assert r.status_code==200,r.text
        v=r.json();assert (v['min'],v['max'])==(-limit,limit);assert v['palette_name']=='quake'
        assert v['palette'][3]==[255,255,255] and v['clipped_percent']>0
    q=c.get(f'/api/visualization/{ident}/P05/reference_support?mode=quake&palette=quake').json()
    assert q['mode']=='shared' and q['palette_name']=='standard'
    r=c.get(f'/api/map-image/{ident}/P05/event_displacement_cm?mode=quake&palette=quake');assert r.status_code==200,r.text
    meta=json.loads(Image.open(io.BytesIO(r.content)).info['NISAR_Observatory'])
    assert meta['scale']['palette_name']=='quake' and meta['scale']['max']==50
    assert 'not a damage map' in meta['interpretation']
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.glob('*.tif')}


def test_event_source_legend_is_a_source_key_not_patch_severity():
    from backend.map_image import legend_spec
    result={'extra':{'event_mosaic':{'source_key':{'1':'162_A_007','2':'061_A_007'}}}}
    assert legend_spec({'id':'event_source','unit':'source index','kind':'categorical'},{'class_values':[1,2]},result)==[(1,'162_A_007'),(2,'061_A_007')]


def test_api_event_mosaic_is_scoped_to_p05_and_directions_stay_separate(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from backend import app as module
    (tmp_path/'raw').mkdir();(tmp_path/'jobs').mkdir()
    monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS_DIR',tmp_path/'jobs');monkeypatch.setattr(module,'JOBS',{})
    items={f'g{i}':{'id':f'g{i}','product':'GUNW','group':f'{i+1:03}_A_007_4000_SH_P05023'} for i in range(2)}
    for item in items.values():item.update(start='2026-08-01T00:00:00Z',end='2026-08-13T00:00:00Z')
    for key in items:(tmp_path/'raw'/f'{key}.h5').write_bytes(b'synthetic route-only fixture')
    monkeypatch.setattr(module,'CATALOG',items)
    class Pool:
        def submit(self,*args):pass
    monkeypatch.setattr(module,'POOL',Pool());client=TestClient(module.app)
    request={'bbox':BBOX,'granules':list(items),'projects':['P05'],'options':{'quake_mosaic':True,'reference_bbox':BBOX,'event_date':'2026-08-05'}}
    assert client.post('/api/run',json=request).status_code==200
    monkeypatch.setattr(module,'JOBS',{})
    for projects in [['P04'],['P04','P05']]:
        request['projects']=projects
        assert client.post('/api/run',json=request).status_code==422
    request['projects']=['P05'];items['g1']['group']='002_D_007_4000_SH_P05023'
    assert client.post('/api/run',json=request).status_code==422
    items['g1']['group']='002_A_007_4000_SH_P05023';request['options']={}
    assert client.post('/api/run',json=request).status_code==422


def test_single_group_mosaic_option_cannot_bypass_duplicate_pair_guard():
    grid=target_grid(BBOX,200);seq=scene('GUNW',grid,[0,0]);seq[1]['item'].update(start=seq[0]['item']['start'],end=seq[0]['item']['end'])
    with pytest.raises(ValueError,match='Duplicate'):
        process('P05',seq,grid,{**options(),'quake_mosaic':True})


def test_shared_physical_reference_preferred_over_independent_origins():
    grid=target_grid(BBOX,200);seq=pair_groups(grid)
    # Both groups have valid reference ground, but only their central row overlap
    # is shared. A broad independent median would use different terrain samples.
    h=grid['shape'][0];seq[0]['array'][3*h//4:]=np.nan;seq[1]['array'][:h//4]=np.nan
    ref=region_mask(REFERENCE,grid);shared=ref&np.isfinite(seq[0]['array'])&np.isfinite(seq[1]['array'])
    r=process('P05',seq,grid,{**options(),'quake_mosaic':True})
    assert r['extra']['event_mosaic']['reference_mode']=='shared physical cells'
    assert r['extra']['event_mosaic']['shared_reference_pixels']==int(shared.sum())
    for group in r['extra']['event_mosaic']['groups']:
        actual=r['layers'][f"group_{group['index']}_reference_support"]['data']==1
        assert np.array_equal(actual,shared)


@pytest.mark.parametrize('valid_phase',[0.,2.])
def test_native_packed_mask_rejects_invalid_samples_without_masking_real_zero_phase(tmp_path,monkeypatch,valid_phase):
    import h5py
    from backend import science
    from pyproj import Transformer
    from rasterio.transform import from_origin
    monkeypatch.setattr(science,'DATA',tmp_path);(tmp_path/'raw').mkdir()
    x,y=Transformer.from_crs(4326,6933,always_xy=True).transform(-114.73,36.15)
    xs=x+np.arange(8)*100;ys=y-np.arange(8)*100;conv=Transformer.from_crs(6933,4326,always_xy=True)
    west,south=conv.transform(xs[0]-50,ys[-1]-50);east,north=conv.transform(xs[-1]+50,ys[0]+50);bbox=[west,south,east,north]
    grid={'crs':'EPSG:6933','shape':(4,4),'transform':from_origin(xs[0]-50,ys[0]+50,200,200),'resolution':200,'bbox':bbox}
    with h5py.File(tmp_path/'raw/masked.h5','w') as f:
        g=f.create_group('/science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram');g['xCoordinates']=xs;g['yCoordinates']=ys;g['projection']=6933
        a=np.full((8,8),valid_phase,'float32');a[:,1::2]=99;g['HH/unwrappedPhase']=a;g['HH/coherenceMagnitude']=np.full((8,8),.9,'float32');g['HH/connectedComponents']=np.ones((8,8),'uint16')
        mask=np.full((8,8),(1<<25)|11,'uint32');mask[:,1::2]=(1<<25)|10
        g['mask']=mask;g['mask'].attrs['description']='Bits 0-7: water and reference/secondary subswath encoding; zero subswath means invalid'
    item={'id':'masked','product':'GUNW','url':''}
    o=science.load_observation(item,bbox,grid,{},lambda:False)
    assert np.allclose(o['array'],valid_phase)
    assert o['attrs']['native_accepted_fraction']==pytest.approx(.5)
    assert np.allclose(o['aux']['rejected_invalid_subswath'],.5)
    assert o['reader_version']=='0.3.3'
    cached=science.load_observation(item,bbox,grid,{},lambda:False)
    assert cached['cache_hit'] and np.array_equal(o['array'],cached['array'])


def test_generic_palettes_work_for_other_continuous_tools(monkeypatch,tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    from fastapi.testclient import TestClient
    from backend import app as module
    monkeypatch.setattr(module,'JOBS_DIR',tmp_path);ident='d'*32;d=tmp_path/ident/'P07';d.mkdir(parents=True)
    with rasterio.open(d/'change.tif','w',driver='GTiff',height=10,width=10,count=1,dtype='float32',crs=6933,transform=from_origin(0,1000,100,100),nodata=np.nan) as ds:ds.write(np.linspace(-.1,.1,100,dtype='float32').reshape(10,10),1)
    (d/'result.json').write_text(json.dumps({'layers':[{'id':'change','unit':'m³/m³','kind':'diverging'}]}))
    c=TestClient(module.app)
    for palette,n in [('rainbow',256),('diverging',7)]:
        r=c.get(f'/api/visualization/{ident}/P07/change?palette={palette}&mode=custom&low=-0.1&high=0.1');assert r.status_code==200,r.text
        assert r.json()['palette_name']==palette and len(r.json()['palette'])==n
