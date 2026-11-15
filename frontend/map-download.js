function mountMapExportControls(base){
 const host=$('#map-export-panel');if(!host)return;
 host.innerHTML=`<div class="map-export-heading"><div><h3>Download this map</h3><p id="map-export-layer" class="small">Preparing the displayed layer…</p></div>${state.result?.extra?.workflow?`<a href="${base}workflow.json" download class="small">Processing recipe · JSON ↓</a>`:''}<a href="${base}result.json" download class="small">Run record · JSON ↓</a></div><div class="downloads map-export-options"><label class="png-extent-choice" for="png-extent">PNG area<select id="png-extent"><option value="result">Full result area</option><option value="view">Current map view · zoom &amp; surroundings</option></select></label><label class="export-background-choice"><input type="checkbox" id="export-background"> Include background</label><a id="map-image-link" class="download-button primary" aria-disabled="true">↓ Download PNG</a><a id="raster-link" class="download-button secondary">↓ Download GeoTIFF</a></div><p class="small export-explanation">PNG keeps the colour scale and legend; place names follow the map switch. GeoTIFF contains the full saved numeric layer, regardless of the PNG area. Reference outlines are omitted from PNGs.</p><p id="map-export-status" class="small" role="status" aria-live="polite"></p>`;
}
function currentMapExportBounds(){
 if(typeof map==='undefined'||!map)return null;
 const bounds=map.getBounds(),sw=map.options.crs.project(bounds.getSouthWest()),ne=map.options.crs.project(bounds.getNorthEast());
 const limit=Math.PI*6378137;return [Math.max(-limit,sw.x),Math.max(-limit,sw.y),Math.min(limit,ne.x),Math.min(limit,ne.y)];
}
/* The link follows the active layer, applied scale and optional geographic context. */
function refreshMapImageDownload(){
 const current=state.mapImageExport,link=$('#map-image-link');if(!current||!link||!state.currentJob||!state.result)return;
 if($('#map-export-layer'))$('#map-export-layer').textContent='Displayed layer: '+(current.layer.label||current.layer.id)+' · '+(current.layer.unit||'');
 const include=$('#export-background')?.checked===true,query=new URLSearchParams(current.query);
 const scope=$('#png-extent')?.value||'result';
 if(scope==='view'){const bounds=currentMapExportBounds();if(bounds){query.set('extent','view');query.set('view_bbox',bounds.join(','))}}
 if(include){query.set('basemap',$('#basemap-select')?.value||'satellite');query.set('place_names',String($('#basemap-labels')?.checked===true));query.set('overlay_opacity',String(Number($('#layer-opacity')?.value??.9)))}
 link.href=`/api/map-image/${state.currentJob.id}/${state.result.project}/${current.layer.id}?${query}`;
 link.download=`${state.result.project.toLowerCase()}_${current.layer.id}_map.png`;
 link.title=include?'Download this result with the selected background, place names, overlay opacity, scale and source credits.':'Download the current map with its palette, scale, units, dates and source notes. No basemap imagery is included.';
}
function syncMapImageDownload(layer,query){
 const link=$('#map-image-link');if(!link)return;
 if(!state.mapImageExportBusy&&$('#map-export-status'))$('#map-export-status').textContent='';
 state.mapImageExport={layer,query:String(query)};link.hidden=false;
 if(state.mapImageExportBusy){link.setAttribute('aria-disabled','true');if($('#map-export-status'))$('#map-export-status').textContent='Finishing PNG for '+(state.mapImageExportLabel||'the previous map')+'…'}else link.removeAttribute('aria-disabled');
 refreshMapImageDownload();
 const toggle=$('#export-background');if(toggle)toggle.onchange=refreshMapImageDownload;
 const extent=$('#png-extent');if(extent)extent.onchange=refreshMapImageDownload;
 link.onclick=async event=>{
  event.preventDefault();if(state.mapImageExportBusy)return;
  refreshMapImageDownload();
  const url=link.href,filename=link.download,label=state.mapImageExport?.layer?.label||state.mapImageExport?.layer?.id||'this map';state.mapImageExportBusy=true;state.mapImageExportLabel=label;link.setAttribute('aria-disabled','true');
  const report=message=>{const status=$('#map-export-status');if(status)status.textContent=message;else toast(message)};
  const sameView=()=>$('#map-image-link')===link&&link.href===url;
  report(toggle?.checked?'Preparing PNG with map background and source credits…':'Preparing result PNG…');
  try{
   const response=await (typeof fetchRenderedMap==='function'?fetchRenderedMap(url,{onWaiting:()=>report('Waiting to prepare PNG for '+label+'…')}):fetch(url));
   if(!response.ok){let message='The PNG export could not finish. Please try again.';try{const body=await response.json();if(typeof body.detail==='string')message=body.detail}catch{}throw Error(message)}
   const blob=await response.blob(),objectUrl=URL.createObjectURL(blob),download=document.createElement('a');download.href=objectUrl;download.download=filename;document.body.append(download);download.click();download.remove();setTimeout(()=>URL.revokeObjectURL(objectUrl),60000);
   report(sameView()?'PNG ready. Your numeric GeoTIFF is unchanged.':'Previous PNG ready: '+label+'.'+(state.mapImageExport&&!$('#map-image-link')?.hidden?' You can now download the displayed map.':''));
  }catch(error){report((sameView()?'':'Previous PNG export: ')+error.message)}finally{state.mapImageExportBusy=false;state.mapImageExportLabel=null;link.removeAttribute('aria-disabled');const current=$('#map-image-link');if(current&&state.mapImageExport&&!current.hidden)current.removeAttribute('aria-disabled')}
 };
}
