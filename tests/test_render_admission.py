"""Concurrent render work must be bounded without blocking health/control APIs."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import json,threading
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.render_admission import RenderAdmission
from backend.execution import ProcessingCancelled


def test_one_owner_nested_calls_and_fail_fast_competitors():
    gate=RenderAdmission();entered=threading.Event();release=threading.Event()
    @gate
    def inner():return 'nested'
    @gate
    def outer():
        entered.set();assert release.wait(3)
        return inner()
    with ThreadPoolExecutor(max_workers=12) as pool:
        active=pool.submit(outer)
        try:
            assert entered.wait(2)
            def attempt():
                with pytest.raises(HTTPException) as error:inner()
                assert error.value.status_code==429
                assert error.value.headers=={'Retry-After':'1','X-NISAR-Render-Busy':'1'}
            futures=[pool.submit(attempt) for _ in range(20)]
            for future in futures:future.result(timeout=2)
        finally:release.set()
        assert active.result(timeout=3)=='nested'
    assert inner()=='nested'


@pytest.mark.parametrize('error',[ValueError('fixture error'),ProcessingCancelled('fixture cancellation')])
def test_exception_or_cancellation_releases_the_slot_and_context(error):
    gate=RenderAdmission()
    @gate
    def fail():raise error
    @gate
    def healthy():return 42
    with pytest.raises(type(error)):fail()
    with ThreadPoolExecutor(max_workers=1) as pool:assert pool.submit(healthy).result(timeout=2)==42
    assert healthy()==42


def test_copied_context_cannot_bypass_admission_on_another_thread():
    gate=RenderAdmission()
    @gate
    def child():return 'unsafe'
    @gate
    def parent():
        ctx=copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(HTTPException) as error:pool.submit(ctx.run,child).result(timeout=2)
        assert error.value.status_code==429
    parent()
    assert child()=='unsafe'


def test_http_preview_and_png_share_admission_but_health_is_available(monkeypatch,tmp_path):
    from backend import app as service,exports,map_image
    ident='a'*32;directory=tmp_path/ident/'P01';directory.mkdir(parents=True)
    layer={'id':'event','unit':'class','kind':'binary','label':'Test event','raster':'event.tif'}
    (directory/'result.json').write_text(json.dumps({'layers':[layer]}))
    with rasterio.open(directory/'event.tif','w',driver='GTiff',height=3,width=3,count=1,dtype='float32',crs='EPSG:6933',transform=from_origin(0,300,100,100),nodata=np.nan) as ds:ds.write(np.ones((3,3),dtype='float32'),1)
    monkeypatch.setattr(service,'JOBS_DIR',tmp_path)
    entered=threading.Event();release=threading.Event();original=exports.colorize
    def blocking(*args,**kwargs):
        entered.set();assert release.wait(3)
        return original(*args,**kwargs)
    monkeypatch.setattr(exports,'colorize',blocking)
    preview=f'/api/visualization/{ident}/P01/event';png=f'/api/map-image/{ident}/P01/event'
    client=TestClient(service.app)
    with ThreadPoolExecutor(max_workers=1) as pool:
        active=pool.submit(client.get,preview)
        try:
            assert entered.wait(2)
            for url in [preview,png]:
                response=client.get(url);assert response.status_code==429
                assert response.headers['x-nisar-render-busy']=='1' and response.headers['retry-after']=='1'
                assert 'Another map' in response.json()['detail']
            assert client.get('/api/health').status_code==200
        finally:release.set()
        assert active.result(timeout=3).status_code==200
    # A PNG owns the outer slot and may call the decorated resolver internally.
    monkeypatch.setattr(exports,'colorize',original)
    monkeypatch.setattr(map_image,'render_map',lambda *args,**kwargs:b'png-fixture')
    response=client.get(png)
    assert response.status_code==200 and response.content==b'png-fixture'
    assert client.get(preview).status_code==200
