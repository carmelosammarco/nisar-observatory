/* Guided discovery and controlled experiments. Numeric methods live in the backend. */
const StudyExperience=(()=>{
 let resultVersion=0,comparisonVersion=0,observationMaps=[],experimentMaps=[];
 const method=result=>result.extra?.workflow_method||(result.extra?.los_series?'P04':result.project);
 const date=value=>value?String(value).replace('T',' ').replace('Z',' UTC'):'Not recorded';
 function entry(){
  const root=$('#explore');if(!root||$('#study-entry'))return;
  const panel=document.createElement('section');panel.id='study-entry';panel.className='study-entry';panel.setAttribute('aria-labelledby','study-entry-title');
  panel.innerHTML='<div><span class="eyebrow">A QUESTION. REAL OBSERVATIONS. A REPEATABLE RESULT.</span><h2 id="study-entry-title">How would you like to begin?</h2><p>Follow a documented story, or investigate your own place. The laboratory stays available when you are ready to experiment.</p></div><div class="study-entry-actions"><button type="button" class="primary" id="study-start-example">Explore a documented example →</button><button type="button" class="secondary" id="study-start-area">Investigate my own area ↓</button></div>';
  const intro=root.querySelector('.intro');if(intro)intro.after(panel);else root.prepend(panel);
  $('#study-start-example').onclick=()=>{resetExamplesView();view('examples')};
  $('#study-start-area').onclick=()=>{const target=$('#draw-area');PageNavigation.focus(target,{scroll:true});toast('Draw a small area or choose a place. Next, find observations before choosing a processing method.')};
 }
 function storyHTML(m){
  const s=m.story;if(!s)return '';
  return `<section class="study-story" aria-labelledby="study-question-title"><div class="study-story-heading"><span class="eyebrow">FOLLOW THE EVIDENCE</span><h2 id="study-question-title">${esc(s.question)}</h2><p>${esc(s.context)}</p><span class="study-audience">For ${esc(s.audience.toLowerCase())}</span><div class="study-actions"><button type="button" class="primary" id="study-recorded-example">Explore the recorded result →</button><button type="button" class="secondary" id="study-run-it-yourself">Run it yourself ↓</button></div><p class="small">Recorded results were computed previously from the protected inputs. Explore their maps immediately, or create a new saved analysis. No Earthdata login is needed.</p><p id="study-recorded-status" role="status"></p></div><ol class="study-journey" aria-label="Study journey"><li><b>01</b> Ask a question</li><li><b>02</b> Inspect observations</li><li><b>03</b> Reveal the change</li><li><b>04</b> Check the evidence</li><li><b>05</b> Make an experiment</li></ol><div class="study-story-columns"><article><span class="eyebrow">A PHYSICAL HYPOTHESIS</span><h3>What could explain the pattern?</h3><p>${esc(s.driver)}</p><h4>Other explanations to check</h4><ul>${s.alternatives.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></article><article><span class="eyebrow">FROM A MAP TO A RESPONSIBLE NEXT STEP</span><h3>What can this help you do?</h3><p>${esc(s.use)}</p><h4>What would confirm it?</h4><p>${esc(s.confirm)}</p></article></div><div class="study-exercise"><span class="eyebrow">TRY ONE CONTROLLED CHANGE</span><p>${esc(s.exercise)}</p><p class="small">Run the documented setup first, then customize its steps. Change one setting at a time and compare the new saved run. A modified workflow does not inherit the original case’s evaluation.</p></div></section>`;
 }
 function mountExample(m){
  const button=$('#study-recorded-example');if(!button)return;
  $('#study-run-it-yourself').onclick=()=>PageNavigation.focus($('#example-start'),{scroll:true});
  button.onclick=async()=>{
   button.disabled=true;
   try{
    if(state.jobRunning)throw Error('Finish or cancel the current analysis before opening a recorded study.');
    const job=await api('/api/examples/'+encodeURIComponent(m.id)+'/recorded');
    view('explore');drawArea(m.request.bbox);state.exampleWorkspace=true;state.pendingDisplayPreferences=m.request.display;state.recordedStudy=m.id;
    renderResults(job);$('#map').scrollIntoView({block:'start',behavior:'smooth'});
    toast('Previously computed example opened. No new processing was started; recorded maps are read-only.');
   }catch(e){if($('#study-recorded-status'))$('#study-recorded-status').textContent=e.message;else toast(e.message)}finally{if(button.isConnected)button.disabled=false}
  };
 }
 function cleanup(){
  resultVersion++;comparisonVersion++;
  observationMaps.forEach(m=>m.remove());observationMaps=[];
  experimentMaps.forEach(m=>m.remove());experimentMaps=[];
 }
 async function mountResult(result,job,pid){
  cleanup();const version=resultVersion;
  const host=document.createElement('section');host.className='study-result panel';host.id='study-result';host.setAttribute('aria-labelledby','study-result-title');
  host.innerHTML='<p role="status">Preparing the study summary…</p>';
  $('#result-content')?.prepend(host);
  try{
   const summary=await api(`/api/studies/${job.id}/${pid}`);
   if(version!==resultVersion||state.result!==result){host.remove();return}
   const s=summary.interpretation;
   host.innerHTML=`${job.kind==='recorded'?'<p class="study-recorded-banner"><b>PREVIOUSLY COMPUTED EXAMPLE</b> · These protected maps are read-only. No analysis was started by opening this view. Run the tutorial to create your own saved result.</p>':''}<div class="study-result-heading"><div><span class="eyebrow">THE OBSERVATION & THE INTERPRETATION</span><h2 id="study-result-title">${esc(s.question)}</h2><p>${esc(date(summary.record.start))} → ${esc(date(summary.record.end))} · ${summary.record.source_count} source files</p></div><button type="button" class="secondary" id="study-report">Download study report ↓</button></div><div class="study-finding"><h3>What this run found</h3><ul>${(summary.findings.length?summary.findings:['Inspect the saved measurement summaries and declared steps. No physical cause is automatically assigned.']).map(v=>`<li>${esc(v)}</li>`).join('')}</ul></div><div class="study-story-columns"><article><h3>What could explain it?</h3><p>${esc(s.driver)}</p><ul>${s.alternatives.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></article><article><h3>What should you check next?</h3><p>${esc(s.confirm)}</p><p>${esc(s.use)}</p></article></div><p class="study-caveat">${esc(summary.cannot)}</p>${summary.example?`<p class="small">Case context: ${esc(summary.example.title)} · ${summary.example.exact_settings?'Recorded source/settings match; read the case’s evidence limits.':'Modified experiment: the case’s evaluation does not validate this run.'}</p>`:''}<div class="study-actions"><button type="button" class="primary" id="study-customize">Make a controlled experiment →</button><button type="button" class="secondary" id="study-compare">Compare with another run</button><button type="button" class="secondary" id="study-dates">Compare acquired observations</button>${summary.example?'<button type="button" class="secondary" id="study-return-tutorial">Read the comparison tutorial ↗</button>':''}</div><p id="study-action-status" role="status" class="small">The report contains your currently selected map with its scale, actual findings, sources, settings and limitations. It opens offline; use your browser to print or save as PDF.</p><div id="study-comparison" hidden></div><div id="study-observations" hidden></div>`;
   $('#study-report').onclick=()=>downloadReport(result,job,pid);
   $('#study-customize').onclick=()=>customize(result,job,pid);
   $('#study-compare').onclick=()=>chooseComparison(result,job,pid);
   $('#study-dates').onclick=()=>observationComparison(result,job,pid);
   if($('#study-return-tutorial'))$('#study-return-tutorial').onclick=async()=>{view('examples');await openExample(summary.example.id);const heading=$('#example-evidence h2');if(heading)PageNavigation.focus(heading,{scroll:true})};
   if(job.kind==='recorded'){
    const save=$('#save-opening-view');if(save){save.disabled=true;save.title='Recorded examples are read-only. Run this study to save your own opening view.'}
    const status=$('#opening-view-status');if(status)status.textContent='Read-only recorded example. Appearance can be explored and exported; run it yourself to save a personalized opening view.';
   }
  }catch(e){if(version===resultVersion)host.innerHTML=`<h2>Study summary unavailable</h2><p>${esc(e.message)}</p><p>The existing maps, saved results and downloads remain below.</p>`}
 }
 async function downloadReport(result,job,pid){
  const button=$('#study-report');button.disabled=true;$('#study-action-status').textContent='Preparing the selected map and its legend. Your numeric data remain unchanged.';
  try{
   const layer=state.layer;if(!layer)throw Error('Choose an available result map before exporting a report.');
   if($('#display-mode')&&($('#display-mode').value!==displayMode||displayMode==='custom'&&(Number($('#display-low').value)!==displayLow||Number($('#display-high').value)!==displayHigh)))throw Error('Apply your colour range first so the report matches the displayed map.');
   const display={layer:layer.id,unit:layer.unit,palette:state.displayPalette||'standard',mode:isCategoryMap(layer)?'shared':displayMode,low:displayMode==='custom'?displayLow:null,high:displayMode==='custom'?displayHigh:null,category_colors:state.categoryColors||{},category_opacity:state.categoryOpacity||{}};
   const response=await fetchRenderedMap(`/api/studies/${job.id}/${pid}/report`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(display)});
   if(!response.ok){const error=await response.json();throw Error(error.detail||'The report could not be generated.')}
   const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=`nisar-study-${job.id.slice(0,8)}.html`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
   if(state.result===result)$('#study-action-status').textContent='Study report downloaded. It includes a presentation map and evidence, but not the satellite files or Earthdata session.';
  }catch(e){if(state.result===result)$('#study-action-status').textContent=e.message}finally{if(button.isConnected)button.disabled=false}
 }
 async function customize(result,job,pid){
  try{
   let recipe=result.extra?.workflow;
   if(!recipe){
    recipe=await api('/api/workflows/from-method',{method:'POST',body:JSON.stringify({method:pid,options:result.processing_options||{}})});
    recipe.name=(result.title||'Study')+' · experiment';recipe.options={...result.processing_options};recipe.context={bbox:result.grid.bbox,sources:result.sources.map(s=>({name:s.name,catalog_id:s.catalog_id||s.id,start:s.start,end:s.end,group:s.group}))};recipe.display=result.display_preferences;
   }
   state.studyBaseline={id:job.id,pid,title:result.title};await loadWorkflowRecipe(structuredClone(recipe));
   workflowStatus('Original run kept as your comparison baseline. '+(recipe.name||'Workflow')+' is an editable experiment. Change one setting, Check, then Run. Compare the new result with '+job.id.slice(0,8)+'.');
  }catch(e){toast(e.message)}
 }
 async function chooseComparison(result,job,pid){
  const host=$('#study-comparison');host.hidden=false;host.innerHTML='<p role="status">Loading completed studies…</p>';
  const token=++comparisonVersion;
  try{
   const jobs=await api('/api/jobs');if(token!==comparisonVersion||state.result!==result)return;
   const entries=jobs.filter(j=>j.status==='completed'&&j.id!==job.id).flatMap(j=>Object.entries(j.results||{}).filter(([,r])=>r.status==='exploratory').map(([p,r])=>({id:j.id,pid:p,title:r.title||j.request?.workflow?.name||p,date:j.created_at})));
   if(state.studyBaseline?.id.startsWith('example-')&&state.studyBaseline.id!==job.id)entries.unshift({...state.studyBaseline,date:'Previously computed example'});
   if(!entries.length){host.innerHTML='<h3>Your first comparison needs another run.</h3><p>Choose Make a controlled experiment, change one setting and run it. The original remains in Runs.</p>';return}
   host.innerHTML=`<h3>Compare a controlled experiment</h3><p>The selected study is “before”; this open run is “after.” Numeric differences require matching observations, area, method, grid, units and class meanings.</p><label>Original or comparison run<select id="study-before">${entries.map((r,i)=>`<option value="${i}">${esc(r.title)} · ${esc(r.id.slice(0,8))} · ${esc(date(r.date))}</option>`).join('')}</select></label><button type="button" class="secondary" id="study-compare-run">Compare saved measurements</button><div id="study-comparison-result" role="status"></div>`;
   const baseline=entries.findIndex(r=>r.id===state.studyBaseline?.id&&r.pid===state.studyBaseline?.pid);if(baseline>=0)$('#study-before').value=String(baseline);
   $('#study-compare-run').onclick=async()=>{
    const before=entries[Number($('#study-before').value)],button=$('#study-compare-run'),output=$('#study-comparison-result');button.disabled=true;output.textContent='Comparing settings and saved raster windows…';
    try{
     const report=await api('/api/studies/compare',{method:'POST',body:JSON.stringify({before:before.id,before_product:before.pid,after:job.id,after_product:pid})});
     if(token!==comparisonVersion||state.result!==result)return;
     output.innerHTML=comparisonHTML(report);
     await experimentComparison(report,before,result,job,pid,token);
    }catch(e){if(output.isConnected)output.textContent=e.message}finally{if(button.isConnected)button.disabled=false}
   };
  }catch(e){if(token===comparisonVersion)host.textContent=e.message}
 }
 function comparisonHTML(report){
  return `<p class="study-caveat">${esc(report.meaning)}</p><h4>What changed in the process?</h4>${report.settings.length?`<div class="table-scroll"><table><thead><tr><th>Setting</th><th>Before</th><th>After</th></tr></thead><tbody>${report.settings.map(r=>`<tr><th scope="row">${esc(r.setting.replaceAll('_',' '))}</th><td>${esc(r.before)}</td><td>${esc(r.after)}</td></tr>`).join('')}</tbody></table></div>`:'<p>No recorded science-option or ordered-step changes. Display styles are excluded.</p>'}<h4>What changed in the maps?</h4><details class="study-map-differences"><summary>Inspect all ${report.layers.length} saved-map differences and support checks</summary><div class="table-scroll"><table><thead><tr><th>Saved map</th><th>Comparable support</th><th>Difference</th></tr></thead><tbody>${report.layers.map(r=>`<tr><th scope="row">${esc(r.label)} · ${esc(r.unit)}</th><td>${r.available?r.common_cells.toLocaleString()+' jointly valid cells':esc(r.reason)}</td><td>${r.available?(r.quantity_type==='category agreement'?r.changed_percent.toFixed(2)+'% changed category':`Mean change ${Number(r.mean_change).toPrecision(4)} ${esc(r.unit)}; mean absolute change ${Number(r.mean_absolute_change).toPrecision(4)} ${esc(r.unit)}`):'Not calculated'}</td></tr>`).join('')}</tbody></table></div></details>`;
 }
 async function experimentComparison(report,before,result,job,pid,token){
  const available=report.layers.filter(l=>l.available),host=$('#study-comparison-result');
  experimentMaps.forEach(m=>m.remove());experimentMaps=[];
  if(!available.length){host.insertAdjacentHTML('beforeend','<p class="info-note">There are no compatible numeric maps to compare. The settings table still helps explain why these are different studies; inspect their results separately.</p>');return}
  host.insertAdjacentHTML('afterbegin',`<h4>See the same quantity before and after</h4><label>Comparable result<select id="study-experiment-layer">${available.map((l,i)=>`<option value="${i}">${esc(l.label)} · ${esc(l.unit)}</option>`).join('')}</select></label><button type="button" class="secondary" id="study-experiment-show">Show matching maps</button><p id="study-experiment-status" role="status"></p><div class="study-twin-maps"><div><div id="study-before-map" class="study-mini-map" aria-label="Original run map"></div><p id="study-before-caption"></p></div><div><div id="study-after-map" class="study-mini-map" aria-label="Modified run map"></div><p id="study-after-caption"></p></div></div><div id="study-experiment-legend"></div>`);
  const preferred=available.findIndex(l=>l.after_layer===state.layer?.id);if(preferred>=0)$('#study-experiment-layer').value=String(preferred);
  $('#study-experiment-show').onclick=async()=>{
   const row=available[Number($('#study-experiment-layer').value)],button=$('#study-experiment-show'),status=$('#study-experiment-status');button.disabled=true;status.textContent='Rendering the original and modified maps with one common scale…';
   try{
    const original=await api(`/api/artifacts/${before.id}/${before.pid}/result.json`),a=original.layers.find(l=>l.id===row.before_layer),b=result.layers.find(l=>l.id===row.after_layer);
    const query=new URLSearchParams({mode:'full',palette:state.displayPalette||'standard'});
    if(isCategoryMap(b)){query.set('category_colors',JSON.stringify(state.categoryColors?.[b.id]||{}));query.set('category_opacity',JSON.stringify(state.categoryOpacity?.[b.id]||{}))}
    let left=await api(`/api/visualization/${before.id}/${before.pid}/${a.id}?${query}`),right=await api(`/api/visualization/${job.id}/${pid}/${b.id}?${query}`);
    if(!isCategoryMap(b)&&left.available!==false&&right.available!==false){query.set('mode','custom');query.set('low',Math.min(left.min,right.min));query.set('high',Math.max(left.max,right.max));left=await api(`/api/visualization/${before.id}/${before.pid}/${a.id}?${query}`);right=await api(`/api/visualization/${job.id}/${pid}/${b.id}?${query}`)}
    if(token!==comparisonVersion||state.result!==result)return;
    if(left.available===false||right.available===false)throw Error(left.reason||right.reason);
    experimentMaps.forEach(m=>m.remove());experimentMaps=[];
    for(const [id,layer,display] of [['study-before-map',a,left],['study-after-map',b,right]]){const m=L.map(id,{zoomControl:true,attributionControl:false,worldCopyJump:false,maxZoom:23,zoomSnap:.1});L.imageOverlay(display.image,layer.bounds).addTo(m);m.fitBounds(layer.bounds,{animate:false,padding:[8,8]});experimentMaps.push(m)}
    let syncing=false;experimentMaps.forEach((m,i)=>m.on('moveend',()=>{if(syncing)return;syncing=true;experimentMaps[1-i].setView(m.getCenter(),m.getZoom(),{animate:false});syncing=false}));
    $('#study-before-caption').textContent='Before · '+before.title+' · '+before.id.slice(0,16);$('#study-after-caption').textContent='After · '+result.title+' · '+job.id.slice(0,8);
    $('#study-experiment-legend').innerHTML=legendHTML(left,b.unit,'shared across both saved runs');
    status.textContent='Same observations, area, quantity and grid. Both maps use identical colours and limits. The full jointly valid numeric comparison is in the detailed table; missing support is not zero change.';
   }catch(e){if(status.isConnected)status.textContent=e.message}finally{if(button.isConnected)button.disabled=false}
  };
  $('#study-experiment-show').click();
 }
 function legendHTML(display,unit,scope){
  const categories=display.categories||[];
  return (categories.length?categories.map(c=>`<span class="study-legend-entry"><i style="background:${esc(c.color)};opacity:${Number(c.opacity??1)}"></i>${esc(c.label||c.name||c.value)}${c.opacity===0?' (transparent)':''}</span>`).join(''):`<div class="study-gradient" style="background:linear-gradient(to right,${display.palette.map(c=>'rgb('+c.join(',')+')').join(',')})"></div><p>${esc(display.min)} → ${esc(display.max)} ${esc(unit)} · ${esc(scope)}</p>`)+'<p>Plain grey background: no mapped observation. A valid category that does not meet the rule is a different state.</p>';
 }
 function observationComparison(result,job,pid){
  const host=$('#study-observations');host.hidden=false;
  const frames=resultFrames();
  if(frames.length<2){host.innerHTML='<h3>One interval is not a time series.</h3><p>This run has fewer than two comparable acquired-state maps. A GOFF pair estimates motion during one interval; it is not two independent speed observations. Select additional suitable observations to investigate temporal variation.</p>';return}
  host.innerHTML=`<h3>Two acquired states. One geographic view.</h3><p>Both panels use the same colour range and measurement type. Pan or zoom either map to move both. The gap between acquisition times is unobserved.</p><div class="study-date-choices"><label>Earlier or first state<select id="study-left-date">${frames.map((f,i)=>`<option value="${i}">${esc(frameLabel(f))}</option>`).join('')}</select></label><label>Later or second state<select id="study-right-date">${frames.map((f,i)=>`<option value="${i}" ${i===frames.length-1?'selected':''}>${esc(frameLabel(f))}</option>`).join('')}</select></label></div><button type="button" class="secondary" id="study-observation-show">Show these observations</button><p id="study-observation-status" role="status"></p><div class="study-twin-maps"><div><div id="study-left-map" class="study-mini-map" aria-label="First acquired observation map"></div><p id="study-left-caption"></p></div><div><div id="study-right-map" class="study-mini-map" aria-label="Second acquired observation map"></div><p id="study-right-caption"></p></div></div><div id="study-shared-legend"></div>`;
  $('#study-observation-show').onclick=async()=>{
   const a=frames[Number($('#study-left-date').value)],b=frames[Number($('#study-right-date').value)],button=$('#study-observation-show'),status=$('#study-observation-status');
   const group=f=>f.group||result.sources.find(s=>s.start===f.start)?.group;
   if(a.id===b.id){status.textContent='Choose two different acquired states. Showing the same observation twice cannot reveal change.';return}
   if(a.unit!==b.unit||a.kind!==b.kind||(group(a)&&group(b)&&group(a)!==group(b))){status.textContent='These states have different quantities or viewing groups. Choose observations of the same quantity and view; no misleading common scale is applied.';return}
   button.disabled=true;status.textContent='Rendering both acquired states with a shared range…';const version=resultVersion;
   try{
    const query=new URLSearchParams({mode:'shared',palette:state.displayPalette||'standard'});
    if(isCategoryMap(a)){
     query.set('category_colors',JSON.stringify(state.categoryColors?.[a.id]||{}));
     query.set('category_opacity',JSON.stringify(state.categoryOpacity?.[a.id]||{}));
    }
    // Sequential reads respect the server’s single-render admission slot.
    const left=await api(`/api/visualization/${job.id}/${pid}/${a.id}?${query}`),right=await api(`/api/visualization/${job.id}/${pid}/${b.id}?${query}`);
    if(version!==resultVersion||state.result!==result)return;
    if(left.available===false||right.available===false)throw Error(left.reason||right.reason);
    if(left.min!==right.min||left.max!==right.max)throw Error('These maps do not resolve to the same range. Inspect them individually rather than comparing unequal colours.');
    observationMaps.forEach(m=>m.remove());observationMaps=[];
    for(const [id,frame,display] of [['study-left-map',a,left],['study-right-map',b,right]]){
     const m=L.map(id,{zoomControl:true,attributionControl:false,worldCopyJump:false,maxZoom:23,zoomSnap:.1});L.imageOverlay(display.image,frame.bounds,{opacity:1}).addTo(m);m.fitBounds(frame.bounds,{animate:false,padding:[8,8]});observationMaps.push(m);
    }
    let syncing=false;
    observationMaps.forEach((m,i)=>m.on('moveend',()=>{if(syncing)return;syncing=true;observationMaps[1-i].setView(m.getCenter(),m.getZoom(),{animate:false});syncing=false}));
    $('#study-left-caption').textContent=frameLabel(a)+' · '+a.unit;$('#study-right-caption').textContent=frameLabel(b)+' · '+b.unit;
    $('#study-shared-legend').innerHTML=legendHTML(left,a.unit,'shared across the dated maps');
    status.textContent='Actual acquired states; no interpolation. The plain background identifies unmapped space. Full result controls and exports remain on the main map.';
   }catch(e){if(status.isConnected)status.textContent=e.message}finally{if(button.isConnected)button.disabled=false}
  };
  $('#study-observation-show').click();
 }
 return {entry,storyHTML,mountExample,mountResult,cleanup,comparisonHTML};
})();
