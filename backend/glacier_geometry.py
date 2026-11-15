"""GOFF viewing geometry and a constrained two-component horizontal inversion.

Range offsets increase away from the sensor; delivered LOS vectors point toward
it. Along-track offsets follow the ground-track vector. Zero vertical velocity
is an explicit model constraint, never a measured conclusion.
"""
from .execution import cancellable,checkpoint
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from pyproj import Transformer
from rasterio.warp import transform_bounds

ROOT='/science/LSAR/GOFF/metadata/radarGrid'
FIELDS=('losUnitVectorX','losUnitVectorY','alongTrackUnitVectorX','alongTrackUnitVectorY','incidenceAngle')
VERSION='goff-geometry-1'
INTERPOLATION_VERSION='goff-geometry-2'
MAX_GEOMETRY_BYTES=64*1024**2
MAX_AXIS_SAMPLES=1_000_000
MAX_POINT_BATCH=65_536
MAX_TARGET_CELLS=4_000_000

def copy_cubes(source,output,bbox,attrs,storage_path=None):
 if ROOT not in source or any(ROOT+'/'+n not in source for n in FIELDS):
  return {'available':False,'reason':'The input does not contain the required GOFF viewing-geometry cubes.'}
 g=source[ROOT];x=np.asarray(g['xCoordinates'][:]);y=np.asarray(g['yCoordinates'][:]);z=np.asarray(g['heightAboveEllipsoid'][:])
 if min(len(x),len(y),len(z))<2:raise ValueError('Viewing geometry needs at least two samples on every axis.')
 epsg=int(np.asarray(g['projection'].attrs.get('epsg_code',g['projection'][()])).item())
 w,s,e,n=transform_bounds(4326,epsg,*bbox,densify_pts=21)
 def interval(axis,lo,hi):
  if not np.isfinite(axis).all() or not (np.all(np.diff(axis)>0) or np.all(np.diff(axis)<0)):raise ValueError('Viewing-geometry axes must be finite and strictly monotonic.')
  margin=float(np.max(np.abs(np.diff(axis))))
  idx=np.flatnonzero((axis>=lo-margin)&(axis<=hi+margin))
  if idx.size<2:raise ValueError('Viewing-geometry grid does not overlap this area.')
  return slice(int(idx.min()),int(idx.max())+1)
 ix=interval(x,w,e);iy=interval(y,s,n)
 shape=(len(z),iy.stop-iy.start,ix.stop-ix.start)
 if np.prod(shape)*8*len(FIELDS)>64*1024**2:raise ValueError('Viewing geometry exceeds 64 MiB. Select a smaller area.')
 if storage_path is not None:
  from .storage_budget import require_space
  require_space(storage_path,int(np.prod(shape))*8*len(FIELDS)+1024**2,operation='Saving viewing geometry')
 expected=(len(z),len(y),len(x))
 for key in FIELDS:
  if g[key].shape!=expected:raise ValueError('Unsupported GOFF viewing-cube dimensions.')
 if ROOT in output:del output[ROOT]
 dest=output.require_group(ROOT);attrs(g,dest)
 for name,values in [('xCoordinates',x[ix]),('yCoordinates',y[iy]),('heightAboveEllipsoid',z),('projection',g['projection'][()])]:
  ds=dest.create_dataset(name,data=values);attrs(g[name],ds)
 for name in FIELDS:
  checkpoint()
  ds=dest.create_dataset(name,data=g[name][:,iy,ix],compression='gzip',shuffle=True);attrs(g[name],ds)
 return {'available':True,'version':VERSION,'paths':[ROOT+'/'+n for n in FIELDS],'shape':list(shape),'height_range_m':[float(z.min()),float(z.max())],'horizontal_window':[ix.start,ix.stop,iy.start,iy.stop],'projection_epsg':epsg,'meaning':'Native height-dependent viewing cubes cropped with an interpolation buffer. No invented heading, incidence angle or terrain height.'}

def _axis(dataset):
 if dataset.ndim!=1 or dataset.size>MAX_AXIS_SAMPLES:raise ValueError('Viewing-geometry axes must be one-dimensional and contain at most one million samples each.')
 axis=np.asarray(dataset[:],dtype='float64')
 if len(axis)<2 or not np.isfinite(axis).all():raise ValueError('Viewing-geometry axes need at least two finite, strictly monotonic samples.')
 delta=np.diff(axis)
 if not (np.all(delta>0) or np.all(delta<0)):raise ValueError('Viewing-geometry axes need at least two finite, strictly monotonic samples.')
 return axis


