/* Explicit event coverage selection: per-group LOS evidence, never mixed with other tools. */
const QUAKE_GROUP='__event_coverage__';
function quakeCoverageMode(){return (state.selected==='P05'||!state.selected&&typeof scientificMethod==='function'&&scientificMethod()==='P05')&&state.groups.GUNW===QUAKE_GROUP}
function quakeItemBrackets(item){
 const exact=$('#event-timestamp')?.value?.trim(),event=exact||$('#event-date')?.value;if(!event)return false;
 const stamps=(item.name||'').match(/\d{8}T\d{6}/g),stamp=s=>s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8)+'T'+s.slice(9,11)+':'+s.slice(11,13)+':'+s.slice(13,15)+'Z';
 const start=stamps?.length===4?stamp(stamps[1]):item.start,end=stamps?.length===4?stamp(stamps[2]):item.end;
 return exact?Date.parse(start)<Date.parse(exact)&&Date.parse(exact)<Date.parse(end):start?.slice(0,10)<event&&event<end?.slice(0,10);
}
function selectQuakeCoverage({silent=false}={}){
 const items=state.catalog.GUNW?.items||[],matches=items.filter(quakeItemBrackets);
 if(!matches.length){toast('Enter the documented earthquake date or timestamp, then search for pairs with an acquisition before and after it.');return null}
 const viewed=items.find(i=>i.group===state.groups.GUNW)||matches.find(i=>state.checked.has(i.id))||matches[0],parts=viewed.group.split('_');
 const excluded=new Set(typeof activeQualityExclusions==='function'?activeQualityExclusions():[]);
 const eligible=matches.filter(i=>!excluded.has(i.id)).filter(i=>{const f=i.group.split('_');return f[1]===parts[1]&&f.slice(3).join('_')===parts.slice(3).join('_')});
 if(!eligible.length){toast('No event-bracketing files match the viewed direction, mode and release. Choose a group that spans the event and try again.');return null}
 const selected=new Map();for(const item of eligible){const old=selected.get(item.group);if(!old||Date.parse(item.end)-Date.parse(item.start)<Date.parse(old.end)-Date.parse(old.start))selected.set(item.group,item)}
 if(selected.size>32){toast('More than 32 source groups found. Narrow the area or dates before selecting event coverage.');return null}
 items.forEach(i=>{state.checked.delete(i.id);state.downloadChecked.delete(i.id)});selected.forEach(i=>state.checked.add(i.id));state.groups.GUNW=QUAKE_GROUP;renderCatalog();
 if(!silent)toast(`${selected.size} event-bracketing files selected across adjacent tracks/frames. The processor prefers valid reference cells shared across groups and reports any independent group references; inspect source coverage and overlap differences after processing.`);
 return [...selected.values()];
}
function mountQuakeCoverage(){
 if(state.selected!=='P05'||state.tab!=='GUNW')return;
 const host=$('#quake-coverage-action');if(!host)return;
 host.innerHTML='<p class="small">Earthquake coverage is selected inside the guided setup, together with the event time and reference check.</p><button type="button" class="text-button" id="review-quake-setup">Prepare earthquake analysis →</button>';
 $('#review-quake-setup').onclick=()=>showWorkflowSetup('P05');
}
function quakeSetupPath(){return '<section class="info-note"><h3>Earthquake displacement in three steps</h3><ol><li>Find GUNW pairs with an acquisition before and after the documented event. One pair is enough for one frame; adjacent frames add coverage.</li><li>Choose Prepare, then Continue to check the selected data and compare reference candidates. Choose a stable reference on independently justified ground away from the rupture. In mosaic mode it must include coherent ground inside every selected group. The processor first looks for the same valid analysis cells across all groups. If fewer than 25 are shared, it explicitly reports independent group references.</li><li>Read the main displacement map in cm. Negative LOS is away from the satellite and positive is toward it. Read the active color key: Rainbow has many colors; Diverging emphasizes the scale midpoint. This is interval change, not a daily or annual rate.</li></ol><p>For NASA’s Venezuela example: June 13–25 and June 18–30, 2026, covering the June 24 earthquake sequence. The two earthquakes are not separated by these radar intervals.</p><button type="button" class="secondary" id="setup-quake-example">Use Venezuela paper’s area →</button></section>'}
function applyQuakePreset(p){
 if(p.id!=='P05'||!p.event_date)return;
 state.selected='P05';$('#event-date').value=p.event_date;$('#event-timestamp').value=p.event_timestamp||'';resetSearchDates();
 if($('#data-maturity'))$('#data-maturity').value='PROVISIONAL';renderTools('all');
}

// Area presets keep the full mission search range and shared quality choices.
function applyAreaPreset(p){
 state.selected=p.id;state.tab=p.product;state.p04Reviewed=false;
 if(!['P03','P06'].includes(p.id)&&$('#baseline-end'))$('#baseline-end').value='';
 if(p.id==='P03'){restoreAnalysisOptions(p.options||{fire_method:'combined',baseline_count:3,patch_area_m2:100000,resolution:20});state.reference=null;state.referenceChoice=null}
 if(p.id==='P07'&&p.options){restoreAnalysisOptions(p.options);state.reference=null;state.referenceChoice=null}
 if(p.id==='P06'){restoreAnalysisOptions(p.options||{surface_method:'evolving',smoothing_m:40,baseline_count:1,patch_area_m2:30000,resolution:20,channel:'HHHH'});state.reference=null;state.referenceChoice=null}
 if($('#flood-date'))$('#flood-date').value=p.flood_date||'';
 if(p.id==='P05'){applyQuakePreset(p);return}
 $('#event-date').value='';$('#event-timestamp').value='';
 resetSearchDates();
 if($('#data-maturity'))$('#data-maturity').value=p.maturity||(p.id==='P04'?'BETA':'PROVISIONAL');
 renderTools('all');
}
