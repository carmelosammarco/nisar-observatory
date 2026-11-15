"""Shared scientific option models, independent of service initialization."""
from datetime import date
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,StrictBool,AwareDatetime,field_validator,model_validator
from .spatial import validate_context

class RegionalReference(BaseModel):
 product:Literal['GCOV','GUNW','GOFF','SME2']|None=None
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 date:date
 end:date|None=None
 value:float
 source:str=Field(min_length=1,max_length=1000)
 quantity:Literal['los_displacement','radar_component_rate','horizontal_speed']|None=None
 unit:Literal['mm','cm','m','mm/day','cm/day','m/day','mm/year','cm/year','m/year']|None=None
 component:Literal['slantRangeOffset','alongTrackOffset']|None=None
 @model_validator(mode='after')
 def matched_fields(self):
  if (self.quantity is None)!=(self.unit is None):raise ValueError('Specify both quantity and unit for a regional reference.')
  if self.end is not None and self.end<=self.date:raise ValueError('A regional pair reference must end after its start date.')
  if not self.source.strip():raise ValueError('Regional references need a source citation.')
  return self

class AnalysisOptions(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 surface_method:Literal['legacy','evolving']='legacy'
 fire_method:Literal['relative','combined']='relative'
 smoothing_m:float=Field(default=80,ge=0,le=1000)
 score_threshold:float=Field(default=2,gt=0,le=20)
 grid_crs:str|None=Field(default=None,pattern=r'^EPSG:32[67][0-6][0-9]$')
 grid_bounds:list[float]|None=Field(default=None,min_length=4,max_length=4)
 baseline_count:int=Field(default=1,ge=1,le=31)
 baseline_end:date|None=None
 baseline_noise_floor_db:float=Field(default=1,gt=0,le=20)
 patch_area_m2:float=Field(default=30000,ge=0,le=1000000000)
 water_tracking_enabled:StrictBool=True
 water_unknown_db:float=Field(default=1,ge=0,le=5)
 compare_polarizations:StrictBool=False
 offset_local_filter:StrictBool=False
 offset_stable_bias:StrictBool=False
 offset_solution:Literal['radar','horizontal']='radar'
 offset_geometry_height_m:float=Field(default=0,ge=-500,le=9000)
 offset_condition_limit:float=Field(default=10,ge=1,le=100)
 offset_vertical_scenario_m_year:float=Field(default=20,ge=0,le=1000)
 offset_layer:Literal['layer1','layer2','layer3']='layer1'
 offset_rate_unit:Literal['m/day','m/year']='m/day'
 apply_ionosphere:StrictBool=False
 quake_mosaic:StrictBool=False
 phase_network:StrictBool=True
 phase_allow_mixed_revisions:StrictBool=False
 reference_assistant_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
 reference_candidate_id:str|None=Field(default=None,pattern=r'^(candidate_[123]|current)$')
 event_timestamp:AwareDatetime|None=None
 spatial_context:dict|None=None
 reference_observations:list[RegionalReference]=Field(default_factory=list,max_length=500)
 @field_validator('spatial_context')
 @classmethod
 def context_valid(cls,value):return validate_context(value)
 resolution:float=Field(default=100,ge=20,le=2000)
 water_threshold:float=Field(default=-17,ge=-40,le=0)
 water_method:Literal['single','hh_hv']='single'
 water_hh_threshold:float=Field(default=-14,ge=-40,le=0)
 water_hv_threshold:float=Field(default=-23,ge=-45,le=0)
 change_threshold:float=Field(default=3,ge=.1,le=20)
 coherence:float=Field(default=.4,ge=0,le=1)
 snr:float=Field(default=5,ge=0,le=100)
 min_valid_fraction:float=Field(default=.5,gt=0,le=1)
 offset_filter:StrictBool=True
 offset_mad_multiplier:float=Field(default=8,ge=1,le=50)
 offset_min_cutoff_m:float=Field(default=1,gt=0,le=100)
 component:Literal['slantRangeOffset','alongTrackOffset']='slantRangeOffset'
 reference_bbox:list[float]|None=None
 event_date:date|None=None
 flood_date:date|None=None
 channel:Literal['auto','HHHH','HVHV','VVVV','VHVH','RHRH','RVRV']='auto'
 patch_cells:int=Field(default=3,ge=1,le=1000000)
 graph_distance:float=Field(default=2000,ge=0,le=1000000)


def positive_smoothing_field():
 """A workflow smoothing step is enabled and positive; shared settings allow 0 to disable."""
 import copy
 from annotated_types import Ge,Gt
 field=copy.deepcopy(AnalysisOptions.model_fields['smoothing_m'])
 field.metadata=[m for m in field.metadata if not isinstance(m,(Ge,Gt))]+[Gt(0)]
 return field