def _bracket_window(axis,lo,hi):
 """Retain exactly the source cells bracketing all requested coordinates.

 Internal exact-grid coordinates use the interval to their right, as in the
 former full-cube interpolant. This matters when a zero-weight neighbour is NaN.
 """
 ascending=axis[-1]>axis[0];ordered=axis if ascending else axis[::-1]
 if hi<ordered[0] or lo>ordered[-1]:return None
 first=int(np.clip(np.searchsorted(ordered,max(lo,ordered[0]),side='right')-1,0,len(axis)-2))
 stop=int(np.clip(np.searchsorted(ordered,min(hi,ordered[-1]),side='right')-1,0,len(axis)-2))+2
 return slice(first,stop) if ascending else slice(len(axis)-stop,len(axis)-first)


def _target_points(target,convert,height):
 h,w=target['shape'];t=target['transform']
 for start in range(0,h*w,MAX_POINT_BATCH):
  checkpoint();stop=min(h*w,start+MAX_POINT_BATCH);rows,cols=np.divmod(np.arange(start,stop),w)
  x,y=convert.transform(t.c+(cols+.5)*t.a+(rows+.5)*t.b,t.f+(cols+.5)*t.d+(rows+.5)*t.e)
  yield start,stop,np.column_stack([np.full(stop-start,height),y,x])


@cancellable
def interpolate(f,target,height):
 from .science import decode
 if ROOT not in f or any(ROOT+'/'+n not in f for n in FIELDS):raise ValueError('Horizontal speed needs viewing geometry. Prepare geometry for the selected saved files, or save a new GOFF area extract. Older radar-only subsets remain usable in radar mode.')
 h,w=target['shape']
 if min(h,w)<1 or max(h,w)>2048 or h*w>MAX_TARGET_CELLS:raise ValueError('Viewing geometry supports at most 2048 target cells per side and 4 million cells. Select a smaller analysis grid.')
 g=f[ROOT];axes=[_axis(g[n]) for n in ['heightAboveEllipsoid','yCoordinates','xCoordinates']]
 if not axes[0].min()<=height<=axes[0].max():raise ValueError('Geometry height is outside the delivered height cube. Choose an ellipsoidal height inside its range.')
 epsg=int(np.asarray(g['projection'].attrs.get('epsg_code',g['projection'][()])).item());descriptions={}
 expected=tuple(len(a) for a in axes)
 for name in FIELDS:
  ds=g[name];desc=str(decode(ds.attrs.get('description','')));descriptions[name]=desc
  if name!='incidenceAngle':
   direction='east' if name.endswith('X') else 'north'
   if direction not in desc.lower() or 'utm' in desc.lower():raise ValueError('Viewing-vector coordinate convention is not explicitly East/North. This schema needs a reviewed adapter; no grid-vector rotation is guessed.')
   if str(decode(ds.attrs.get('units',''))).lower() not in ['1','unitless','dimensionless']:raise ValueError('Viewing-vector units must explicitly be dimensionless.')
  elif str(decode(ds.attrs.get('units',''))).lower() not in ['degrees','degree','deg']:raise ValueError('Incidence-angle units must explicitly be degrees.')
  if ds.shape!=expected:raise ValueError('Viewing-cube dimensions disagree with their axes.')
  if ds.dtype.kind not in 'fiub':raise ValueError('Viewing-geometry values must be real numeric samples.')
  if ds.chunks and int(np.prod(ds.chunks))*ds.dtype.itemsize>MAX_GEOMETRY_BYTES:raise ValueError('A viewing-geometry HDF5 chunk exceeds 64 MiB. Use a source with bounded chunks before interpolation.')
 convert=Transformer.from_crs(target['crs'],epsg,always_xy=True);lo=np.array([np.inf,np.inf]);hi=-lo
 # First pass uses actual target centres, including nonlinear CRS transforms;
 # a perimeter-only envelope could miss an interior extremum.
 for _,_,points in _target_points(target,convert,height):
  finite=np.isfinite(points[:,1:]).all(axis=1)
  if finite.any():lo=np.minimum(lo,points[finite,1:].min(axis=0));hi=np.maximum(hi,points[finite,1:].max(axis=0))
 windows=[_bracket_window(axes[0],height,height)]
 windows+=[_bracket_window(a,l,r) if np.isfinite(l) and np.isfinite(r) else None for a,l,r in zip(axes[1:],lo,hi)]
 overlap=all(s is not None for s in windows);shape=tuple(s.stop-s.start for s in windows) if overlap else (0,0,0)
 retained_bytes=int(np.prod(shape))*8*len(FIELDS)
 if retained_bytes>MAX_GEOMETRY_BYTES:raise ValueError('The required viewing-geometry window exceeds 64 MiB. Select a smaller area.')
 out={name:np.full((h,w),np.nan,dtype='float32') for name in FIELDS}
 if overlap:
  interpolants={};slices=tuple(windows);local_axes=tuple(a[s] for a,s in zip(axes,slices))
  for name in FIELDS:
   checkpoint();ds=g[name];data=np.asarray(ds[slices],dtype='float64')
   for key in ['_FillValue','missing_value']:
    if key in ds.attrs:data[data==float(ds.attrs[key])]=np.nan
   data[~np.isfinite(data)]=np.nan
   interpolants[name]=RegularGridInterpolator(local_axes,data,bounds_error=False,fill_value=np.nan)
  for start,stop,points in _target_points(target,convert,height):
   for name in FIELDS:
    checkpoint();out[name].ravel()[start:stop]=interpolants[name](points).astype('float32')
 return out,{'version':INTERPOLATION_VERSION,'height_above_ellipsoid_m':float(height),'height_source':'User-specified constant ellipsoidal height; not a per-pixel DEM','interpolation':'Trilinear on delivered height/y/x cube axes; no extrapolation','vector_basis':'East/North/Up (ENU), verified from source dataset descriptions','source_descriptions':descriptions,'paths':[ROOT+'/'+n for n in FIELDS],'projection_epsg':epsg,'source_cube_shape':list(expected),'read_window_shape':list(shape),'retained_geometry_bytes':retained_bytes,'geometry_budget_bytes':MAX_GEOMETRY_BYTES,'maximum_point_batch':MAX_POINT_BATCH,'read_window_indices':[[s.start,s.stop] for s in windows] if overlap else None,'resource_scope':'Bounded source window and interpolation point batches; output arrays, HDF5/PROJ/SciPy overhead and the rest of the analysis are additional.'}

