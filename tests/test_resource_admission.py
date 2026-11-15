"""Metadata resource gates must protect every science-reading entry point."""
import json
import pytest
from fastapi.testclient import TestClient
from backend import app as module


def reference_request(monkeypatch,tmp_path):
    raw=tmp_path/'raw';raw.mkdir();jobs=tmp_path/'jobs';jobs.mkdir()
    items=[{'id':f'{i:032x}','name':f'source-{i}.h5','product':'GUNW','group':'same','start':f'2026-01-{1+i:02}T00:00:00Z','end':f'2026-01-{13+i:02}T00:00:00Z'} for i in range(3)]
    for item in items:(raw/(item['id']+'.h5')).write_bytes(b'route fixture; must not be read')
    monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'JOBS_DIR',jobs);monkeypatch.setattr(module,'JOBS',{});monkeypatch.setattr(module,'CATALOG',{i['id']:i for i in items})
    monkeypatch.setattr(module,'processing_grid',lambda *a:{'shape':(1000,1000),'resolution':100})
    calls=[];monkeypatch.setattr(module,'submit_job',lambda *args:calls.append(args))
    return TestClient(module.app),{'projects':['P04'],'bbox':[-99.4,19.1,-98.8,19.7],'granules':[i['id'] for i in items],'options':{}},calls,jobs


def test_reference_assistant_rejects_over_budget_before_saving_or_queueing(monkeypatch,tmp_path):
    client,body,calls,jobs=reference_request(monkeypatch,tmp_path)
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','1')
    response=client.post('/api/reference-assistant',json=body)
    assert response.status_code==422,response.text
    assert 'memory' in response.json()['detail'].lower()
    assert not calls and not list(jobs.iterdir()) and not module.JOBS


def test_reference_assistant_accepts_a_budgeted_check_without_requiring_a_reference(monkeypatch,tmp_path):
    client,body,calls,jobs=reference_request(monkeypatch,tmp_path)
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','1024')
    response=client.post('/api/reference-assistant',json=body)
    assert response.status_code==200,response.text
    assert len(calls)==1
    report=response.json()['resource_preflight']
    assert report['ready'] and report['estimated_grid_bytes']==416_000_000
    assert report['memory_budget_bytes']==1024**3
    assert 'not a RAM reservation' in report['scope']
    saved=json.loads(next(jobs.glob('*/job.json')).read_text())
    assert saved['resource_preflight']==report
    assert saved['request']['options']=={}


@pytest.mark.parametrize('value',['0','-1','no','1.2'])
def test_bad_memory_configuration_cannot_queue_a_reference_read(monkeypatch,tmp_path,value):
    client,body,calls,jobs=reference_request(monkeypatch,tmp_path)
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB',value)
    response=client.post('/api/reference-assistant',json=body)
    assert response.status_code==422,response.text
    assert 'positive integer' in response.json()['detail']
    assert not calls and not list(jobs.iterdir())


def test_low_destination_space_cannot_queue_reference_reads(monkeypatch,tmp_path):
    from backend import storage_budget
    client,body,calls,jobs=reference_request(monkeypatch,tmp_path)
    original=storage_budget.storage_status
    monkeypatch.setattr(storage_budget,'storage_status',lambda root:{**original(root),'fits':False})
    response=client.post('/api/reference-assistant',json=body)
    assert response.status_code==422 and 'safety reserve' in response.json()['detail']
    assert not calls and not list(jobs.iterdir())


def test_worker_rechecks_budget_before_any_source_read(monkeypatch,tmp_path):
    client,body,calls,jobs=reference_request(monkeypatch,tmp_path)
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','1024')
    response=client.post('/api/reference-assistant',json=body);assert response.status_code==200
    _,job,items,request=calls[0]
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','1')
    reads=[];monkeypatch.setattr(module,'load_observation',lambda *a:reads.append(a))
    module.reference_work(job,items,request)
    assert not reads and job['status']=='needs_input'
    assert job['resource_preflight']['ready'] is False
    assert 'memory' in job['message'].lower()
    assert json.loads((jobs/job['id']/'job.json').read_text())['status']=='needs_input'


def test_direct_assistant_checks_budget_before_numpy_stack(monkeypatch):
    from backend import reference
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','1')
    seq=[{'item':{'id':'one','name':'one','group':'same','product':'GUNW','start':'2026-01-01','end':'2026-01-13'},'path':'/frequencyA/HH/unwrappedPhase'}]
    with pytest.raises(ValueError,match='memory'):
        reference.reference_assistant(seq,{'shape':(1000,1000)},{})


def test_shared_estimate_retains_the_existing_analysis_arithmetic(monkeypatch):
    from backend.resource_budget import assess_resources
    from backend.readiness import assess
    from backend.workflows import Step
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','3072')
    items=[{'id':str(i),'name':str(i),'group':'same','product':'GCOV','start':f'2026-01-{1+i:02}','end':f'2026-01-{1+i:02}'} for i in range(3)]
    grid={'shape':(500,400),'resolution':100};steps=[Step(operation='db'),Step(operation='summary',parameters={'statistic':'mean'})]
    shared=assess_resources(items,grid,steps);full=assess(items,[0,0,1,1],grid,'LAB',{},steps,product='GCOV')
    assert shared['estimated_grid_bytes']==200_000*(3*12+16)*8+shared['estimated_trace_bytes']
    for key in ['estimated_grid_bytes','estimated_trace_bytes','estimated_trace_maps','memory_budget_bytes']:
        assert shared[key]==full[key]


def test_invalid_memory_configuration_stops_startup_before_runtime_ownership(monkeypatch):
    import asyncio
    monkeypatch.setenv('NISAR_MEMORY_BUDGET_MB','invalid')
    monkeypatch.setattr(module,'RuntimeLease',lambda *a:pytest.fail('Invalid configuration must not acquire runtime storage'))
    async def start():
        async with module.lifespan(module.app):pytest.fail('Startup must fail')
    with pytest.raises(ValueError,match='NISAR_MEMORY_BUDGET_MB'):
        asyncio.run(start())
