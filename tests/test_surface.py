import numpy as np
from rasterio.transform import from_origin
from backend.surface import evolving_surface
from backend.raster_methods import smooth

def test_late_growth_is_retained_repeated_and_transient_evidence_are_distinct():
 db=np.full((5,60,60),-15.,dtype='float32')
 db[1:,5:15,5:15]+=6 # Early change remains.
 db[4,25:35,25:35]+=6 # Late growth: previously discarded by all-date rule.
 db[2,40:50,5:15]+=6 # Transient: should not appear in latest map.
 grid={'shape':(60,60),'transform':from_origin(600000,6100000,20,20),'resolution':20,'crs':'EPSG:32657'}
 dates=[f'2026-07-{i+1:02}T00:00:00Z' for i in range(5)]
 layers,m,e,rows,notes=evolving_surface(db,db[0],[0],np.ones((60,60),bool),dates,grid,{'change_threshold':3,'patch_area_m2':30000,'smoothing_m':0})
 assert layers['surface']['data'][30,30]==1
 assert layers['confirmed_change']['data'][30,30]==0
 assert layers['confirmed_change']['data'][10,10]==1
 assert layers['surface']['data'][45,10]==0
 assert layers['first_change']['data'][30,30]==4
 assert layers['repeat_count']['data'][10,10]==4
 assert m['latest_change_area_km2']==.08 and m['repeated_latest_change_area_km2']==.04
 assert rows[0]['change_candidate_km2']==0 and rows[2]['change_candidate_km2']==.08
 assert e['surface_method']['repeated_latest_available'] and e['tracking']['objects']

def test_two_dates_do_not_claim_repeated_change_and_missing_is_never_filled():
 db=np.full((2,40,40),-15.,dtype='float32');db[1,5:25,5:25]+=6;common=np.ones((40,40),bool);common[12:14,12:14]=False;db[:,~common]=np.nan
 grid={'shape':(40,40),'transform':from_origin(600000,6100000,20,20),'resolution':20,'crs':'EPSG:32657'}
 layers,m,e,_,_=evolving_surface(db,db[0],[0],common,['2026-06-18','2026-06-30'],grid,{'smoothing_m':40,'change_threshold':3,'patch_area_m2':30000})
 assert not e['surface_method']['repeated_latest_available']
 assert m['repeated_latest_change_area_km2']==0
 assert np.isnan(layers['latest_departure']['data'][12:14,12:14]).all()
 assert np.isnan(layers['surface']['data'][12:14,12:14]).all()

def test_sign_changes_reset_latest_evidence_streak():
 db=np.full((4,30,30),-15.,dtype='float32');db[1,5:20,5:20]+=6;db[2:,5:20,5:20]-=6
 grid={'shape':(30,30),'transform':from_origin(600000,6100000,20,20),'resolution':20,'crs':'EPSG:32657'}
 l,_,_,_,_=evolving_surface(db,db[0],[0],np.ones((30,30),bool),['2026-06-18','2026-06-30','2026-07-12','2026-07-24'],grid,{'smoothing_m':0,'change_threshold':3,'patch_area_m2':30000})
 assert l['change_direction']['data'][10,10]==-1 and l['repeat_count']['data'][10,10]==2

def test_rotated_metric_envelope_excludes_corners_outside_selected_geography():
 from backend.raster_methods import analysis_grid,geographic_window_mask
 from pyproj import Geod
 bbox=[160.15,54.51,160.50,54.70];grid=analysis_grid(bbox,20);mask=geographic_window_mask(grid)
 assert mask.any() and not mask.all()
 area,_=Geod(ellps='WGS84').polygon_area_perimeter([bbox[0],bbox[2],bbox[2],bbox[0]],[bbox[1],bbox[1],bbox[3],bbox[3]])
 assert abs(mask.sum()*400/abs(area)-1)<.002
