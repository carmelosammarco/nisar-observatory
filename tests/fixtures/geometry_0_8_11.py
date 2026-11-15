"""Frozen 0.8.11 full-cube interpolant: numeric regression oracle, not production code.
Source commit b555775; retained to check window/height/batch equivalence.
"""
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from pyproj import Transformer
from backend.execution import cancellable,checkpoint
ROOT='/science/LSAR/GOFF/metadata/radarGrid'
FIELDS=('losUnitVectorX','losUnitVectorY','alongTrackUnitVectorX','alongTrackUnitVectorY','incidenceAngle')
VERSION='goff-geometry-1'

@cancellable
def interpolate(f,target,height):
 from backend.science import decode
 if ROOT not in f or any(ROOT+'/'+n not in f for n in FIELDS):raise ValueError('Horizontal speed needs viewing geometry. Prepare geometry for the selected saved files, or save a new GOFF area extract. Older radar-only subsets remain usable in radar mode.')
 g=f[ROOT];axes=[np.asarray(g[n][:],dtype='float64') for n in ['heightAboveEllipsoid','yCoordinates','xCoordinates']]
 if not axes[0].min()<=height<=axes[0].max():raise ValueError('Geometry height is outside the delivered height cube. Choose an ellipsoidal height inside its range.')
 epsg=int(np.asarray(g['projection'].attrs.get('epsg_code',g['projection'][()])).item())
 h,w=target['shape'];t=target['transform'];xx,yy=np.meshgrid(t.c+(np.arange(w)+.5)*t.a,t.f+(np.arange(h)+.5)*t.e)
 x,y=Transformer.from_crs(target['crs'],epsg,always_xy=True).transform(xx,yy)
 points=np.column_stack([np.full(x.size,height),y.ravel(),x.ravel()]);out={};descriptions={}
 for name in FIELDS:
  checkpoint()
  ds=g[name];desc=str(decode(ds.attrs.get('description','')));descriptions[name]=desc
  if name!='incidenceAngle':
   direction='east' if name.endswith('X') else 'north'
   if direction not in desc.lower() or 'utm' in desc.lower():raise ValueError('Viewing-vector coordinate convention is not explicitly East/North. This schema needs a reviewed adapter; no grid-vector rotation is guessed.')
   if str(decode(ds.attrs.get('units',''))).lower() not in ['1','unitless','dimensionless']:raise ValueError('Viewing-vector units must explicitly be dimensionless.')
  elif str(decode(ds.attrs.get('units',''))).lower() not in ['degrees','degree','deg']:raise ValueError('Incidence-angle units must explicitly be degrees.')
  data=np.asarray(ds[:],dtype='float64')
  if data.shape!=tuple(len(a) for a in axes):raise ValueError('Viewing-cube dimensions disagree with their axes.')
  for key in ['_FillValue','missing_value']:
   if key in ds.attrs:data[data==float(ds.attrs[key])]=np.nan
  data[~np.isfinite(data)]=np.nan
  out[name]=RegularGridInterpolator(tuple(axes),data,bounds_error=False,fill_value=np.nan)(points).reshape(h,w).astype('float32')
 return out,{'version':VERSION,'height_above_ellipsoid_m':float(height),'height_source':'User-specified constant ellipsoidal height; not a per-pixel DEM','interpolation':'Trilinear on delivered height/y/x cube axes; no extrapolation','vector_basis':'East/North/Up (ENU), verified from source dataset descriptions','source_descriptions':descriptions,'paths':[ROOT+'/'+n for n in FIELDS],'projection_epsg':epsg}

