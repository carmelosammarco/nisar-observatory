const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../frontend/experience.js'),'utf8');
function render(validation){const esc=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');const c={esc};vm.createContext(c);vm.runInContext(source,c);return c.renderScientificEvidence({report:{headline:'Test',findings:[],validation:'SYNTHETIC fixture'},extra:{independent_validation:validation}})}
test('reference result identifies its physical quantity, component, canonical units and matched values',()=>{
 const html=render({status:'evaluated against supplied regional references',quantity_label:'Signed radar-component interval-average rate',component:'alongTrackOffset',unit:'m/day',samples:1,requested_samples:1,excluded_samples:0,bias:.00002,rmse:.00004,unbiased_rmse:0,comparison_basis:'Regional median on fixed common support',meaning:'Matched references are not global accuracy.',matched_pairs:[{date:'2026-01-01',end:'2026-01-13',observed:.00003,reference:.00001,unit:'m/day',source:'Independent test record'}]});
 for(const text of ['along-track component','m/day','Regional median','Bias · app − reference','2.000e-5','4.000e-5','1 of 1','2026-01-01 → 2026-01-13','Independent test record'])assert.ok(html.includes(text),text);
});
test('legacy assumptions, missing comparisons and untrusted citations remain visible and escaped',()=>{
 const html=render({status:'partially evaluated',samples:1,requested_samples:2,excluded_samples:1,unit:'mm',bias:0,rmse:0,unbiased_rmse:0,assumptions:['Legacy unit assumed <mm>'],matched_pairs:[{date:'2026-01-01',end:'2026-01-13',observed:1,reference:1,unit:'mm',source:'<script>bad()</script>'}],excluded_references:[{date:'2026-01-13',source:'<img onerror=bad>',reason:'No finite regional summary'}]});
 assert.ok(html.includes('1 of 2'));assert.ok(html.includes('Why records were excluded'));assert.ok(html.includes('Legacy unit assumed &lt;mm&gt;'));assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<img '));
});
test('large comparison tables are bounded and old saved reports remain readable',()=>{
 const records=Array.from({length:25},(_,i)=>({date:'2026-01-01',end:'2026-01-13',observed:i,reference:i,unit:'mm',source:'source-'+i}));
 const html=render({status:'evaluated',samples:25,unit:'mm',bias:0,rmse:0,unbiased_rmse:0,matched_pairs:records});assert.ok(html.includes('source-19'));assert.ok(!html.includes('source-20'));assert.ok(html.includes('first 20'));assert.ok(html.includes('run JSON'));
 const old=render({status:'evaluated against supplied regional references',samples:1,unit:'mm',bias:2,rmse:2,unbiased_rmse:0});assert.ok(old.includes('Matched regional reference check'));assert.ok(old.includes('RMSE'));
});
test('settings explain paired dates, units and all supported quantities without equating speed and components',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../../frontend/index.html'),'utf8');for(const text of ['los_displacement','radar_component_rate','horizontal_speed','slantRangeOffset','alongTrackOffset','regional <b>median</b>','vertical velocity fixed to zero','not the fitted annual rate'])assert.ok(html.includes(text),text);
});
test('reference help follows product visibility and stays hidden for elementary workflows',()=>{
 const app=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'../../frontend/index.html'),'utf8');
 assert.ok(html.includes('id="regional-reference-inputs" data-settings-products="GUNW GOFF" data-guided-only'));
 assert.ok(html.includes('<tr data-settings-products="GUNW">'));assert.ok(html.includes('<tr data-settings-products="GOFF">'));
 const nodes=[{dataset:{settingsProducts:'GUNW GOFF',guidedOnly:''}},{dataset:{settingsProducts:'GUNW'}},{dataset:{settingsProducts:'GOFF'}}];
 const c={state:{selected:'P07',plans:[]},$:()=>({}),$$:()=>nodes,productFor:id=>({P07:'GOFF',P04:'GUNW',P01:'GCOV'}[id]),hasScientificBlocks:()=>false};vm.createContext(c);vm.runInContext(app.slice(app.indexOf('function renderAnalysisSettings('),app.indexOf('let coverageLayer=')),c);
 c.renderAnalysisSettings();assert.equal(nodes[0].hidden,false);assert.equal(nodes[1].hidden,true);assert.equal(nodes[2].hidden,false);
 c.state.selected='P04';c.renderAnalysisSettings();assert.equal(nodes[1].hidden,false);assert.equal(nodes[2].hidden,true);
 c.state.selected='P01';c.renderAnalysisSettings();assert.equal(nodes[0].hidden,true);
 c.state.selected=null;c.state.labRecipe={method:'custom',product:'GOFF',steps:[]};c.renderAnalysisSettings();assert.equal(nodes[0].hidden,true);
});
