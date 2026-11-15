/* Native area extraction is separate from complete-original downloads. */
function areaContains(outer,inner){return Array.isArray(outer)&&Array.isArray(inner)&&outer[0]<=inner[0]&&outer[1]<=inner[1]&&outer[2]>=inner[2]&&outer[3]>=inner[3]}
function areaDownloadItems(){return (state.catalog[state.tab]?.items||[]).filter(i=>state.checked.has(i.id))}
function areaAlreadySaved(item){return !!state.bbox&&state.localFiles.some(s=>s.subset&&(s.source_id===(item.source_id||item.id))&&areaContains(s.subset_bbox,state.bbox))}
function updateAreaDownload(){
 const button=$('#download-area-button');if(!button)return;
 const items=areaDownloadItems(),pending=items.filter(i=>!i.subset&&!areaAlreadySaved(i));
 button.disabled=!state.bbox||!pending.length;
 button.textContent=!items.length?'Select analysis rows to save their area':!pending.length?'Selected area already saved':`Save area from ${pending.length} ${state.tab} file${pending.length===1?'':'s'} ↓`;
}
function openAreaDownload(){
 const items=areaDownloadItems().filter(i=>!i.subset&&!areaAlreadySaved(i));
 if(!state.bbox||!items.length){toast('Select your rectangle and check Use in analysis beside source files in this product tab. Saved area extracts can be reused through Use saved data.');return}
 const bbox=[...state.bbox],revision=state.areaRevision;let dialog=$('#area-download-dialog');
 if(!dialog){dialog=document.createElement('dialog');dialog.id='area-download-dialog';dialog.setAttribute('aria-labelledby','area-download-title');document.body.append(dialog)}
 const area=NisarCatalogGuide.rectangleKm2(bbox);
 dialog.innerHTML=`<span class="eyebrow">SMALLER LOCAL INPUTS</span><h2 id="area-download-title">Save only your selected area</h2><p><b>${items.length} ${esc(state.tab)} source file${items.length===1?'':'s'} · ${area?.toLocaleString(undefined,{maximumFractionDigits:2})} km²</b></p><p>Rectangle: ${bbox.map(v=>v.toFixed(5)).join(', ')} (west, south, east, north).</p><div class="info-note"><b>What you keep</b><p>Native-resolution geocoded science and quality layers within this rectangle, plus a small edge buffer for reading and map projection. No quality threshold or analysis-grid averaging is applied during saving. Analyses use your drawn rectangle.</p></div><p><b>What changes?</b> These are local area extracts, not complete NASA products. Other large or non-geocoded auxiliary arrays are omitted. You can change thresholds, reference areas and analysis settings within the saved area. To study ground outside it, save a new area or the complete original.</p><p><b>Size:</b> known after extraction. Remote reads include HDF5 metadata and storage chunks, so transferred bytes can exceed the saved file size. The app does not silently fall back to a full download. Existing local originals are read without a network transfer. Limits: 256 MiB remote reads per source, 8 million native pixels per layer and 512 MiB of uncompressed science arrays per extract; use a smaller rectangle if needed.</p><p>Each product/download batch is saved under <code>data/subsets/PRODUCT_YYYY-MM-DD_HH-MM-SS_UTC/</code>. Completed extracts remain available through <b>Use saved data</b> and <b>Runs</b>. Each HDF5 embeds its source and saved-area bounds. To import manually later, choose Import subset folder and select the folder once, or import individual .h5 files. JSON files are optional.</p><div class="run-actions"><button type="button" class="secondary" id="area-download-cancel">Back</button><button type="button" class="primary" id="area-download-confirm">Save selected area ↓</button></div><p class="error" id="area-download-error" role="alert"></p>`;
 $('#area-download-cancel').onclick=()=>dialog.close();
 $('#area-download-confirm').onclick=async()=>{
  const button=$('#area-download-confirm');button.disabled=true;
  try{
   if(revision!==state.areaRevision)throw new Error('The area changed. Close this dialog and review the new rectangle.');
   const j=await api('/api/download-area',{method:'POST',body:JSON.stringify({bbox,granules:items.map(i=>i.id)})});dialog.close();watchJob(j.id);
  }catch(error){$('#area-download-error').textContent=error.message;button.disabled=false}
 };
 dialog.showModal();
}
async function finishAreaDownload(job,revision){
 await refreshLocalFiles();
 const compatible=areaContains(job.request?.bbox,state.bbox)&&revision===state.areaRevision;
 if(compatible){
  for(const item of job.saved_areas||[]){
   const catalog=state.catalog[item.product]??={items:[],hits:0};
   const originals=catalog.items.filter(i=>(i.source_id||i.id)===item.source_id);
   const selected=originals.some(i=>state.checked.has(i.id));
   originals.forEach(i=>{state.checked.delete(i.id);state.downloadChecked.delete(i.id)});
   catalog.items=catalog.items.filter(i=>!originals.includes(i));catalog.items.push(item);catalog.hits=catalog.items.length;
   if(selected)state.checked.add(item.id);
  }
  renderCatalog();
 }
 let dialog=$('#area-download-report');if(!dialog){dialog=document.createElement('dialog');dialog.id='area-download-report';document.body.append(dialog)}
 dialog.innerHTML=`<h2>Selected-area download · ${esc(job.status.replaceAll('_',' '))}</h2><p>${esc(job.message)}</p>${(job.source_errors||[]).map(e=>`<div class="warning-note"><b>${esc(e.name)}</b><p>${esc(e.message)}</p></div>`).join('')}<p>${compatible?'Saved extracts are now selected in your observation table. Choose a tool and run it.':'Your current area has been kept. Draw an area inside the saved rectangle and choose Use saved data to load these extracts.'}</p>${(job.download_folders||[]).length?`<div class="info-note"><b>Saved folders · UTC date and time</b><ul>${job.download_folders.map(folder=>`<li><code>data/subsets/${esc(folder)}/</code></li>`).join('')}</ul><p>For manual import, choose <b>Import subset folder</b> and select this folder once. All its HDF5 files are loaded; other files are skipped. You can also use <b>Import .h5 data</b> for individual files. Source details and saved-area bounds are embedded; JSON sidecars are optional.</p></div>`:''}<p>Complete originals have been kept if already present. Saved extracts remain available after restarting the app.</p>${!compatible&&job.saved_areas?.length?'<button type="button" class="secondary" id="area-report-load">Load saved rectangle</button>':''}<button type="button" class="primary" id="area-report-close">Continue</button>`;
 $('#area-report-close').onclick=()=>dialog.close();if($('#area-report-load'))$('#area-report-load').onclick=async()=>{dialog.close();drawArea(job.request.bbox);await useLocalFiles()};dialog.showModal();
}
if(typeof document!=='undefined')document.getElementById('download-area-button')?.addEventListener('click',openAreaDownload);

async function prepareOffsetGeometry(){
 const items=Object.values(state.catalog).flatMap(c=>c.items||[]).filter(i=>i.product==='GOFF'&&state.checked.has(i.id));
 if(!state.bbox||!items.length){toast('Choose an area and select GOFF observations in Explore Earth first. Then prepare their viewing geometry.');return false}
 try{const job=await api('/api/download-geometry',{method:'POST',body:JSON.stringify({bbox:state.bbox,granules:items.map(i=>i.id)})});view('explore');watchJob(job.id);return true}catch(e){toast(e.message);return false}
}
if(typeof document!=='undefined')document.getElementById('prepare-offset-geometry')?.addEventListener('click',prepareOffsetGeometry);
