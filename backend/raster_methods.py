"""Shared metric grids and missing-data-preserving filters for radar change tools."""
from .execution import cancellable,checkpoint
import math
import numpy as np
from scipy import ndimage
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

def analysis_grid(bbox,resolution=20,crs=None,bounds=None):
 if crs is None:
  lon=(bbox[0]+bbox[2])/2;lat=(bbox[1]+bbox[3])/2
  crs=f'EPSG:{(32600 if lat>=0 else 32700)+min(60,max(1,int((lon+180)//6)+1))}'
 if not (str(crs).startswith('EPSG:326') or str(crs).startswith('EPSG:327')) or not 1<=int(str(crs)[-2:])<=60:raise ValueError('This method requires a local UTM CRS, EPSG:32601–32660 or 32701–32760.')
 res=float(resolution);actual=transform_bounds('EPSG:4326',crs,*bbox,densify_pts=21)
 if bounds is None:
  w,s,e,n=actual;bounds=[math.floor(w/res)*res,math.floor(s/res)*res,math.ceil(e/res)*res,math.ceil(n/res)*res]
 else:
  if len(bounds)!=4 or not all(np.isfinite(v) for v in bounds):raise ValueError('Grid bounds need four finite UTM coordinates.')
  w,s,e,n=map(float,bounds)
  if not w<e or not s<n:raise ValueError('Grid bounds must be ordered west, south, east, north.')
  envelope=transform_bounds(crs,'EPSG:4326',w,s,e,n,densify_pts=21)
  if any(abs(a-b)>.001 for a,b in zip(envelope,bbox)):raise ValueError('Grid bounds must match the selected geographic window within 0.001 degrees.')
 w,s,e,n=bounds;width=int(round((e-w)/res));height=int(round((n-s)/res))
 if min(width,height)<2 or max(width,height)>2048 or width*height>4_000_000:raise ValueError('This metric grid supports at most 2048 cells per side and 4 million cells. Select a smaller area or increase cell spacing.')
 if abs(width*res-(e-w))>.01 or abs(height*res-(n-s))>.01:raise ValueError('Grid bounds must be aligned to the requested cell spacing.')
 return {'crs':crs,'transform':from_origin(w,n,res,res),'shape':(height,width),'resolution':res,'bbox':bbox}

@cancellable
def smooth(a,sigma):
 # Shared contract: normalized Gaussian, reflected boundary, >=30% finite
 # kernel support, and no interpolation into a missing central cell.
 if not np.isfinite(sigma) or sigma<0:raise ValueError('Smoothing sigma must be finite and nonnegative.')
 valid=np.isfinite(a)
 if sigma==0:return a.copy()
 support=ndimage.gaussian_filter(valid.astype('float64'),sigma)
 checkpoint()
 total=ndimage.gaussian_filter(np.where(valid,a,0).astype('float64'),sigma)
 return np.where(valid&(support>=.3),total/np.maximum(support,1e-20),np.nan)

@cancellable
def candidate_mask(z,threshold,minimum_cells):
 labels,_=ndimage.label(z>=threshold);sizes=np.bincount(labels.ravel());keep=sizes>=minimum_cells;keep[0]=False
 return keep[labels]


@cancellable
def geographic_window_mask(grid):
 """Clip a rotated metric envelope to the selected WGS84 rectangle (cell centres)."""
 from pyproj import Transformer
 h,w=grid['shape'];t=grid['transform'];x=t.c+(np.arange(w)+.5)*t.a;y=t.f+(np.arange(h)+.5)*t.e
 xx,yy=np.meshgrid(x,y);lon,lat=Transformer.from_crs(grid['crs'],'EPSG:4326',always_xy=True).transform(xx,yy)
 west,south,east,north=grid['bbox']
 return (lon>=west)&(lon<=east)&(lat>=south)&(lat<=north)
