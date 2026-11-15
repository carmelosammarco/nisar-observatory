"""Known-value tests for dual-polarised sigma-zero candidates, not accuracy."""
from datetime import datetime, timedelta, timezone
import h5py
import numpy as np
import pytest
from pyproj import Transformer
from rasterio.transform import from_origin
from backend.water import read_dual_sigma
from backend.science import cache_path
from backend.processors import process
from backend.validation import water_calibration


@pytest.fixture
def native(tmp_path):
    path = tmp_path / 'dual.h5'
    x, y = Transformer.from_crs(4326, 6933, always_xy=True).transform(-73.1, 41.18)
    hh = np.tile(np.array([[1., 2.], [3., 4.]], 'float32'), (2, 2))
    factor = np.tile(np.array([[.1, .2], [.3, .4]], 'float32'), (2, 2))
    with h5py.File(path, 'w') as f:
        g = f.create_group('/science/LSAR/GCOV/grids/frequencyA')
        g['xCoordinates'] = x + np.arange(4) * 10
        g['yCoordinates'] = y - np.arange(4) * 10
        g['projection'] = 6933
        g['HHHH'] = hh
        g['HVHV'] = hh / 10
        g['rtcGammaToSigmaFactor'] = factor
        g['mask'] = np.ones((4, 4), 'uint8')
        g['inputDataExceptionMask'] = np.zeros((4, 4), 'uint8')
    inverse = Transformer.from_crs(6933, 4326, always_xy=True)
    west, south = inverse.transform(x - 5, y - 35)
    east, north = inverse.transform(x + 35, y + 5)
    target = {'crs': 'EPSG:6933', 'shape': (2, 2), 'transform': from_origin(x - 5, y + 5, 20, 20), 'resolution': 20, 'bbox': [west, south, east, north]}
    return path, target, hh, factor


def test_native_conversion_precedes_averaging(native):
    path, grid, hh, factor = native
    with h5py.File(path) as f:
        aux, metadata, paths = read_dual_sigma(f, '/science/LSAR/GCOV/grids/frequencyA', grid['bbox'], grid)
    expected = (hh[:2, :2] * factor[:2, :2]).mean()
    assert expected != pytest.approx(hh[:2, :2].mean() * factor[:2, :2].mean())
    np.testing.assert_allclose(aux['water_hh_sigma_power'], expected)
    np.testing.assert_allclose(aux['water_hv_sigma_power'], expected / 10)
    assert metadata['joint_native_valid_samples'] == 16 and any('rtcGamma' in p for p in paths)


@pytest.mark.parametrize('channel', ['HHHH', 'HVHV'])
def test_main_cross_channel_keeps_physical_cross_to_co_ratio(native, monkeypatch, channel):
    from contextlib import contextmanager
    from backend import science
    from backend.app import AnalysisOptions
    path, grid, _, _ = native
    @contextmanager
    def local(*args):
        with h5py.File(path) as f:
            yield f, None
    monkeypatch.setattr(science, 'open_science', local)
    options = AnalysisOptions(channel=channel, compare_polarizations=True).model_dump()
    result = science._load_observation({'id':'test','product':'GCOV'}, grid['bbox'], grid, options, lambda:False)
    assert result['path'].endswith('/'+channel)
    np.testing.assert_allclose(result['aux']['cross_copol_ratio_db'], -10, atol=1e-5)
    np.testing.assert_allclose(result['aux']['cross_power'], .25, atol=1e-6)
    assert result['additional_paths']['copol_power'].endswith('/HHHH')


@pytest.mark.parametrize('layer,value', [('HVHV', -1), ('rtcGammaToSigmaFactor', np.nan), ('mask', 0), ('inputDataExceptionMask', 2)])
def test_both_channels_use_the_same_native_quality_support(native, layer, value):
    path, grid, hh, factor = native
    with h5py.File(path, 'r+') as f:
        g = f['/science/LSAR/GCOV/grids/frequencyA'];g[layer][0, 0] = value
        aux, metadata, _ = read_dual_sigma(f, g.name, grid['bbox'], grid)
        assert aux['water_joint_accepted_fraction'][0, 0] == pytest.approx(.75)
        expected = np.mean((hh[:2, :2] * factor[:2, :2]).ravel()[1:])
        assert aux['water_hh_sigma_power'][0, 0] == pytest.approx(expected)
        assert aux['water_hv_sigma_power'][0, 0] == pytest.approx(expected / 10)
        stricter, _, _ = read_dual_sigma(f, g.name, grid['bbox'], grid, .9)
        assert np.isnan(stricter['water_hh_sigma_power'][0, 0]) and np.isnan(stricter['water_hv_sigma_power'][0, 0])


