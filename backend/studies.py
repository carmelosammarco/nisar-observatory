"""Read-only study summaries, bounded saved-run comparisons and portable reports."""
import base64
import hashlib
import html
import json
import re
from pathlib import Path

import numpy as np
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from .result_contracts import method_for, reading_guide
from .study_stories import story,general_story

ID = re.compile(r'^[a-f0-9]{32}$')
LAYER = re.compile(r'^[a-z0-9_]{1,120}$')


def load_result(root, ident, pid):
 if ident.startswith('example-'):
  from .recorded_studies import recorded
  _,result,directory=recorded(ident[len('example-'):])
  if result.get('project')!=pid:raise HTTPException(404,'Recorded product does not match this example.')
  return result,directory
 if not ID.fullmatch(ident) or pid not in ('LAB','P01','P02','P03','P04','P05','P06','P07'):
  raise HTTPException(404,'Saved study not found.')
 directory=Path(root)/ident/pid
 if directory.is_symlink() or not directory.resolve().is_relative_to(Path(root).resolve()):
  raise HTTPException(404,'Saved study not found.')
 try:
  path=directory/'result.json'
  if path.is_symlink() or path.stat().st_size>16*1024**2:raise ValueError('Invalid result record.')
  result=json.loads(path.read_text())
  if not isinstance(result.get('layers'),list):raise ValueError('Missing saved layers.')
 except (OSError,ValueError,TypeError):raise HTTPException(404,'Saved study is unavailable; its files were not changed.') from None
 return result,directory


def matching_example(result):
 """A source match supplies context; only exact settings permit replay wording."""
 from .examples import CASES,definition
 names=sorted(s.get('name','') for s in result.get('sources',[]))
 for ident in CASES:
  case=definition(ident)
  if names and names==sorted(s['name'] for s in case['sources']) and result.get('grid',{}).get('bbox')==case['request']['bbox']:
   options=result.get('processing_options',{})
   exact=all(options.get(k)==v for k,v in case['request'].get('options',{}).items())
   # Elementary/custom output transforms change the study even with the same source settings.
   extra=result.get('extra',{})
   actual_method=method_for(result)
   if actual_method=='LAB' and extra.get('los_series'):actual_method='P04'
   if actual_method!=case['tool']:exact=False
   workflow=extra.get('workflow')
   if workflow and workflow.get('method')=='custom':
    from .workflow_templates import example_recipe
    from .workflows import Recipe
    expected=Recipe.model_validate(example_recipe(ident)).model_dump(mode='json')['steps']
    if workflow.get('steps')!=expected:exact=False
   if extra.get('workflow_output_statistics') or extra.get('scientific_blocks',{}).get('source_smoothing') is not None:exact=False
   return {'id':ident,'title':case['title'],'exact_settings':exact,
           'evidence':case.get('comparison_review',{}),'references':case.get('references',[])}
 return None


def study_summary(result):
 method=method_for(result)
 extra=result.get('extra',{})
 if method=='LAB' and extra.get('los_series'):method='P04'
 example=matching_example(result)
 interpretation=story(method) if example and example['id'].startswith(method+'_') else general_story(method)
 guide=result.get('reading_guide') or reading_guide(result)
 sources=result.get('sources',[])
 times=sorted(s[k] for s in sources for k in ('start','end') if s.get(k))
 return {'method':method,'title':result.get('title','Experimental study'),
         'record':{'start':times[0] if times else None,'end':times[-1] if times else None,'source_count':len(sources)},
         'observed':guide.get('measurement','Read the saved measurement units.'),
         'findings':result.get('report',{}).get('findings',[]),
         'interpretation':interpretation,'checks':guide.get('checks',''),
         'cannot':guide.get('cannot','Independent evidence is required before assigning a physical cause.'),
         'example':example,
         'validation':'Source integrity, numerical reproducibility and independent environmental accuracy are different checks. A completed analysis does not establish scientific accuracy.'}


def _value(value):
 text=json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,default=str)
 if len(text)>500:return f'Complex spatial/context value · SHA-256 {hashlib.sha256(text.encode()).hexdigest()[:16]}'
 return text


