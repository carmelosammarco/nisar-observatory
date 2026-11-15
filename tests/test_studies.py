"""Study storytelling must stay distinct from measurements and validation."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import app as service
from backend.studies import compare_results, compare_settings, load_result, matching_example, report_html, report_processing_record, study_summary
from backend.study_stories import STORIES,story


def result():
 return {'project':'P01','title':'Flood comparison','grid':{'bbox':[32.9,-24.65,33.14,-24.43],'resolution_m':100},
  'processing_options':{'water_threshold':-17},'sources':[{'name':'NISAR_source','start':'2026-01-05T00:00:00Z','end':'2026-01-17T00:00:00Z','group':'one','quality_paths':[]}],
  'layers':[{'id':'event','label':'New water candidates','kind':'binary','unit':'class','classes':{'0':'No new candidate','1':'New candidate'},'spatial_scope':'study domain'}],
  'extra':{},'report':{'findings':['2 cells meet the declared rule.']},'metrics':{'new_water_candidate_km2':.02},'notes':['Not confirmed flooding.']}


def raster(directory,data,transform=None):
 directory.mkdir(parents=True,exist_ok=True)
 with rasterio.open(directory/'event.tif','w',driver='GTiff',width=2,height=2,count=1,dtype='float32',nodata=np.nan,crs='EPSG:6933',transform=transform or Affine(100,0,0,0,-100,200)) as f:
  f.write(np.array(data,'float32'),1)


@pytest.mark.parametrize('method',list(STORIES))
def test_seven_stories_explain_hypotheses_alternatives_confirmation_and_use(method):
 s=story(method)
 for field in ('question','audience','context','driver','confirm','use','exercise'):assert len(s[field])>25
 assert len(s['alternatives'])>=2
 s['alternatives'].clear();assert story(method)['alternatives']


def test_summary_uses_actual_findings_not_case_numbers_and_keeps_time():
 r=result();s=study_summary(r)
 assert s['findings']==r['report']['findings']
 assert s['record']['source_count']==1 and s['record']['end'].startswith('2026-01-17')
 assert s['method']=='P01' and 'independent' in s['validation']
 assert matching_example(r) is None
 assert 'NASA' not in s['interpretation']['driver'] and 'Chókwè' not in s['interpretation']['context']


def test_numeric_comparison_counts_common_support_without_treating_missing_as_zero(tmp_path):
 a,b=tmp_path/'a',tmp_path/'b';raster(a,[[0,1],[1,np.nan]]);raster(b,[[1,1],[np.nan,0]])
 report=compare_results(result(),result(),a,b);row=report['layers'][0]
 assert row['available'] and row['common_cells']==2 and row['changed_cells']==1
 assert row['changed_percent']==50 and row['before_valid_cells']==3 and row['after_valid_cells']==3
 assert row['quantity_type']=='category agreement' and 'mean_change' not in row


def test_continuous_comparison_is_after_minus_before_and_windowed(tmp_path):
 a,b=tmp_path/'a',tmp_path/'b';raster(a,[[1,2],[3,4]]);raster(b,[[2,0],[3,8]])
 r=result();r['layers'][0].update(unit='dB',kind='continuous');r['layers'][0].pop('classes')
 row=compare_results(r,r,a,b)['layers'][0]
 assert row['mean_change']==pytest.approx(.75) and row['mean_absolute_change']==pytest.approx(1.75)
 assert row['maximum_absolute_change']==4


@pytest.mark.parametrize('change,reason',[
 ('grid','grids differ'),('unit','Quantity'),('classes','Category meanings'),('source','same source'),('area','same source'),('method','same source')])
def test_unlike_maps_have_a_reason_instead_of_misleading_difference(tmp_path,change,reason):
 a,b=tmp_path/'a',tmp_path/'b';raster(a,[[0,1],[1,0]]);raster(b,[[1,1],[1,0]],Affine(200,0,0,0,-200,400) if change=='grid' else None)
 left=result();right=copy.deepcopy(left)
 if change=='unit':right['layers'][0]['unit']='cm'
 if change=='classes':right['layers'][0]['classes']['1']='Different condition'
 if change=='source':right['sources'][0]['name']='other'
 if change=='area':right['grid']['bbox']=[0,0,1,1]
 if change=='method':right['project']='P02'
 row=compare_results(left,right,a,b)['layers'][0]
 assert not row['available'] and reason in row['reason']


def test_settings_keep_geometry_changes_visible_but_not_display_name_changes(tmp_path):
 a,b=tmp_path/'a',tmp_path/'b';raster(a,[[0,1],[1,0]]);raster(b,[[0,1],[1,0]])
 left=result();right=copy.deepcopy(left);right['processing_options'].update(water_threshold=-18,spatial_context={'coordinates':list(range(1000))})
 right['display_preferences']={'palette':'rainbow'}
 report=compare_results(left,right,a,b)
 assert {c['setting'] for c in report['settings']}=={'water_threshold','spatial_context'}
 assert 'SHA-256' in next(c['after'] for c in report['settings'] if c['setting']=='spatial_context')


def test_comparison_does_not_report_implicit_defaults_as_changed_science():
 left=result();right=copy.deepcopy(left)
 right['processing_options'].update(baseline_count=1,water_tracking_enabled=True,water_unknown_db=1,water_threshold=-18)
 assert [row['setting'] for row in compare_settings(left,right)]==['water_threshold']


def test_report_keeps_real_ordered_operations_and_sampled_observations():
 r=result();r['extra']['workflow']={'steps':[{'operation':'water_rule','parameters':{'threshold_db':-18}},{'operation':'flood_history','parameters':{}}]}
 r['series']=[{'date':'2026-01-05','water_candidate_km2':25.16},{'date':'2026-01-17','water_candidate_km2':100.65}]
 document=report_processing_record(r)
 assert document.index('water rule')<document.index('flood history')
 for text in ['-18','25.16','100.65','Missing times are unobserved','water candidate km2']:assert text in document


def test_report_is_self_contained_escaped_and_labels_hypotheses():
 r=result();r['title']='<script>alert(1)</script>';r['sources'][0]['name']='<img src=x onerror=alert(1)>'
 document=report_html(r,study_summary(r),b'pngbytes',r['layers'][0],'a'*32)
 assert '<script>' not in document and '<img src=x' not in document
 assert '&lt;script&gt;' in document and 'data:image/png;base64,' in document
 for phrase in ['What this run found','What could explain','Other explanations','What would confirm','Processing settings','Source observations','not contain satellite input files']:assert phrase in document


def test_study_routes_export_and_compare_actual_saved_maps(tmp_path,monkeypatch):
 monkeypatch.setattr(service,'JOBS_DIR',tmp_path)
 for ident in ('a'*32,'b'*32):
  directory=tmp_path/ident/'P01';raster(directory,[[0,1],[1,0]]);(directory/'result.json').write_text(json.dumps(result()))
 client=TestClient(service.app)
 assert client.get('/api/studies/'+'a'*32+'/P01').json()['method']=='P01'
 comparison=client.post('/api/studies/compare',json={'before':'a'*32,'before_product':'P01','after':'b'*32,'after_product':'P01'})
 assert comparison.status_code==200 and comparison.json()['layers'][0]['changed_cells']==0
 export=client.post('/api/studies/'+'a'*32+'/P01/report',json={'layer':'event','unit':'class','palette':'standard','mode':'shared'})
 assert export.status_code==200 and 'data:image/png;base64,' in export.text
 assert 'attachment;' in export.headers['content-disposition'] and "default-src 'none'" in export.headers['content-security-policy']
 invalid=client.post('/api/studies/'+'a'*32+'/P01/report',json={'layer':'event','unit':'cm'})
 assert invalid.status_code==422


def test_result_resolution_rejects_paths_and_symlinks(tmp_path):
 for ident,pid in [('..','P01'),('a'*32,'../P01'),('a'*32,'P08')]:
  with pytest.raises(HTTPException):load_result(tmp_path,ident,pid)
 outside=tmp_path/'outside';outside.mkdir();target=tmp_path/('a'*32);target.mkdir();(target/'P01').symlink_to(outside)
 with pytest.raises(HTTPException):load_result(tmp_path,'a'*32,'P01')