@pytest.mark.parametrize('missing', ['HVHV', 'rtcGammaToSigmaFactor', 'mask'])
def test_required_native_layers_never_fall_back(native, missing):
    path, grid, _, _ = native
    with h5py.File(path, 'r+') as f:
        del f['/science/LSAR/GCOV/grids/frequencyA/' + missing]
        with pytest.raises(ValueError, match='requires'):
            read_dual_sigma(f, '/science/LSAR/GCOV/grids/frequencyA', grid['bbox'], grid)


def scenes(grid):
    out = []
    # 2x2: both wet, HV vetoes, HH vetoes, near HH but HV clearly dry.
    hh = np.array([[-16., -16.], [-10., -14.5]], 'float32')
    hv = np.array([[-25., -20.], [-25., -15.]], 'float32')
    for i in range(3):
        h = hh.copy();v = hv.copy()
        if i == 1:h[1, 0] = -17
        start = datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(days=12 * i)
        out.append({'array': np.full((2, 2), .001, 'float32'), 'aux': {'water_hh_sigma_power': 10 ** (h / 10), 'water_hv_sigma_power': 10 ** (v / 10)}, 'item': {'id': str(i), 'name': 'SYNTHETIC DUAL TEST', 'product': 'GCOV', 'start': start.isoformat(), 'end': (start + timedelta(seconds=30)).isoformat(), 'group': 'one'}, 'path': '/science/LSAR/GCOV/grids/frequencyA/HHHH', 'attrs': {}, 'quality_paths': [], 'warnings': [], 'bytes_transferred': 0})
    return out


def test_joint_rule_occupancy_ambiguity_and_sensitivity(native):
    _, grid, _, _ = native
    r = process('P02', scenes(grid), grid, {'water_method': 'hh_hv'})
    np.testing.assert_allclose(r['layers']['occupancy']['data'], [[1, 0], [1 / 3, 0]])
    assert r['layers']['water_state']['data'][1, 1] == 0  # HV veto, not ambiguous.
    assert r['metrics']['always_water_candidate_km2'] == pytest.approx(.0004)
    assert r['metrics']['intermittent_water_candidate_km2'] == pytest.approx(.0004)
    assert r['algorithm_version'] == '0.5.0'
    assert r['extra']['grid_sensitivity'][0]['area_km2'] == pytest.approx([.0004, .0008, .0004])
    assert r['extra']['threshold_sensitivity']['scenarios'][2]['hh_threshold_db'] == -14
    assert 'sigma-zero' in ' '.join(r['report']['findings'])
    assert r['extra']['water_validation']['test_cells'] == 0


def test_missing_converted_observation_stops_p02_but_not_single_channel(native):
    _, grid, _, _ = native;obs = scenes(grid);obs[1]['aux'] = {}
    with pytest.raises(ValueError, match='missing'):
        process('P02', obs, grid, {'water_method': 'hh_hv'})
    legacy = process('P02', obs, grid, {'water_method': 'single'})
    assert np.all(legacy['layers']['occupancy']['data'] == 1)
    obs[1]['attrs']['water_method_error'] = 'Required HV is absent'
    with pytest.raises(ValueError, match='Required HV'):
        process('P02', obs, grid, {'water_method': 'hh_hv'})


def test_dual_cache_is_separate_but_threshold_edits_reuse_native_arrays(native):
    _, grid, _, _ = native;item = {'id': 'synthetic', 'product': 'GCOV'}
    old = cache_path(item, grid['bbox'], grid, {})
    assert old == cache_path(item, grid['bbox'], grid, {'water_method': 'single'})
    dual = cache_path(item, grid['bbox'], grid, {'water_method': 'hh_hv'})
    assert dual != old
    assert dual == cache_path(item, grid['bbox'], grid, {'water_method': 'hh_hv', 'water_hh_threshold': -12})


def test_held_out_labels_evaluate_fixed_states_without_threshold_fitting():
    mask = np.ones((2, 2), bool);states = np.array([[[True, False], [False, True]]])
    labels = [{'mask': mask, 'role': 'water', 'properties': {'date': '2026-08-01', 'split': 'test', 'source': 'Independent sensor labels'}}]
    threshold, report = water_calibration(np.full((1, 2, 2), -10.), ['2026-08-01'], labels, -14, fixed_states=states)
    assert threshold == -14 and report['true_positive'] == 2 and report['false_negative'] == 2
    assert report['calibration_cells'] == 0 and report['recall'] == .5
