import numpy as np
import pytest
from rasterio.transform import from_origin
from backend.fire import process,analysis_grid,candidate_mask

def observations():
 y,x=np.indices((80,80));noise=.05+.15*(1+np.sin(x*.21)*np.cos(y*.14));burn=np.zeros((80,80),bool);burn[25:55,25:55]=True
 result=[]
 for view,sign in [('042_D_070',1),('135_A_020',-1)]:
  for i,date in enumerate(['2026-06-01','2026-06-13','2026-06-25','2026-09-01']):
   delta=sign*(noise+2*burn) if i==3 else np.zeros((80,80))
   result.append({'item':{'id':view+str(i),'name':view+str(i),'product':'GCOV','group':view,'start':date+'T00:00:00Z','end':date+'T00:00:30Z'},'array':10**(delta/10),'aux':{'cross_power':.2*10**(-delta/10)},'attrs':{},'path':'/frequencyA/HHHH','quality_paths':[],'warnings':[],'bytes_transferred':0})
 return result
GRID={'shape':(80,80),'transform':from_origin(600000,4020000,20,20),'crs':'EPSG:32610','resolution':20,'bbox':[-122,36,-121,37]}
OPT={'baseline_count':3,'smoothing_m':40,'score_threshold':2,'patch_area_m2':100000}

def test_opposite_sign_views_reinforce_magnitude_and_keep_sources():
 r=process(observations(),GRID,OPT)
 assert r['metrics']['viewing_groups']==2 and r['metrics']['candidate_area_ha']>20
 assert np.nanmedian(r['layers']['fire_score']['data'][30:50,30:50])>2
 assert len(r['sources'])==8 and r['extra']['fire_method']['terrain_mask_applied'] is False
 assert len(r['series'])==2 and all('group' in row for row in r['series'])
 assert [row['date'] for row in r['series']]==sorted(row['date'] for row in r['series'])

def test_missing_baseline_is_not_silently_replaced_but_another_view_can_fill():
 obs=observations();obs[0]['array'][30,30]=np.nan
 r=process(obs,GRID,OPT)
 assert r['layers']['view_count']['data'][30,30]==1
 obs[4]['array'][30,30]=np.nan
 r=process(obs,GRID,OPT)
 assert np.isnan(r['layers']['fire_score']['data'][30,30])

def test_missing_hv_or_short_baseline_fails_closed():
 obs=observations();del obs[0]['aux']['cross_power']
 with pytest.raises(ValueError,match='both required'):process(obs,GRID,OPT)
 with pytest.raises(ValueError,match='three baseline'):process(observations(),GRID,{**OPT,'baseline_count':2})

def test_flat_window_has_no_defined_score():
 obs=observations()
 for o in obs:o['array'][:]=1;o['aux']['cross_power'][:]=.2
 with pytest.raises(ValueError,match='robust spread'):process(obs,GRID,OPT)

def test_grid_is_local_aligned_and_bounded():
 g=analysis_grid([-121.8484,36.1455,-121.564,36.351],20,'EPSG:32610',[603600,4001040,628860,4023500]);assert g['shape']==(1123,1263)
 with pytest.raises(ValueError,match='2048'):analysis_grid([-125,30,-115,40],20)
 with pytest.raises(ValueError):analysis_grid([-122,36,-121,37],20,'EPSG:4326')

def test_four_connected_ten_hectare_filter():
 z=np.zeros((60,60));z[1:11,1:26]=2;z[30:40,1:25]=2
 assert candidate_mask(z,2,250).sum()==250
