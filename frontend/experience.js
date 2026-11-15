/* Guided inputs and display-only exploration of saved numeric results. */
const workflowMinimum={P01:2,P02:3,P03:3,P04:1,P05:1,P06:2,P07:1};
const referenceTools=['P03','P04','P05'];
function fireCombined(){return (state.selected==='P03'||!state.selected&&(state.labRecipe?.method==='P03'||typeof scientificMethod==='function'&&scientificMethod()==='P03'))&&($('#fire-method')?.value||'combined')==='combined'}
function needsReference(id){return referenceTools.includes(id)&&!(id==='P03'&&fireCombined())}
function workflowMinimumFor(id){if(id==='P03'&&fireCombined())return 4;return state.plans?.find(p=>p.id===id)?.minimum??workflowMinimum[id]}
function workflowIssues(id){
 if(!id)return ['Choose an analysis tool.'];
 const product=productFor(id),items=Object.values(state.catalog).flatMap(c=>c.items||[]).filter(i=>state.checked.has(i.id)&&i.product===product),issues=[];
 if(!state.bbox)issues.push('Select your analysis area.');
 if(state.bbox&&items.some(i=>i.subset&&!areaContains(i.subset_bbox,state.bbox)))issues.push('The analysis rectangle extends outside a selected saved area. Draw an area inside all selected extracts, or load different data.');
 if(items.some(i=>!i.local)&&$('#rail-connect')?.textContent?.includes('disconnected'))issues.push('Connect your Earthdata account, or import the original files.');
 if(items.length<workflowMinimumFor(id))issues.push(`Select at least ${workflowMinimumFor(id)} compatible ${product} observations; ${items.length} checked.`);
 if(id==='P07'&&$('#offset-solution')?.value==='horizontal'&&items.some(i=>i.subset&&!i.viewing_geometry?.available))issues.push('Prepare viewing geometry for the selected older subsets before horizontal-speed processing. The existing files are preserved.');
 if(needsReference(id)&&!state.reference&&!hasContextRole('reference'))issues.push('Draw a reference rectangle inside the analysis area.');
 if(id==='P03'&&fireCombined()){
  if(!['auto','HHHH'].includes($('#channel')?.value||'auto'))issues.push('Combined change needs HH and HV. Choose Auto or HH in settings.');
  const groups={};items.forEach(i=>(groups[i.group]??=[]).push(i));const end=$('#baseline-end')?.value,n=Number($('#baseline-count')?.value||3);
  for(const [g,rows] of Object.entries(groups)){const before=end?rows.filter(i=>i.start.slice(0,10)<=end).length:Math.min(n,rows.length);if(before<3||rows.length<=before)issues.push(`${g}: select at least 3 baseline dates and 1 later date. Set the baseline end in settings.`)}
 }
 if(id==='P06'&&items.length>=2){const end=$('#baseline-end')?.value;if(end){const before=items.filter(i=>i.start?.slice(0,10)<=end).length;if(!before||before===items.length)issues.push('Select at least one observation on/before the baseline end and one later comparison. Check the baseline date in Area & analysis settings.')}}
 if(id==='P05'&&!$('#event-date').value&&!$('#event-timestamp')?.value?.trim())issues.push('Enter the independently documented earthquake date.');
 if(id==='P05'&&!$('#event-timestamp')?.value?.trim()&&$('#event-date').value&&items.some(i=>i.start&&i.end)&&!items.some(i=>i.start?.slice(0,10)<$('#event-date').value&&$('#event-date').value<i.end?.slice(0,10)))issues.push('Choose an observation pair strictly bracketing the earthquake date.');
 return issues;
}
function referenceExplanation(id){return id==='P05'?'Choose independently justified stable ground away from the fault and suspected deformation. Each group subtracts its median reference phase. A mosaic prefers identical valid analysis cells across all groups inside your reference. If fewer than 25 are shared, it reports independent group references; revise the area if possible. Inspect the saved per-group counts and overlap differences. Coherence does not prove stability.':id==='P03'?'Choose an independently checked, unaffected comparison area with similar land cover inside your rectangle. The tool subtracts its median backscatter change to normalize the comparison. It must contain valid pixels on every date. Leave part of the analysis area outside the blue reference box for comparison.':'Phase has an arbitrary relative offset. Choose ground believed to be stable, inside your rectangle and away from the suspected change. The tool subtracts the reference’s median phase for each pair, making results relative to that ground. Exactly the same reference cells must be coherent and valid in every selected pair. The result shows their count and spread. This does not remove atmosphere or prove stability.'}
function renderInputGuide(){
 const host=$('#tool-input-guide');if(!host)return;
 if(!state.selected&&typeof workflowGuideHTML==='function'){host.innerHTML=workflowGuideHTML();return}
 if(!state.selected){host.innerHTML='<span class="eyebrow">CHOOSE YOUR ANALYSIS</span><h3>Choose a tool to continue</h3><p>Select a tool above to see its data requirements and prepare an analysis. You can select an area and find data first.</p>';return}
 const id=state.selected,issues=workflowIssues(id).filter(issue=>!issue.startsWith('Draw a reference')),p=state.plans.find(p=>p.id===id),minimum=workflowMinimumFor(id),viewing=state.result?.project===id;
 host.innerHTML=`<span class="eyebrow">NEXT RUN INPUTS · ${esc(id)}</span><h3>${viewing?'Prepare another analysis':issues.length?'Before you run':'Inputs supplied'}</h3>${viewing?'<p><b>You are viewing a saved result.</b> The checklist below is for a new run and does not change the result on the map.</p>':''}<p>${esc(p?.name||id)} uses ${productFor(id)} · minimum ${minimum} ${minimum===1?'observation pair':'observations'}.</p>${id==='P04'?'<p><strong>For a motion-rate map:</strong> select at least two connected GUNW pairs linking three dates; four or more dates over several weeks are preferable. One pair gives an interval map only. A pair connects its start and end acquisitions.</p>':''}${id==='P02'?'<p><b>Water method:</b> '+(($('#water-method')?.value||'hh_hv')==='hh_hv'?'HH/HV sigma-zero: both channels and a native conversion factor are required. Review both thresholds in Area & analysis settings.':'Single-channel gamma-zero: uses the previous threshold method.')+'</p>':''}${issues.length?`<ul>${issues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>Ready to prepare. Continue checks data quality before processing.</p>'}${needsReference(id)?'<p class="small">Next: Prepare opens the reference assistant. You can choose a suggested patch or check a reference you drew. A reference sets the comparison baseline; its stability or unaffected status needs your judgment.</p>':'<p class="small">No reference rectangle or external dataset is required by this tool’s processor.</p>'}<p class="small">This check is for a new run. Saved results retain their original inputs.</p>`;
}
function workflowStagesHTML(id,active=1){
 const labels=['Prepare data',needsReference(id)?'Choose reference':'Review inputs','Explore results'];
 return `<ol class="workflow-stages" aria-label="Analysis steps">${labels.map((label,i)=>`<li ${active===i+1?'aria-current="step"':''}><span>${i+1}</span>${label}</li>`).join('')}</ol>`;
}
async function continueWorkflow(id,coverage='selected',manual=false){
 if(state.jobRunning)throw Error('A data save or analysis is still running. Wait for it to finish, then Continue. Your inputs are kept.');
 if(id==='P05'){
  state.quakeCoveragePreference=coverage;
  if(coverage==='event'){
   const selected=selectQuakeCoverage({silent:true});
   if(!selected)throw Error('Enter the documented event time and load event-bracketing GUNW files first.');
  }
 }
 const missing=workflowIssues(id).filter(issue=>!(!manual&&needsReference(id)&&issue.startsWith('Draw a reference')));
 const blocking=missing;
 if(blocking.length)throw Error(blocking.join(' '));
 if(needsReference(id)&&!manual)return Boolean(await startReferenceAssistant());
 if(id==='P04')state.p04Reviewed=true;
 await run(true);return true;
}
function showWorkflowSetup(id){
 if(!id){toast('Choose a tool before preparing an analysis.');return}
 state.selected=id;renderTools();$('#run-selected').innerHTML=`Prepare ${esc(state.plans.find(p=>p.id===id)?.name||id)} →`;
 let dialog=$('#workflow-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='workflow-dialog';dialog.setAttribute('aria-labelledby','workflow-title');document.body.append(dialog)}
 const plan=state.plans.find(p=>p.id===id),needsRef=needsReference(id),phase=productFor(id)==='GUNW';
 const selected=Object.values(state.catalog).flatMap(c=>c.items||[]).filter(i=>state.checked.has(i.id)&&i.product===productFor(id));
 dialog.innerHTML=`<button type="button" class="dialog-close" aria-label="Close setup">×</button><span class="eyebrow">ONE GUIDED ANALYSIS · ${esc(id)}</span><h2 id="workflow-title">${esc(plan?.name||id)}</h2>${workflowStagesHTML(id)}
 <p class="workflow-intro">${needsRef?'Confirm the measurements below. Continue to compare reference areas, choose one, then run the analysis.':'Confirm your selected measurements and inputs, then run the analysis.'} Each step uses the same saved settings and keeps its evidence with the result.</p>
 <section class="workflow-step"><h3>1 · Your measurements</h3><div class="workflow-facts"><span><b>${selected.length}</b> selected ${esc(productFor(id))} file${selected.length===1?'':'s'}</span><span><b>${workflowMinimumFor(id)}</b> minimum</span><span>${state.bbox?'Analysis area selected':'Draw an analysis area first'}</span></div><p>${id==='P04'?'For a fitted rate, use at least two connected pairs linking three dates. A single pair gives interval change only.':id==='P05'?'A documented earthquake must fall between the two satellite acquisitions.':'Compatible observations and valid shared coverage are checked before results are produced.'}</p><button type="button" class="text-button" data-setup-action="catalog">Change selected files or acquisition group →</button>${!state.bbox?'<button type="button" class="secondary" data-setup-action="area">Draw analysis area</button>':''}
 ${id==='P05'?`<div class="workflow-event"><label>Event timing<select id="setup-event-mode"><option value="exact" ${$('#event-timestamp')?.value?.trim()?'selected':''}>Exact time · preferred when documented</option><option value="date" ${!$('#event-timestamp')?.value?.trim()?'selected':''}>Date only · exact time unknown</option></select></label><label id="setup-exact-event-label">Documented earthquake time · timezone required<input id="setup-event-time" type="text" value="${esc($('#event-timestamp')?.value||'')}" placeholder="2026-06-24T22:05:04Z"></label><label id="setup-date-event-label">Documented earthquake date<input type="date" id="setup-event" value="${esc($('#event-date').value)}"></label><label>Area coverage<select id="setup-coverage"><option value="event" ${state.quakeCoveragePreference!=='selected'?'selected':''}>Wider event coverage · choose matching groups for me</option><option value="selected" ${state.quakeCoveragePreference==='selected'?'selected':''}>Only the files I selected</option></select></label><p class="small">With wider coverage, Continue selects the shortest event-bracketing pair in each matching track/frame. Direction, mode and release stay compatible. Adjacent groups can extend the mapped ground; file count alone does not measure coverage. ${typeof activeQualityExclusions==='function'&&activeQualityExclusions().length?activeQualityExclusions().length+' previously excluded quality failure(s) will stay out while these settings are unchanged.':''} Source quality is checked next; unusable files require an explicit exclusion. Different views remain identified in the results.</p></div>`:''}
 ${id==='P01'?`<label>Flood comparison date · optional<input type="date" id="setup-flood" value="${esc($('#flood-date')?.value||'')}"></label><p class="small">Leave blank to find the largest observed consecutive expansion of candidate water; this does not independently establish a flood.</p>`:''}
 <section class="workflow-step"><h3>2 · ${needsRef?'Choose a reference with guidance':'Review the processing inputs'}</h3><p>${needsRef?'The next step checks your current reference and suggests up to three alternatives. Locate a patch on the map, read its quality warnings, and choose it explicitly. The assistant assesses measurements; it cannot certify stable or unaffected ground.':'This tool needs no reference rectangle. It uses the selected product measurements and the shared quality settings.'}</p>${needsRef&&state.reference?'<p class="small">Your drawn reference will also be checked. You can keep it if suitable or compare other candidates.</p>':''}</section>
 <details class="setup-advanced workflow-options"><summary>Settings, manual reference and other options</summary><p class="small">Shared grid: ${esc($('#resolution').value)} m requested; at least ${esc($('#min-valid-fraction').value)} native accepted fraction. ${phase?`Coherence ${esc($('#coherence').value)}; ionosphere subtraction ${$('#apply-ionosphere').checked?'on':'off'}.`:''} Opening setup preserves these choices.</p>${phase?'<button type="button" class="secondary" id="setup-phase-recommended">Apply recommended phase settings</button><p class="small">80 m, coherence 0.30, accepted fraction 0.50 and delivered ionosphere subtraction. This does not establish accuracy or choose a reference.</p>':''}
 ${id==='P04'?`<label><input type="checkbox" id="setup-phase-mixed" ${$('#phase-mixed')?.checked?'checked':''}> Compare processing revisions within one release family</label><p class="small">Needed for the six-file BETA Mexico comparison (X05009/X05010). View directions and release families remain separate.</p>`:''}
 ${needsRef?`<p>${esc(referenceExplanation(id))}</p><button type="button" data-setup-action="reference" class="secondary">${state.reference?'Redraw':'Draw'} my reference</button><button type="button" class="secondary" id="setup-manual-run">Run using my drawn reference</button><p class="small">Draw two opposite corners inside the analysis rectangle. This manual route skips candidate search; processing still checks shared reference support.</p>`:''}<button type="button" data-setup-action="connection" class="text-button">Earthdata connection →</button><button type="button" class="text-button" id="setup-save">Keep inputs and close</button></details>
 ${id==='P07'&&$('#offset-solution')?.value==='horizontal'?'<section class="info-note"><b>Horizontal speed assumes zero vertical velocity.</b><p>Review the constant ellipsoidal geometry height, matching layer, SNR and filter sensitivity in settings. Missing viewing cubes must be prepared from NASA first.</p>'+(selected.some(i=>i.subset&&!i.viewing_geometry?.available)?'<button type="button" class="secondary" id="setup-geometry">Prepare viewing geometry →</button>':'<p>Selected inputs are ready for geometry processing. The processor verifies the native cubes before producing a speed map.</p>')+'</section>':''}
 <div id="setup-error" role="status"></div><div class="setup-actions workflow-primary"><p class="small">${needsRef?'Next: data check → reference choice → run.':'Next: process measurements → inspect results.'}</p><button class="primary" id="setup-continue">${needsRef?'Continue · check data & reference':'Run analysis'} →</button></div>`;
 dialog.querySelector('.dialog-close').onclick=()=>dialog.close();
 const syncEventMode=()=>{if($('#setup-event-mode')){$('#setup-exact-event-label').hidden=$('#setup-event-mode').value!=='exact';$('#setup-date-event-label').hidden=$('#setup-event-mode').value!=='date'}};
 if($('#setup-event-mode')){$('#setup-event-mode').onchange=syncEventMode;syncEventMode()}
 const save=(referenceOnly=false)=>{
  if($('#setup-event-mode')){if($('#setup-event-mode').value==='date')$('#setup-event-time').value='';else $('#setup-event').value=''}
  if($('#setup-phase-mixed')){const changed=$('#phase-mixed').checked!==$('#setup-phase-mixed').checked;$('#phase-mixed').checked=$('#setup-phase-mixed').checked;if(changed){state.groups.GUNW=null;renderCatalog()}}
  for(const [source,target] of [['setup-event-time','event-timestamp'],['setup-event','event-date'],['setup-flood','flood-date']])if($('#'+source))$('#'+target).value=$('#'+source).value;
  try{options([id],{referenceOnly});renderInputGuide();return true}catch(e){$('#setup-error').textContent=e.message;return false}
 };
 if($('#setup-geometry'))$('#setup-geometry').onclick=async()=>{if(await prepareOffsetGeometry())dialog.close()};
 $('#setup-continue').onclick=async()=>{if(!save(needsRef))return;const button=$('#setup-continue');button.disabled=true;try{if(await continueWorkflow(id,$('#setup-coverage')?.value||'selected'))dialog.close()}catch(e){$('#setup-error').textContent=e.message}finally{button.disabled=false}};
 if($('#setup-manual-run'))$('#setup-manual-run').onclick=async()=>{if(!save())return;try{if(await continueWorkflow(id,$('#setup-coverage')?.value||'selected',true))dialog.close()}catch(e){$('#setup-error').textContent=e.message}};
 $('#setup-save').onclick=()=>{if(save(true)){dialog.close();toast('Inputs kept. Use Prepare analysis when you are ready.')}};
 if($('#setup-phase-recommended'))$('#setup-phase-recommended').onclick=()=>{if(!save(true))return;$('#resolution').value='80';$('#coherence').value='.3';$('#min-valid-fraction').value='.5';$('#apply-ionosphere').checked=true;state.p04Reviewed=false;showWorkflowSetup(id)};
 dialog.querySelectorAll('[data-setup-action]').forEach(b=>b.onclick=()=>{if(!save(true))return;dialog.close();if(b.dataset.setupAction==='connection'){view('settings');return}view('explore');if(b.dataset.setupAction==='area'||b.dataset.setupAction==='reference'){setDraw(b.dataset.setupAction);$('#map').scrollIntoView({behavior:'smooth',block:'center'})}else $('#catalog-content').scrollIntoView({behavior:'smooth',block:'start'})});
 dialog.showModal();
}

let seekTimer=null,timelineTimer=null,timelineVersion=0,previewVersion=0,displayMode='shared',displayLow=null,displayHigh=null;
function stopTimeline(){timelineVersion++;previewVersion++;if(typeof cancelMapPreviewRequest==='function')cancelMapPreviewRequest();if(typeof state!=='undefined'&&state.layer&&$('#frame-status'))$('#frame-status').textContent='Paused on the displayed map.';clearTimeout(seekTimer);clearTimeout(timelineTimer);timelineTimer=null;const b=$('#time-play');if(b)b.textContent='▶ Play observations'}
function resultFrames(){return (state.result?.layers||[]).map((l,index)=>({...l,index})).filter(l=>l.id.startsWith('observation_')).sort((a,b)=>(a.frame_index??Number(a.id.split('_')[1]))-(b.frame_index??Number(b.id.split('_')[1])))}
function frameLabel(l){const project=state.result.extra?.workflow_method||state.result.project;if(l.group)return `${l.start.slice(0,10)} → ${(l.end||'').slice(0,10)} · ${l.group}`;if(['epoch','processed_epoch'].includes(l.frame_scope))return l.start.slice(0,10);const idx=l.frame_index??Number(l.id.split('_')[1]),row=state.result.series[idx];return l.start?`${l.start.slice(0,10)}${['P04','P05','P07'].includes(project)?' → '+(l.end||'').slice(0,10):''}`:row?`${row.date.slice(0,10)}${['P04','P05','P07'].includes(project)?' → '+(row.end||'').slice(0,10):''}`:l.label}
const sharedDisplayPalettes=[['standard','Default'],['diverging','Diverging'],['rainbow','Rainbow']];
function sharedPaletteOptions(selected){return sharedDisplayPalettes.map(([value,label])=>`<option value="${value}" ${selected===value?'selected':''}>${label}</option>`).join('')}
function prepareResultDisplay(result){
 if(result.project==='P04'){const p=result.display_preferences;state.p04RateUnit=p?.layer==='los_rate_month'&&p.unit==='cm/month'&&result.layers.some(l=>l.id==='los_rate_month')?'cm/month':'cm/year';}
}
function openingDisplaySettings(result){
 const p=result.display_preferences;
 const palette=p&&['standard','diverging','rainbow'].includes(p.palette)?p.palette:['P04','P05'].includes(result.project)?'rainbow':'standard';
 if(!p)return {palette,mode:'shared',low:null,high:null,unit:null};
 const opening=typeof initialResultLayer==='function'&&typeof resultViewGroups==='function'?result.layers[initialResultLayer()]:result.layers[0];
 if(p.layer!==opening?.id||p.unit!==opening?.unit||!['shared','robust','full','custom'].includes(p.mode)||p.mode==='custom'&&(!Number.isFinite(p.low)||!Number.isFinite(p.high)||p.high<=p.low))return {palette,mode:'shared',low:null,high:null,unit:null};
 return {palette,mode:p.mode,low:p.low,high:p.high,unit:p.unit};
}
async function saveOpeningView(){
 const result=state.result,job=state.currentJob,layer=state.layer,button=$('#save-opening-view');
 if(!result||!job||!layer)return;
 button.disabled=true;
 try{
  if(!isCategoryMap(layer)&&($('#display-mode').value!==displayMode||displayMode==='custom'&&(Number($('#display-low').value)!==displayLow||Number($('#display-high').value)!==displayHigh)))throw Error('Apply your range first, then save the displayed view.');
  const recipe={palette:state.displayPalette||'standard',mode:displayMode,layer:layer.id,unit:layer.unit,low:displayMode==='custom'?displayLow:null,high:displayMode==='custom'?displayHigh:null};
  if(isCategoryMap(layer)){recipe.mode='shared';recipe.low=recipe.high=null}
  if(Object.keys(state.categoryColors||{}).length)recipe.category_colors=state.categoryColors;
  if(Object.keys(state.categoryOpacity||{}).length)recipe.category_opacity=state.categoryOpacity;
  $('#opening-view-status').textContent='Saving opening view…';
  const saved=await api(`/api/jobs/${job.id}/display/${result.project}`,{method:'PUT',body:JSON.stringify(recipe)});
  result.display_preferences=saved.display_preferences;
  if(state.result===result)$('#opening-view-status').textContent='Opening view saved. Reopening this run restores this map, units, palette, range and saved category colors and opacity.';
 }catch(e){toast(e.message)}finally{button.disabled=false}
}
function restoreResultReference(result,job){
 // A saved run may be opened from a workspace belonging to a different case.
 if(refRectangle){map.removeLayer(refRectangle);refRectangle=null}
 const bbox=result.processing_options?.reference_bbox||job.request?.options?.reference_bbox;
 state.reference=referenceTools.includes(result.project)&&Array.isArray(bbox)?[...bbox]:null;
 if(state.reference){const [w,s,e,n]=state.reference;refRectangle=L.rectangle([[s,w],[n,e]],{color:'#4d8dd3',weight:2,fillOpacity:.15}).addTo(map)}
}
function isCategoryMap(layer){return ['binary','categorical','water_state'].includes(layer.kind)||['class','observation index'].includes(layer.unit)}
function categoryColorKey(value){return String(Number(value))}
// Only maps with the same category meaning share styles. Code 0 in a flood
// map must never recolor code 0 in a reference, water-state or patch-ID map.
function categoryStyleFamily(layer){
 let family=layer.id;
 if(layer.kind==='binary'&&layer.unit==='class'&&(family==='water'||/^observation_\d+$/.test(family)))family='open_water';
 else if(family.endsWith('reference_support'))family='reference_support';
 else if(layer.unit!=='observation index')family=family.replace(/_\d+$/,'');
 return [layer.kind,layer.unit,family].join('|');
}
function categoryStylePeers(layer){
 return (state.result?.layers||[]).filter(other=>isCategoryMap(other)&&categoryStyleFamily(other)===categoryStyleFamily(layer));
}
function updateCategoryStyle(layer,key,value,setting){
 state[setting]??={};
 for(const peer of categoryStylePeers(layer))state[setting][peer.id]={...(state[setting][peer.id]||{}),[key]:value};
}
function normalizeCategoryStyles(){
 for(const setting of ['categoryColors','categoryOpacity']){
  const saved=JSON.parse(JSON.stringify(state[setting]||{}));state[setting]={};
  for(const [id,entries] of Object.entries(saved)){
   const layer=state.result.layers.find(layer=>layer.id===id);if(!layer||!isCategoryMap(layer))continue;
   for(const [key,value] of Object.entries(entries))updateCategoryStyle(layer,key,value,setting);
  }
 }
}
function renderCategoryColors(layer,display){
 const entries=display.categories||[],host=$('#category-color-list');if(!host)return;
 const limit=state.categoryPageSize||40;
 const peers=categoryStylePeers(layer),dated=peers.filter(peer=>peer.id.startsWith('observation_')||peer.start);
 if($('#category-style-scope'))$('#category-style-scope').textContent=dated.length>1?`Shared across ${dated.length} dated maps of this classification, including playback.`:'This classification has no other matching date maps in this run. Different classifications keep separate styles.';
 host.innerHTML=entries.slice(0,limit).map(entry=>`<div class="category-swatch"><label class="category-color-label"><input type="color" data-category="${esc(categoryColorKey(entry.value))}" value="${esc(entry.color)}" aria-label="Color for ${esc(entry.label)}"><span><b>${esc(entry.label)}</b><small>Code ${esc(entry.value)}</small></span></label><label class="category-opacity-label">Category opacity <output data-opacity-output="${esc(categoryColorKey(entry.value))}">${Math.round((entry.opacity??1)*100)}%</output><input type="range" min="0" max="1" step=".05" data-opacity="${esc(categoryColorKey(entry.value))}" value="${entry.opacity??1}" aria-label="Opacity for ${esc(entry.label)}"></label></div>`).join('');
 if(entries.length>limit)host.innerHTML+=`<button type="button" class="secondary" id="more-category-colors">Show next ${Math.min(40,entries.length-limit)} categories (${entries.length} total)</button>`;
 host.querySelectorAll?.('input[data-category]').forEach(input=>input.onchange=async()=>{
  stopTimeline();const colors=state.categoryColors[layer.id]||{};
  if(!Object.hasOwn(colors,input.dataset.category)&&Object.keys(colors).length>=512){toast('Up to 512 category colors can be customized per map. Reset colors to start again.');return}
  updateCategoryStyle(layer,input.dataset.category,input.value,'categoryColors');
  await selectLayer(state.result.layers.indexOf(layer));
 });
 host.querySelectorAll?.('input[data-opacity]').forEach(input=>{
  input.oninput=()=>{const output=host.querySelector(`[data-opacity-output="${input.dataset.opacity}"]`);if(output)output.textContent=Math.round(Number(input.value)*100)+'%'};
  input.onchange=async()=>{stopTimeline();const values=state.categoryOpacity?.[layer.id]||{};
   if(!Object.hasOwn(values,input.dataset.opacity)&&Object.keys(values).length>=512){toast('Up to 512 category opacity values can be customized per map.');return}
   updateCategoryStyle(layer,input.dataset.opacity,Number(input.value),'categoryOpacity');await selectLayer(state.result.layers.indexOf(layer));
  };
 });
 const more=$('#more-category-colors');if(more)more.onclick=()=>{state.categoryPageSize=limit+40;renderCategoryColors(layer,display)};
 $('#reset-category-colors').onclick=()=>{stopTimeline();for(const peer of categoryStylePeers(layer)){delete state.categoryColors[peer.id];if(state.categoryOpacity)delete state.categoryOpacity[peer.id]}selectLayer(state.result.layers.indexOf(layer))};
}
function syncOpeningViewStatus(layer){
 if(state.currentJob?.kind==='recorded'){const b=$('#save-opening-view');if(b)b.disabled=true;const s=$('#opening-view-status');if(s)s.textContent='Read-only recorded example. Run it yourself to save a personalized view.';return}
 const p=state.result.display_preferences,category=isCategoryMap(layer);
 const matches=p&&p.layer===layer.id&&p.unit===layer.unit&&p.mode===(category?'shared':displayMode)&&(category||p.palette===state.displayPalette&&(displayMode!=='custom'||p.low===displayLow&&p.high===displayHigh))&&JSON.stringify(p.category_colors||{})===JSON.stringify(state.categoryColors||{})&&JSON.stringify(p.category_opacity||{})===JSON.stringify(state.categoryOpacity||{});
 $('#opening-view-status').textContent=matches?'This view matches the saved opening view, including shared category colors and opacity.':'Save this view to retain its map, colors and applied range when reopening this run.';
}
function syncMapAppearance(layer,available=true,display={}){
 const category=isCategoryMap(layer),status=$('#map-color-status');
 if(status)status.textContent=!available?'Map unavailable · '+(display.reason||'No valid mapped values are available for this result. Missing values do not mean zero change.')+' Choose another result or add the observations described here.':category?'Category colors · each labelled swatch identifies a class, observed date or patch. Edit a swatch or its opacity; the same category stays consistent across dates. Codes and classifications stay unchanged; a numerical range does not apply.':'Measurement colors · choose Default, Diverging or Rainbow and an automatic or custom range. Read the units and endpoints in the map legend.';
 if($('#continuous-color-help'))$('#continuous-color-help').hidden=category||!available;
 if($('#measurement-color-controls'))$('#measurement-color-controls').hidden=category||!available;
 if($('#category-color-controls'))$('#category-color-controls').hidden=!category||!available;
 if($('#layer-opacity'))$('#layer-opacity').disabled=!available;
 if(available&&category)renderCategoryColors(layer,display);
}
function mountMapExplorer(){
 const project=state.result.extra?.workflow_method||state.result.project;
 stopTimeline();const savedDisplay=openingDisplaySettings(state.result);displayMode=savedDisplay.mode;displayLow=savedDisplay.low;displayHigh=savedDisplay.high;state.displayPalette=savedDisplay.palette;state.displayUnit=savedDisplay.unit;state.categoryColors=JSON.parse(JSON.stringify(state.result.display_preferences?.category_colors||{}));state.categoryOpacity=JSON.parse(JSON.stringify(state.result.display_preferences?.category_opacity||{}));normalizeCategoryStyles();state.categoryPageSize=40;const frames=resultFrames(),host=$('#map-result-controls');host.hidden=false;setTimeout(()=>map.invalidateSize?.(),0);
 host.innerHTML=`<div class="map-explorer-head"><div><span class="eyebrow">SAVED RESULT · ${esc(state.result.project)}</span><strong id="map-layer-title"></strong><span class="small">${esc(state.result.title)}</span></div><button id="map-fit-result" class="text-button">Fit result ↗</button></div><div class="map-visual-key"><div id="map-scale" class="legend" aria-label="Active map legend"></div><label class="map-opacity">Radar overlay opacity <output id="opacity-value">90%</output><input id="layer-opacity" type="range" min="0" max="1" step=".05" value=".9" aria-label="Radar overlay opacity"></label></div><section id="map-export-panel" class="map-export-panel" aria-label="Download displayed map"></section><div class="observation-player" id="observation-player" hidden><div class="player-heading"><b>Explore observed dates</b><span>${frames.length} snapshot${frames.length===1?'':'s'}</span></div><output id="time-label" aria-live="polite">Summary map</output><div class="time-controls"><button type="button" class="secondary" id="time-prev" ${!frames.length?'disabled':''}>← Previous</button><button type="button" class="primary" id="time-play" ${frames.length<2?'disabled':''}>▶ Play observations</button><button type="button" class="secondary" id="time-next" ${!frames.length?'disabled':''}>Next →</button></div><label class="frame-picker">Jump to an observation<select id="frame-choice" ${!frames.length?'disabled':''}><option value="">Choose an observed date…</option>${frames.map((l,i)=>`<option value="${i}">${i+1} / ${frames.length} · ${esc(frameLabel(l))}</option>`).join('')}</select></label><input id="time-slider" aria-label="Move between observed dates" type="range" min="0" max="${Math.max(0,frames.length-1)}" value="0" ${!frames.length?'disabled':''}><div class="player-options"><label>Time per snapshot<select id="time-speed"><option value="2500">2.5 seconds</option><option value="1500" selected>1.5 seconds</option><option value="800">0.8 seconds</option></select></label><label class="player-loop"><input type="checkbox" id="time-loop"> Repeat sequence</label><span id="frame-status" role="status">Choose a date, or play all observations.</span></div><p class="small">${frames.length<2?'At least two usable frames are needed for playback. Rerun with multiple compatible observations. ':''}${state.result.extra?.los_series?'These are reconstructed accumulated LOS changes at acquired dates, relative to the first acquisition and chosen ground reference. Missing times are not interpolated.':['P04','P05','P07'].includes(project)?'Each snapshot is a separate pair interval, not cumulative motion.':'Only acquired dates are shown; missing times are not interpolated.'} ${state.result.extra?.event_mosaic?'Different groups can show different places, dates and look directions: this sequence is source inspection, not a continuous time history. ':''}Each snapshot has equal screen time, regardless of the days between acquisitions.</p></div><section class="contrast-panel" aria-label="Map appearance"><h3>Map appearance · colors and range</h3><p id="map-color-status" class="info-note" role="status"></p><p class="small palette-explanation" id="continuous-color-help">Colors change presentation only. Automatic range starts from the 2nd–98th percentiles and is centred on zero for signed motion; values beyond the endpoints are clipped to the end colors. A shared range keeps the same meaning throughout playback. On signed maps, the center color is zero only when the chosen limits are symmetric. Rainbow includes blue, cyan, green, yellow and red; its midpoint is green. Diverging uses a light midpoint. Rainbow colors can emphasize apparent boundaries; use the standard palette to cross-check.</p><div class="display-controls" id="measurement-color-controls"><label>Color palette<select id="display-palette">${sharedPaletteOptions(state.displayPalette)}</select></label><label>Color range<select id="display-mode"><option value="shared">Automatic · shared across dates</option><option value="robust">Automatic · this map only (2–98%)</option><option value="full">Full range of this map</option><option value="custom">Custom · choose min and max</option></select></label><label class="range-number">Min · <span id="display-range-unit"></span><input id="display-low" type="number" step="any" disabled></label><label class="range-number">Max<input id="display-high" type="number" step="any" disabled></label><button id="apply-display" class="secondary">Apply range</button></div><div id="category-color-controls" hidden><div class="category-color-heading"><b>Category key · click a color to edit</b><button type="button" id="reset-category-colors" class="text-button">Reset shared category styles</button></div><p class="small">Colours and category opacity apply to the same category across all dates of this map type in the run, including playback and PNG exports. Different classifications keep separate styles. Set the background category to 0% to reveal the basemap without fading the detected changes. A background code (often 0) is a valid classification, not missing data; missing observations remain transparent. Category opacity combines with Radar overlay opacity. Save the opening view to retain these styles.</p><p id="category-style-scope" class="small" role="status"></p><div id="category-color-list" class="category-color-list"></div></div><div class="opening-view-save"><button id="save-opening-view" class="text-button">Save this as the opening view</button><span class="small" id="opening-view-status" role="status">Keep this map, units and applied colors when reopening this run. Measurements are unchanged.</span></div></section><p class="small" id="display-note" role="status"></p>`;
 if(typeof mountMapExportControls==='function')mountMapExportControls(state.artifactBase);
 $('#layer-opacity').oninput=e=>{const value=Number(e.target.value);if(overlay)overlay.setOpacity(value);$('#opacity-value').textContent=Math.round(value*100)+'%';if(typeof refreshMapImageDownload==='function')refreshMapImageDownload()};
 $('#save-opening-view').onclick=saveOpeningView;
 $('#display-mode').value=displayMode;if(displayMode==='custom'){$('#display-low').value=displayLow;$('#display-high').value=displayHigh;$('#display-low').disabled=$('#display-high').disabled=false;}
 const seek=async pos=>{stopTimeline();state.resultCategory='time';const frames=resultFrames();if(frames[pos])await selectLayer(frames[pos].index)};
 $('#time-prev').onclick=()=>{const frames=resultFrames(),pos=frames.findIndex(l=>l.id===state.layer?.id);seek(pos<0?0:Math.max(0,pos-1))};
 $('#time-next').onclick=()=>{const frames=resultFrames(),pos=frames.findIndex(l=>l.id===state.layer?.id);seek(pos<0?0:Math.min(frames.length-1,pos+1))};
 $('#frame-choice').onchange=e=>{if(e.target.value!=='')seek(Number(e.target.value))};
 $('#time-slider').oninput=e=>{stopTimeline();const pos=Number(e.target.value);$('#frame-status').textContent='Loading selected observation…';seekTimer=setTimeout(()=>seek(pos),120)};
 $('#time-play').onclick=()=>{
  if(timelineTimer!==null){stopTimeline();return}state.resultCategory='time';const frames=resultFrames();if(frames.length<2)return;
  if(['robust','full','mexico'].includes(displayMode)){displayMode='shared';$('#display-mode').value='shared';toast('Playback uses one shared automatic range so colors stay comparable across dates.')}
  const result=state.result,token=++timelineVersion;let pos=frames.findIndex(l=>l.id===state.layer?.id);pos=pos<0||pos===frames.length-1?0:pos+1;
  $('#time-play').textContent='Ⅱ Pause';
  const tick=async()=>{if(token!==timelineVersion||state.result!==result)return;const ok=await selectLayer(frames[pos].index);if(!ok||token!==timelineVersion||state.result!==result)return;
   if(pos===frames.length-1&&!$('#time-loop').checked){stopTimeline();$('#time-play').textContent='↻ Replay observations';$('#frame-status').textContent='End of observations. Replay or choose another date.';return}
   pos=(pos+1)%frames.length;timelineTimer=setTimeout(tick,Number($('#time-speed').value));
  };timelineTimer=setTimeout(tick,0);
 };
 $('#map-fit-result').onclick=()=>{if(state.layer){map.stop?.();map.invalidateSize?.({pan:true,animate:false});map.fitBounds(state.layer.bounds,{padding:[20,20],maxZoom:MAP_MAX_ZOOM,animate:false})}};
 $('#display-palette').onchange=e=>{stopTimeline();state.displayPalette=e.target.value;selectLayer(state.result.layers.indexOf(state.layer))};
 $('#display-mode').onchange=e=>{stopTimeline();$('#display-low').disabled=$('#display-high').disabled=e.target.value!=='custom';if(e.target.value!=='custom'){displayMode=e.target.value;selectLayer(state.result.layers.indexOf(state.layer))}};
 $('#apply-display').onclick=()=>{const mode=$('#display-mode').value,low=$('#display-low').value.trim(),high=$('#display-high').value.trim();if(mode==='custom'&&(!low||!high||!Number.isFinite(Number(low))||!Number.isFinite(Number(high))||Number(high)<=Number(low))){toast('Enter a finite minimum smaller than the maximum, in the displayed layer’s units.');return}stopTimeline();displayMode=mode;displayLow=Number(low);displayHigh=Number(high);state.displayUnit=state.layer?.unit;selectLayer(state.result.layers.indexOf(state.layer))};
 const chart=$('#result-chart');if(chart&&typeof chart.on==='function')chart.on('plotly_click',e=>{const pos=e.points?.[0]?.pointIndex;if(Number.isInteger(pos)&&resultFrames()[pos])seek(pos)});
}

// Settings shortcuts reuse the same guided input flow as the tool checklist.
if(typeof document!=='undefined'){
document.querySelectorAll('[data-settings-tool]').forEach(b=>b.onclick=()=>{view('explore');showWorkflowSetup(b.dataset.settingsTool)});
document.querySelectorAll('[data-settings-action]').forEach(b=>b.onclick=()=>{view('explore');showWorkflowSetup(b.dataset.settingsAction==='phase'?(['P04','P05'].includes(state.selected)?state.selected:'P04'):state.selected)});
['event-date','flood-date'].forEach(id=>document.getElementById(id)?.addEventListener('input',()=>renderInputGuide()));
}

async function refreshLocalFiles(){
 const files=await api('/api/local');state.localFiles=files;const names=new Set(files.filter(i=>!i.subset).map(i=>i.name));
 const ids=new Set(files.map(i=>i.id));
 for(const catalog of Object.values(state.catalog))catalog.items=(catalog.items||[]).filter(item=>{
  const available=item.subset?ids.has(item.id):names.has(item.name);
  if(item.local&&!available){
   state.checked.delete(item.id);state.downloadChecked.delete(item.id);
   if(item.subset||!item.url)return false;
  }
  item.local=available;if(available)state.downloadChecked.delete(item.id);return true;
 });
 const b=$('#use-local-files');if(b){b.textContent=`Use saved data (${files.length})`;b.disabled=!files.length}
 return files;
}
function preferSavedSource(candidate,previous){
 if(candidate.product==='GOFF'){const a=!!candidate.viewing_geometry?.available,b=!!previous.viewing_geometry?.available;if(a!==b)return a}
 return candidate.size_mb<previous.size_mb;
}
async function useLocalFiles(){
 if(!state.bbox){toast('Select an analysis area first, then choose Use saved data.');return}
 try{
  const files=await refreshLocalFiles(),[w,s,e,n]=state.bbox;
  let matches=files.filter(i=>{if(i.subset&&!areaContains(i.subset_bbox,state.bbox))return false;if(i.end?.slice(0,10)<$('#start-date').value||i.start?.slice(0,10)>$('#end-date').value)return false;const boxes=NisarCatalogGuide.boxes(i);return !boxes.length||boxes.some(b=>b[0]<=e&&b[2]>=w&&b[1]<=n&&b[3]>=s)});
  const originals=new Set(matches.filter(i=>!i.subset).map(i=>i.name));matches=matches.filter(i=>!i.subset||!originals.has(i.name));
  const unique=new Map();for(const i of matches){const previous=unique.get(i.name);if(!previous||preferSavedSource(i,previous))unique.set(i.name,i)}matches=[...unique.values()];
  state.catalog={};state.checked.clear();state.downloadChecked.clear();
  for(const item of matches){state.catalog[item.product]??={items:[],hits:0};state.catalog[item.product].items.push(item);state.catalog[item.product].hits++}
  Object.keys(state.catalog).forEach(autoSelect);renderCatalog();$('#catalog-content').scrollIntoView({behavior:'smooth',block:'start'});
  toast(matches.length?`${matches.length} saved source(s) available, including area extracts. Check the group, dates and valid coverage; files without footprints need inspection.`:'No saved data covers this area and date range. Find NASA data or import files.');
 }catch(e){toast(e.message)}
}

const analysisFields={'surface-method':['surface_method','evolving'],'fire-method':['fire_method','combined'],'smoothing-m':['smoothing_m',80],'score-threshold':['score_threshold',2],'water-method':['water_method','hh_hv'],'water-hh-threshold':['water_hh_threshold',-14],'water-hv-threshold':['water_hv_threshold',-23],resolution:['resolution',100],coherence:['coherence',.4],'min-valid-fraction':['min_valid_fraction',.5],snr:['snr',5],component:['component','slantRangeOffset'],'offset-solution':['offset_solution','radar'],'offset-height':['offset_geometry_height_m',0],'offset-condition':['offset_condition_limit',10],'offset-vertical-scenario':['offset_vertical_scenario_m_year',20],'offset-layer':['offset_layer','layer1'],'offset-rate-unit':['offset_rate_unit','m/day'],'water-threshold':['water_threshold',-17],'change-threshold':['change_threshold',3],'baseline-count':['baseline_count',1],'baseline-end':['baseline_end',''],'patch-area':['patch_area_m2',30000],'water-unknown':['water_unknown_db',1],'offset-cutoff':['offset_min_cutoff_m',1],'event-timestamp':['event_timestamp',''],'event-date':['event_date',''],'flood-date':['flood_date',''],channel:['channel','auto']};
const analysisChecks={'compare-pol':['compare_polarizations',false],'offset-local':['offset_local_filter',false],'offset-bias':['offset_stable_bias',false],'apply-ionosphere':['apply_ionosphere',false],'phase-mixed':['phase_allow_mixed_revisions',false],'phase-network':['phase_network',true],'offset-filter':['offset_filter',true]};
function restoreAnalysisOptions(o={}){
 state.restoredAnalysisOptions={...o};
 for(const [id,[key,value]] of Object.entries(analysisFields))if($('#'+id))$('#'+id).value=o[key]??value;
 for(const [id,[key,value]] of Object.entries(analysisChecks))if($('#'+id))$('#'+id).checked=o[key]??value;
 if($('#spatial-context'))$('#spatial-context').value=o.spatial_context?JSON.stringify(o.spatial_context):'';
 if($('#reference-observations'))$('#reference-observations').value=o.reference_observations?.length?JSON.stringify(o.reference_observations):'';
 if(Object.keys(o).length&&!('surface_method' in o)&&$('#surface-method'))$('#surface-method').value='legacy';
 if(Object.keys(o).length&&!('fire_method' in o)&&$('#fire-method'))$('#fire-method').value='relative';
 if(Object.keys(o).length&&!('water_method' in o)&&$('#water-method'))$('#water-method').value='single';
 state.p04Reviewed=false;
}

function newExploration(configuration={}){
 state.exampleWorkspace=false;
 const advanced=$('.advanced-settings');if(advanced)advanced.open=false;
 const active=$('#job-progress')&&!$('#job-progress').hidden&&!$('#cancel-job').hidden;
 requestVersions.job++;clearTimeout(state.poll);state.poll=null;state.job=null;state.jobRunning=false;clearArea();
 if(typeof resetWorkflowDraft==='function')resetWorkflowDraft();
 state.selected=null;state.tab='GCOV';state.groups={};state.catalogRange=null;state.previewCache=new Map();state.artifactBase=null;
 if(typeof Plotly!=='undefined'&&typeof Plotly.purge==='function'){for(const id of ['result-chart','profile-chart']){const node=$('#'+id);if(node)Plotly.purge(node)}}
 for(const id of ['result-content','result-tabs','map-result-controls','selection-summary'])$('#'+id).innerHTML='';
 $('#download-button').disabled=true;$('#file-input').value='';
 state.p04Reviewed=false;state.p04DefaultsApplied=false;state.qualityExclusions=null;state.pendingDisplayPreferences=null;state.quakeCoveragePreference='event';
 if(typeof clearReferenceAssistant==='function')clearReferenceAssistant();state.toolFamily='all';
 restoreAnalysisOptions();if($('#data-maturity'))$('#data-maturity').value='VALIDATED';clearContextMap();resetSearchDates();
 $('#job-progress').hidden=true;$('#run-selected').disabled=true;$('#run-selected').innerHTML='Choose a tool to continue';
 $$('[data-family]').forEach(b=>b.classList.toggle('active',b.dataset.family==='all'));renderTools();$('#tool-list').scrollTop=0;view('explore');
 if(!configuration.quiet)toast(active?'Clean workspace ready. Your background job continues in Runs.':'Clean workspace ready. Saved runs and original files are kept; use Runs or Use saved data to return.');
}

function resultPassportHTML(result){
 const p=result.extra?.result_passport;if(!p)return '';
 const record=p.record||{},support=p.support||{};
 return `<section class="info-note result-passport"><h3>How to read this run</h3><p>${esc(p.interpretation)}</p><div class="passport-facts"><span><b>Record:</b> ${esc(record.start?.slice(0,10)||'Not recorded')} → ${esc(record.end?.slice(0,10)||'Not recorded')}</span><span><b>Method:</b> ${esc(p.method)} · algorithm ${esc(p.algorithm_version||'See manifest')}</span>${Number.isFinite(support.common_area_km2)?`<span><b>Usable support:</b> ${support.common_area_km2.toFixed(2)} km² · ${esc(support.mode||'Read support details')}</span>`:''}</div><p class="small">${esc(p.reference?.meaning||'')} ${esc(p.validation)}</p></section>`;
}

function resultRecipeHTML(result,job={}){
 const sources=result.sources||[],o=result.processing_options||job.request?.options||{},groups=[...new Set(sources.map(s=>s.group).filter(Boolean))];
 const times=sources.flatMap(s=>[s.start,s.end]).filter(Boolean).sort(),phase=sources.some(s=>s.product==='GUNW')||['P04','P05'].includes(result.project);
 const posting=Number.isFinite(result.grid?.resolution_m)?result.grid.resolution_m.toFixed(1)+' m':'See source manifest';
 const describeGroup=g=>{const parts=g.split('_');return /^\d+$/.test(parts[0])&&['A','D'].includes(parts[1])?'Track '+parts[0]+' · '+(parts[1]==='A'?'ascending':'descending')+' · '+g:g};
 const diagnostics=result.extra?.reference_diagnostics,mosaic=result.extra?.event_mosaic;
 const cells=mosaic?.shared_reference_pixels??diagnostics?.fixed_pixels??diagnostics?.pixels??result.metrics?.reference_pixels;
 const bounds=o.reference_bbox,boundsText=Array.isArray(bounds)?bounds.map(v=>Number(v).toFixed(4)).join(', '):o.spatial_context?.features?.some(f=>f.properties?.role==='reference')?'Saved reference polygon(s)':'See saved processing parameters';
 const waterMethod=result.extra?.water_method;
 const waterRecipe=result.project==='P02'?'<p><b>Water method:</b> '+(waterMethod?.id==='hh_hv'?'HH/HV sigma-zero · HH &lt; '+esc(waterMethod.thresholds_db.HH)+' dB AND HV &lt; '+esc(waterMethod.thresholds_db.HV)+' dB. Native conversion precedes averaging; no Enhanced Lee filter.':'Single-channel gamma-zero · '+esc(waterMethod?.threshold_db??result.extra?.water_states?.threshold_db??o.water_threshold??-17)+' dB.')+'</p>':'';
 return resultPassportHTML(result)+workflowStagesHTML(result.project,3)+waterRecipe+'<section class="info-note result-recipe"><h3>What this run actually used</h3><p><b>Observations:</b> '+sources.length+' source file(s) · '+esc(times.length?times[0].slice(0,10)+' → '+times.at(-1).slice(0,10):'Dates unavailable')+' · actual grid '+esc(posting)+'.</p><p><b>Viewing groups:</b> '+esc(groups.map(describeGroup).join('; ')||'See source manifest')+'. Different tracks, directions or date spans can produce different results for the same place.</p>'+(phase?'<p><b>Phase screening:</b> coherence ≥ '+esc(o.coherence??'not recorded')+' · accepted native fraction ≥ '+esc(o.min_valid_fraction??'not recorded')+' · ionosphere subtraction '+(o.apply_ionosphere===true?'requested; check each source correction manifest':o.apply_ionosphere===false?'off':'not recorded')+'.</p>':'')+(['P03','P04','P05'].includes(result.project)&&result.extra?.fire_method?.id!=='combined'?'<p><b>Spatial reference:</b> '+(Number.isFinite(cells)?esc(cells)+' usable '+(mosaic?'shared reference cells':'reference cells')+' · ':'')+esc(boundsText)+(bounds?' (west, south, east, north)':'')+'. '+esc(mosaic?.reference||'Its stability or unaffected condition remains an assumption; changing it changes the spatial zero.')+'</p>':'')+'<p class="small">This recipe belongs to the saved result. Current workspace settings do not change it. Compare the same files, geometry, dates, quality and reference before expecting the same map.</p></section>';
}

function layerExplanation(l,result){
 const text=measurementLayerExplanation(l,result);
 if(!result.extra?.spatial_support)return text;
 const scope={'study domain':'This measurement is restricted to the supplied study domain.','reference support':'Reference cells may lie outside the study domain; they set the relative zero and do not enlarge regional measurement summaries.','source quality':'This diagnostic shows source quality and can extend outside the study domain. It is not the area used by regional measurement summaries.','source diagnostic':'This supporting source measurement can extend outside the study domain. It is not included in regional result summaries.','processing footprint':'This diagnostic shows the processing footprint, which can include supporting reference or stable-ground samples outside the study domain.'}[l.spatial_scope];
 return text+(scope?' '+scope:'');
}
function measurementLayerExplanation(l,result){
 const first=result.series[0]?.date?.slice(0,10)||'first date',second=result.series[1]?.date?.slice(0,10)||'second date',last=result.series.at(-1)?.date?.slice(0,10)||'last date';
 const method=result.extra?.water_method;
 if(method?.id==='hh_hv'){
  const rule=`HH sigma-zero < ${method.thresholds_db.HH} dB AND HV sigma-zero < ${method.thresholds_db.HV} dB.`;
  if(['backscatter','change','variability','baseline_departure','standardized_departure'].includes(l.id))return 'Context from the original HH gamma-zero measurements: '+({backscatter:'latest radar brightness in dB',change:'latest minus first brightness in dB',variability:'maximum minus minimum brightness in dB',baseline_departure:'latest minus the declared baseline median in dB',standardized_departure:'baseline departure divided by robust spread'}[l.id])+'. These context layers do not use the HH/HV sigma-zero classification. Use the separately named HH and HV sigma-zero maps to inspect its inputs.';
  if(l.id==='occupancy')return 'Fraction of the selected valid acquisitions meeting both thresholds: '+rule+' 0 means none, 1 every acquired date. Not continuous flooded time or depth.';
  if(l.id.startsWith('observation_')||l.id==='water')return 'One observed water-candidate snapshot. '+rule+' Same joint valid support and thresholds on every date. Missing times are not interpolated.';
  if(l.id==='threshold_sensitive')return 'Classification can change when both declared thresholds move together within ±2 dB. This is sensitivity, not confidence or accuracy.';
  if(['hh_sigma','hv_sigma'].includes(l.id))return 'Latest '+(l.id==='hh_sigma'?'HH':'HV')+' sigma-zero backscatter in dB, after native gamma-to-sigma conversion and averaging. Read with both declared thresholds; brightness alone does not establish inundation.';
 }
 const extra=typeof extraLayerExplanation==='function'?extraLayerExplanation(l,result):null;if(extra)return extra;
 const text={variability:'Largest minus smallest valid measurement at each pixel across the selected acquisitions. Requires at least two valid observations. Highlights variability, not the order, direction or cause of change; missing dates and outliers affect the result. For radar offsets, this compares interval rates, not cumulative displacement.',event:`New water candidates on the saved comparison date, relative to the pre-comparison baseline. 1 means newly mapped water, 0 means this condition was not detected. For historical runs without event-selection metadata, the second selected observation was used. Current runs identify their supplied or automatically selected comparison date in the saved findings. Neither is an independently verified flood date.`,recovery:'For new water candidates, shows the first later observation at which the pixel was dry. Numbers are observation indices, not days of flooding. Blank pixels have no mapped recovery; they are not proof of continuing flooding.',water:`Water candidates at the latest observation (${last}). A threshold classification, not a validated water mask.`,occupancy:'Fraction of valid observations classified as water at each pixel (new runs require at least two valid observations): 0 means none; 1 means every valid observation. Read the observation-count map to understand the evidence.',count:'Number of valid observations at each pixel. This is a coverage/quality map, not an environmental change measurement.',backscatter:`Radar echo strength at the latest observation (${last}), in dB. Moisture, roughness and vegetation can all affect it.`,change:`Latest minus first observed value (${first} → ${last}). Positive and negative values show the direction of change, not its cause.`,margin:'Water-candidate gain (+1), loss (−1), or no state change (0) between the first and last observations on the common valid footprint.',persistent:'Pixels whose candidate-water state differs from the baseline on every later selected observation. This is not automatically river-bank erosion.',patches:'Persistent scattering-change patches. Each color identifies a separate patch; patch IDs do not measure severity or forest loss.',relative_change:'Backscatter change after subtracting the reference area’s median change. Fire attribution still needs independent context.',surface:'Read the saved surface method: evolving results show latest changed patches; legacy results require persistence across later observations. Neither measures temperature or eruption probability.',range:'Relative phase-equivalent range change for one pair interval, in millimeters. It is referenced to the saved stable-area assumption, not cumulative or vertical motion.',value:'Latest quality-screened measurement. Read the units: soil moisture is a modeled retrieval; glacier offsets are a radar-geometry rate component.'};
 if(l.frame_scope==='processed_epoch')return 'Reconstructed relative LOS change in cm after temporal baseline subtraction. The first date need not be zero. Read the saved baseline step and dates; this is not a direct height measurement or an interpolated history.';
 if(l.frame_scope==='epoch')return 'Accumulated relative LOS change in cm, reconstructed from connected measured pairs. The first date is zero by definition. Not a direct height measurement; no interpolation fills unobserved dates.';
 if(l.id.startsWith('observation_'))return `${frameLabel(l)} · One observed snapshot${['P04','P05','P07'].includes(result.project)?' for the labeled pair interval':''}. Use previous/next, choose a date or play the sequence. Missing times are not interpolated.`;
 if(['0.2.0','0.3.0','0.4.0','0.4.1'].includes(result.algorithm_version)){
  if(l.id==='event')return `New water candidates at ${result.extra.event_selection?.date?.slice(0,10)||'the saved comparison date'}, relative to median backscatter across earlier baseline observations. Automatic selection finds the largest consecutive expansion, not a verified flood.`;
  if(l.id==='persistent')return 'Candidate water state differs from baseline on every later selected observation. This is not evidence of river-bank erosion by itself.';
  if(l.id==='patches'||l.id==='surface')return 'Change must exceed the threshold in the same direction on every later observation. Alternating brightening and darkening is excluded; environmental cause is not identified.';
 }
 return ({los_rate_year:'A fitted slope across the acquired dates, in cm/year. Negative means away from the satellite; positive toward it. It is relative to your chosen reference, not vertical sinking. The year is an annualized unit, not necessarily a year of observations.',los_rate_month:'Exactly the same fitted rate as the annual map, divided by 12. A mean month is 365.25/12 days. Read the observed span before extrapolating.',los_change:'Reconstructed relative change between the first and last acquisitions, in cm: the final accumulated-change frame relative to the first date. It is not the trend multiplied by time when the observations depart from a straight line.',los_fit_residual:'RMS departure of reconstructed dates from their fitted straight-line trend, in cm. It measures internal fit, not ground-truth accuracy, and can include noise or nonlinear motion.',los_pair_residual:'Mismatch between measured pairs and the connected reconstruction. A tree has zero residual by construction and no independent closure validation.',threshold_sensitive:'Cells where at least one measurement is within 2 dB of your water threshold. Compare the area table for five thresholds; this is sensitivity, not an uncertainty interval.',recovery_lower_days:'Days from comparison to the last observed wet state before the first later dry observation. Read with the first-dry map. Wet/dry changes between acquisitions are unknown.',recovery_upper_days:'Days from comparison to the first later dry observation. It bounds the first observed return to dry, not total flood duration. Blank means unresolved or no new candidate water.',unresolved:'New candidate water with no later dry observation. A final-date event can have no follow-up. A value of 1 does not prove it stayed flooded.',transitions:'Number of switches between wet and dry candidates over every consecutive acquisition on the common footprint.',water_gains:'Dry-to-water switches across consecutive observed dates, not separate verified floods.',water_losses:'Water-to-dry switches across consecutive observed dates, not erosion measurements.',change_direction:'Consistent brightness increase (+1), decrease (−1), or no qualifying persistence (0). Threshold and dates affect this classification.',largest_step:'Observation index ending the largest absolute brightness difference between consecutive dates. Use the dated interval table to locate it; no eruption is inferred.',reference_support:'Reference cells shared by every selected observation. Drawing the rectangle does not establish that this ground is stable.',interval_rate:'Relative phase-equivalent range change divided by exact elapsed pair days. Separate interval-average rates, not a fitted velocity or vertical motion.',interval_rate_spread:'Largest minus smallest duration-normalized pair rate. Different seasons, atmospheric errors and interval lengths affect this comparison; it is not thaw amplitude.',moisture_anomaly:'Latest retrieval minus the temporal median of the selected observations at each common cell. This is a record-relative anomaly, not a climatic normal.',wetting_steps:'Number of consecutive moisture increases at or above the saved step threshold. Gaps between observations are not monitored continuously.',drying_steps:'Number of consecutive moisture decreases at or above the saved step threshold. This does not identify irrigation or drought.'})[l.id]||text[l.id]||l.label;
}
function layerTitle(l){return ({variability:'Observed variability · maximum minus minimum',event:'New water at the comparison date',recovery:'First later dry observation',water:'Water candidates · latest date',occupancy:'How often water was observed',count:'Observation count · data coverage',backscatter:'Radar brightness · latest date',change:'Change from first to last date',margin:'Water gained or lost',persistent:'Repeated boundary-state changes',patches:'Persistent change patches',relative_change:'Change relative to the reference',surface:'Persistent surface-change candidates',range:'Relative radar range · selected pair',value:l.unit==='m³/m³'?'Latest soil moisture':'Latest offset-rate component'})[l.id]||l.label}
function summaryLayers(){return typeof resultViewGroups==='function'?resultViewGroups().main:[]}
function initialResultLayer(){
 const saved=state.result?.display_preferences,index=saved?state.result.layers.findIndex(l=>l.id===saved.layer&&l.unit===saved.unit):-1;if(index>=0)return index;
 const groups=resultViewGroups();return (groups.main[0]||groups.time[0]||groups.advanced[0]||groups.quality[0])?.index??0;
}
function mountLayerBrowser(){
 const host=$('#result-layer-browser'),groups=resultViewGroups();state.resultCategory='main';
 const hasRate=state.result.project==='P04'&&p04RateLayer();
 host.innerHTML=`<section class="result-map-browser"><span class="eyebrow">READ THE RESULT IN FOUR STEPS</span><h3 id="result-category-heading">Main results</h3><div class="result-category-tabs" role="group" aria-label="Result views">${['main','time','quality','advanced'].map(key=>`<button type="button" id="result-category-${key}" aria-pressed="${key==='main'}" ${!groups[key].length?'disabled':''}><b>${esc(resultCategoryInfo[key].title)}</b><span>${groups[key].length} view${groups[key].length===1?'':'s'}</span></button>`).join('')}</div><p class="small" id="result-category-description">${esc(resultCategoryInfo.main.intro)}</p><label id="summary-choice-label">Choose a map in this section<select id="summary-choice">${groups.main.map(l=>`<option value="${l.index}">${esc(friendlyResultTitle(l))} · ${esc(l.unit||'')}</option>`).join('')}</select></label>${hasRate?`<section id="p04-rate-units" class="p04-rate-units" hidden><label>Motion rate unit<select id="p04-rate-unit">${state.result.layers.some(l=>l.id==='los_rate_year')?'<option value="cm/year">cm/year</option>':''}${state.result.layers.some(l=>l.id==='los_rate_month')?'<option value="cm/month">cm/month</option>':''}</select></label><p>These are the same fitted rate in different units: cm/month = cm/year ÷ 12. This does not change the observation period or make the motion vertical. The acquired-date history stays in cm.</p></section>`:''}<div id="active-layer-explanation" class="active-layer-explanation" aria-live="polite"></div><button type="button" class="text-button" id="layer-show-map">Show this view on the map ↑</button></section>`;
 $('#summary-choice').onchange=e=>{stopTimeline();selectLayer(Number(e.target.value))};
 for(const key of ['main','time','quality','advanced'])$('#result-category-'+key).onclick=()=>{stopTimeline();state.resultCategory=key;const current=groups[key].find(l=>l.id===state.layer?.id),first=key==='main'?resultViewGroups().main[0]:groups[key][0];if(current||first){selectLayer((current||first).index);if(key==='time')$('#map-result-controls').scrollIntoView({behavior:'smooth',block:'center'})}};
 if($('#p04-rate-unit'))$('#p04-rate-unit').onchange=e=>switchP05RateUnit(e.target.value);
 $('#layer-show-map').onclick=()=>$('#map').scrollIntoView({behavior:'smooth',block:'start'});
}
function layerCoverageText(layer,result){
 const domain=result?.extra?.spatial_support?.domain_pixels;
 if(layer.spatial_scope==='study domain'&&domain>0&&Number.isFinite(layer.valid_pixels))return `${(100*layer.valid_pixels/domain).toFixed(1)}% of the study domain has valid values.`;
 return `${(100*layer.valid_fraction).toFixed(1)}% of the analysis grid has valid values.`;
}
function syncResultNavigation(l){
 const frames=resultFrames(),pos=frames.findIndex(f=>f.id===l.id),temporal=pos>=0;
 if(typeof syncCategoryPicker==='function')syncCategoryPicker(l);
 const explain=$('#active-layer-explanation');if(explain){explain.innerHTML=`<strong>${esc(friendlyResultTitle(l))}</strong>${Number.isFinite(l.valid_fraction)?`<p class="small"><b>${esc(l.unit)}</b> · ${esc(layerCoverageText(l,state.result))} ${l.start?esc(l.start.slice(0,10))+(l.end&&l.end!==l.start?' → '+esc(l.end.slice(0,10)):''):''} ${l.valid_pixels===0?esc(l.unavailable_reason||'No usable measurement for this map.'):''}</p>`:''}<p>${esc(layerExplanation(l,state.result))}</p>${l.id==='recovery'&&state.result.extra?.recovery_calendar?`<ul class="recovery-dates">${state.result.extra.recovery_calendar.map(r=>`<li>Index ${r.index} → ${esc(r.date.slice(0,10))}</li>`).join('')}</ul>`:''}${l.id==='first_change'&&state.result.extra?.first_change_calendar?`<ul class="recovery-dates">${state.result.extra.first_change_calendar.map(r=>`<li>Index ${r.index} → ${esc(r.date.slice(0,10))}</li>`).join('')}</ul>`:''}${l.id==='largest_step'&&state.result.extra?.step_calendar?`<ul class="recovery-dates">${state.result.extra.step_calendar.map(r=>`<li>Index ${r.index} → ${esc(r.start.slice(0,10))} to ${esc(r.end.slice(0,10))}</li>`).join('')}</ul>`:''}`}
 if($('#time-label'))$('#time-label').textContent=temporal?`${frameLabel(l)} · ${pos+1} of ${frames.length}`:'Select Explore time to inspect acquired dates or intervals';
 if(temporal){$('#time-slider').value=pos;$('#frame-choice').value=pos}else if($('#frame-choice'))$('#frame-choice').value='';
 if($('#time-prev'))$('#time-prev').disabled=!frames.length||(temporal&&pos===0);
 if($('#time-next'))$('#time-next').disabled=!frames.length||(temporal&&pos===frames.length-1);
 if($('#frame-status'))$('#frame-status').textContent=temporal?'Observation displayed.':'Main, quality or advanced view displayed.';
}
if(typeof document!=='undefined'){
 document.getElementById('new-exploration')?.addEventListener('click',newExploration);
 document.getElementById('catalog-new-exploration')?.addEventListener('click',newExploration);
 document.getElementById('use-local-files')?.addEventListener('click',useLocalFiles);
}


function resultMetricEntries(result){
 const project=result.extra?.workflow_method||result.project;
 if(project==='LAB'&&result.extra?.workflow?.method==='custom'){const u=result.layers.find(l=>l.id==='summary')?.unit||result.unit;return [['Summary spatial median · '+u,result.metrics.median],['Common valid area · km²',result.metrics.common_area_km2],['Common analysis cells',result.metrics.valid_pixels],['Selected observations',result.metrics.observations]]}
 if(result.extra?.horizontal_velocity){const h=result.extra.horizontal_velocity;return [['Mapped horizontal cells',h.latest_speed.valid_pixels],['Median estimated speed · '+h.unit,h.latest_speed.median],['90th percentile · '+h.unit,h.latest_speed.p90],['Maximum condition number allowed',h.maximum_condition_number]]}
 if(project==='P07')return [['valid_pixels',result.metrics.valid_pixels],['common_valid_area_km2',result.metrics.common_valid_area_km2],['Selected component median · '+result.unit,result.metrics.median],['Selected component 10th percentile · '+result.unit,result.metrics.p10]];
 if(result.extra?.fire_method?.id==='combined')return [['candidate_area_ha',result.metrics.candidate_area_ha],['valid_land_ha',result.metrics.valid_land_ha],['candidate_percent',100*result.metrics.candidate_fraction],['viewing_groups',result.metrics.viewing_groups]];
 if(project==='P05'&&result.extra?.event_measurement)return ['median','p10','p90'].map(k=>[k+'_cm',result.metrics[k]]).concat(result.extra.event_mosaic?[['mapped_area_km2',result.metrics.mapped_area_km2]]:[['interval_days',result.metrics.interval_days]]);
 if(result.extra?.los_series)return ['median_rate_cm_year','median_rate_cm_month','span_days','acquisition_dates'].map(k=>[k,result.metrics[k]]);
 const preferred={P01:['new_water_candidate_km2','observed_dry_again_km2','unresolved_water_candidate_km2','common_valid_area_km2']};
 const keys=preferred[project];return keys?keys.filter(k=>k in result.metrics).map(k=>[k,result.metrics[k]]):Object.entries(result.metrics).slice(0,4);
}
function processingTraceHTML(result){
 const trace=result.extra?.processing_trace;if(!trace)return '';
 if(trace.version!=='1.0.0')return '<p class="info-note">This saved processing trace uses a different format. Update the app or download the complete run record to inspect it.</p>';
 const layers=new Map((result.layers||[]).map(l=>[l.id,l])),history=result.extra?.step_history||[];
 const label=key=>key.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
 const cards=trace.stages.map(stage=>{
  const row=history.find(s=>s.step===stage.step)||{},help=typeof workflowStageHelp==='function'?workflowStageHelp(stage.operation,row.input_domain):typeof workflowHelp==='function'?workflowHelp(stage.operation):{name:label(stage.operation)},maps=stage.maps.filter(m=>layers.has(m.id));
  const operator=(state.labOperators||[]).find(o=>o.id===stage.operation),fields=new Map((operator?.fields||[]).map(f=>[f.key,f.label])),visible=operator&&typeof visibleWorkflowFields==='function'?new Set(visibleWorkflowFields({operation:stage.operation,parameters:row.parameters||{}},operator).map(f=>f.key)):null;
  const parameters=Object.entries(row.parameters||{}).filter(([k])=>!visible||visible.has(k)).map(([k,v])=>`<div><dt>${esc(typeof workflowParameterTitle==='function'?workflowParameterTitle(k,operator):fields.get(k)||label(k))}</dt><dd>${esc(v===null?'Automatic / not set':v===true?'Enabled':v===false?'Disabled':k==='method'?({single:'Single-channel brightness threshold',hh_hv:'Joint HH/HV sigma-zero thresholds'}[v]||String(v)):String(v))}</dd></div>`).join('');
  const diagnostic=Object.fromEntries((stage.diagnostic_keys||[]).filter(k=>result.extra[k]!==undefined).map(k=>[k,result.extra[k]]));
  const raw=JSON.stringify(diagnostic,null,2),clipped=raw.length>6000;
  return `<article class="processing-trace-card"><div class="processing-trace-title"><span class="processing-trace-number">${esc(stage.step)}</span><h4>${esc(help.name||label(stage.operation))}</h4></div>${help.why?`<p>${esc(help.why)}</p>`:''}<p class="small">Plan: ${esc(row.input_unit||'input')} → ${esc(row.output_unit||'output')}. ${esc(row.scope||'')}</p>${parameters?`<dl class="processing-trace-parameters">${parameters}</dl>`:''}${stage.parameter_note?`<p class="info-note">${esc(stage.parameter_note)}</p>`:''}${maps.length?`<label>Inspect this step’s evidence<select id="trace-layer-${stage.step}" aria-label="Step ${stage.step} evidence map">${maps.map(m=>`<option value="${esc(m.id)}">${esc(m.role)} · ${esc(m.label)} · ${esc(m.unit)}</option>`).join('')}</select></label><p class="small" id="trace-info-${stage.step}"></p><button type="button" class="secondary" data-trace-show="${stage.step}">Show selected map ↑</button>`:`<p class="info-note">${esc(stage.unavailable_reason||'This step records decisions or trajectories rather than a separate raster. Inspect its diagnostics below.')}</p>`}${Object.keys(diagnostic).length?`<details class="processing-trace-diagnostics"><summary>Recorded diagnostics · advanced</summary><pre>${esc(raw.slice(0,6000))}</pre>${clipped?'<p class="small">Preview shortened. Download the run record for all diagnostic values.</p>':''}</details>`:''}</article>`;
 }).join('');
 return `<section class="processing-trace" aria-labelledby="processing-trace-title"><span class="eyebrow">FOLLOW THE MEASUREMENTS</span><h3 id="processing-trace-title">Inspect your executed steps</h3><p>Choose evidence from any step and show it on the main map. PNG and numeric GeoTIFF downloads are beside that map. Intermediate maps explain a calculation; they are not additional independent findings.</p><p class="small">${esc(trace.scope)} For compound calculations, diagnostic units can differ from the plan’s abstract input/output: read the selected map’s actual units, dates and explanation.</p><div class="processing-trace-grid">${cards}</div><p><a href="${esc(state.artifactBase||'')}workflow.json" download>Download the exact workflow · JSON ↓</a> · <a href="${esc(state.artifactBase||'')}result.json" download>Download the complete run record · JSON ↓</a></p></section>`;
}
function mountProcessingTrace(result){
 const stages=result.extra?.processing_trace?.version==='1.0.0'?result.extra.processing_trace.stages:[];
 for(const stage of stages){
  const select=$('#trace-layer-'+stage.step),button=$('[data-trace-show="'+stage.step+'"]'),info=$('#trace-info-'+stage.step);
  if(!select||!button)continue;
  const explain=()=>{const layer=result.layers.find(l=>l.id===select.value),evidence=stage.maps.find(m=>m.id===select.value);if(!info||!layer)return;info.textContent=[evidence?.role,layer.unit,layer.start?layer.start.slice(0,10)+(layer.end&&layer.end.slice(0,10)!==layer.start.slice(0,10)?' → '+layer.end.slice(0,10):''):'Spatial diagnostic',Number.isFinite(layer.valid_fraction)?(100*layer.valid_fraction).toFixed(1)+'% valid coverage':null,layer.trace_group||null,layer.valid_pixels===0?layer.unavailable_reason:null].filter(Boolean).join(' · ')};
  select.onchange=explain;explain();
  button.onclick=async()=>{const index=result.layers.findIndex(l=>l.id===select.value);if(index<0||state.result!==result)return;stopTimeline();const shown=await selectLayer(index);if(shown!==false&&state.result===result)$('#map').scrollIntoView({behavior:'smooth',block:'start'})};
 }
}

function regionalReferenceHTML(v,table){
 const fmt=value=>typeof value!=='number'||!Number.isFinite(value)?'—':value!==0&&Math.abs(value)<.001?value.toExponential(3):value.toLocaleString(undefined,{maximumSignificantDigits:5});
 let html=`<h3>Matched regional reference check</h3><p>${esc(v.status)}</p>`;
 if(v.quantity_label)html+=`<p><b>${esc(v.quantity_label)}</b>${v.component?' · '+esc(v.component==='slantRangeOffset'?'slant-range component':'along-track component'):''}${v.unit?' · '+esc(v.unit):''}</p>`;
 if(v.comparison_basis)html+=`<p>${esc(v.comparison_basis)}</p>`;
 if(v.assumptions?.length)html+='<div class="warning-note">'+v.assumptions.map(note=>`<p>${esc(note)}</p>`).join('')+'</div>';
 if(v.samples)html+=table(['Compared records','Bias · app − reference','RMSE','Bias-removed RMSE','Unit'],[[v.samples,fmt(v.bias),fmt(v.rmse),fmt(v.unbiased_rmse),v.unit]]);
 const metricNotes=v.metric_notes?.length?v.metric_notes:v.samples===1?['One compared record cannot test bias-removed variability; an older saved zero is true by construction.']:[];
 if(metricNotes.length)html+=metricNotes.map(note=>`<p class="small">${esc(note)}</p>`).join('');
 if(v.requested_samples!=null)html+=`<p>${esc(v.samples||0)} of ${esc(v.requested_samples)} supplied records compared; ${esc(v.excluded_samples||0)} excluded because the matched regional summary was unavailable.</p>`;
 if(v.matched_pairs?.length){const rows=v.matched_pairs.slice(0,20);html+='<details><summary>Inspect the matched measurements</summary>'+table(['Pair interval · UTC','App regional median','Reference · same unit','Unit','Source'],rows.map(r=>[r.date.slice(0,10)+' → '+(r.end?.slice(0,10)||'unspecified'),fmt(r.observed),fmt(r.reference),r.unit,r.source]))+(v.matched_pairs.length>20?'<p>Showing the first 20 comparisons. The full matched records and original unit conversions are in the run JSON.</p>':'<p>Original values and unit conversions are retained in the run JSON.</p>')+'</details>'}
 if(v.excluded_references?.length)html+='<details><summary>Why records were excluded</summary>'+table(['Date','Source','Reason'],v.excluded_references.slice(0,20).map(r=>[r.date,r.source,r.reason]))+'</details>';
 if(v.meaning)html+=`<p class="small">${esc(v.meaning)} Display rounding does not change the saved measurements.</p>`;
 return `<section class="regional-reference-check">${html}</section>`;
}
function spatialSupportHTML(result,table){
 const e=result.extra||{},options=result.processing_options||e.workflow?.options||{},roles=new Set([...(e.spatial_context||[]).map(f=>f.role),...(options.spatial_context?.features||[]).map(f=>f.properties?.role)]),domainDeclared=roles.has('domain');
 if(e.spatial_support){const domain=e.spatial_support.domain_pixels,valid=e.event_mosaic?e.support?.mosaic_pixels:e.support?.common_pixels;return '<h3>Study boundary and supporting samples</h3><p>'+esc(e.spatial_support.policy)+'</p>'+table(['Geometry support','Cells'],[['Study domain',domain],['Processing footprint',e.spatial_support.processing_footprint_pixels],['Auxiliary footprint outside study',e.spatial_support.auxiliary_pixels_outside_domain]])+'<p class="small">These are geometry-mask counts, not guaranteed usable measurements. The result passport gives the actual common valid comparison support.</p>'+(Number.isFinite(valid)&&domain>0?'<p><b>'+(e.event_mosaic?'Mapped study cells · mosaic union: ':'Processed common valid study cells: ')+esc(valid)+' of '+esc(domain)+' ('+esc((100*valid/domain).toLocaleString(undefined,{maximumFractionDigits:1}))+'%).</b> Outside-domain areas do not count as missing study coverage.</p>':'')}
 const method=e.scientific_blocks?.compiled_method||(result.project==='LAB'?e.workflow?.method:result.project),elementary=e.workflow?.method==='custom'&&!e.scientific_blocks;
 const affectedLegacy=!method||elementary||roles.has('reference')||roles.has('stable')||(method==='P07'&&(options.offset_filter!==false||options.offset_local_filter===true))||(['P04','P05'].includes(method)&&e.support?.common_pixels===0);
 if(domainDeclared&&affectedLegacy&&e.fire_method?.id!=='combined'&&e.surface_method?.id!=='evolving')return '<div class="warning-note"><b>Earlier study-boundary handling</b><p>This saved result uses an earlier boundary path affected by the shared study-domain fixes. Some maps, summaries or filters may include samples outside the supplied study boundary. Rerun with the current application before comparing new results. The original saved files are preserved.</p></div>';
 return '';
}
function renderScientificEvidence(result){
 const e=result.extra||{},report=result.report;if(!report)return '';
 const num=v=>typeof v==='number'?v.toLocaleString(undefined,{maximumFractionDigits:3}):'—';
 const table=(head,rows)=>`<div class="evidence-table-wrap"><table class="evidence-table"><thead><tr>${head.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${esc(String(v??'—'))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 let html=typeof resultReadingGuideHTML==='function'?'':`<section class="discovery-report"><span class="eyebrow">OBSERVATIONS · NOT A CAUSAL DIAGNOSIS</span><h3>${esc(report.headline)}</h3>${report.findings.map(t=>`<p>${esc(t)}</p>`).join('')}<p class="small">${esc(report.validation)}</p></section>`;
 html+=spatialSupportHTML(result,table);
 if(e.workflow_output_statistics)html+='<h3>Added experimental output · statistics</h3>'+table(['Measure','Value'],Object.entries(e.workflow_output_statistics).map(([k,v])=>[k.replaceAll('_',' '),v]))+'<p>These values describe the added output map; the method statistic cards retain their original measurement.</p>';
 if(e.processing_trace)html+=processingTraceHTML(result);
 else if(e.step_history)html+='<h3>Your executed processing order</h3>'+table(['Step','Operation','Applied parameters','Output units'],e.step_history.map(s=>[s.step,typeof workflowHelp==='function'?workflowHelp(s.operation).name:s.operation,JSON.stringify(s.parameters),s.output_unit]))+'<p>'+(e.scientific_blocks?'Scientific blocks retain the method’s published maps and diagnostics; not every internal calculation is a separate map. Added map operations have separately named outputs. Dated views retain their own measurement and units.':'Each intermediate step has a saved latest map in Advanced maps. The final processed observations are in Explore time.')+' <a href="'+state.artifactBase+'workflow.json" download>Download this run’s exact workflow · JSON ↓</a></p>';
 if(e.los_model){const m=e.los_model;html+=`<h3>Multi-date motion rate</h3><p>${esc(m.status)}. ${esc(m.reason||m.interpretation||'')}</p>`;if(e.los_series)html+=`<p><b>Start with the annual rate map.</b> Switch to cm/month for the same rate in different units. Play the dated reconstruction to inspect accumulated changes. Original pair maps are under Advanced maps. Reference support and residuals are under Quality & reliability.</p>`+table(['Acquired dates','Pairs','Span · days','Redundant pair checks'],[[m.epoch_count,m.pair_count,num(m.span_days),m.redundancy]])+`<p>${m.closure_check_available?'Redundant pairs support internal network checks; this does not establish environmental accuracy.':'No redundant pair cycle: pair residual is zero by construction. The trend is exploratory and cannot independently verify unwrapping errors.'}</p>`;if(e.processing_revisions?.length>1)html+='<p class="warning-note">Processing revisions were combined with your explicit consent. Their differences can mimic motion; compare a single-revision run.</p>';}
 if(e.event_mosaic){const m=e.event_mosaic;html+='<h3>Source and reference checks</h3><p>'+esc(m.selection)+'</p><p>'+esc(m.reference)+'</p>'+table(['Source key','Track/frame group','Before → after · UTC','Reference cells','Mapped cells'],m.groups.map(g=>[g.index,g.group,g.start.slice(0,10)+' → '+g.end.slice(0,10),g.reference_pixels,g.valid_pixels]))+'<p>Source index identifies the group selected at each map cell. Overlap spread compares different referenced LOS views; it is not an error bound or an east/up decomposition.</p>'; }
 if(e.event_mosaic?.overlap_difference_cm?.valid_pixels){const d=e.event_mosaic.overlap_difference_cm;html+=`<div class="warning-note"><b>Check agreement between overlapping views</b><p>Spatial median difference: ${num(d.median)} cm; 90th percentile: ${num(d.p90)} cm. Different viewing directions, post-event dates, reference offsets and measurement errors can contribute. These are not accuracy bounds. Inspect the overlap-difference map and individual groups before interpreting seams as surface change.</p></div>`;}
 if(e.event_measurement)html+='<h3>Earthquake displacement · read the colors</h3><p>Centimeters of relative line-of-sight change across an event-bracketing interval. Positive is toward the satellite; negative is away. A radar view mixes horizontal and vertical motion. The NASA illustration describes geological direction using its viewing geometry and earthquake context; this app does not infer east/west or vertical motion from phase alone.</p>';
 if(e.support&&!e.event_mosaic&&!e.fire_method)html+=`<h3>Comparable coverage</h3><p>${num(e.support.common_area_km2)} km² · ${num(100*e.support.common_fraction)}% of the analysis grid · ${num(e.support.common_pixels)} cells shared across all observations. ${e.spatial_context?.some(f=>f.role==='domain')?'The supplied domain restricts this result: cells outside its boundary are excluded by choice, not missing satellite coverage. ':''}The observation-count map also shows evidence outside this fixed comparison footprint.</p>`;
 if(e.water_method?.id==='hh_hv')html+=`<h3>Water classification · HH/HV sigma-zero</h3><p>${esc(e.water_method.rule)} HH &lt; ${num(e.water_method.thresholds_db.HH)} dB and HV &lt; ${num(e.water_method.thresholds_db.HV)} dB. ${esc(e.water_method.radiometry)} ${esc(e.water_method.filtering)} ${esc(e.water_method.calibration)}</p>`;
 if(e.threshold_sensitivity){html+='<h3>How much does the water threshold matter?</h3><p>'+esc(e.threshold_sensitivity.description||'')+'</p><p>Area in km² on the same footprint. ±1 and ±2 dB are comparison scenarios, not confidence bounds. A large change across columns means the result is sensitive to your setting.</p>';html+=table(['Observed date',...e.threshold_sensitivity.scenarios.map(s=>s.hh_threshold_db!==undefined?`HH ${s.hh_threshold_db} / HV ${s.hv_threshold_db} dB`:`${s.threshold_db} dB`)],result.series.map((r,i)=>[r.date.slice(0,10),...e.threshold_sensitivity.scenarios.map(s=>num(s.area_km2[i]))]));}
 if(e.reference_assistant){const a=e.reference_assistant;html+=`<h3>Reference chosen with the assistant</h3><p>${esc(a.candidate.name)} · ${a.candidate.shared_cells} shared cells · ${(100*a.candidate.shared_fraction).toFixed(1)}% shared coverage. ${esc(a.candidate.data_suitability)}.</p><p>${esc(a.stability)}</p><p>Assessment saved with this result: ${esc(a.assessment_id)}. Suitable measurements do not establish stationary or unaffected ground.</p>${a.maximum_candidate_offset_span!=null?`<p>Largest candidate reference-offset spread: ${num(a.maximum_candidate_offset_span)} ${esc(a.comparison_unit)}. This is sensitivity to the reference choice, not an accuracy bound.</p>`:''}`;}
 if(e.reference_diagnostics){const d=e.reference_diagnostics;html+='<h3>Reference evidence</h3>';if(d.pairs)html+=table(['Pair start','Days','Fixed cells','Reference phase p10 / p90 · rad'],d.pairs.map((r,i)=>[result.series[i].date.slice(0,10),num(r.interval_days),r.reference_pixels,`${num(r.reference_phase_p10_rad)} / ${num(r.reference_phase_p90_rad)}`]));else html+=`<p>${num(d.pixels)} fixed reference cells. Latest brightness-change spread (p10 to p90): ${num(d.latest_change_p10_db)} to ${num(d.latest_change_p90_db)} dB. Spatial spread describes heterogeneity; it is not uncertainty in the mean.</p>`;}
 if(e.pair_network){const n=e.pair_network;html+=`<h3>Pair network consistency</h3><p>${n.epochs} acquisition epochs · ${n.pairs} pairs · ${n.connected_components} connected component(s) · ${n.cycle_rank} redundant edge(s). ${n.triangle_closures.length} exact-endpoint triangle(s) checked. ${n.inversion_performed?'The connected graph was reconstructed; read the motion-model limits above.':'These are graph diagnostics; read the separate network-model status for any supported reconstruction.'}</p>`;if(n.triangle_closures.length)html+=table(['Triangle epochs','Closure median · mm','Closure RMS · mm'],n.triangle_closures.map(t=>[t.epochs.map(d=>d.slice(0,10)).join(' → '),num(t.median_closure_mm),num(t.rms_closure_mm)]));}
 if(e.horizontal_velocity){const h=e.horizontal_velocity;html+='<h3>Horizontal-speed assumptions</h3><p>'+esc(h.assumption)+'</p><p>'+esc(h.equations)+'</p><p>Geometry height: '+num(h.height_above_ellipsoid_m)+' m above ellipsoid. '+esc(h.height_source)+'. Maximum condition number: '+num(h.maximum_condition_number)+'.</p><p>Vertical-motion scenario: '+num(h.vertical_scenario_m_year)+' m/year. '+esc(h.vertical_scenario_meaning)+'</p>'+table(['Pair','Accepted horizontal cells','Rejected by conditioning'],h.pairs.map(p=>[p.start.slice(0,10)+' → '+p.end.slice(0,10),p.accepted_cells,p.condition_rejected_cells]));}
 if(e.offset_measurement){const m=e.offset_measurement;html+='<h3>What the motion maps measure</h3><p>'+esc(m.layer)+' · '+esc(m.component)+' · '+esc(m.unit)+'. '+esc(m.meaning)+'</p>'+table(['Source interval','Correlation window · source samples'],result.sources.map(s=>[s.start.slice(0,10)+' → '+s.end.slice(0,10),Object.entries(s.attributes?.correlation_window_samples||{}).map(([k,v])=>k.replace('WindowSize','')+': '+v).join(' · ')||'Not available in source metadata']))+'<p>Correlation windows describe source-image matching support, not the 80 m output posting or a measured accuracy. Larger windows can reduce detail. Inspect the original source paths and compare filter-off results.</p>'; }
 if(e.offset_filter_diagnostics)html+='<h3>Offset screening</h3><p>Cutoffs are in offset meters before conversion to the selected rate unit. Rerun with the filter disabled to check whether localized real motion was removed.</p>'+table(['Pair start','Days','Cutoff · m','Removed cells'],e.offset_filter_diagnostics.map((r,i)=>[result.series[i].date.slice(0,10),num(r.interval_days),num(r.cutoff_m),r.removed_pixels]));
 if(e.surface_method){const m=e.surface_method;if(e.support?.requested_window_pixels)html+=`<p>Selected geographic window: ${num(e.support.requested_window_pixels)} cell centres; ${num(100*e.support.selected_window_valid_fraction)}% have shared usable measurements. Rotated grid corners outside your rectangle are excluded.</p>`;html+='<h3>Evolving surface evidence</h3><p>Latest changed patches include late appearances. Repeated change requires the same sign on at least two consecutive later acquisitions; gaps between passes are unobserved. '+(m.repeated_latest_available?'':'Only one later acquisition: repetition cannot yet be assessed. ')+'These are brightness candidates, not validated lava.</p>'+table(['Smoothing sigma · m','Change threshold · dB','Minimum patch · m²'],[[m.smoothing_m,m.change_threshold_db,m.minimum_patch_area_m2]]);}
 if(e.first_change_calendar)html+='<h3>First observed change · date key</h3>'+table(['Index','Acquired date'],e.first_change_calendar.map(r=>[r.index,r.date.slice(0,10)]));
 if(e.step_calendar)html+='<h3>Largest-step index key</h3>'+table(['Index','Interval start','Interval end'],e.step_calendar.map(r=>[r.index,r.start.slice(0,10),r.end.slice(0,10)]));
 if(e.seasonal_intervals)html+='<h3>Seasonal interval diary</h3>'+table(['Start → end','Days','Median · mm/day'],e.seasonal_intervals.map(r=>[`${r.start.slice(0,10)} → ${r.end.slice(0,10)}`,num(r.days),num(r.median_rate_mm_day)]));
 if(e.fire_method){html+=`<h3>Valid combined coverage</h3><p>${num(e.support.common_area_km2)} km² of usable land. Each contributing view requires all its declared baseline dates and a valid latest HH/HV comparison. The view-count map records how many groups contribute at each cell; this is not a footprint shared by every observation.</p>`;const f=e.fire_method;html+='<h3>Combined HH/HV method</h3><p>Each view has its own median linear-power baseline. Its absolute HH and HV dB changes are added. The latest valid magnitudes are averaged across views, then smoothed and standardized across the land window. No unaffected reference rectangle is subtracted.</p>'+table(['Viewing group','Baseline dates','Latest comparison'],f.groups.map(g=>[g.group,g.baseline_dates.map(d=>d.slice(0,10)).join(', '),g.latest.slice(0,10)]))+`<p>Smoothing sigma ${num(f.smoothing_m)} m; score threshold ${num(f.score_threshold)}; minimum patch ${num(f.minimum_patch_ha)} ha. Normalization median ${num(f.normalization.median_db)} dB; scaled MAD ${num(f.normalization.scaled_mad_db)} dB. Terrain-shadow masking is not applied. Check water exclusions and independent fire evidence.</p>`;}
 if(e.method_references)html+='<h3>Method background</h3><ul>'+e.method_references.filter(u=>u.startsWith('https://')).map((u,i)=>`<li><a href="${esc(u)}" target="_blank" rel="noopener">${i===0?'Official product guide':'Scientific method reference'} ↗</a></li>`).join('')+'</ul>';
 if(e.baseline)html+=`<h3>Which baseline is used?</h3><p>General baseline-departure maps use the per-cell median of ${e.baseline.dates.map(d=>esc(d.slice(0,10))).join(', ')}. The standardized view divides by robust spread with a ${e.baseline.noise_floor_db} dB floor; it is not a probability. The first-to-last map remains explicitly an endpoint comparison.</p>`;
 if(e.event_baseline)html+=`<p><b>Flood event baseline:</b> ${e.event_baseline.dates.map(d=>esc(d.slice(0,10))).join(', ')}. Its candidate-water area is ${num(e.event_baseline.water_candidate_km2)} km². This pre-comparison baseline is separate from the first-to-last context map.</p>`;
 html+='<h3>Native sample contribution</h3><p>Data availability and quality maps include accepted fraction and rejection fractions for each source. These describe contributions within the native window before averaging, not confidence in an environmental classification. Read source paths and units in the saved provenance.</p>';
 if(e.water_states?.thresholds_db)html+=`<h3>Ambiguous water states</h3><p>0 = rule not met; 1 = water candidate; 2 = the joint classification can change within ±${num(e.water_states.ambiguity_half_width_db)} dB of HH ${num(e.water_states.thresholds_db.HH)} / HV ${num(e.water_states.thresholds_db.HV)} dB. A channel clearly above its threshold excludes water even if the other is near its threshold. Occupancy uses the hard binary rule; this band is separate, not calibrated uncertainty.</p>`;
 else if(e.water_states)html+=`<h3>Ambiguous water states</h3><p>0 = dry candidate; 1 = water candidate; 2 = within ±${num(e.water_states.ambiguity_half_width_db)} dB of the fitted/user threshold (${num(e.water_states.threshold_db)} dB). The binary candidate-area chart is retained; ambiguity is shown separately and is not calibrated uncertainty.</p>`;
 if(e.water_validation){const v=e.water_validation;html+=`<h3>Independent label evaluation</h3><p>${esc(v.status)}. Calibration: ${v.calibration_cells} labeled cells. Held-out test: ${v.test_cells} cells. Metrics evaluate the binary threshold rule; the ambiguous band is reported separately. ${esc(v.calibration_method||'')}</p>`;if(v.test_cells)html+=table(['Precision','Recall','IoU','False water / missed water'],[[num(v.precision),num(v.recall),num(v.iou),`${v.false_positive} / ${v.false_negative}`]]);html+=`<p class="small">${esc(v.sampling_note)}</p>`;}
 if(e.grid_sensitivity)html+=(e.water_method?.id==='hh_hv'?'<p>Grid scenarios average both converted sigma-zero powers, then apply both thresholds.</p>':'')+'<h3>Grid-resolution sensitivity</h3><p>Valid linear power is coarsened by factors 1, 2 and 4 before thresholding. Common support can shrink at edges; compare its area as well as classified area.</p>'+table(['Factor','Common km²','Latest candidate-water km²'],e.grid_sensitivity.map(r=>[r.factor,num(r.common_area_km2),num(r.area_km2.at(-1))]));
 if(e.reference_sensitivity?.length)html+='<h3>Reference-choice sensitivity</h3>'+table(['Reference polygon','Latest relative change · dB'],e.reference_sensitivity.map(r=>[r.name,num(r.relative_change_db)]));
 if(e.network_model){const n=e.network_model;html+=`<h3>Phase-network model</h3><p><b>${esc(n.status)}</b>. ${esc(n.reason||n.interpretation||'')} Rank ${n.rank}; redundancy ${n.redundancy}. ${esc(n.method)}</p>`;if(e.network_series)html+='<div id="network-chart" class="chart"></div>';}
 if(e.seasonal_model)html+=`<h3>Annual model availability</h3><p>${esc(e.seasonal_model.status)} · ${esc(e.seasonal_model.reason||e.seasonal_model.interpretation||'')}</p>`;
 if(e.corrections)html+='<h3>Applied phase corrections</h3>'+table(['Source','Applied operation'],e.corrections.map(r=>[r.source.slice(0,16),r.applied.map(c=>c.operation+' '+c.path).join('; ')||'No supplied screen applied']));
 if(e.phase_reference_sensitivity?.length)html+='<h3>Phase reference-choice sensitivity</h3>'+table(['Reference','Fixed cells','Latest pair origin shift · mm'],e.phase_reference_sensitivity.map(r=>[r.name,r.fixed_pixels,num(r.pair_reference_shift_mm.at(-1))]));
 if(e.event_controls)html+=`<p><b>Non-bracketing comparison intervals:</b> ${e.event_controls.length}. These are timing controls, not independently proven unchanged ground.</p>`;
 if(e.method_sensitivity?.length)html+='<h3>Retrieval-method sensitivity</h3><p>Methods share radar inputs and are not independent votes. Differences are reported on matched recommended support.</p>'+table(['Method','Matched cells','Latest median · m³/m³'],e.method_sensitivity.map(r=>[r.method,r.common_pixels,num(r.median_by_date.at(-1))]));
 if(e.stable_terrain)html+='<h3>Stable-terrain offset comparison</h3>'+table(['Date','Stable cells','Bias · m/day','Removed'],e.stable_terrain.map(r=>[r.date.slice(0,10),r.stable_pixels,num(r.median_rate_bias_m_day),r.applied?'yes':'no']));
 if(e.independent_validation)html+=regionalReferenceHTML(e.independent_validation,table);
 if(e.observation_gaps)html+=`<p><b>Longest gap between observed starts:</b> ${num(e.observation_gaps.longest_gap_days)} days. ${esc(e.observation_gaps.meaning)}</p>`;
 if(e.tracking?.available===false){html+=`<section class="warning-note" role="status"><h3>Candidate object tracking unavailable</h3><p>${esc(e.tracking.reason)}</p><p>${esc(e.tracking.meaning)} Increase the minimum patch area in an edited workflow, or use a smaller area/date selection, to try tracking separately. No tracking GeoJSON is available for this run.</p></section>`;}
 else if(e.tracking){const t=e.tracking;html+=`<h3>Dated candidate objects</h3><p>${t.objects.length} objects · ${t.links.length} overlap links · minimum ${num(t.minimum_area_m2)} m². ${esc(t.meaning)}</p><div class="evidence-actions"><button class="secondary" id="toggle-patches">Show candidate outlines on map</button><a href="${state.artifactBase+t.geometry_file}" download>Download patch GeoJSON ↓</a></div><label>Inspect an observed object<select id="patch-choice"><option value="">Choose an object…</option>${t.objects.map(r=>`<option value="${r.id}">${r.id} · ${esc(r.date.slice(0,10))} · ${num(r.area_m2/1e6)} km² · ${esc(r.event)}</option>`).join('')}</select></label><div id="patch-inspection" class="patch-record">Select an object, or click a displayed outline, to inspect its acquired date and overlap relationships.</div>`;}
 return html;
}

function metricLabel(key){return ({median_cm:'Median LOS change · cm',p10_cm:'Spatial 10th percentile · cm',p90_cm:'Spatial 90th percentile · cm',mapped_area_km2:'Mapped area · km²',median_rate_cm_year:'Median LOS rate · cm/year',median_rate_cm_month:'Same rate · cm/month',span_days:'Observed span · days',acquisition_dates:'Acquired dates',baseline_water_candidate_km2:'Baseline candidate water · km²',latest_water_candidate_km2:'Latest candidate water · km²',water_gain_km2:'Water gained · km²',water_loss_km2:'Water lost · km²',common_valid_area_km2:'Comparable area · km²',new_water_candidate_km2:'New candidate water · km²',observed_dry_again_km2:'Later observed dry · km²',unresolved_water_candidate_km2:'Unresolved · km²',valid_pixels:'Compared cells',valid_fraction:'Valid comparison fraction',median:'Spatial median',p10:'Spatial 10th percentile',p90:'Spatial 90th percentile'})[key]||key.replaceAll('_',' ')}

let contextDrawingLayer=null,patchOutlineLayer=null;
function hasContextRole(role){try{return JSON.parse($('#spatial-context')?.value||'null')?.features?.some(f=>f.properties?.role===role)||false}catch{return false}}
function clearContextMap(){if(contextDrawingLayer&&typeof map!=='undefined')map.removeLayer(contextDrawingLayer);contextDrawingLayer=null}
function clearPatchOutlines(){if(patchOutlineLayer&&typeof map!=='undefined')map.removeLayer(patchOutlineLayer);patchOutlineLayer=null;if(typeof state!=='undefined'){state.patchGeometry=null;state.showPatches=false}}
function refreshContextMap(){
 clearContextMap();const text=$('#spatial-context')?.value?.trim();if(!text){if($('#context-status'))$('#context-status').textContent='No spatial context supplied.';return}
 try{const context=JSON.parse(text);if(context.type!=='FeatureCollection'||!Array.isArray(context.features))throw new Error('Use a GeoJSON FeatureCollection.');
 contextDrawingLayer=L.geoJSON(context,{style:{color:'#8a729e',weight:2,fillOpacity:.04},onEachFeature:(f,l)=>l.bindTooltip(esc((f.properties?.name||'Context')+' · '+(f.properties?.role||'zone')))}).addTo(map);
 $('#context-status').textContent=`${context.features.length} polygon(s) supplied. Processing validates geometry, roles, dates and source labels.`;renderInputGuide();
 }catch(e){$('#context-status').textContent='Context error: '+e.message}
}
function addContextRectangle(bbox){
 const [w,s,e,n]=bbox;const main=state.bbox;if(!main||w<main[0]||s<main[1]||e>main[2]||n>main[3]){toast('Keep named rectangles inside the analysis area, or enlarge the main area first.');return}let context;try{context=JSON.parse($('#spatial-context').value||'{"type":"FeatureCollection","features":[]}')}catch{toast('Fix the context JSON before adding a rectangle.');return}
 const f=state.pendingContext||{name:'Comparison zone',role:'zone',source:'user supplied'};
 context.features.push({type:'Feature',properties:f,geometry:{type:'Polygon',coordinates:[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}});$('#spatial-context').value=JSON.stringify(context,null,2);refreshContextMap();toast('Named rectangle added. Review its role and source before running.');state.pendingContext=null;
}
function setupAdvancedInputs(){
 document.getElementById('water-method')?.addEventListener('change',()=>{renderAnalysisSettings();renderInputGuide()});
 const bindFile=(id,target,after)=>{const input=document.getElementById(id);if(input)input.onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2*1024**2)throw new Error('Use a JSON file smaller than 2 MiB.');const text=await file.text();JSON.parse(text);$('#'+target).value=text;after?.()}catch(err){toast(err.message)}}};
 bindFile('context-file','spatial-context',refreshContextMap);bindFile('reference-file','reference-observations');
 document.getElementById('spatial-context')?.addEventListener('change',refreshContextMap);
 const draw=document.getElementById('draw-context');if(draw)draw.onclick=()=>{if(!state.bbox){toast('Select the main analysis area first.');return}state.pendingContext={name:$('#context-name').value.trim()||'Comparison zone',role:$('#context-role').value,source:$('#context-source').value.trim()||'user supplied; interpretation requires justification'};view('explore');setDraw('context');$('#draw-hint').textContent='Named area: click two opposite corners inside your study rectangle.';$('#map').scrollIntoView({behavior:'smooth',block:'center'})};
}
function syncPatchOutlines(){
 if(patchOutlineLayer){map.removeLayer(patchOutlineLayer);patchOutlineLayer=null}if(!state.showPatches||!state.patchGeometry)return;
 const frame=state.layer?.frame_index;
 const data={type:'FeatureCollection',features:state.patchGeometry.features.filter(f=>frame===undefined||f.properties.frame===frame)};
 patchOutlineLayer=L.geoJSON(data,{style:{color:'#f0a24f',weight:2,fillOpacity:.05},onEachFeature:(f,l)=>{l.bindTooltip(`Object ${f.properties.id} · ${String(f.properties.date).slice(0,10)}`);l.on('click',()=>inspectPatch(f.properties.id))}}).addTo(map);
}
function inspectPatch(id){
 const record=state.result?.extra?.tracking?.objects.find(r=>r.id===Number(id));const host=$('#patch-inspection');if(!record||!host)return;
 host.innerHTML=`<b>Candidate object ${record.id} · ${esc(record.date.slice(0,10))}</b><p>${(record.area_m2/1e6).toFixed(4)} km² · ${esc(record.event)}<br>Parents: ${record.parents.join(', ')||'none'} · Children: ${record.children.join(', ')||'none'}</p><p>First observed candidate: ${esc(record.first_observed_active?.slice(0,10)||'unavailable')}<br>Last earlier fully inactive footprint: ${esc(record.last_observed_inactive_before_first_active?.slice(0,10)||'not observed')}<br>First later fully inactive footprint: ${esc(record.first_later_observed_inactive?.slice(0,10)||'not observed')}</p><p>Links mean overlap on consecutive acquired snapshots. Activity between dates is unknown.</p>`;
 if($('#patch-choice'))$('#patch-choice').value=String(id);const frame=resultFrames().find(f=>f.frame_index===record.frame);if(frame)selectLayer(frame.index);
}
function mountScientificExtras(result){
 mountProcessingTrace(result);
 const tracking=result.extra?.tracking;
 const button=$('#toggle-patches');if(button)button.onclick=async()=>{try{if(!state.patchGeometry){const geometry=await api(state.artifactBase+tracking.geometry_file);if(state.result!==result)return;state.patchGeometry=geometry}state.showPatches=!state.showPatches;syncPatchOutlines();button.textContent=state.showPatches?'Hide candidate outlines':'Show candidate outlines on map'}catch(e){toast(e.message)}};
 if(tracking&&$('#patch-choice'))$('#patch-choice').onchange=e=>inspectPatch(e.target.value);
 if(result.extra.network_series&&typeof Plotly!=='undefined')Plotly.newPlot('network-chart',[{x:result.extra.network_series.map(r=>r.date),y:result.extra.network_series.map(r=>r.median_mm),type:'scatter',mode:'lines+markers',connectgaps:false}],{margin:{l:50,r:15,t:15,b:55},xaxis:{title:'Reconstructed acquisition epoch'},yaxis:{title:'Phase-equivalent mm · first epoch zero'},paper_bgcolor:'transparent',plot_bgcolor:'transparent'},{responsive:true,displayModeBar:false});
}
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',setupAdvancedInputs);

async function reuseAnalysisSetup(result,job){
 try{
  const display=state.result===result&&state.layer?{palette:state.displayPalette||'standard',mode:displayMode,low:displayLow,high:displayHigh,layer:state.layer.id,unit:state.layer.unit,category_colors:state.categoryColors||{},category_opacity:state.categoryOpacity||{}}:result.display_preferences;
  const ids=result.sources.map(s=>s.id),request={...job.request,projects:[result.project],granules:ids};
  await restoreReferenceWorkspace({...job,request},ids);state.pendingDisplayPreferences=display||null;
  view('explore');showWorkflowSetup(result.project);toast('This run’s exact local files and settings are restored. Continue to check the saved reference or review inputs.');
 }catch(e){toast(e.message)}
}

if(typeof document!=='undefined')document.getElementById('fire-method')?.addEventListener('change',()=>{state.referenceChoice=null;renderAnalysisSettings();renderInputGuide();if(state.catalog.GCOV)renderCatalog()});
