"""Standalone presentation raster with an honest legend and reproducibility metadata."""
import base64,io,json
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,PngImagePlugin
from .exports import colorize

INK='#163c3d';MUTED='#536d68';GREEN='#176953'

@lru_cache(maxsize=32)
def font(size,bold=False):
 candidates=('/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
 for name in candidates:
  if Path(name).is_file():return ImageFont.truetype(name,size)
 return ImageFont.load_default(size=size)

def number(value):return f'{value:.4g}'

def legend_spec(info,display,result=None):
 from .result_contracts import explicit_classes
 entries=explicit_classes({**info,'class_values':display.get('class_values',[])},result)
 if entries is not None:return entries
 if info['kind']=='diverging' and info['unit']=='class':return [(v,f'Class {number(v)}') for v in display.get('class_values',[])]
 return None


def parse_view_bounds(extent, value):
 if extent=='result':
  if value is not None:raise ValueError('Choose Current map view to supply map bounds.')
  return None
 if not value:raise ValueError('Current map view requires its visible map bounds.')
 try:bounds=[float(v) for v in value.split(',')]
 except (ValueError,AttributeError):raise ValueError('Invalid current map bounds.')
 limit=np.pi*6378137
 if len(bounds)!=4 or not np.isfinite(bounds).all() or max(map(abs,bounds))>limit+1 or bounds[2]<=bounds[0] or bounds[3]<=bounds[1]:raise ValueError('Choose a valid map view inside the single-world map.')
 return bounds


def render_map(result,info,display,ident,tool_name,directory,basemap=None,place_names=False,overlay_opacity=1,view_bounds=None):
 # Older saved phase summaries keep their interval in extra, rather than
 # layer metadata. Never label a single-pair map with the whole run's span.
 if result.get('project') in ['P04','P05'] and info['id'] in ['range','interval_rate']:
  interval=result.get('extra',{}).get('selected_interval',{})
  info={**interval,**info}
 width,height=1800,1570
 image=Image.new('RGB',(width,height),'#f4f6ef');draw=ImageDraw.Draw(image)
 def text(x,y,value,size=22,color=INK,bold=False):draw.text((x,y),str(value),font=font(size,bold),fill=color)
 def para(x,y,value,max_width,size=22,color=MUTED,line=31):
  # Wrap on measured glyph width; long filenames also break safely.
  value=str(value);words=value.split();lines=[];current=''
  for word in words:
   if draw.textlength(word,font=font(size))>max_width:
    if current:lines.append(current);current=''
    piece=''
    for char in word:
     if draw.textlength(piece+char,font=font(size))>max_width:lines.append(piece);piece=''
     piece+=char
    current=piece;continue
   candidate=(current+' '+word).strip()
   if draw.textlength(candidate,font=font(size))>max_width:lines.append(current);current=word
   else:current=candidate
  if current:lines.append(current)
  for value in lines:text(x,y,value,size,color);y+=line
  return y
 draw.rectangle((0,0,width,16),fill=GREEN)
 text(80,49,'NISAR OBSERVATORY  /  RESULT MAP',18,GREEN,True)
 draw.rounded_rectangle((1430,44,1720,83),radius=18,fill='#e4eddb');text(1460,53,'EXPLORATORY RESULT',16,GREEN,True)
 text(80,91,tool_name,43,INK,True)
 title_end=para(80,154,info.get('label',info['id']),1630,28,INK,37)
 text(80,max(211,title_end+12),f"{result.get('project','')}  ·  {info['unit']}  ·  {'Rainbow' if display.get('palette_name') in ['mexico','rainbow'] else 'Diverging palette' if display.get('palette_name') in ['quake','diverging'] else 'Custom category colors' if display.get('category_colors') else 'Standard palette'}",19,MUTED)
 # Preserve the display projection's aspect ratio, rather than stretching a thumbnail.
 rgba=Image.open(io.BytesIO(base64.b64decode(display['image'].split(',',1)[1]))).convert('RGBA')
 source_merc=display['display_bounds_mercator'];merc=view_bounds if view_bounds is not None else source_merc;aspect=(merc[2]-merc[0])/(merc[3]-merc[1])
 box=(110,300,1280,1050);avail_w=box[2]-box[0];avail_h=box[3]-box[1]
 mw=min(avail_w,round(avail_h*aspect));mh=min(avail_h,round(avail_w/aspect));mw=max(mw,1);mh=max(mh,1)
 mx=box[0]+(avail_w-mw)//2;my=box[1]+(avail_h-mh)//2
 # No-data checker is explicit; valid pixels use the same opaque palette as the legend.
 pixels=np.array(rgba);valid=pixels[:,:,3]>0
 if display.get('category_opacity'):
  valid=np.array(Image.open(io.BytesIO(base64.b64decode(display['validity_image'].split(',',1)[1]))))>0
  # Preserve the category alpha; overall browser overlay opacity is not exported.
 else:pixels[:,:,3]=np.where(valid,255,0)
 if view_bounds is not None:
  from rasterio.warp import reproject,Resampling
  from rasterio.transform import from_bounds
  source_transform=from_bounds(*source_merc,rgba.width,rgba.height);target_transform=from_bounds(*merc,mw,mh)
  target=np.zeros((mh,mw,4),'uint8');target_valid=np.zeros((mh,mw),'uint8')
  for channel in range(4):reproject(pixels[:,:,channel],target[:,:,channel],src_transform=source_transform,src_crs='EPSG:3857',dst_transform=target_transform,dst_crs='EPSG:3857',dst_nodata=0,resampling=Resampling.nearest)
  reproject(valid.astype('uint8'),target_valid,src_transform=source_transform,src_crs='EPSG:3857',dst_transform=target_transform,dst_crs='EPSG:3857',dst_nodata=0,resampling=Resampling.nearest)
  valid=target_valid>0;pixels=target
 rendered=Image.fromarray(pixels).resize((mw,mh),Image.Resampling.NEAREST)
 checker=Image.new('RGB',(mw,mh),'#e7ebe5');cd=ImageDraw.Draw(checker)
 for x in range(0,mw,16):
  for y in range(0,mh,16):
   if (x//16+y//16)%2:cd.rectangle((x,y,x+15,y+15),fill='#f5f7f2')
 # Valid but transparent categories reveal the neutral page; missing observations keep a checker.
 if display.get('category_opacity'):
  valid_mask=Image.fromarray(np.where(valid,255,0).astype('uint8')).resize((mw,mh),Image.Resampling.NEAREST)
  checker.paste(Image.new('RGB',(mw,mh),'#f4f6ef'),(0,0),valid_mask)
 background_meta=None;label_image=None
 if basemap is not None:
  from .basemap_export import background
  checker,label_image,background_meta=background(basemap,place_names,merc,(mw,mh))
  rendered.putalpha(rendered.getchannel('A').point(lambda a:round(a*overlay_opacity)))
  background_meta['radar_overlay_opacity']=overlay_opacity
 if background_meta:checker.alpha_composite(rendered)
 else:checker.paste(rendered,(0,0),rendered)
 # Reference windows are processing context, never an automatic decoration on exports.
 reference_outline=False
 if label_image is not None:checker.alpha_composite(label_image)
 image.paste(checker.convert('RGB'),(mx,my));draw.rectangle((mx,my,mx+mw,my+mh),outline='#aabeb1',width=2)
 from pyproj import Transformer
 inverse=Transformer.from_crs(3857,4326,always_xy=True)
 west,south=inverse.transform(merc[0],merc[1]);east,north=inverse.transform(merc[2],merc[3])
 lon_precision=min(7,max(3,int(np.ceil(-np.log10(max(east-west,1e-9))))+1));lat_precision=min(7,max(3,int(np.ceil(-np.log10(max(north-south,1e-9))))+1))
 for fraction in [0,.5,1]:
  x=mx+int(mw*fraction);lon=west+(east-west)*fraction
  draw.line((x,my+mh,x,my+mh+8),fill=MUTED,width=2);label=f'{lon:.{lon_precision}f}°';text(x-draw.textlength(label,font=font(16))/2,my+mh+13,label,16)
  y=my+int(mh*fraction);_,lat=inverse.transform(merc[0],merc[3]-(merc[3]-merc[1])*fraction)
  draw.line((mx-8,y,mx,y),fill=MUTED,width=2);text(max(6,mx-93),y-10,f'{lat:.{lat_precision}f}°',16)
 text(mx+mw-30,max(250,my-45),'N ↑',20,INK,True)
 if background_meta and background_meta['attribution']:para(80,1093,background_meta['attribution'],1640,14,MUTED,18)
 text(110,1140 if background_meta else 1110,'North up · longitude / latitude · Web Mercator display; geographic scale varies with latitude.',17,MUTED)
 # Metadata rail remains readable when the plotted area is narrow or tall.
 draw.rounded_rectangle((1340,280,1730,1080),radius=14,fill='#e9f0e3')
 y=306
 def fact(label,value):
  nonlocal y
  text(1365,y,label.upper(),15,GREEN,True);y+=27
  y=para(1365,y,value,335,20,INK,28)+24
 sources=result.get('sources',[]);starts=[s.get('start','') for s in sources if s.get('start')];ends=[s.get('end',s.get('start','')) for s in sources if s.get('end') or s.get('start')]
 period=(info.get('start') or (min(starts) if starts else 'Not recorded'))
 if info.get('end') and info.get('end')!=period:period+=' → '+info['end']
 elif not info.get('start') and ends:period+=' → '+max(ends)
 fact('Observation / record · UTC',period.replace('T',' ').replace('Z',''))
 fact('Input evidence',f"{len(sources)} source file{'' if len(sources)==1 else 's'} · {sum(bool(s.get('attributes',{}).get('source_subset')) for s in sources)} native area extracts")
 grid=result.get('grid',{});resolution=grid.get('resolution_m');fact('Analysis cell spacing',f'{number(resolution)} m · not native sensor resolution' if resolution else 'See numeric GeoTIFF')
 fact('Reference',('Relative to the saved processing reference. No reference box is drawn.' if any(l['id']=='reference_support' for l in result['layers']) else 'No spatial reference subtraction in this display.'))
 fact('Display',f"{display['clipped_percent']:.1f}% of valid values outside endpoints. Colors at endpoints are saturated."+(f" Background: {basemap.title()}; radar opacity {overlay_opacity:.0%}." if background_meta else ''))
 text(80,1175,'MAP KEY',17,GREEN,True)
 entries=legend_spec(info,display,result)
 if entries is None:
  vals=np.linspace(display['min'],display['max'],1200,dtype='float32')[None,:]
  bar,_,_=colorize(vals,info['kind'],(display['min'],display['max']),display['palette'],display.get('category_colors'));bar[:,:,3]=255
  image.paste(Image.fromarray(bar).resize((1200,34)),(80,1213))
  for f in [0,.25,.5,.75,1]:text(80+int(1200*f)-(0 if f==0 else 30),1260,number(display['min']+f*(display['max']-display['min'])),19)
  text(1365,1220,info['unit'],27,INK,True)
  legend_note='Clipped values retain their numeric values in the GeoTIFF. '+('One common range across '+str(display.get('shared_frames',1))+' acquired frames.' if display['mode']=='shared' and info['id'].startswith('observation_') else 'Range applies to this displayed layer.')
 else:
  for index,(value,label) in enumerate(entries[:8]):
   row=index//4;col=index%4;x=80+col*405;y=1210+row*42
   color,_,_=colorize(np.array([[value]],'float32'),info['kind'],(display['min'],display['max']),display['palette'],display.get('category_colors'))
   opacity=display.get('category_opacity',{}).get(str(int(value)) if float(value).is_integer() else str(value),1)
   ink=tuple(round(c*opacity+b*(1-opacity)) for c,b in zip(color[0,0,:3],(244,246,239)))
   draw.rectangle((x,y,x+25,y+25),fill=ink,outline='#aabeb1');text(x+35,y,f'{number(value)} · {label}'+(f' ({opacity:.0%})' if opacity!=1 else ''),17)
  legend_note=('Patch colors identify objects; they do not measure severity. '+(f'Showing {min(8,len(entries))} of {len(entries)} IDs; all IDs remain in the numeric GeoTIFF.' if len(entries)>8 else '')) if info['kind']=='categorical' else 'Category colors and opacity are display choices. Class numbers are labels, not a continuous physical scale.'
  if info['id']=='event_source':legend_note='Colors identify source groups, not displacement severity. Read group dates and references in the result JSON and event-mosaic table.'
  if info['unit']=='observation index':legend_note=f'Indices identify observed dates, not elapsed days. Showing {min(8,len(entries))} of {len(entries)} mapped indices; all mapped index/date labels are embedded in PNG metadata and retained in the result JSON.'
 draw.rectangle((1470,1170,1490,1190),fill='#e7ebe5',outline='#aabeb1');text(1500,1168,'No valid radar result' if background_meta else 'No valid result',17)
 if display.get('category_opacity') and not background_meta:legend_note+=' Category opacity is preserved against a neutral page; checker areas indicate missing observations. No basemap is included.'
 if view_bounds is not None:legend_note+=' Current map view; colour limits are unchanged.'
 if not valid.any():legend_note+=' No valid radar observations fall inside this view.'
 if background_meta:legend_note+=' Background-only areas have no valid radar result. Background dates may differ from NISAR.'
 note_end=para(80,1310,legend_note,1640,18,MUTED,24)
 interpretation='Read the tool method, quality evidence and selected dates before attributing a cause. A completed run does not establish independent scientific accuracy.'
 if not info.get('trace_operation') and result.get('project')=='P04' and info['kind']=='diverging' and info['unit']!='class':
  temporal=('A rate annualizes the observed record; it is not a year of measurements.' if info['unit'] in ['cm/year','cm/month'] else 'Accumulated change is relative to the first acquired date; unobserved dates are not filled in.' if info.get('frame_scope')=='epoch' or info['unit']=='cm' else 'This is an individual pair interval or interval-average rate, not a cumulative displacement history.')
  interpretation='Positive LOS: toward the satellite. Negative: away, relative to the chosen reference. This is not direct vertical subsidence. '+temporal
 if not info.get('trace_operation') and result.get('project')=='P05' and info['kind']=='diverging':
  interpretation='Relative LOS: positive toward satellite, negative away. Horizontal and vertical motion are mixed. Different groups may use different dates and reference cells. This is not a damage map.'
 if info.get('trace_operation'):interpretation=info.get('interpretation','Intermediate processing evidence. Read the stated units and dates; this is not an additional independent finding.')
 para(80,max(1380,note_end+8),interpretation,1640,20,INK,28)
 draw.line((80,1470,1720,1470),fill='#c9d6c5',width=2)
 text(80,1490,f"NASA–ISRO NISAR inputs · algorithm {result.get('algorithm_version','not recorded')} · run {ident[:12]}",17,MUTED)
 text(80,1520,('Presentation raster · with map background · ' if background_meta else 'Presentation raster · no basemap · ')+'PNG has no georeferencing · use the numeric GeoTIFF for GIS analysis.',16,MUTED)
 metadata={'tool':result.get('project'),'tool_name':tool_name,'layer':info,'scale':{k:display.get(k) for k in ['min','max','mode','palette_name','clipped_percent','shared_frames','class_values']},'palette':display['palette'],'category_colors':display.get('category_colors',{}),'category_opacity':display.get('category_opacity',{}),'categories':display.get('categories',[]),'legend_classes':entries,'grid':grid,'reference_outline':reference_outline,'basemap':background_meta,'export_extent':'current_view' if view_bounds is not None else 'full_result','bounds_mercator':list(merc),'result_bounds_mercator':list(source_merc),'visible_radar_fraction':float(np.mean(valid)),'processing_reference_bbox':result.get('processing_options',{}).get('reference_bbox'),'run_id':ident,'algorithm_version':result.get('algorithm_version'),'sources':[{k:s.get(k) for k in ['id','name','start','end']} for s in sources],'interpretation':interpretation}
 pnginfo=PngImagePlugin.PngInfo();pnginfo.add_text('Title',f"{tool_name} — {info.get('label',info['id'])}");pnginfo.add_text('NISAR_Observatory',json.dumps(metadata,ensure_ascii=False,allow_nan=False));pnginfo.add_text('Description','Presentation map with legend; not a georeferenced numeric raster. NASA–ISRO inputs; exploratory scientific interpretation.')
 output=io.BytesIO();image.save(output,format='PNG',pnginfo=pnginfo,dpi=(200,200));return output.getvalue()
