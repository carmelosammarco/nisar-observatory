"""Small, bounded map-image compositions from an explicit provider allowlist.

No caller-supplied URLs, Earthdata session, disk cache or offline tile prefetch.
"""
import io
import math
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import requests
from PIL import Image

ROOT = 'https://services.arcgisonline.com/ArcGIS/rest/services/'
CREDIT = 'Esri, HERE, Garmin, © OpenStreetMap contributors, GIS User Community'
STYLES = {
    'satellite': ('World_Imagery', 19, 'Reference/World_Boundaries_and_Places',
                  'Esri, Vantor, Earthstar Geographics, GIS User Community'),
    'light': ('Canvas/World_Light_Gray_Base', 16, 'Canvas/World_Light_Gray_Reference', CREDIT),
    'dark': ('Canvas/World_Dark_Gray_Base', 16, 'Canvas/World_Dark_Gray_Reference', CREDIT),
    'streets': ('World_Street_Map', 19, None, 'Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors, GIS User Community'),
    'plain': (None, 16, 'Canvas/World_Light_Gray_Reference', ''),
}
HALF_WORLD = math.pi * 6378137


class BackgroundUnavailable(Exception):
    pass


@lru_cache(maxsize=128)
def tile(service, z, x, y):
    if service not in {s for v in STYLES.values() for s in (v[0], v[2]) if s}:
        raise ValueError('Unknown background service.')
    response = requests.get(f'{ROOT}{service}/MapServer/tile/{z}/{y}/{x}',
                            timeout=(3, 6), allow_redirects=False,
                            headers={'User-Agent': 'NISAR-Observatory/0.7.2 (single result PNG export)'},
                            stream=True)
    try:
        response.raise_for_status()
        if response.status_code != 200:
            raise BackgroundUnavailable('Unexpected provider response.')
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > 2 * 1024**2:
                raise BackgroundUnavailable('Background tile exceeds the safe image size.')
        with Image.open(io.BytesIO(data)) as image:
            if image.size != (256, 256):
                raise BackgroundUnavailable('Unexpected background tile dimensions.')
            image.verify()
        return bytes(data)
    finally:
        response.close()


def mosaic(service, bounds, size, zoom):
    west, south, east, north = bounds
    scale = 256 * 2**zoom / (2 * HALF_WORLD)
    left, right = (west + HALF_WORLD) * scale, (east + HALF_WORLD) * scale
    top, bottom = (HALF_WORLD - north) * scale, (HALF_WORLD - south) * scale
    x0, x1 = math.floor(left / 256), math.ceil(right / 256) - 1
    y0, y1 = math.floor(top / 256), math.ceil(bottom / 256) - 1
    if (x1-x0+1)*(y1-y0+1) > 36:
        raise BackgroundUnavailable('Background footprint exceeds the export tile budget.')
    canvas = Image.new('RGBA', ((x1-x0+1)*256, (y1-y0+1)*256))
    coords = [(x, y) for y in range(y0, y1+1) for x in range(x0, x1+1)
              if 0 <= x < 2**zoom and 0 <= y < 2**zoom]
    def load(coord):
        x, y = coord
        return x, y, tile(service, zoom, x, y)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for x, y, data in pool.map(load, coords):
            with Image.open(io.BytesIO(data)) as image:
                canvas.paste(image.convert('RGBA'), ((x-x0)*256, (y-y0)*256))
    # Transform with subpixel crop coordinates: preserve the raster's exact Mercator extent.
    return canvas.transform(size, Image.Transform.EXTENT,
                            (left-x0*256, top-y0*256, right-x0*256, bottom-y0*256),
                            resample=Image.Resampling.BICUBIC)


def background(style, labels, bounds, size):
    if style not in STYLES:
        raise ValueError('Unknown map background.')
    if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds):
        raise ValueError('Invalid map extent.')
    west, south, east, north = bounds
    if east <= west or north <= south or max(map(abs, bounds)) > HALF_WORLD * 1.01:
        raise ValueError('Invalid map extent.')
    base, max_zoom, names, credit = STYLES[style]
    spacing = max((east-west)/size[0], (north-south)/size[1])
    zoom = max(0, min(max_zoom, math.floor(math.log2(2*HALF_WORLD/(256*spacing)))))
    base_image = Image.new('RGBA', size, '#262a2d' if style == 'dark' else '#f2f3ef')
    label_image = None
    try:
        if base:
            base_image.alpha_composite(mosaic(base, bounds, size, zoom))
        if labels and names:
            label_image = mosaic(names, bounds, size, min(zoom, 16))
    except (requests.RequestException, OSError, ValueError) as exc:
        raise BackgroundUnavailable('The background or place-name tiles could not be retrieved.') from exc
    credits = credit
    if labels and names and CREDIT not in credits:
        credits = (credits + '; place names: ' + CREDIT).strip('; ')
    return base_image, label_image, {'style': style, 'place_names': labels or style == 'streets',
                                   'attribution': credits, 'tile_zoom': zoom,
                                   'bounds_mercator': list(bounds)}