def compare_settings(before,after):
 """Compare actual science and steps, excluding display styles and recipe names."""
 from .analysis_options import AnalysisOptions
 defaults=AnalysisOptions().model_dump(mode='json')
 a={'options':{**defaults,**before.get('processing_options',{})},'steps':before.get('extra',{}).get('workflow',{}).get('steps',[])}
 b={'options':{**defaults,**after.get('processing_options',{})},'steps':after.get('extra',{}).get('workflow',{}).get('steps',[])}
 rows=[]
 for kind in ('options','steps'):
  if kind=='steps':
   if a[kind]!=b[kind]:
    def describe(steps,result):
     if not steps:return 'Guided '+study_summary(result)['method']+' · internal sequence; exact scientific options compared above'
     return ' → '.join(str(i+1)+'. '+s.get('operation','step').replace('_',' ')+' '+_value(s.get('parameters',{})) for i,s in enumerate(steps))
    rows.append({'setting':'Ordered processing steps','before':describe(a[kind],before),'after':describe(b[kind],after)})
  else:
   for key in sorted(a[kind].keys()|b[kind].keys()):
    if a[kind].get(key)!=b[kind].get(key):rows.append({'setting':key,'before':_value(a[kind].get(key)),'after':_value(b[kind].get(key))})
 return rows


def compare_results(before,after,left_dir,right_dir):
 """Never resample or compare unlike quantities merely because colours match."""
 import rasterio
 changes=compare_settings(before,after)
 source_key=lambda r:sorted((s.get('name',''),s.get('start',''),s.get('end',''),s.get('group','')) for s in r.get('sources',[]))
 same_sources=source_key(before)==source_key(after) and bool(before.get('sources'))
 same_area=before.get('grid',{}).get('bbox')==after.get('grid',{}).get('bbox')
 same_method=study_summary(before)['method']==study_summary(after)['method']
 rows=[]
 right={l['id']:l for l in after['layers']}
 aliases={'los_rate_year':'summary','los_change':'change','los_fit_residual':'trend_residual','los_pair_residual':'network_residual'} if study_summary(before)['method']=='P04' else {}
 for left in before['layers']:
  key=left['id'];other=right.get(key)
  if other is None:
   alternate=aliases.get(key) if before.get('project')!='LAB' else next((a for a,b in aliases.items() if b==key),None)
   other=right.get(alternate)
  if not LAYER.fullmatch(key) or other is None:continue
  row={'id':key,'before_layer':key,'after_layer':other['id'],'label':left.get('label',key),'unit':left.get('unit'),'available':False}
  if not (same_sources and same_area and same_method):row['reason']='Numeric comparison requires the same source observations, geographic area and method. Review these studies separately.'
  elif (left.get('unit'),left.get('kind'),left.get('spatial_scope'))!=(other.get('unit'),other.get('kind'),other.get('spatial_scope')):row['reason']='Quantity, category type or spatial scope differs.'
  elif left.get('classes')!=other.get('classes'):row['reason']='Category meanings differ; class numbers cannot be compared as the same condition.'
  else:
   paths=[Path(left_dir)/(key+'.tif'),Path(right_dir)/(other['id']+'.tif')]
   if any(p.is_symlink() for p in paths):row['reason']='A saved raster is not a regular study file.'
   else:
    try:
     with rasterio.open(paths[0]) as a,rasterio.open(paths[1]) as b:
      if a.shape!=b.shape or a.crs!=b.crs or a.transform!=b.transform:row['reason']='Analysis grids differ. No automatic resampling or misleading pixel comparison is performed.'
      elif a.width*a.height>4_000_000:row['reason']='This comparison exceeds the bounded map size.'
      else:
       common_count=left_count=right_count=changed=0;sum_delta=sum_abs=0.;maximum=0.
       for _,window in a.block_windows(1):
        from .execution import checkpoint
        checkpoint()
        x=a.read(1,window=window,masked=True).filled(np.nan).astype('float64');y=b.read(1,window=window,masked=True).filled(np.nan).astype('float64')
        common=np.isfinite(x)&np.isfinite(y);delta=y[common]-x[common]
        left_count+=int(np.isfinite(x).sum());right_count+=int(np.isfinite(y).sum());common_count+=len(delta)
        changed+=int(np.count_nonzero(delta));sum_delta+=float(delta.sum());sum_abs+=float(np.abs(delta).sum())
        if len(delta):maximum=max(maximum,float(np.abs(delta).max()))
       if not common_count:row['reason']='No jointly valid cells. Missing support is not zero difference.'
       else:
        categorical=left.get('unit')=='class' or left.get('kind') in ('binary','categorical','water_state') or left.get('unit')=='observation index'
        row.update(available=True,common_cells=common_count,before_valid_cells=left_count,after_valid_cells=right_count,changed_cells=changed,changed_percent=100*changed/common_count,quantity_type='category agreement' if categorical else 'measurement difference')
        if not categorical:row.update(mean_change=sum_delta/common_count,mean_absolute_change=sum_abs/common_count,maximum_absolute_change=maximum)
    except (OSError,rasterio.errors.RasterioError):row['reason']='A saved raster is missing or unreadable; no comparison was invented.'
  rows.append(row)
 return {'same_sources':same_sources,'same_area':same_area,'same_method':same_method,'settings':changes,'layers':rows,
         'meaning':'Differences are experiment sensitivity on jointly valid cells, not accuracy or confidence. Numeric changes use after minus before. Changing support changes the comparison population.'}


