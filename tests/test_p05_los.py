"""Known-answer P04 checks. Synthetic truth verifies implementation, not accuracy."""
import numpy as np
import pytest
from backend.los import los_trend,phase_group
from backend.processors import process,region_mask
from backend.science import target_grid
from test_processing_maturity import scene,options,BBOX,REFERENCE


def test_connected_chain_units_and_known_rate():
    grid=target_grid(BBOX,200);seq=scene('GUNW',grid,[0,0,0])
    # 12-day pairs, -24 cm/year, with a second pixel having no movement.
    changes=np.zeros((3,2,2),'float32');changes[:,:,0]=-240*12/365.25
    fit,meta=los_trend(seq,changes)
    assert meta['epoch_count']==4 and meta['span_days']==36
    assert meta['closure_check_available'] is False
    assert np.allclose(fit['rate_year'][:,0],-24,atol=1e-5)
    assert np.allclose(fit['rate_month'],fit['rate_year']/12)
    assert np.all(fit['cube_cm'][0]==0)
    assert np.max(fit['pair_residual_cm'])<1e-12


def test_overlap_pair_is_constraint_not_double_count():
    seq=[{'item':{'start':a,'end':b}} for a,b in [('2026-01-01T00:00:00Z','2026-01-13T00:00:00Z'),('2026-01-13T00:00:00Z','2026-01-25T00:00:00Z'),('2026-01-01T00:00:00Z','2026-01-25T00:00:00Z')]]
    fit,meta=los_trend(seq,np.array([-10,-10,-20],dtype='float32')[:,None,None])
    assert meta['redundancy']==1 and meta['closure_check_available']
    assert fit['change_cm'][0,0]==pytest.approx(-2)
    assert fit['rate_year'][0,0]==pytest.approx(-2*365.25/24)


def test_short_and_disconnected_explain_missing_trend():
    grid=target_grid(BBOX,200);seq=scene('GUNW',grid,[0,0,0])
    assert los_trend(seq[:1],np.zeros((1,2,2)))[1]['status']=='pair only'
    result,meta=los_trend([seq[0],seq[2]],np.zeros((2,2,2)))
    assert result is None and 'disconnected' in meta['reason']


def test_common_support_and_temporal_curvature():
    grid=target_grid(BBOX,200);seq=scene('GUNW',grid,[0,0])
    a=np.array([[[10,np.nan],[10,10]],[[20,20],[20,20]]])
    fit,meta=los_trend(seq,a)
    assert np.isnan(fit['rate_year'][0,1]) and np.isnan(fit['cube_cm'][:,0,1]).all()
    assert fit['fit_rms_cm'][1,1]>0
    assert fit['change_cm'][1,1]==3


def test_processor_retains_pair_maps_and_correct_validation_units():
    grid=target_grid(BBOX,200);ref=region_mask(REFERENCE,grid)
    phase=np.where(ref,0,1).astype('float32');seq=scene('GUNW',grid,[phase,phase])
    pair_mm=-.24/(4*np.pi)*1000
    opts={**options(),'reference_observations':[{'date':'2026-08-01','end':'2026-08-13','product':'GUNW','value':pair_mm,'source':'SYNTHETIC matched truth'}]}
    result=process('P04',seq,grid,opts)
    assert result['unit']=='cm/year'
    assert result['extra']['independent_validation']['unit']=='mm'
    assert result['extra']['independent_validation']['rmse']<1e-5
    assert len(result['extra']['los_series'])==3
    assert result['layers']['observation_0']['frame_scope']=='epoch'
    assert result['layers']['pair_0']['unit']=='mm'
    assert np.allclose(result['layers']['los_rate_month']['data'],result['layers']['los_rate_year']['data']/12)
    assert np.allclose(result['layers']['los_rate_year']['data'][ref],0)
    assert result['layers']['los_rate_year']['data'][~ref].mean()<0


@pytest.mark.parametrize('other,allowed',[('113_D_079_4000_SH_X05010',True),('113_D_079_4000_SH_P05010',False),('114_D_079_4000_SH_X05010',False)])
def test_revision_join_is_narrow_and_opt_in(other,allowed):
    first='113_D_079_4000_SH_X05009'
    assert phase_group(first)!=phase_group(other)
    assert (phase_group(first,True)==phase_group(other,True)) is allowed


def test_processor_revision_consent_and_other_tools_stay_strict():
    grid=target_grid(BBOX,200);seq=scene('GUNW',grid,[0,0])
    seq[0]['item']['group']='113_D_079_4000_SH_X05009';seq[1]['item']['group']='113_D_079_4000_SH_X05010'
    with pytest.raises(ValueError,match='group'):process('P04',seq,grid,options())
    result=process('P04',seq,grid,{**options(),'phase_allow_mixed_revisions':True})
    assert len(result['extra']['processing_revisions'])==2
    assert any('artificial' in n or 'mimic' in n for n in result['notes'])
    with pytest.raises(ValueError,match='group'):process('P05',seq,grid,{**options(),'phase_allow_mixed_revisions':True})


def test_api_mixed_revision_only_for_p04(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from backend import app as module
    (tmp_path/'raw').mkdir();(tmp_path/'jobs').mkdir()
    monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS_DIR',tmp_path/'jobs');monkeypatch.setattr(module,'JOBS',{})
    items={f'g{i}':{'id':f'g{i}','product':'GUNW','group':f'113_D_079_4000_SH_X{5009+i:05d}'} for i in range(2)}
    for index,item in enumerate(items.values()):item.update(start=f'2026-01-{1+12*index:02}T00:00:00Z',end=f'2026-01-{13+12*index:02}T00:00:00Z')
    for key in items:(tmp_path/'raw'/f'{key}.h5').write_bytes(b'synthetic route test only')
    monkeypatch.setattr(module,'CATALOG',items)
    class Pool:
        def submit(self,*args):pass
    monkeypatch.setattr(module,'POOL',Pool());client=TestClient(module.app)
    request={'bbox':BBOX,'granules':list(items),'projects':['P04'],'options':{'reference_bbox':BBOX}}
    assert client.post('/api/run',json=request).status_code==422
    request['options']['phase_allow_mixed_revisions']=True
    assert client.post('/api/run',json=request).status_code==200
    monkeypatch.setattr(module,'JOBS',{})
    request['projects']=['P04','P05']
    assert client.post('/api/run',json=request).status_code==422
