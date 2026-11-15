"""Known physical quantities, not matching numeric units alone, define a check."""
import numpy as np
import pytest
from backend.analysis_options import RegionalReference
from backend.validation import regional_reference_spec,regional_validation,continuous_validation


def reference(**values):
    return {'date':'2026-08-01','end':'2026-08-13','value':10.,'source':'SYNTHETIC regional truth','quantity':'horizontal_speed','unit':'m/year',**values}


@pytest.mark.parametrize('field,value',[('unit',None),('quantity',None),('end','2026-08-01'),('source','  ')])
def test_schema_rejects_half_specified_quantity_invalid_interval_and_empty_citation(field,value):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):RegionalReference.model_validate(reference(**{field:value}))


def test_horizontal_and_component_references_select_different_measured_series():
    radar=[{'date':'2026-08-01','end':'2026-08-13','median':-3.}]
    horizontal=[{**radar[0],'median':5.}]
    options={'offset_solution':'horizontal','offset_rate_unit':'m/year'}
    speed=regional_validation(radar,[reference(value=5.)],'GOFF',options,horizontal_series=horizontal)
    component=regional_validation(radar,[reference(quantity='radar_component_rate',component='slantRangeOffset',value=-3.)],'GOFF',options,horizontal_series=horizontal)
    assert speed['rmse']==0 and speed['quantity']=='horizontal_speed'
    assert speed['unbiased_rmse'] is None and 'one record' in speed['metric_notes'][0]
    assert component['rmse']==0 and component['quantity']=='radar_component_rate'
    assert speed['matched_pairs'][0]['observed']==5.
    assert component['matched_pairs'][0]['observed']==-3.


@pytest.mark.parametrize('source_unit,value,expected_unit,expected',[
    ('cm',2.,'mm',20.),('m',.02,'mm',20.),('mm',20.,'mm',20.),
    ('cm/day',2.,'m/day',.02),('mm/year',20.,'m/year',.02),
    ('m/year',365.25,'m/day',1.),('m/day',1.,'m/year',365.25)])
def test_explicit_unit_conversion_is_dimension_preserving(source_unit,value,expected_unit,expected):
    phase=expected_unit=='mm'
    record=reference(quantity='los_displacement' if phase else 'horizontal_speed',unit=source_unit,value=value)
    spec=regional_reference_spec([record],'GUNW' if phase else 'GOFF',{'offset_solution':'horizontal','offset_rate_unit':expected_unit})
    converted=spec['references'][0]
    assert converted['value']==pytest.approx(expected)
    assert converted['unit']==expected_unit
    assert converted['input_value']==value and converted['input_unit']==source_unit


@pytest.mark.parametrize('record,product,options,message',[
    (reference(unit='m'),'GOFF',{'offset_solution':'horizontal'},'same physical quantity'),
    (reference(quantity='los_displacement',unit='m/year'),'GUNW',{},'same physical quantity'),
    (reference(quantity='los_displacement',unit='mm'),'GOFF',{},'not available'),
    (reference(),'GOFF',{'offset_solution':'radar'},'horizontal solution'),
    (reference(value=-1),'GOFF',{'offset_solution':'horizontal'},'nonnegative'),
    (reference(end=None),'GOFF',{'offset_solution':'horizontal'},'both date and end'),
    (reference(quantity='radar_component_rate'),'GOFF',{},'must name'),
    (reference(quantity='radar_component_rate',component='alongTrackOffset'),'GOFF',{},'selected slantRangeOffset'),
    (reference(component='slantRangeOffset'),'GOFF',{'offset_solution':'horizontal'},'applies only'),
])
def test_incompatible_quantities_units_intervals_and_components_are_rejected(record,product,options,message):
    with pytest.raises(ValueError,match=message):regional_reference_spec([record],product,options)


