"""Bounded user-supplied spatial context and inspectable candidate-object histories."""
import numpy as np
from scipy import ndimage
from rasterio.features import rasterize,shapes
from rasterio.warp import transform_geom
from shapely.geometry import shape,mapping
from shapely.ops import transform as transform_shape
from pyproj import Transformer

ROLES={'domain','affected','zone','reference','stable','water','dry'}

def validate_context(context):
    if context is None:return None
    if not isinstance(context,dict) or context.get('type')!='FeatureCollection':raise ValueError('Context must be a WGS84 GeoJSON FeatureCollection.')
    features=context.get('features',[])
    if not isinstance(features,list) or len(features)>100:raise ValueError('Context supports at most 100 polygon features.')
    vertices=0
    for f in features:
        if not isinstance(f,dict) or f.get('type')!='Feature':raise ValueError('Every context entry must be a GeoJSON Feature.')
        props=f.get('properties') or {};role=props.get('role','zone')
        if role not in ROLES:raise ValueError('Context roles are domain, affected, zone, reference, stable, water or dry.')
        geom=f.get('geometry') or {}
        if geom.get('type') not in ['Polygon','MultiPolygon']:raise ValueError('Context features must be Polygon or MultiPolygon geometries.')
        def count(value):
            nonlocal vertices
            if not isinstance(value,list) or not value:raise ValueError('Invalid polygon coordinates.')
            if isinstance(value[0],(float,int)):
                if len(value)!=2 or not np.isfinite(value).all() or not(-180<=value[0]<=180 and -85<=value[1]<=85):raise ValueError('Use finite WGS84 longitude/latitude coordinates.')
                vertices+=1
            else:
                for v in value:count(v)
        count(geom.get('coordinates'))
        if vertices>10000:raise ValueError('Context exceeds 10000 vertices; simplify polygons.')
        g=shape(geom)
        if g.is_empty or not g.is_valid:raise ValueError('Context polygon is empty or invalid; repair its geometry.')
        if role in ['water','dry']:
            from datetime import date
            try:date.fromisoformat(props.get('date',''))
            except (ValueError,TypeError):raise ValueError('Water/dry validation polygons need an observation date.') from None
            if props.get('split') not in ['train','test']:raise ValueError('Validation polygons need split=train or split=test.')
            if not isinstance(props.get('source'),str) or not props['source'].strip():raise ValueError('Validation labels need an independent source citation.')
        if len(str(props.get('name','')))>100 or len(str(props.get('source','')))>1000:raise ValueError('Context names or source citations are too long.')
    return context

def context_masks(context,grid):
    result=[]
    for i,f in enumerate((context or {}).get('features',[])):
        geom=transform_geom('EPSG:4326',grid['crs'],f['geometry'])
        mask=rasterize([(geom,1)],out_shape=grid['shape'],transform=grid['transform'],fill=0,dtype='uint8',all_touched=False).astype(bool)
        result.append({'mask':mask,'name':str((f.get('properties') or {}).get('name',f'Zone {i+1}')),'role':(f.get('properties') or {}).get('role','zone'),'properties':f.get('properties') or {}})
    return result

def union_role(context,role,shape_,fallback=None):
    masks=[f['mask'] for f in context if f['role']==role]
    return np.logical_or.reduce(masks) if masks else (np.ones(shape_,bool) if fallback is None else fallback.copy())

def role_mask(context,role,grid,fallback=None):
    """Rasterize one role's union without retaining a mask per feature."""
    geometries=[transform_geom('EPSG:4326',grid['crs'],f['geometry']) for f in (context or {}).get('features',[]) if (f.get('properties') or {}).get('role','zone')==role]
    if not geometries:return np.ones(grid['shape'],bool) if fallback is None else fallback.copy()
    return rasterize([(geometry,1) for geometry in geometries],out_shape=grid['shape'],transform=grid['transform'],fill=0,dtype='uint8',all_touched=False).astype(bool)

class CandidateTrackingLimit(ValueError):
    """The optional object diagnostic exceeded its declared resource bound."""


def optional_patch_history(states,dates,grid,min_area_m2=0,max_objects=1000):
    """Keep core maps when tracking is too large; never return partial objects."""
    try:return patch_history(states,dates,grid,min_area_m2,max_objects)
    except CandidateTrackingLimit as error:
        return {'available':False,'reason':str(error),'object_limit':max_objects,
                'minimum_area_m2':min_area_m2,'objects':[],'links':[],
                'meaning':'Object tracking was not completed. No partial objects or overlap links are exported; the separately calculated measurement and change maps retain their original values.'}


def patch_history(states,dates,grid,min_area_m2=0,max_objects=1000):
    """Objects are dated components linked by cell overlap; IDs are not physical truth."""
    area=abs(grid['transform'].a*grid['transform'].e);records=[];links=[];features=[];previous=np.zeros(grid['shape'],dtype='int32');serial=0
    for frame,(state,date) in enumerate(zip(states,dates)):
        labels,n=ndimage.label(np.asarray(state,dtype=bool));sizes=np.bincount(labels.ravel());current=np.zeros(labels.shape,dtype='int32')
        for label in range(1,n+1):
            if sizes[label]*area<min_area_m2:continue
            if serial>=max_objects:raise CandidateTrackingLimit(f'Candidate tracking exceeds {max_objects} objects; increase minimum patch area or narrow the area/date selection to run this optional diagnostic.')
            serial+=1;mask=labels==label;current[mask]=serial
            parents,counts=np.unique(previous[mask],return_counts=True);parent_ids=[]
            for parent,count in zip(parents,counts):
                if parent:
                    parent_ids.append(int(parent));links.append({'from':int(parent),'to':serial,'overlap_cells':int(count),'overlap_area_m2':float(count*area)})
            fractions=[float(np.asarray(v,dtype=bool)[mask].mean()) for v in states]
            active=[i for i,v in enumerate(fractions) if v>0];first=active[0] if active else None
            before=[i for i in range(first or 0) if fractions[i]==0];later=[i for i in range(frame+1,len(fractions)) if fractions[i]==0]
            record={'id':serial,'frame':frame,'date':date,'cells':int(sizes[label]),'area_m2':float(sizes[label]*area),'parents':parent_ids,'children':[],
                    'first_observed_active':dates[first] if first is not None else None,'last_observed_inactive_before_first_active':dates[before[-1]] if before else None,'first_later_observed_inactive':dates[later[0]] if later else None,'calendar':[{'date':d,'candidate_fraction':v} for d,v in zip(dates,fractions)]}
            records.append(record)
        for geom,value in shapes(current,mask=current>0,transform=grid['transform']):
            rid=int(value);record=next(r for r in records if r['id']==rid)
            features.append({'type':'Feature','geometry':transform_geom(grid['crs'],'EPSG:4326',geom),'properties':{k:v for k,v in record.items() if k not in ['parents','children']}})
        previous=current
    lookup={r['id']:r for r in records}
    for link in links:lookup[link['from']]['children'].append(link['to'])
    for record in records:
        record['event']='merge' if len(record['parents'])>1 else 'continuation' if record['parents'] else 'first observed'
        if len(record['children'])>1:record['event']+='; split at next observation'
    for feature in features:feature['properties'].update(lookup[feature['properties']['id']])
    return {'objects':records,'links':links,'connectivity':4,'minimum_area_m2':min_area_m2,'geometry':{'type':'FeatureCollection','features':features},'meaning':'Dated candidate objects linked by overlap on a common analysis grid. Gaps are unobserved; links do not establish uninterrupted physical identity.'}
