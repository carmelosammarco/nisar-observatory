"""Check every saved map of the latest recorded example replays, without rerunning them.

Run after verify_examples.py has written each case's verification.json.
Requires the local app; never downloads satellite inputs or changes recipes.
"""
import base64
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
API = 'http://127.0.0.1:8765'


def check_layer(task):
    job, tool, layer = task
    ident = layer['id']
    directory = ROOT / 'data/jobs' / job / tool
    with rasterio.open(directory / (ident + '.tif')) as ds:
        count = int(np.isfinite(ds.read(1)).sum())
    response = requests.get(f'{API}/api/visualization/{job}/{tool}/{ident}', timeout=180)
    response.raise_for_status()
    view = response.json()
    if count:
        assert view.get('available') is not False, (tool, ident, view)
        assert view['valid_pixels'] == count, (tool, ident)
        assert np.isfinite([view['min'], view['max']]).all()
        with Image.open(io.BytesIO(base64.b64decode(view['image'].split(',', 1)[1]))) as image:
            image.verify()
    else:
        assert view.get('available') is False and view.get('reason'), (tool, ident, view)
    return {'layer': ident, 'valid_pixels': count,
            'available': bool(count), 'reason': view.get('reason')}


def main():
    from sys import path
    path.insert(0, str(ROOT))
    from backend.examples import CASES
    for case in CASES:
        folder = ROOT / 'Examples' / case
        record = json.loads((folder / 'verification.json').read_text())
        job, tool = record['job_id'], record['tool']
        result = json.loads((ROOT / 'data/jobs' / job / tool / 'result.json').read_text())
        with ThreadPoolExecutor(max_workers=2) as pool:
            checks = list(pool.map(check_layer, [(job, tool, layer) for layer in result['layers']]))
        record['all_map_checks'] = checks
        record['all_saved_rasters_and_previews_checked'] = True
        (folder / 'verification.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({'example': case, 'maps_checked': len(checks),
                          'unavailable_explained': sum(not c['available'] for c in checks)}), flush=True)


if __name__ == '__main__':
    main()
