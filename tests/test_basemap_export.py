"""No network in unit tests: preserve positioning, legends and numerical files."""
import io
import json
import hashlib

import numpy as np
import pytest
from PIL import Image
from backend import basemap_export as backgrounds
from test_map_image import fixture


def solid(color):
    stream = io.BytesIO()
    Image.new('RGBA', (256, 256), color).save(stream, format='PNG')
    return stream.getvalue()


def test_mosaic_crops_the_exact_mercator_footprint_without_tile_wrap(monkeypatch):
    calls = []
    def tile(service, z, x, y):
        calls.append((z, x, y))
        return solid((x*70, y*70, 80, 255))
    monkeypatch.setattr(backgrounds, 'tile', tile)
    half = backgrounds.HALF_WORLD
    # The left and right halves cross the x=2 tile edge at longitude zero.
    bounds = [-half/8, half/8, half/8, half*3/8]
    image = backgrounds.mosaic('World_Imagery', bounds, (100, 100), 2)
    assert image.getpixel((10, 50))[:2] == (70, 70)
    assert image.getpixel((90, 50))[:2] == (140, 70)
    assert set(calls) == {(2, 1, 1), (2, 2, 1)}


def test_plain_does_not_fetch_tiles_and_labels_use_only_the_known_reference(monkeypatch):
    calls = []
    monkeypatch.setattr(backgrounds, 'mosaic', lambda service, bounds, size, zoom: calls.append(service) or Image.new('RGBA', size))
    bounds = [-1000, 2000, 5000, 6000]
    _, labels, meta = backgrounds.background('plain', False, bounds, (400, 200))
    assert not calls and labels is None and meta['style'] == 'plain'
    _, labels, meta = backgrounds.background('plain', True, bounds, (400, 200))
    assert calls == ['Canvas/World_Light_Gray_Reference'] and labels is not None
    assert meta['place_names'] and 'Esri' in meta['attribution']


def test_streets_uses_esri_and_has_labels_without_a_second_reference(monkeypatch):
    calls = []
    monkeypatch.setattr(backgrounds, 'mosaic', lambda service, bounds, size, zoom: calls.append(service) or Image.new('RGBA', size))
    _, labels, meta = backgrounds.background('streets', False, [-1, -1, 1, 1], (100, 100))
    assert calls == ['World_Street_Map'] and labels is None and meta['place_names']


def test_unknown_sources_and_unbounded_tile_requests_are_rejected():
    with pytest.raises(ValueError):backgrounds.tile('https://untrusted.test', 1, 0, 0)
    with pytest.raises(ValueError):backgrounds.background('unknown', False, [-1, -1, 1, 1], (100, 100))
    with pytest.raises(backgrounds.BackgroundUnavailable):backgrounds.mosaic('World_Imagery', [-1e7, -1e7, 1e7, 1e7], (100, 100), 15)


@pytest.mark.parametrize('pid', [f'P{i:02}' for i in range(1, 8)])
def test_background_png_preserves_every_tools_scale_legend_and_geotiff(monkeypatch, tmp_path, pid):
    client, ident, directory = fixture(monkeypatch, tmp_path, pid)
    monkeypatch.setattr(backgrounds, 'tile', lambda *args: solid('#aabbd0'))
    path = f'/api/map-image/{ident}/{pid}/main?palette=rainbow&mode=custom&low=-12&high=8'
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}
    plain = Image.open(io.BytesIO(client.get(path).content))
    response = client.get(path+'&basemap=light&place_names=true&overlay_opacity=0.55')
    assert response.status_code == 200, response.text
    image = Image.open(io.BytesIO(response.content))
    old = json.loads(plain.info['NISAR_Observatory'])
    meta = json.loads(image.info['NISAR_Observatory'])
    assert meta['scale'] == old['scale'] and meta['palette'] == old['palette']
    assert meta['legend_classes'] == old['legend_classes']
    assert meta['basemap']['style'] == 'light' and meta['basemap']['place_names']
    assert meta['basemap']['radar_overlay_opacity'] == .55
    assert 'Esri' in meta['basemap']['attribution']
    assert np.array_equal(np.array(image)[1213:1247, 80:1280], np.array(plain)[1213:1247, 80:1280])
    assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.tif')}


def test_export_failure_is_explained_and_raster_only_export_still_works(monkeypatch, tmp_path):
    client, ident, _ = fixture(monkeypatch, tmp_path)
    def fail(*args):raise backgrounds.BackgroundUnavailable('network unavailable')
    monkeypatch.setattr(backgrounds, 'background', fail)
    response = client.get(f'/api/map-image/{ident}/P04/main?basemap=light')
    assert response.status_code == 503 and 'turn off Include background' in response.json()['detail']
    assert client.get(f'/api/map-image/{ident}/P04/main').status_code == 200
    assert client.get(f'/api/map-image/{ident}/P04/main?basemap=bad').status_code == 422
    assert client.get(f'/api/map-image/{ident}/P04/main?overlay_opacity=2').status_code == 422


def test_labels_are_composited_above_the_radar_and_opacity_is_applied(monkeypatch, tmp_path):
    client, ident, _ = fixture(monkeypatch, tmp_path)
    def backdrop(style, labels, bounds, size):
        names = Image.new('RGBA', size)
        names.putpixel((size[0]//2, size[1]//2), (255, 0, 255, 255))
        return Image.new('RGBA', size, '#123456'), names, {'attribution':'Synthetic tile test', 'style':style}
    monkeypatch.setattr(backgrounds, 'background', backdrop)
    response = client.get(f'/api/map-image/{ident}/P04/main?basemap=light&overlay_opacity=0')
    image = Image.open(io.BytesIO(response.content))
    colors = image.getcolors(image.width*image.height)
    assert any(color == (18, 52, 86) and count > 1000 for count, color in colors)
    assert any(color == (255, 0, 255) for count, color in colors)