def test_legacy_phase_and_radar_records_retain_disclosed_meaning_but_horizontal_is_ambiguous():
    old={'date':'2026-08-01','value':-2.,'source':'Old synthetic fixture'}
    phase=regional_reference_spec([old],'GUNW',{})
    radar=regional_reference_spec([old],'GOFF',{'component':'alongTrackOffset','offset_rate_unit':'m/year'})
    assert phase['unit']=='mm' and phase['quantity']=='los_displacement' and phase['assumptions']
    assert radar['component']=='alongTrackOffset' and radar['unit']=='m/year'
    with pytest.raises(ValueError,match='must state quantity and unit'):regional_reference_spec([old],'GOFF',{'offset_solution':'horizontal'})


def test_duplicates_mixed_quantities_and_nonfinite_values_do_not_inflate_comparison():
    with pytest.raises(ValueError,match='Duplicate'):regional_reference_spec([reference(),reference()],'GOFF',{'offset_solution':'horizontal'})
    with pytest.raises(ValueError,match='one physical quantity'):regional_reference_spec([reference(),reference(quantity='radar_component_rate',component='slantRangeOffset')],'GOFF',{'offset_solution':'horizontal'})
    with pytest.raises(ValueError,match='finite'):regional_reference_spec([reference(value=np.inf)],'GOFF',{'offset_solution':'horizontal'})


def test_calendar_matching_uses_utc_and_missing_summaries_are_explicit():
    series=[{'date':'2026-08-02T01:00:00+02:00','end':'2026-08-14T01:00:00+02:00','median':4.},
            {'date':'2026-08-13','end':'2026-08-25','median':np.nan}]
    references=[reference(value=4.),reference(date='2026-08-13',end='2026-08-25',value=8.)]
    result=regional_validation(series,references,'GOFF',{'offset_solution':'horizontal','offset_rate_unit':'m/year'},horizontal_series=series)
    assert result['samples']==1 and result['excluded_samples']==1 and result['requested_samples']==2
    assert result['status'].startswith('partially') and result['rmse']==0
    assert result['excluded_references'][0]['date']=='2026-08-13'
    assert result['matched_pairs'][0]['end']==series[0]['end']
    with pytest.raises(ValueError,match='exactly one'):continuous_validation(series,[reference(end='2026-09-01')],'m/year')


def test_no_usable_comparison_is_not_reported_as_zero_error():
    series=[{'date':'2026-08-01','end':'2026-08-13','median':None}]
    result=regional_validation(series,[reference()],'GOFF',{'offset_solution':'horizontal','offset_rate_unit':'m/year'},horizontal_series=series)
    assert result['status'].startswith('not evaluated') and result['unit']=='m/year'
    assert result['excluded_samples']==1 and result['requested_samples']==1
    assert 'rmse' not in result and 'bias' not in result


@pytest.mark.parametrize('magnitude',[1e200,1e-200])
def test_error_metrics_do_not_overflow_or_round_tiny_nonzero_errors_to_zero(magnitude):
    series=[{'date':'2026-08-01','median':magnitude},{'date':'2026-08-13','median':-magnitude}]
    references=[{'date':row['date'],'value':0.,'source':'SYNTHETIC arithmetic check'} for row in series]
    result=continuous_validation(series,references,'m/day')
    assert result['bias']==0 and result['rmse']==magnitude and result['unbiased_rmse']==magnitude
    assert result['mae']==magnitude


