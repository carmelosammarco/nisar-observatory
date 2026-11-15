"""Frozen 0.8.3 renderer for pixel-identical streaming regression checks."""
import numpy as np
def colorize(a,kind,limits=None,palette=None,category_colors=None,category_opacity=None):
 v=a[np.isfinite(a)]
 lo,hi=(float(np.percentile(v,2)),float(np.percentile(v,98))) if v.size else (0.,1.)
 if limits is not None:lo,hi=map(float,limits)
 elif kind=='diverging':hi=max(abs(lo),abs(hi),1e-6);lo=-hi
 if kind=='binary':lo,hi=0.,1.
 if kind=='water_state':lo,hi=0.,2.
 if hi<=lo:hi=lo+1
 z=np.clip((np.nan_to_num(a,nan=lo)-lo)/(hi-lo),0,1)
 stops=np.array([[24,45,61],[41,155,165],[231,230,166]]) if kind!='diverging' else np.array([[61,137,205],[242,239,222],[229,102,76]])
 if palette is not None:stops=np.array(palette)
 if kind=='water_state':stops=np.array([[225,220,198],[49,143,191],[142,143,151]])
 if kind=='binary':stops=np.array([[225,220,198],[49,143,191],[20,88,151]])
 c=z*(len(stops)-1);i=np.minimum(c.astype(int),len(stops)-2);f=(c-i)[...,None]
 rgb=(stops[i]*(1-f)+stops[i+1]*f).astype('uint8');alpha=np.where(np.isfinite(a),255 if category_opacity is not None else 210,0).astype('uint8')
 if kind=='categorical':
  ids=np.nan_to_num(a,nan=0).astype('int64')
  rgb=np.stack([55+(ids*67)%175,65+(ids*103)%160,65+(ids*43)%175],axis=-1).astype('uint8')
  rgb[ids==0]=[225,220,198]
 if category_colors:
  for value,color in category_colors.items():
   rgb[a==float(value)]=[int(color[i:i+2],16) for i in (1,3,5)]
 if category_opacity:
  for value,opacity in category_opacity.items():
   alpha[a==float(value)]=round(255*opacity)
 return np.dstack((rgb,alpha)),lo,hi
