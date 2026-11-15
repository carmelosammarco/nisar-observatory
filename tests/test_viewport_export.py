import hashlib
import io
import json

import numpy as np
import pytest
from PIL import Image
from test_map_image import fixture


def metadata(response):
    assert response.status_code == 200, response.text
    return json.loads(Image.open(io.BytesIO(response.content)).info['NISAR_Observatory'])


@pytest.mark.parametrize('pid', [f'P{i:02}' for i in range(1, 8)])
def test_zoomed_out_view_preserves_scale_and_numeric_raster_and_adds_surroundings(monkeypatch, tmp_path, pid):
    client, ident, directory = fixture(monkeypatch, tmp_path, pid)
    url = f'/api/map-image/{ident}/{pid}/main'
    params = {'mode': 'custom', 'palette': 'rainbow', 'low': -12, 'high': 8}
    full = metadata(client.get(url, params=params))
    west, south, east, north = full['bounds_mercator']
    dx, dy = (east-west)/2, (north-south)/2
    view = [west-dx, south-dy, east+dx, north+dy]
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}
    response = client.get(url, params={**params, 'extent': 'view', 'view_bbox': ','.join(map(str, view))})
    cropped = metadata(response)
    assert cropped['bounds_mercator'] == view
    assert cropped['result_bounds_mercator'] == full['bounds_mercator']
    assert cropped['export_extent'] == 'current_view' and full['export_extent'] == 'full_result'
    assert cropped['scale'] == full['scale'] and cropped['palette'] == full['palette']
    assert cropped['reference_outline'] is False
    assert .20 < cropped['visible_radar_fraction'] < .30
    assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}


def test_zoomed_in_and_empty_views_do_not_change_limits_or_invent_measurements(monkeypatch, tmp_path):
    client, ident, _ = fixture(monkeypatch, tmp_path)
    url = f'/api/map-image/{ident}/P04/main'
    full = metadata(client.get(url))
    west, south, east, north = full['bounds_mercator']
    dx, dy = east-west, north-south
    zoom = [west+dx*.25, south+dy*.25, east-dx*.25, north-dy*.25]
    close = metadata(client.get(url, params={'extent':'view', 'view_bbox':','.join(map(str,zoom))}))
    assert close['scale'] == full['scale'] and close['visible_radar_fraction'] > .99
    outside = [west+dx*2, south, east+dx*2, north]
    empty = metadata(client.get(url, params={'extent':'view', 'view_bbox':','.join(map(str,outside))}))
    assert empty['scale'] == full['scale'] and empty['visible_radar_fraction'] == 0


@pytest.mark.parametrize('params', [
    {'extent':'view'}, {'extent':'view','view_bbox':'1,2,3'},
    {'extent':'view','view_bbox':'1,2,NaN,4'},
    {'extent':'view','view_bbox':'1,2,0,4'},
    {'extent':'view','view_bbox':'-3e8,2,3e8,4'},
    {'extent':'view','view_bbox':'bad'},
    {'extent':'result','view_bbox':'1,2,3,4'}, {'extent':'unknown'}
])
def test_invalid_camera_bounds_are_rejected(monkeypatch, tmp_path, params):
    client, ident, _ = fixture(monkeypatch, tmp_path)
    assert client.get(f'/api/map-image/{ident}/P04/main', params=params).status_code == 422


def test_automatic_reference_decoration_is_removed_even_with_reference_raster(monkeypatch, tmp_path):
    client, ident, directory = fixture(monkeypatch, tmp_path)
    meta = metadata(client.get(f'/api/map-image/{ident}/P04/main'))
    assert (directory/'reference_support.tif').exists()
    assert meta['reference_outline'] is False
