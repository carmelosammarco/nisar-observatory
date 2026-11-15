"""Inspectable evidence from real kernel boundaries, without replaying a method.

Existing result maps are referenced, not copied. Missing intermediate snapshots
are copied only while an editable recipe is being executed. For repeated frames
we retain the latest snapshot per view/component; final dated maps remain in the
ordinary timeline. A recipe's blocks can configure a fused kernel, so a diagnostic
snapshot carries its actual units rather than pretending to be another block I/O.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import numpy as np
from .execution import checkpoint

_ACTIVE=ContextVar('nisar_processing_trace',default=None)
VERSION='1.0.0'
# Presentation associations, not another dependency/parameter contract.
EVIDENCE={
 'water_rule':(['water','water_state','hh_sigma','hv_sigma','observation_'],['water_method','water_states','water_validation']),
 'flood_history':(['event','event_baseline_departure','recovery','recovery_lower_days','recovery_upper_days','unresolved'],['event_selection','event_baseline','recovery_calendar']),
 'wetland_history':(['occupancy','count','threshold_sensitive'],['zones','threshold_sensitivity','grid_sensitivity']),
 'water_tracking':([],['tracking']),
 'dual_change':(['change_intensity','view_count','view_','observation_'],['fire_method']),
 'robust_score':(['fire_score'],['fire_method']),
 'surface_baseline':(['baseline_departure','standardized_departure'],['baseline']),
 'signed_change':([],['surface_method']),
 'surface_history':(['confirmed_change','first_change','repeat_count','largest_step'],['surface_method','first_change_calendar','step_calendar']),
 'event_pairs':([],['event_selection','event_mosaic','selected_interval','event_measurement']),
 'event_los':(['event_displacement_cm','reference_support','event_overlap_spread','event_source','group_'],['reference_diagnostics','event_mosaic','event_measurement']),
 'offset_screen':(['offset_rejected_'],['offset_filter_diagnostics','offset_measurement']),
 'offset_bias':([],['stable_terrain']),
 'horizontal_velocity':(['horizontal_condition_','horizontal_vertical_sensitivity_'],['horizontal_velocity']),
 'radar_components':(['radar_magnitude'],['offset_measurement']),
 'rate_units':(['horizontal_speed','radar_magnitude','value','observation_'],['offset_measurement','horizontal_velocity']),
}

class Collector:
 def __init__(self,recipe):
  self.operations={s.operation for s in recipe.steps};self.snapshots={}
 def record(self,operation,key,data,label,unit,kind,group='',**metadata):
  if operation not in self.operations:return
  checkpoint()
  ident='trace_'+operation+'_'+key.lower()+'_'+hashlib.sha256(str(group).encode()).hexdigest()[:8]
  # All identifier components are developer-defined, never file paths from recipes.
  if not all(c.isalnum() or c=='_' for c in ident):raise ValueError('Invalid internal trace map identifier.')
  if ident in self.snapshots and self.snapshots[ident]['layer']['trace_group']!=str(group):raise ValueError('Processing trace group identity collision; no snapshot was replaced.')
  a=np.asarray(data,dtype='float32')
  if a.ndim!=2:raise ValueError('A processing snapshot must be a two-dimensional map.')
  self.snapshots[ident]={'operation':operation,'layer':{'data':a.copy(),'label':label,'unit':unit,'kind':kind,'interpretation':'Intermediate processing evidence. '+metadata.pop('interpretation','Read this map’s own units and dates; it is not an additional independent finding.'),'trace_operation':operation,'trace_group':str(group),**metadata}}

@contextmanager
def capture(recipe):
 collector=Collector(recipe) if recipe.method=='custom' else None
 token=_ACTIVE.set(collector)
 try:yield collector
 finally:_ACTIVE.reset(token)


def enabled(operation):
 collector=_ACTIVE.get()
 return collector is not None and operation in collector.operations


def snapshot(operation,key,data,label,unit,kind='continuous',group='',**metadata):
 collector=_ACTIVE.get()
 if collector is not None:collector.record(operation,key,data,label,unit,kind,group,**metadata)


def estimated_snapshot_count(steps,items):
 """Conservative extra resident float32 maps; metadata only, no science reads."""
 ops={s.operation for s in steps};groups=max(1,len({i.get('group','') for i in items}))
 weights={'source_smooth':5*groups,'dual_change':2*groups,'surface_baseline':2,'signed_change':1,'event_pairs':groups,'offset_screen':2*groups,'offset_bias':2*groups,'horizontal_velocity':1,'threshold':1,'flood_history':1}
 # Elementary steps already retain their own latest outputs. Only instrumented
 # scientific kernels need these additional resident snapshots.
 scientific=bool(ops&{'water_rule','dual_change','surface_baseline','event_pairs','horizontal_velocity','radar_components'})
 return sum(n for op,n in weights.items() if op in ops) if scientific else 0


def attach(result,recipe,collector):
 if collector is None:return
 layers=result['layers'];extra=result['extra'];stages=[]
 for ident,entry in collector.snapshots.items():
  if ident in layers:raise ValueError('Processing trace would overwrite a result map.')
  shape=next(iter(layers.values()))['data'].shape if layers else entry['layer']['data'].shape
  if entry['layer']['data'].shape!=shape:raise ValueError('An intermediate map does not match the analysis grid.')
  layers[ident]=entry['layer']
 scientific=extra.get('scientific_blocks');post_index=0
 for i,step in enumerate(recipe.steps):
  op=step.operation;captured=[k for k,v in collector.snapshots.items() if v['operation']==op]
  if scientific:
   patterns,diagnostics=EVIDENCE.get(op,([],[]))
   if op=='smooth':patterns=['smoothed_intensity'] if scientific['compiled_method']=='P03' else ['latest_departure']
   elif op=='patches':patterns=['fire_candidate'] if scientific['compiled_method']=='P03' else ['surface','change_direction']
   elif op=='publish':patterns=[scientific['opening_layer']]
   # Post-operations are distinguished by their actual saved workflow_post map.
   post=scientific['post_operations'];last_publish=len(recipe.steps)-1
   if post and last_publish-post<=i<last_publish:
    patterns=['workflow_post_'+str(post_index)];diagnostics=[];captured=[];post_index+=1
   selected=[k for k in layers if k not in collector.snapshots and any(k.startswith(p) if p.endswith('_') else k==p for p in patterns)]
  else:
   selected=['summary'] if op=='summary' else [k for k in [f'step_{i}_latest',f'step_{i}_baseline'] if k in layers]
   if op=='network':selected+=['network_residual']
   if op=='trend':selected+=['trend_residual']
   if op=='los':selected+=['reference_support']
   diagnostics={'network':['network_reconstruction'],'trend':['trend_fit'],'los':['reference_diagnostics'],'rate':['offset_filter_diagnostics']}.get(op,[])
  if op=='event_los':selected=[k for k in selected if not k.startswith('group_') or k.endswith(('_event_displacement_cm','_reference_support'))]
  selected=[k for k in dict.fromkeys(captured+selected) if k in layers]
  refs=[key for key in diagnostics if extra.get(key) is not None]
  parameter_note=None
  calibration=extra.get('water_validation',{})
  if op=='water_rule' and calibration.get('calibration_cells',0)>0:
   parameter_note=f"The recipe's starting threshold was calibrated with {calibration['calibration_cells']} supplied training cells. Effective threshold: {calibration['threshold_db']:g} dB. Training fit is not held-out accuracy; inspect the recorded validation diagnostics."
  stages.append({'step':i+1,'operation':op,'maps':[{'id':key,'role':'Captured intermediate' if key in captured else 'Saved method evidence','unit':layers[key]['unit'],'label':layers[key]['label']} for key in selected if key in layers],'diagnostic_keys':refs,'parameter_note':parameter_note,'map_scope':'Latest captured frame per viewing group/component plus linked saved method maps. Existing dated maps retain their own acquired times.','note':'This block configures part of a compound kernel. Snapshot units describe the actual diagnostic quantity; they need not match the abstract block I/O. Read each map label.' if scientific else 'The latest processed output of this step is saved separately; the final timeline retains its own measurement.','unavailable_reason':extra['tracking']['reason'] if op=='water_tracking' and extra.get('tracking',{}).get('available') is False else None if selected or refs else 'This operation does not create a separate raster or stored diagnostic. Its applied parameters are recorded in the exact recipe.'})
 extra['processing_trace']={'version':VERSION,'stages':stages,'snapshot_maps':len(collector.snapshots),'scope':'Inspectable captured boundaries and linked method evidence; not every internal temporary or every intermediate date is retained. Kernel order is fixed inside compound blocks.','scientific_limits':'Intermediate maps explain calculations; they do not establish environmental accuracy.'}
