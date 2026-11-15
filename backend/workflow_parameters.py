"""Typed parameter schemas shared by registry, recipe validation and draft inspection."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from . import workflow_templates as templates
from .analysis_options import positive_smoothing_field

class StrictModel(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Empty(StrictModel):pass
class Baseline(StrictModel):count:int=templates.option_field('baseline_count')
class Smooth(StrictModel):sigma_m:float=positive_smoothing_field()
class Threshold(StrictModel):value:float=Field(default=3,ge=-1000000,le=1000000);direction:Literal['above','below','absolute']='above'
class Patches(StrictModel):minimum_m2:float=templates.option_field('patch_area_m2')
class Rate(StrictModel):annualized:bool=False
class Network(StrictModel):require_cycles:bool=False
class Summary(StrictModel):statistic:Literal['mean','median','std','minimum','maximum','frequency']='mean'
PARAMS={'db':Empty,'los':Empty,'rate':Rate,'baseline':Baseline,'smooth':Smooth,'threshold':Threshold,'patches':Patches,'summary':Summary,'network':Network,'trend':Rate,**templates.PARAMS}

from functools import lru_cache
import copy
@lru_cache(maxsize=1)
def parameter_schemas():return {key:model.model_json_schema() for key,model in PARAMS.items()}
@lru_cache(maxsize=1)
def _defaults():return {key:{name:meta['default'] for name,meta in schema.get('properties',{}).items() if 'default' in meta} for key,schema in parameter_schemas().items()}
def parameter_defaults():return copy.deepcopy(_defaults())