def report_processing_record(result):
 """Keep the declared order and actual sampled series inspectable offline."""
 esc=lambda value:html.escape(str(value),quote=True)
 steps=result.get('extra',{}).get('workflow',{}).get('steps',[])
 document='<h2>Declared processing sequence</h2>'
 if steps:
  document+='<ol>'+''.join('<li><b>'+esc(step.get('operation','Processing step')).replace('_',' ')+'</b><pre>'+esc(json.dumps(step,indent=2,ensure_ascii=False))+'</pre></li>' for step in steps)+'</ol>'
 else:document+='<p>Guided method '+esc(study_summary(result)['method'])+'. The exact scientific options and algorithm identity are recorded below. Use the application’s editable-workflow export to inspect or change its declared steps.</p>'
 series=result.get('series',[])
 if series:
  keys=list(dict.fromkeys(key for row in series for key in row))
  document+='<h2>Acquired observation summaries</h2><p>Only sampled dates or measured pair intervals are listed. Missing times are unobserved. Column names retain their recorded units; a regional median can hide local variation.</p><div class="wide"><table><thead><tr>'+''.join('<th>'+esc(key.replace('_',' '))+'</th>' for key in keys)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(row.get(key,'—'))+'</td>' for key in keys)+'</tr>' for row in series)+'</tbody></table></div>'
 return document


