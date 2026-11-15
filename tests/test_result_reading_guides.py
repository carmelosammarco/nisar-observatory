"""Interpretation must follow the actual method/mode and travel with exports."""
import json
from pathlib import Path
import pytest
from backend.result_contracts import reading_guide
from backend.examples import CASES,definition

@pytest.mark.parametrize('pid',[f'P{i:02}' for i in range(1,8)])
def test_every_tool_has_shared_reading_fields_without_certifying_a_run(pid):
 extra={'P03':{'fire_method':{'id':'combined'}},'P04':{'los_series':[{}]},'P07':{'horizontal_velocity':{'unit':'m/year'}}}.get(pid,{})
 guide=reading_guide({'project':pid,'extra':extra})
 for key in ['measurement','colours','checks','cannot','validation']:assert len(guide[key])>40
 assert 'Neither establishes independent environmental accuracy' in guide['validation']
 assert guide['method']==pid and 'variants' not in guide

@pytest.mark.parametrize('pid,extra,phrase',[
 ('P03',{},'relative'),('P03',{'fire_method':{'id':'combined'}},'combined HH/HV'),
 ('P04',{},'pair interval'),('P04',{'los_series':[{}]},'fitted rate'),
 ('P07',{},'radar-component'),('P07',{'horizontal_velocity':{}},'radar-component'),
 ('P07',{'horizontal_velocity':{'unit':'m/year'}},'zero vertical'),
])
def test_guides_do_not_describe_a_different_processing_mode(pid,extra,phrase):
 assert phrase in reading_guide({'project':pid,'extra':extra})['measurement']


def test_editable_method_keeps_correct_quantity_and_flags_added_operations():
 r={'project':'LAB','extra':{'workflow_method':'P03','fire_method':{'id':'combined'},'scientific_blocks':{'source_smoothing':20}}}
 g=reading_guide(r);assert g['method']=='P03' and 'new experiment' in g['modified_workflow']
 generic=reading_guide({'project':'LAB','extra':{}});assert generic['method']=='LAB' and 'declared editable steps' in generic['measurement']


def test_all_case_assessments_explain_alignment_and_keep_processing_identity():
 for case in CASES:
  m=definition(case);r=m['comparison_review']
  for key in ['agrees','differs','unverified']:assert len(r[key])>=2
  for key in ['quantity_reference','quantity_ours','support','next_check','conclusion','reproducibility']:assert len(r[key])>25
  assert r['review_date']=='2026-10-23'
  assert any(row[0]=='Measurement alignment' for row in m['comparison'])
  assert any(word in ' '.join(r['unverified']).lower() for word in ['independent','held-out'])
  assert m['sources'] and m['request']['display'] and m['gallery']


def test_archived_fire_statistics_recompute_from_the_recorded_confusion_counts():
 path=Path(__file__).resolve().parents[1]/'Examples/P03_Timber_Fire/references/integrated-comparison.json'
 for key in ['perimeter','published_outline']:
  r=json.loads(path.read_text())[key];tp,fp,fn=r['tp'],r['fp'],r['fn']
  assert r['precision']==pytest.approx(tp/(tp+fp))
  assert r['recall']==pytest.approx(tp/(tp+fn))
  assert r['f1']==pytest.approx(2*tp/(2*tp+fp+fn))
  assert r['iou']==pytest.approx(tp/(tp+fp+fn))
  assert r['valid_ha']==pytest.approx(sum(r[k] for k in ['tp','fp','fn','tn'])*.04)


@pytest.mark.parametrize('ident',['recovery','recovery_lower_days','recovery_upper_days','unresolved'])
def test_empty_recovery_maps_explain_missing_temporal_evidence_without_claiming_persistence(ident):
 import numpy as np
 from affine import Affine
 from backend.result_contracts import attach
 data=np.full((2,2),np.nan)
 result={'project':'P01','sources':[],'layers':{ident:{'data':data,'unit':'days','kind':'continuous'}}}
 grid={'crs':'EPSG:32736','transform':Affine(100,0,0,0,-100,0),'shape':[2,2],'bbox':[32.9,-24.65,33.14,-24.43]}
 attach(result,grid)
 reason=result['layers'][ident]['unavailable_reason']
 assert 'no later acquisition' in reason and 'no new-water candidates' in reason
 assert 'not proof of continuing flooding' in reason
 assert np.isnan(data).all()