@cancellable
def horizontal(range_rate,along_rate,geometry,max_condition=10.,vertical_scenario_m_year=20.,annualization=1.):
 le,ln,ae,an=[np.asarray(geometry[k],dtype='float64') for k in FIELDS[:4]]
 incidence=np.asarray(geometry['incidenceAngle']);a=-le;b=-ln;c=ae;d=an
 determinant=a*d-b*c
 # Analytic singular values of the per-cell 2x2 matrix avoid NaN SVD failures.
 trace=a*a+b*b+c*c+d*d;discriminant=np.sqrt(np.maximum(trace*trace-4*determinant**2,0))
 large=(trace+discriminant)/2;small=np.divide(determinant**2,large,out=np.zeros_like(large),where=large>0)
 condition=np.sqrt(np.divide(large,small,out=np.full_like(large,np.inf),where=small>0))
 hnorm=np.hypot(le,ln);anorm=np.hypot(ae,an)
 geometry_valid=np.isfinite(trace)&np.isfinite(incidence)&(incidence>0)&(incidence<90)&(hnorm>0)&(hnorm<1)&(np.abs(anorm-1)<.02)&(np.abs(hnorm-np.sin(np.deg2rad(incidence)))<.02)
 valid=geometry_valid&(condition<=max_condition)&np.isfinite(range_rate)&np.isfinite(along_rate)&(np.abs(determinant)>1e-10)
 det=np.where(valid,determinant,np.nan)
 east=(d*range_rate-b*along_rate)/det;north=(-c*range_rate+a*along_rate)/det
 speed=np.hypot(east,north);bearing=np.mod(np.degrees(np.arctan2(east,north)),360);bearing=np.where(speed>1e-10,bearing,np.nan)
 up=np.sqrt(np.maximum(1-hnorm**2,0))
 # If actual vertical differs from zero, vector error magnitude is bounded by
 # ||A^-1 [LOS_up,0]|| * |vertical|. This is a scenario, not a confidence interval.
 sensitivity=np.hypot(d*up/det,-c*up/det)*vertical_scenario_m_year*annualization/365.25
 return {'east':east.astype('float32'),'north':north.astype('float32'),'speed':speed.astype('float32'),'bearing':bearing.astype('float32'),'condition':np.where(geometry_valid,condition,np.nan).astype('float32'),'vertical_sensitivity':sensitivity.astype('float32'),'valid':valid}, {'geometry_valid_cells':int(geometry_valid.sum()),'joint_offset_cells':int((np.isfinite(range_rate)&np.isfinite(along_rate)).sum()),'accepted_cells':int(valid.sum()),'condition_rejected_cells':int((geometry_valid&(condition>max_condition)&np.isfinite(range_rate)&np.isfinite(along_rate)).sum())}