def report_html(result,summary,png,layer,ident):
 """Self-contained escaped HTML. No scripts, network images or private paths."""
 esc=lambda v:html.escape(str(v),quote=True)
 paragraphs=lambda values:''.join('<li>'+esc(v)+'</li>' for v in values)
 rows=lambda values:''.join('<tr><th>'+esc(k)+'</th><td>'+esc(_value(v))+'</td></tr>' for k,v in values)
 sources=''.join('<tr>'+''.join('<td>'+esc(s.get(k,''))+'</td>' for k in ('name','start','end','group'))+'</tr>' for s in result.get('sources',[]))
 narrative=summary['interpretation'];case=summary.get('example');references=''
 if case:
  references='<h2>Case-study context</h2><p>'+esc(case['title'])+'. '+('Recorded case settings match.' if case['exact_settings'] else 'Settings differ: this run is a new experiment and does not inherit the case evaluation.')+'</p>'
  references+='<ul>'+''.join('<li><a href="'+esc(r['url'])+'">'+esc(r['title'])+'</a> — '+esc(r.get('description',''))+'</li>' for r in case['references'] if str(r.get('url','')).startswith('https://'))+'</ul>'
 options={k:v for k,v in result.get('processing_options',{}).items() if k not in ('reference_assistant_id','reference_candidate_id')}
 # Full geometry is portable in the workflow/result JSON; do not turn a report into a coordinate dump.
 if 'spatial_context' in options:options['spatial_context']={'features':len((options['spatial_context'] or {}).get('features',[])),'identity':hashlib.sha256(json.dumps(options['spatial_context'],sort_keys=True).encode()).hexdigest()}
 image='data:image/png;base64,'+base64.b64encode(png).decode()
 return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(summary['title'])+' · NISAR study</title><style>body{margin:0;background:#f4f6ef;color:#173d3b;font:16px/1.65 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:40px 24px}header{border-bottom:3px solid #176953;padding-bottom:24px}h1{font:42px/1.15 Georgia,serif}h2{margin-top:36px}img{width:100%;height:auto;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.wide{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;overflow-wrap:anywhere}th,td{padding:10px;text-align:left;border-bottom:1px solid #ccd8ce;vertical-align:top}th{font-weight:600}a{color:#176953}.note{background:#e5edde;padding:18px;border-radius:10px}figure{margin:28px 0}figcaption{font-size:13px}@media print{body{background:white}main{padding:0}h2,figure,tr{break-inside:avoid}a{color:inherit}}</style><main><header><p>NISAR OBSERVATORY · SAVED STUDY REPORT</p><h1>'+esc(summary['title'])+'</h1><p>'+esc(summary['observed'])+'</p><p>'+esc(summary['record']['start'])+' → '+esc(summary['record']['end'])+' · '+esc(summary['record']['source_count'])+' source files · UTC</p><p>Saved run '+esc(ident)+' · generated from stored results; no new processing.</p></header><figure><img alt="Result map with its own scale, legend and interpretation" src="'+image+'"><figcaption>'+esc(layer.get('label',layer['id']))+' · '+esc(layer.get('unit',''))+'. No basemap is required to read this portable report. Display choices do not change numeric data.</figcaption></figure><h2>What this run found</h2><ul>'+paragraphs(summary['findings'] or ['Read the measurement summaries and saved processing steps; no automatic physical attribution is made.'])+'</ul><h2>What could explain the pattern?</h2><p>'+esc(narrative['driver'])+'</p><h3>Other explanations to check</h3><ul>'+paragraphs(narrative['alternatives'])+'</ul><h2>How this can be used</h2><p>'+esc(narrative['use'])+'</p><h2>What would confirm the interpretation?</h2><p>'+esc(narrative['confirm'])+'</p><p class="note">'+esc(summary['cannot'])+' '+esc(summary['validation'])+'</p>'+references+report_processing_record(result)+'<h2>Recorded measurements</h2><table><tbody>'+rows(result.get('metrics',{}).items())+'</tbody></table><h2>Processing settings</h2><table><tbody>'+rows(options.items())+'</tbody></table><h2>Source observations</h2><table><thead><tr><th>NASA filename</th><th>Start · UTC</th><th>End · UTC</th><th>Group</th></tr></thead><tbody>'+sources+'</tbody></table><h2>Reproducibility</h2><p>Application '+esc(result.get('application_version','not recorded'))+' · algorithm '+esc(result.get('algorithm_version','not recorded'))+' · execution '+esc(result.get('extra',{}).get('execution_fingerprint','not recorded'))+'</p><p>Keep the numeric GeoTIFF, complete result JSON and exact workflow JSON with this report. The HTML is self-contained and can be printed or saved as PDF using your browser. It does not contain satellite input files or Earthdata credentials.</p><h2>Recorded limitations</h2><ul>'+paragraphs(result.get('notes',[]))+'</ul></main></html>'


def install(api):
 from . import app as service
 from .render_admission import render_admission
 from .display_settings import DisplaySettings

 class Comparison(BaseModel):
  model_config=ConfigDict(extra='forbid')
  before:str=Field(pattern=r'^(?:[a-f0-9]{32}|example-P0[1-7]_[A-Za-z_]+)$')
  before_product:str=Field(pattern=r'^(LAB|P0[1-7])$')
  after:str=Field(pattern=r'^[a-f0-9]{32}$')
  after_product:str=Field(pattern=r'^(LAB|P0[1-7])$')

 @api.get('/api/studies/{ident}/{pid}')
 def summary(ident:str,pid:str):
  result,_=load_result(service.JOBS_DIR,ident,pid)
  return study_summary(result)

 @api.post('/api/studies/compare')
 @render_admission
 def compare(body:Comparison):
  left,a=load_result(service.JOBS_DIR,body.before,body.before_product)
  right,b=load_result(service.JOBS_DIR,body.after,body.after_product)
  return compare_results(left,right,a,b)

 @api.post('/api/studies/{ident}/{pid}/report')
 @render_admission
 def report(ident:str,pid:str,display:DisplaySettings):
  result,_=load_result(service.JOBS_DIR,ident,pid)
  layer=next((l for l in result['layers'] if l['id']==display.layer),None)
  if layer is None or layer.get('unit')!=display.unit:raise HTTPException(422,'Choose an available saved map with its original unit.')
  # Reuse the existing legend/palette renderer, including categorical styles.
  colors=display.category_colors.get(display.layer,{})
  opacity=display.category_opacity.get(display.layer,{})
  png=service.map_image(ident,pid,display.layer,display.mode,display.low,display.high,display.palette,json.dumps(colors),json.dumps(opacity))
  document=report_html(result,study_summary(result),png.body,layer,ident)
  return HTMLResponse(document,headers={'Content-Disposition':f'attachment; filename="nisar-study-{ident[:8]}.html"','Content-Security-Policy':"default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})
