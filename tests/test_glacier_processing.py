"""Known-value offset layer, shared-component and rate-unit checks."""
import numpy as np
import pytest
from backend.science import select_path,cache_path,target_grid
from backend.processors import process
from test_science import observations


def test_explicit_offset_layer_never_falls_back():
 base='/science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH/'
 paths=[base+'layer3/slantRangeOffset',base+'layer1/slantRangeOffset']
 assert select_path(paths,'GOFF').endswith('/layer1/slantRangeOffset')
 assert select_path(paths,'GOFF',offset_layer='layer3').endswith('/layer3/slantRangeOffset')
 with pytest.raises(ValueError,match='layer2.*unavailable'):select_path(paths,'GOFF',offset_layer='layer2')


def test_cache_distinguishes_delivered_layers():
 grid=target_grid([0,0,.01,.01],100);item={'id':'test','product':'GOFF'}
 assert cache_path(item,grid['bbox'],grid,{'offset_layer':'layer1'})!=cache_path(item,grid['bbox'],grid,{'offset_layer':'layer3'})


def test_exact_interval_and_annualized_component_norm():
 grid=target_grid([0,0,.01,.01],100);obs=observations('GOFF',grid,1)
 obs[0]['array'][:]=36;obs[0]['aux']={'other_offset':np.full(grid['shape'],48.,dtype='float32')}
 daily=process('P07',obs,grid,{'offset_filter':False})
 yearly=process('P07',obs,grid,{'offset_filter':False,'offset_layer':'layer2','offset_rate_unit':'m/year'})
 assert np.nanmedian(daily['layers']['radar_magnitude']['data'])==pytest.approx(5.)
 assert np.nanmedian(yearly['layers']['value']['data'])==pytest.approx(3*365.25)
 assert np.nanmedian(yearly['layers']['radar_magnitude']['data'])==pytest.approx(5*365.25)
 assert yearly['unit']=='m/year' and yearly['extra']['offset_measurement']['layer']=='layer2'
 assert yearly['series'][0]['median']==pytest.approx(3*365.25)


def test_other_component_outlier_cannot_enter_filtered_norm():
 grid=target_grid([0,0,.01,.01],100);obs=observations('GOFF',grid,1)
 obs[0]['array'][:]=.1;other=np.full(grid['shape'],.1,dtype='float32');other[2,2]=100
 obs[0]['aux']={'other_offset':other};r=process('P07',obs,grid,{})
 assert np.isnan(r['layers']['radar_magnitude']['data'][2,2])
 assert r['layers']['radar_magnitude_0']['data'][2,2]>8
 assert r['extra']['offset_measurement']['other_component_diagnostics'][0]['removed_pixels']==1


def test_both_component_biases_are_removed_before_norm():
 grid=target_grid([0,0,.01,.01],100);obs=observations('GOFF',grid,1)
 obs[0]['array'][:]=3;obs[0]['aux']={'other_offset':np.full(grid['shape'],4.,dtype='float32')}
 fc={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'name':'Synthetic stable terrain','role':'stable','source':'Synthetic fixture'},'geometry':{'type':'Polygon','coordinates':[[[0,0],[.01,0],[.01,.01],[0,.01],[0,0]]]}}]}
 r=process('P07',obs,grid,{'offset_stable_bias':True,'spatial_context':fc})
 assert np.nanmax(r['layers']['radar_magnitude']['data'])==pytest.approx(0.)
 assert np.nanmax(r['layers']['value']['data'])==pytest.approx(0.)


def test_api_rejects_unavailable_layer_names_and_ambiguous_units():
 from backend.app import AnalysisOptions
 from pydantic import ValidationError
 with pytest.raises(ValidationError):AnalysisOptions(offset_layer='layer4')
 with pytest.raises(ValidationError):AnalysisOptions(offset_rate_unit='m/s')
 assert AnalysisOptions(offset_layer='layer3',offset_rate_unit='m/year').offset_layer=='layer3'
