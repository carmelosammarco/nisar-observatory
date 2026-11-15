/* Shared data suitability and reference-choice sensitivity; never stable-ground certification. */
let referenceCandidateLayer=null;
function referenceProject(){return state.selected||'P04'}
function referenceThresholdMeaning(report){return (report.threshold_meaning||'').replace('25 cells, 80% support and 0.70 coherence are engineering screening rules, not scientifically calibrated reliability thresholds.','Candidate patches require at least 25 shared cells and 80% shared coverage. Coherence of 0.70 is preferred for ranking; lower-coherence candidates can appear with review warnings. These are engineering rules, not calibrated reliability thresholds.')}
function referenceToolName(){return state.plans?.find(p=>p.id===referenceProject())?.name||referenceProject()}
function referenceProduct(){return typeof productFor==='function'?productFor(referenceProject()):referenceProject()==='P03'?'GCOV':'GUNW'}
function referenceTimestamp(value){
 if(!value||!Number.isFinite(Date.parse(value)))return value;
 const extra=(String(value).match(/\.(\d+)(?:Z|[+-]\d{2}:\d{2})$/)?.[1]||'').slice(3);
 return new Date(value).toISOString().replace(/Z$/,extra+'Z').replace(/\.0+Z$/,'Z').replace(/(\.\d*?[1-9])0+Z$/,'$1Z');
}
const REFERENCE_ASSISTANT_VERSION='2.1';
function referenceSnapshot(bbox,ids,o,project=referenceProject(),assistantVersion=REFERENCE_ASSISTANT_VERSION){
 const defaults={resolution:100,coherence:.4,min_valid_fraction:.5,apply_ionosphere:false,channel:'auto',phase_allow_mixed_revisions:false,quake_mosaic:false,event_timestamp:null,event_date:null,baseline_count:1,baseline_end:null};
 return JSON.stringify({assistantVersion,project,bbox,ids:[...ids].sort(),options:Object.fromEntries(Object.entries(defaults).map(([k,v])=>[k,k==='event_timestamp'?referenceTimestamp(o[k]??v):o[k]??v])),context:(o.spatial_context?.features||[]).filter(f=>['domain','affected'].includes(f.properties?.role||'zone'))});
}
function currentReferenceSnapshot(){return referenceSnapshot(state.bbox,Object.values(state.catalog).flatMap(c=>c.items||[]).filter(i=>i.product===referenceProduct()&&state.checked.has(i.id)).map(i=>i.id),options([referenceProject()],{referenceOnly:true}))}
function clearReferenceAssistant(){
 if(referenceCandidateLayer&&typeof map!=='undefined')map.removeLayer(referenceCandidateLayer);referenceCandidateLayer=null;
 if($('#reference-map-actions'))$('#reference-map-actions').hidden=true;
 state.referenceChoice=null;state.referenceAssessment=null;state.previousReferenceContext=null;const panel=$('#reference-assistant-panel');if(panel){panel.hidden=true;panel.innerHTML=''}
}
async function startReferenceAssistant(){
 try{
  if(!state.bbox)throw Error('Select your analysis area first.');
  const items=Object.values(state.catalog).flatMap(c=>c.items||[]).filter(i=>i.product===referenceProduct()&&state.checked.has(i.id));
  if(!items.length)throw Error(`Select ${referenceProduct()} files for this area first.`);
  const o=options([referenceProject()],{referenceOnly:true});delete o.reference_assistant_id;delete o.reference_candidate_id;
  const j=await api('/api/reference-assistant',{method:'POST',body:JSON.stringify({bbox:state.bbox,granules:items.map(i=>i.id),projects:[referenceProject()],options:o})});
  watchJob(j.id);$('#job-progress').scrollIntoView({behavior:'smooth',block:'center'});toast('Checking your selected observations. Next you will choose a reference, then run.');return j;
 }catch(e){toast(e.message);return null}
}
function referenceCandidateHTML(c,replacePolygons=false){
 const brightness=state.referenceAssessment?.report?.product==='GCOV',r=state.referenceAssessment?.report||{};
 const n=v=>v===null||v===undefined?'Unavailable':Number(v).toLocaleString(undefined,{maximumFractionDigits:3});
 return `<article class="reference-candidate"><div class="reference-candidate-head"><h3>${esc(c.name)}</h3><span class="source-badge">${esc(c.data_suitability)}</span></div><dl><div><dt>Shared coverage across every observation</dt><dd>${n(100*c.shared_fraction)}% · ${n(c.shared_cells)} cells</dd></div>${!brightness?`<div><dt>Worst-pair median coherence</dt><dd>${n(c.worst_pair_median_coherence)} / 1</dd></div>`:''}<div><dt>Spatial variation inside the patch</dt><dd>${n(c.spatial_spread??c.maximum_pair_spatial_mad_rad)} ${esc(c.spread_unit||'rad')}</dd></div>${(r.project||'P04')==='P04'?`<div><dt>Relative rate versus Candidate 1</dt><dd>${n(c.relative_rate_to_candidate_1_cm_year)}${c.relative_rate_to_candidate_1_cm_year==null?'':' cm/year'}</dd></div>`:''}${c.relative_reference_offsets?.length?`<div><dt>Offsets versus Candidate 1 · each observation</dt><dd>${c.relative_reference_offsets.map(n).join(' · ')} ${esc(r.comparison_unit||'cm')}</dd></div>`:''}</dl><p class="small">${brightness?'Brightness uniformity describes radar measurements. A uniform patch can still have changed; verify that it is unaffected.':'Coherence and phase spread describe accepted measurements. A uniform, coherent patch may still move.'} Candidate 1 is zero by definition.</p>${c.warnings.length?`<ul class="small">${c.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul>`:''}<div class="reference-actions"><button class="secondary" data-preview-reference="${esc(c.id)}">Locate on map</button><button class="primary" data-use-reference="${esc(c.id)}">${replacePolygons?'Replace reference polygons & use':'Use this reference'}</button></div></article>`;
}
async function openReferenceAssessment(job){
 if(job.status!=='completed'||!job.assistant_url){showReferenceFailure(job);return}
 const version=requestVersions.job;const report=await api(job.assistant_url);if(version!==requestVersions.job)return;
 if(referenceCandidateLayer)map.removeLayer(referenceCandidateLayer);referenceCandidateLayer=null;
 state.referenceAssessment={job,report,snapshot:referenceSnapshot(job.request.bbox,report.sources.map(s=>s.id),job.request.options,report.project||job.request.projects?.[0]||'P04',report.assistant_version||'1.0')};
 renderReferenceAssessment();$('#reference-assistant-panel').scrollIntoView({behavior:'smooth',block:'start'});
}
function renderReferenceAssessment(){
 const assessment=state.referenceAssessment,host=$('#reference-assistant-panel');if(!assessment||!host)return;
 const {report:r,job}=assessment,n=v=>v==null?'Unavailable':Number(v).toLocaleString(undefined,{maximumFractionDigits:3});
 let current=false;try{current=currentReferenceSnapshot()===assessment.snapshot}catch{}
 host.hidden=false;
 host.innerHTML=`${typeof workflowStagesHTML==='function'?workflowStagesHTML(r.project||'P04',2):''}<div class="section-head"><div><span class="eyebrow">${esc(r.project||'P04')} · STEP 2 OF 3 · REFERENCE</span><h2>Choose the reference for your analysis.</h2></div></div><p>${r.pair_count} selected observations · ${n(r.grid.resolution_m)} m grid · ${n(r.common_cells)} shared cells inside the drawn study boundary. Boundary cells on the analysis grid can extend slightly beyond that outline, so result-grid counts can differ. The assistant samples the whole study grid and compares up to 225 patches and shows up to three separated candidates. The order reflects measurement suitability, with larger support preferred within the quality screen. Independently check that the patch is stationary or, for brightness comparisons, unaffected.</p><div class="warning-note"><strong>Reference reliability: independent evidence needed.</strong> ${esc(r.stability)} Choose ground outside suspected change. Nearby terrain at similar elevation is preferable when known; this assistant has no elevation or land-cover evidence.</div>${!current?'<div class="info-note"><b>This assessment belongs to different files or settings.</b><p>Restore its saved local inputs, or run the assistant again for your current selection. No reference is applied automatically.</p><button class="secondary" id="restore-reference-inputs">Restore this assessment’s saved inputs</button></div>':''}${r.current_reference?`<section class="info-note"><h3>Keep your checked reference</h3><p>${n(r.current_reference.shared_cells)} shared cells · ${esc(r.current_reference.data_suitability)}. Keeping it preserves your chosen spatial zero. Stability or unaffected status is still your assumption.</p><button type="button" class="primary" id="use-checked-reference" ${!current||r.current_reference.shared_cells<25||r.current_reference.warnings.some(w=>w.includes('No comparison ground'))?'disabled':''}>Keep this reference →</button></section>`:''}<details class="setup-advanced"><summary>Compare reference sensitivity, quality and your current reference</summary>${r.relative_candidate_rate_span_cm_year!=null?`<section class="reference-sensitivity"><h3>How much does the reference choice matter?</h3><strong>${n(r.relative_candidate_rate_span_cm_year)} cm/year</strong><p>Spread between the candidate reference rates over this selected record. Choosing a different reference shifts the entire rate map. A large difference needs investigation; small agreement still cannot prove stability.</p></section>`:''}${(r.project||'P04')==='P04'?`<p><b>Rate comparison:</b> ${esc(r.rate_comparison_status||'See candidate values.')}</p>`:''}${r.maximum_candidate_offset_span!=null?`<section class="reference-sensitivity"><h3>How sensitive are the observation maps?</h3><strong>${n(r.maximum_candidate_offset_span)} ${esc(r.comparison_unit)}</strong><p>Largest offset spread between candidates for any selected observation. Different reference choices shift the corresponding map by this amount; this is not an error bound.</p></section>`:''}<p><b>How to read the comparison:</b> ${esc(r.comparison_meaning||r.relative_rate_meaning)}</p><p class="small">${r.product==='GCOV'?'GCOV has no phase coherence test here. Positive calibrated power is converted to dB. Complete coverage and spatial uniformity guide the search; a patch can still be affected by surface change. See the comparison values in dB.':'Coherence runs from 0 to 1: higher means more consistent radar echoes, not less ground movement. Here it is the median of accepted-sample coherence within each patch, shown for its worst pair. The robust phase spread (median absolute deviation, or MAD) measures variation within a patch: lower means more spatially uniform, not stationary. The screening thresholds are engineering rules, not calibrated confidence percentages.'}</p>${r.current_reference?`<section class="info-note"><h3>Your reference when this assessment ran</h3><p>${esc(r.current_reference.origin)} · ${n(r.current_reference.shared_cells)} common cells · ${n(100*r.current_reference.shared_fraction)}% shared coverage · ${esc(r.current_reference.data_suitability)}. Stability remains unverified.</p><p>Offsets versus Candidate 1: ${(r.current_reference.relative_reference_offsets||[]).map(n).join(' · ')||'Unavailable'} ${esc(r.comparison_unit||'')}. Choosing another reference changes the spatial origin.</p>${r.current_reference.warnings.map(w=>`<p>${esc(w)}</p>`).join('')}</section>`:''}<details class="setup-advanced"><summary>Observation order for the offset comparison</summary><ol>${r.sources.map(s=>`<li>${esc(s.start.slice(0,10))} → ${esc(s.end.slice(0,10))} · ${esc(s.group)}</li>`).join('')}</ol></details></details><div class="reference-candidates">${r.candidates.map(c=>referenceCandidateHTML(c,hasContextRole('reference'))).join('')||'<div class="info-note"><h3>No suggested patch passes the reference screen</h3><p>The selected views may share too little usable ground, or their shared patch coverage does not pass the assistant screen. Review the selected views and shared settings, or draw and check your own justified reference. Quality thresholds stay unchanged until you choose to edit them.</p><button type="button" class="secondary" id="reference-review-settings">Review data &amp; shared settings →</button></div>'}</div><details class="setup-advanced"><summary>Other reference options & assessment download</summary><div class="reference-actions"><button class="secondary" id="reference-show-all" ${!r.candidates.length?'disabled':''}>Show all candidates on map</button><button class="secondary" id="reference-redraw">Draw my own reference</button><button class="secondary" id="reference-repeat">Recheck current selection</button><button class="secondary" id="hide-reference-candidates">Hide candidate outlines</button><a href="${job.assistant_url}" download>Download assessment JSON ↓</a></div></details><p class="small">${esc(referenceThresholdMeaning(r))} ${esc(r.next_step)}</p><div id="reference-choice-status" role="status"></div>`;
 if($('#reference-review-settings'))$('#reference-review-settings').onclick=()=>{showWorkflowSetup(referenceProject());const detail=$('#workflow-dialog .workflow-options');if(detail)detail.open=true};
 if($('#use-checked-reference'))$('#use-checked-reference').onclick=()=>adoptReferenceCandidate('current');
 host.querySelectorAll('[data-use-reference]').forEach(b=>{b.disabled=!current;b.onclick=()=>adoptReferenceCandidate(b.dataset.useReference)});
 host.querySelectorAll('[data-preview-reference]').forEach(b=>b.onclick=()=>showReferenceCandidates(b.dataset.previewReference));
 $('#hide-reference-candidates').onclick=()=>{if(referenceCandidateLayer)map.removeLayer(referenceCandidateLayer);referenceCandidateLayer=null};
 $('#reference-show-all').onclick=()=>showReferenceCandidates();
 $('#reference-repeat').onclick=()=>showWorkflowSetup(referenceProject());
 $('#reference-redraw').onclick=()=>{state.referenceChoice=null;setDraw('reference');$('#map').scrollIntoView({behavior:'smooth',block:'center'})};
 if($('#restore-reference-inputs'))$('#restore-reference-inputs').onclick=()=>restoreReferenceInputs();
}
function showReferenceCandidates(id=null){
 const report=state.referenceAssessment?.report;if(!report)return;
 if(referenceCandidateLayer)map.removeLayer(referenceCandidateLayer);referenceCandidateLayer=L.layerGroup().addTo(map);
 const colors=['#734c9e','#c27629','#237c82'];
 report.candidates.forEach((c,i)=>{if(id&&id!==c.id)return;const [w,s,e,n]=c.bbox;L.rectangle([[s,w],[n,e]],{color:colors[i],weight:3,dashArray:'6 4',fillOpacity:.12}).bindTooltip(`${esc(c.name)} · ${(100*c.shared_fraction).toFixed(1)}% shared coverage · stability unverified`,{permanent:true,direction:'top'}).addTo(referenceCandidateLayer)});
 const selected=report.candidates.find(c=>c.id===id),b=selected?.bbox||report.grid.bbox;
 map.fitBounds([[b[1],b[0]],[b[3],b[2]]],{padding:[65,65],maxZoom:MAP_MAX_ZOOM});$('#map').scrollIntoView({behavior:'smooth',block:'center'});
 if($('#reference-map-actions')){$('#reference-map-actions').hidden=false;$('#reference-map-return').onclick=()=>$('#reference-assistant-panel').scrollIntoView({behavior:'smooth',block:'start'})}
 toast('Dashed boxes are data-quality candidates. Inspect their locations; none is certified stable ground.');
}
function adoptReferenceCandidate(id){
 try{
  const a=state.referenceAssessment;if(!a||currentReferenceSnapshot()!==a.snapshot)throw Error('The selection changed. Recheck the reference candidates before choosing.');
  const c=id==='current'?{...a.report.current_reference,id:'current',name:'Your checked reference',bbox:a.job.request.options.reference_bbox}:a.report.candidates.find(c=>c.id===id);
  if(id==='current'){const current=options([referenceProject()],{referenceOnly:true}),saved=a.job.request.options,refs=o=>(o.spatial_context?.features||[]).filter(f=>f.properties?.role==='reference');if(!a.report.current_reference||c.shared_cells<25||c.warnings.some(w=>w.includes('No comparison ground'))||JSON.stringify(current.reference_bbox??null)!==JSON.stringify(saved.reference_bbox??null)||JSON.stringify(refs(current))!==JSON.stringify(refs(saved)))throw Error('Your drawn reference changed or lacks shared support. Check it again.');}
  if(!c)throw Error('Candidate unavailable.');
  if(id!=='current'&&hasContextRole('reference')){const context=JSON.parse($('#spatial-context').value);state.previousReferenceContext=$('#spatial-context').value;context.features=context.features.filter(f=>f.properties?.role!=='reference');$('#spatial-context').value=JSON.stringify(context);clearContextMap();}
  if(referenceCandidateLayer){map.removeLayer(referenceCandidateLayer);referenceCandidateLayer=null}
  state.reference=c.bbox?[...c.bbox]:null;state.referenceChoice={project:referenceProject(),assessment_id:a.job.id,candidate_id:c.id,bbox:c.bbox?[...c.bbox]:null};if(referenceProject()==='P04')state.p04Reviewed=true;
  if(refRectangle)map.removeLayer(refRectangle);refRectangle=null;if(c.bbox){const [w,s,e,n]=c.bbox;refRectangle=L.rectangle([[s,w],[n,e]],{color:'#4d8dd3',weight:3,fillOpacity:.15}).addTo(map);}
  renderInputGuide();$('#reference-choice-status').innerHTML=`<div class="info-note"><b>${esc(c.name)} selected as your spatial reference.</b><p>Its shared data are usable; stability is still your assumption. Review the location, then run ${esc(referenceToolName())} using the selected files. No processing has started automatically. A higher ranking does not guarantee better agreement between views or a physically stable reference.</p>${state.previousReferenceContext?'<button class="secondary" id="undo-reference-polygons">Restore previous reference polygons</button>':''}<button class="primary" id="run-with-reference">Run ${esc(referenceToolName())} with this reference →</button></div>`;
  if($('#undo-reference-polygons')&&state.previousReferenceContext)$('#undo-reference-polygons').onclick=restorePreviousReferencePolygons;
  if(typeof refreshContextMap==='function')refreshContextMap();
  if($('#reference-map-actions'))$('#reference-map-actions').hidden=true;
  $('#reference-choice-status').scrollIntoView?.({behavior:'smooth',block:'center'});
  $('#run-with-reference').onclick=()=>run(true);toast('Reference selected. Your run will retain the assessment and its limitations.');
 }catch(e){toast(e.message)}
}
async function restoreReferenceWorkspace(job,sourceIds,isCurrent=()=>true){
  const saved=await refreshLocalFiles();if(!isCurrent())return;const items=sourceIds.map(id=>saved.find(i=>i.id===id));
  if(items.some(i=>!i))throw Error('Some assessed originals are not saved locally. Find or import the same files, then recheck the reference.');
  const request=job.request,o=request.options;drawArea(request.bbox);state.selected=request.projects?.[0]||'P04';if(state.selected==='P04')state.p04DefaultsApplied=true;
  restoreAnalysisOptions(o);if(state.selected==='P05')state.quakeCoveragePreference=o.quake_mosaic?'event':'selected';
  state.reference=o.reference_bbox||null;if(state.reference){const [w,s,e,n]=state.reference;refRectangle=L.rectangle([[s,w],[n,e]],{color:'#4d8dd3',weight:2,fillOpacity:.15}).addTo(map)}
  resetSearchDates();
  const releases=new Set(items.map(i=>i.maturity||(/_X\d{5}$/.test(i.group)?'BETA':null)));
  if($('#data-maturity')&&releases.size===1&&!releases.has(null))$('#data-maturity').value=[...releases][0];
  const product=referenceProduct();state.catalog={[product]:{items,hits:items.length}};state.tab=product;state.checked=new Set(items.map(i=>i.id));state.groups[product]=o.fire_method==='combined'?'__fire_views__':o.quake_mosaic?QUAKE_GROUP:state.selected==='P04'&&$('#phase-mixed').checked?items[0].group.replace(/_([A-Z])\d{5}$/,'_$1'):items[0].group;
  if(typeof refreshContextMap==='function')refreshContextMap();renderTools();renderCatalog();
}
async function restoreReferenceInputs(){
 try{
  const a=state.referenceAssessment;if(!a)return;
  await restoreReferenceWorkspace(a.job,a.report.sources.map(s=>s.id));
  state.referenceAssessment=a;renderReferenceAssessment();toast('Saved local inputs restored. Inspect candidates, then choose a reference.');
 }catch(e){toast(e.message)}
}

function restorePreviousReferencePolygons(){
 if(!state.previousReferenceContext)return;
 $('#spatial-context').value=state.previousReferenceContext;state.previousReferenceContext=null;state.referenceChoice=null;state.reference=null;state.p04Reviewed=false;
 if(refRectangle){map.removeLayer(refRectangle);refRectangle=null}
 if(typeof refreshContextMap==='function')refreshContextMap();else clearContextMap();
 renderInputGuide();renderReferenceAssessment();toast('Previous reference polygons restored. The selected tool will use those polygons; review inputs before running.');
}

function activeQualityExclusions(){
 const excluded=state.qualityExclusions;if(!excluded)return [];
 try{return excluded.snapshot===referenceSnapshot(state.bbox,[],options([referenceProject()],{referenceOnly:true}))?excluded.ids.filter(id=>!state.checked.has(id)):[]}catch{return []}
}
// A failed source is never silently dropped. Retry requires an explicit selection change.
function referenceSourceErrors(job){return (job.source_errors||[]).filter(e=>e.message==='No coherent connected-component pixels survive quality screening.')}
function referenceRecoveryMatches(job){
 try{return referenceProject()===job.request.projects[0]&&currentReferenceSnapshot()===referenceSnapshot(job.request.bbox,job.request.granules,job.request.options,job.request.projects[0])}catch{return false}
}
function referenceRecoveryHTML(job){
 const bad=referenceSourceErrors(job);if(!bad.length)return '';
 return `<section class="warning-note"><h3>One or more selected files have no usable pixels</h3><p>The quality screen found no coherent connected-component pixels for these files in the requested area. This is a measurement-quality issue; changing the reference cannot repair it. Keep the quality threshold and explicitly leave these files out to check the remaining coverage. No downloaded files will be deleted.</p><ul>${bad.map(e=>`<li>${esc(e.name||e.source)}<br>${esc(e.message)}</li>`).join('')}</ul><button type="button" class="primary" id="retry-reference-sources" ${referenceRecoveryMatches(job)?'':'disabled'}>Deselect ${bad.length} unusable file${bad.length===1?'':'s'} & find a reference →</button>${!referenceRecoveryMatches(job)?'<button type="button" class="secondary" id="restore-retry-reference">Restore this run’s saved inputs, deselect unusable files & find a reference →</button>':''}<p class="small">${referenceRecoveryMatches(job)?'The next assessment uses only the remaining selected sources. Review its coverage and warnings before processing.':'This run has different inputs from your current workspace. Select the same files and settings, or uncheck the listed file in your current selection and use Find or check a reference.'}</p></section>`;
}
function mountReferenceRecovery(job){
 const button=$('#retry-reference-sources');if(button)button.onclick=()=>retryReferenceSources(job);
 const restore=$('#restore-retry-reference');if(restore)restore.onclick=async()=>{try{await restoreReferenceWorkspace(job,job.request.granules);retryReferenceSources(job)}catch(e){toast(e.message)}};
}
function retryReferenceSources(job){
 if(!referenceRecoveryMatches(job))return toast('Your selection changed. Recheck the current files before leaving any source out.');
 const bad=referenceSourceErrors(job),ids=new Set(bad.map(e=>e.source));
 if(!bad.length)return;
 if(job.request.granules.every(id=>ids.has(id)))return toast('No usable selected files remain. Choose other observations or another area.');
 const snapshot=referenceSnapshot(job.request.bbox,[],job.request.options,job.request.projects[0]);
 state.qualityExclusions={snapshot,ids:[...new Set([...(state.qualityExclusions?.snapshot===snapshot?state.qualityExclusions.ids:[]),...ids])]};
 for(const id of ids)state.checked.delete(id);
 state.referenceChoice=null;state.referenceAssessment=null;
 if(referenceCandidateLayer&&typeof map!=='undefined')map.removeLayer(referenceCandidateLayer);referenceCandidateLayer=null;
 renderCatalog();renderInputGuide();startReferenceAssistant();
}
function showReferenceFailure(job){
 const host=$('#reference-assistant-panel');if(!host){toast(job.message);return}
 host.hidden=false;host.innerHTML=`<span class="eyebrow">REFERENCE CHECK · ACTION NEEDED</span><h2>Check your selected measurements first</h2><p>${esc(job.message)}</p>${referenceRecoveryHTML(job)}${(job.source_errors||[]).filter(e=>!referenceSourceErrors(job).includes(e)).map(e=>`<p><b>${esc(e.name||e.source)}</b><br>${esc(e.message)}</p>`).join('')}<p>You do not need to draw a reference before asking the assistant to find candidates. A reference is applied only when you choose Use this reference.</p>`;
 mountReferenceRecovery(job);host.scrollIntoView({behavior:'smooth',block:'start'});
}
