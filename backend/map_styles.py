"""Shared category semantics and validated display-only color overrides."""
import re
import numpy as np
from .exports import colorize


def is_category(info):
 return info['kind'] in ('binary','categorical','water_state') or info['unit'] in ('class','observation index')


def validate_colors(colors):
 if not isinstance(colors,dict) or len(colors)>512:raise ValueError('Use at most 512 category colors per map.')
 clean={}
 for value,color in colors.items():
  try:number=float(value)
  except (ValueError,TypeError):raise ValueError('Category keys must be finite numbers.')
  if not np.isfinite(number) or not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Use finite category numbers and six-digit hex colors, such as #318fbf.')
  key=str(int(number)) if number.is_integer() else str(number)
  if key in clean:raise ValueError('Each category may have only one color.')
  clean[key]=color.lower()
 return clean


def validate_opacity(values):
 if not isinstance(values,dict) or len(values)>512:raise ValueError('Use at most 512 category opacity values per map.')
 clean={}
 for value,opacity in values.items():
  try:number=float(value)
  except (ValueError,TypeError):raise ValueError('Category keys must be finite numbers.')
  if not np.isfinite(number) or isinstance(opacity,bool) or not isinstance(opacity,(int,float)) or not np.isfinite(opacity) or not 0<=opacity<=1:raise ValueError('Category opacity must be a number from 0 (transparent) to 1 (opaque).')
  key=str(int(number)) if number.is_integer() else str(number)
  if key in clean:raise ValueError('Each category may have only one opacity.')
  clean[key]=float(opacity)
 return clean


def category_entries(info,display,result,colors,opacities=None):
 from .map_image import legend_spec
 entries=legend_spec(info,display,result)
 if entries is None and is_category(info):entries=[(v,f'Class {v:g}') for v in display['class_values']]
 if entries is None:return []
 out=[]
 rgba,_,_=colorize(np.array([[v for v,_ in entries]],dtype='float32'),info['kind'],(display['min'],display['max']),display['palette'],colors)
 for index,(value,label) in enumerate(entries):
  color='#'+''.join(f'{int(c):02x}' for c in rgba[0,index,:3])
  entry={'value':value,'label':label,'color':color}
  key=str(int(value)) if float(value).is_integer() else str(value)
  if opacities and key in opacities:entry['opacity']=opacities[key]
  out.append(entry)
 return out
