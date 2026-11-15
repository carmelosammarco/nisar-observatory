"""Display metadata validation without importing or starting the service."""
import re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from .map_styles import validate_colors,validate_opacity

class DisplaySettings(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 palette:Literal['standard','diverging','rainbow']='standard'
 mode:Literal['shared','robust','full','custom']='shared'
 layer:str=Field(pattern=r'^[a-z0-9_]{1,120}$')
 unit:str=Field(min_length=1,max_length=50)
 low:float|None=None
 high:float|None=None
 category_colors:dict[str,dict[str,str]]=Field(default_factory=dict,max_length=120)
 category_opacity:dict[str,dict[str,float]]=Field(default_factory=dict,max_length=120)
 @field_validator('category_opacity',mode='before')
 @classmethod
 def valid_category_opacity(cls,maps):
  if not isinstance(maps,dict) or len(maps)>120:raise ValueError('Invalid category opacity maps.')
  if any(not isinstance(values,dict) for values in maps.values()):raise ValueError('Invalid category opacity map.')
  if sum(len(values) for values in maps.values())>4096:raise ValueError('Too many saved category opacity values.')
  clean={}
  for layer,values in maps.items():
   if not re.fullmatch(r'[a-z0-9_]{1,120}',layer):raise ValueError('Invalid category map identifier.')
   clean[layer]=validate_opacity(values)
  return clean
 @field_validator('category_colors')
 @classmethod
 def valid_category_colors(cls,maps):
  if sum(len(colors) for colors in maps.values())>4096:raise ValueError('Too many saved category colors.')
  for layer,colors in maps.items():
   if not re.fullmatch(r'[a-z0-9_]{1,120}',layer):raise ValueError('Invalid category map identifier.')
   maps[layer]=validate_colors(colors)
  return maps
 @model_validator(mode='after')
 def ordered_range(self):
  if self.mode=='custom' and (self.low is None or self.high is None or self.high<=self.low):raise ValueError('Custom display limits must be finite and ordered.')
  return self

