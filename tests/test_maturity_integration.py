"""Product-grid isolation and paginated catalog regression checks."""
import json
import numpy as np
import pytest
from backend import app as module,catalog
from backend.science import target_grid
from test_processing_maturity import scene,BBOX

@pytest.mark.parametrize('projects,expected',[(['P01'],{'GCOV':100}),(['P01','P07'],{'GCOV':100,'GOFF':100})])
def test_unused_products_never_coarsen_or_trigger_science_reads(monkeypatch,tmp_path,projects,expected):
    monkeypatch.setattr(module,'JOBS_DIR',tmp_path);monkeypatch.setattr(module,'JOBS',{})
    source_grid=target_grid(BBOX,100)
    items=[o['item'] for product in ['GCOV','GOFF'] for o in scene(product,source_grid,[.2,.3])]
    seen=[]
    def load(item,bbox,grid,options,cancel):
        seen.append((item['product'],grid['resolution']))
        result=scene(item['product'],grid,[.2])[0];result['item']=item
        return result
    monkeypatch.setattr(module,'load_observation',load)
    job=module.newjob('analysis')
    module.work(job,items,module.RunQuery(bbox=BBOX,granules=[i['id'] for i in items],projects=projects,options={'resolution':100}))
    assert job['status']=='completed',job
    assert {p:r for p,r in seen}==expected
    for pid in projects:
        result=json.loads((tmp_path/job['id']/pid/'result.json').read_text())
        assert result['grid']['resolution_m']==expected['GOFF' if pid=='P07' else 'GCOV']
        assert result['report']['findings'] and result['algorithm_version']==('0.4.2' if pid=='P07' else '0.4.0')


def test_cmr_search_fetches_following_pages_and_labels_release(monkeypatch):
    calls=[]
    def get(url,params,timeout):
        page=params['page_num'];calls.append(page);start=(page-1)*params['page_size']
        entries=[]
        for i in range(start,min(start+params['page_size'],205)):
            entries.append({'id':f'G{i}','producer_granule_id':f'NISAR_L2_PR_GCOV_023_101_A_023_2005_DHDH_A_20260621T044315_20260621T044332_P05023_N_P_J_{i:03}.h5','links':[{'href':'https://datapool.asf.alaska.edu/a.h5'}]})
        class Response:
            headers={'CMR-Hits':'205'}
            url='https://cmr.earthdata.nasa.gov/search/granules.json'
            def raise_for_status(self):pass
            def json(self):return {'feed':{'entry':entries}}
        return Response()
    monkeypatch.setattr(catalog.requests,'get',get)
    result=catalog.search('GCOV',[0,0,1,1],'2026-01-01','2026-10-17')
    assert calls==[1,2]
    assert len(result['items'])==205 and not result['truncated']
    assert result['collection']=='NISAR_L2_GCOV_PROVISIONAL_V1'


def test_new_science_options_are_validated():
    for options in [{'min_valid_fraction':0},{'soil_change_threshold':-1},{'offset_filter':'yes'},{'offset_min_cutoff_m':0}]:
        with pytest.raises(ValueError):module.AnalysisOptions.model_validate(options)


def test_unused_remote_or_incompatible_product_does_not_block_local_tool(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    (tmp_path/'raw').mkdir();(tmp_path/'jobs').mkdir()
    monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS_DIR',tmp_path/'jobs');monkeypatch.setattr(module,'JOBS',{})
    monkeypatch.setattr(module.AUTH,'session',None)
    items={'g0':{'id':'g0','product':'GCOV','group':'one'},'g1':{'id':'g1','product':'GCOV','group':'one'},'s0':{'id':'s0','product':'SME2','group':'different-a'},'s1':{'id':'s1','product':'SME2','group':'different-b'}}
    for index,ident in enumerate(['g0','g1']):items[ident].update(start=f'2026-01-{1+12*index:02}T00:00:00Z',end=f'2026-01-{1+12*index:02}T00:01:00Z')
    for ident in ['g0','g1']:(tmp_path/'raw'/f'{ident}.h5').write_bytes(b'not-read-in-this-route-test')
    monkeypatch.setattr(module,'CATALOG',items)
    submitted=[]
    class Pool:
        def submit(self,fn,job,chosen,body):submitted.extend(chosen)
    monkeypatch.setattr(module,'POOL',Pool())
    response=TestClient(module.app).post('/api/run',json={'bbox':BBOX,'granules':list(items),'projects':['P01']})
    assert response.status_code==200,response.text
    assert {i['id'] for i in submitted}=={'g0','g1'}


@pytest.mark.parametrize('pid',[f'P{i:02}' for i in range(1,8)])
def test_every_tool_blocks_when_selected_product_source_fails(monkeypatch,tmp_path,pid):
    from backend.engines import PRODUCT_FOR
    from test_processing_maturity import options
    product=PRODUCT_FOR[pid];grid=target_grid(BBOX,100)
    seq=scene(product,grid,[.2,.2,.2,.2]);items=[o['item'] for o in seq]
    monkeypatch.setattr(module,'JOBS_DIR',tmp_path);monkeypatch.setattr(module,'JOBS',{})
    def load(item,*args):
        if item['id']=='0':raise ValueError('Synthetic source failure')
        return next(o for o in seq if o['item']['id']==item['id'])
    monkeypatch.setattr(module,'load_observation',load)
    job=module.newjob('analysis');module.work(job,items,module.RunQuery(bbox=BBOX,granules=[i['id'] for i in items],projects=[pid],options=options()))
    assert job['status']=='needs_input'
    assert job['results'][pid]['status']=='needs_input'
    assert 'no selected date or coverage is silently omitted' in job['results'][pid]['message']
    assert job['source_errors'][0]['source']=='0'


def test_saved_display_recipe_is_separate_from_science_options_and_validated():
    valid={'palette':'rainbow','mode':'custom','layer':'los_rate_year','unit':'cm/year','low':-30,'high':30}
    request=module.RunQuery(bbox=BBOX,granules=['one'],projects=['P04'],display=valid)
    assert request.display.low==-30 and 'palette' not in request.options
    for change in [{'high':-30},{'low':None},{'high':float('inf')},{'palette':'invalid'},{'layer':'../../secret'}]:
        with pytest.raises(ValueError):module.DisplaySettings.model_validate({**valid,**change})
