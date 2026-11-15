const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function context(fields={}){
 const c={esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),state:{artifactBase:'/api/artifacts/safe/LAB/'},$:s=>fields[s]};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/result-views.js'),'utf8'),c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/experience.js'),'utf8'),c);return c;
}
function result(){return {layers:[{id:'trace_filtered',label:'Filtered offset',unit:'m',trace_operation:'offset_screen',trace_group:'same',valid_fraction:.5,start:'2026-01-01',end:'2026-01-13',interpretation:'Offsets before time normalization.'}],extra:{step_history:[{step:1,operation:'offset_screen',input_unit:'m',output_unit:'m',parameters:{global_filter:true}}],offset_filter_diagnostics:[{cutoff_m:1}],processing_trace:{version:'1.0.0',scope:'Latest captured map per view; not every internal temporary.',stages:[{step:1,operation:'offset_screen',maps:[{id:'trace_filtered',label:'Filtered offset',unit:'m',role:'Captured intermediate'}],diagnostic_keys:['offset_filter_diagnostics']}]}}};}
test('step inspector labels real units, coverage scope and optional advanced diagnostics',()=>{
 const c=context(),html=c.processingTraceHTML(result());
 assert.match(html,/Inspect your executed steps/);assert.match(html,/Captured intermediate · Filtered offset · m/);assert.match(html,/Enabled/);assert.match(html,/Recorded diagnostics · advanced/);assert.match(html,/not every internal temporary/);assert.match(html,/workflow.json/);assert.match(html,/result.json/);assert.match(html,/not additional independent findings/);
});
test('step inspector escapes saved descriptions, parameters and diagnostic values',()=>{
 const c=context(),r=result();r.extra.step_history[0].parameters={note:'<img src=x onerror=alert(1)>'};r.extra.offset_filter_diagnostics=['<script>'];r.extra.processing_trace.stages[0].maps[0].label='<script>';
 const html=c.processingTraceHTML(r);assert.doesNotMatch(html,/<script>|<img src=x/);assert.match(html,/&lt;script>/);assert.match(html,/&lt;img/);
});
test('step map control uses the existing map viewer and never recomputes processing',async()=>{
 const fields={'#trace-layer-1':{value:'trace_filtered'},'[data-trace-show="1"]':{},'#trace-info-1':{},'#map':{scrollIntoView(){fields.scrolled=true}}};
 const c=context(fields),r=result();c.state.result=r;let paused=0,selected=null;c.stopTimeline=()=>paused++;c.selectLayer=async i=>{selected=i;return true};
 c.mountProcessingTrace(r);assert.match(fields['#trace-info-1'].textContent,/50.0% valid coverage/);assert.match(fields['#trace-info-1'].textContent,/2026-01-01 → 2026-01-13/);
 await fields['[data-trace-show="1"]'].onclick();assert.equal(selected,0);assert.equal(paused,1);assert.equal(fields.scrolled,true);
 c.state.result={};selected=null;await fields['[data-trace-show="1"]'].onclick();assert.equal(selected,null);
});
test('unavailable or absent trace maps are explained without inventing outputs',()=>{
 const c=context(),r=result();r.layers=[];r.extra.processing_trace.stages[0].maps=[];r.extra.processing_trace.stages[0].unavailable_reason='This step records decisions rather than a raster.';
 const html=c.processingTraceHTML(r);assert.match(html,/records decisions/);assert.doesNotMatch(html,/data-trace-show/);assert.equal(c.processingTraceHTML({extra:{}}),'');
 r.extra.processing_trace.version='999';assert.match(c.processingTraceHTML(r),/different format/);
});
test('intermediate map quantities and explanations remain separate from final map controls',()=>{
 const c=context(),r=result(),layer=r.layers[0];assert.match(c.resultDisplayQuantity(layer,r),/^intermediate:offset_screen/);assert.equal(c.extraLayerExplanation(layer,r),'Offsets before time normalization.');
});
test('long diagnostics are explicitly shortened and complete run export remains linked',()=>{
 const c=context(),r=result();r.extra.offset_filter_diagnostics=['x'.repeat(9000)];const html=c.processingTraceHTML(r);assert.match(html,/Preview shortened/);assert.match(html,/complete run record/);assert.ok(html.length<11000);
});

test('editor and inspector share relevant water parameter titles and visibility',()=>{
 const c=context();vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/workflow-workspace.js'),'utf8'),c);
 const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/scientific-blocks.json'),'utf8'));c.state.labOperators=fixture.operators;
 const r=result();r.extra.step_history[0]={step:1,operation:'water_rule',input_unit:'power',output_unit:'class',parameters:{method:'single',threshold_db:-17,hh_db:-14,hv_db:-23}};r.extra.processing_trace.stages[0].operation='water_rule';
 const html=c.processingTraceHTML(r);assert.match(html,/Single-channel threshold · dB/);assert.match(html,/Single-channel brightness threshold/);assert.doesNotMatch(html,/HH threshold|HV threshold/);
});

test('effective fitted settings are shown separately from declared recipe parameters',()=>{
 const c=context(),r=result();r.extra.processing_trace.stages[0].parameter_note='Effective threshold: -16 dB after supplied training labels; not held-out accuracy.';
 assert.match(c.processingTraceHTML(r),/Effective threshold: -16 dB/);
});

test('a summary after a fitted map keeps the same non-temporal explanation as the editor',()=>{
 const c=context();vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/workflow-workspace.js'),'utf8'),c);const r=result();
 r.extra.step_history[0]={step:1,operation:'summary',input_domain:'map',input_unit:'cm/year',output_unit:'cm/year',parameters:{statistic:'mean'}};r.extra.processing_trace.stages[0].operation='summary';
 const html=c.processingTraceHTML(r);assert.match(html,/No temporal averaging is performed/);assert.match(c.workflowStepExplanation('summary','cm/year','cm/year','map'),/No temporal averaging is performed/);
});

test('unavailable tracking explains its bound without offering fabricated objects or downloads',()=>{
 const c=context(),r={report:{headline:'Run',findings:[],validation:'Exploratory'},layers:[],extra:{tracking:{available:false,reason:'Limit <1000>',meaning:'No partial objects'}}};
 const html=c.renderScientificEvidence(r);assert.match(html,/Candidate object tracking unavailable/);assert.match(html,/Limit &lt;1000>/);assert.doesNotMatch(html,/id="toggle-patches"|Download patch GeoJSON|id="patch-choice"/);
});