def test_actual_horizontal_processor_checks_speed_or_component_without_changing_maps():
    from backend.processors import process
    from backend.science import target_grid
    from test_science import observations
    from test_horizontal_glacier import geometry,FIELDS
    grid=target_grid([0,0,.01,.01],100);obs=observations('GOFF',grid,1);g=geometry(grid['shape'])
    days=12.;east=-100.;north=-20.
    obs[0]['array']=(-g[FIELDS[0]]*east-g[FIELDS[1]]*north)*days/365.25
    obs[0]['aux']={'other_offset':(g[FIELDS[2]]*east+g[FIELDS[3]]*north)*days/365.25,**{'geometry_'+k:v for k,v in g.items()}}
    options={'offset_solution':'horizontal','offset_filter':False,'offset_rate_unit':'m/year'}
    baseline=process('P07',obs,grid,options)
    start=obs[0]['item']['start'][:10];end=obs[0]['item']['end'][:10]
    records=[reference(date=start,end=end,value=np.hypot(east,north)),reference(date=start,end=end,quantity='radar_component_rate',component='slantRangeOffset',value=-np.sin(np.deg2rad(40))*100)]
    for record in records:
        result=process('P07',obs,grid,{**options,'reference_observations':[record]})
        validation=result['extra']['independent_validation']
        assert validation['rmse']<1e-4
        assert validation['quantity']==record['quantity']
        assert validation['support']['common_pixels']>0
        assert result['metrics']==baseline['metrics'] and result['series']==baseline['series']
        for name in baseline['layers']:np.testing.assert_array_equal(result['layers'][name]['data'],baseline['layers'][name]['data'])


def test_metadata_readiness_rejects_ambiguous_or_unmatched_references_without_reading_science(monkeypatch):
    from backend import science
    from backend.readiness import assess
    from test_processing_maturity import scene
    grid=science.target_grid([0,0,.01,.01],100);items=[o['item'] for o in scene('GOFF',grid,[1])]
    monkeypatch.setattr(science,'load_observation',lambda *args,**kwargs:pytest.fail('Readiness must not read native science'))
    options={'offset_solution':'horizontal','reference_observations':[{'date':'2026-08-01','end':'2026-08-13','value':5.,'source':'synthetic'}]}
    result=assess(items,[0,0,.01,.01],grid,'P07',options)
    assert not result['ready'] and any('must state quantity' in e for e in result['errors'])
    options['reference_observations']=[reference(date='2026-08-01',end='2026-08-13')]
    result=assess(items,[0,0,.01,.01],grid,'P07',options)
    assert result['ready'] and any(c['label']=='Regional reference quantity' for c in result['checks'])
    options['reference_observations']=[reference(date='2026-08-02',end='2026-08-14')]
    result=assess(items,[0,0,.01,.01],grid,'P07',options)
    assert not result['ready'] and any('exactly one selected UTC' in e for e in result['errors'])
    gcov_items=[o['item'] for o in scene('GCOV',grid,[1,1])]
    result=assess(gcov_items,[0,0,.01,.01],grid,'P01',{'reference_observations':[reference()]})
    assert not result['ready'] and any('GCOV water checks' in e for e in result['errors'])


def test_live_route_rejects_incompatible_quantity_before_queue_or_native_read(monkeypatch,tmp_path):
    from backend import app as service
    from fastapi.testclient import TestClient
    raw=tmp_path/'raw';raw.mkdir();(raw/'test.h5').write_bytes(b'Invalid HDF5: must never be read by metadata validation')
    item={'id':'test','product':'GOFF','group':'same','start':'2026-08-01T00:00:00Z','end':'2026-08-13T00:00:00Z'}
    monkeypatch.setattr(service,'DATA',tmp_path);monkeypatch.setattr(service,'CATALOG',{'test':item});monkeypatch.setattr(service,'JOBS',{})
    monkeypatch.setattr(service,'submit_job',lambda *args:pytest.fail('Invalid reference must never queue processing'))
    monkeypatch.setattr(service,'load_observation',lambda *args:pytest.fail('Invalid reference must never read science'))
    body={'bbox':[0,0,.01,.01],'granules':['test'],'projects':['P07'],'options':{'offset_solution':'horizontal','reference_observations':[reference(unit='m')]}}
    response=TestClient(service.app).post('/api/run',json=body)
    assert response.status_code==422 and 'same physical quantity' in response.json()['detail']
    assert service.JOBS=={} and (raw/'test.h5').read_bytes().startswith(b'Invalid HDF5')
    body['options']['reference_observations']=[reference(unit='m/s',source='Do not echo this private input')]
    response=TestClient(service.app).post('/api/run',json=body)
    assert response.status_code==422 and 'Regional reference fields' in response.json()['detail']
    assert 'Do not echo this private input' not in response.text and service.JOBS=={}
