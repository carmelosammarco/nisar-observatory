const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const read=name=>fs.readFileSync(path.join(__dirname,'../../frontend',name),'utf8');
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function context(){const c={esc};vm.createContext(c);vm.runInContext(read('experience.js'),c);return c}
test('measurement, reference and source-quality views explain their different footprints',()=>{
 const c=context(),result={project:'P01',series:[],extra:{spatial_support:{version:'1.0'}}},layer={id:'change',unit:'dB'};
 assert.match(c.layerExplanation({...layer,spatial_scope:'study domain'},result),/restricted to the supplied study domain/);
 assert.match(c.layerExplanation({...layer,spatial_scope:'reference support'},result),/do not enlarge regional/);
 assert.match(c.layerExplanation({...layer,spatial_scope:'source quality'},result),/not the area used/);
 assert.match(c.layerExplanation({...layer,spatial_scope:'processing footprint'},result),/supporting reference or stable-ground/);
});
test('new boundary evidence labels geometry counts and escapes the policy',()=>{
 const c=context(),result={extra:{spatial_support:{version:'1.0',domain_pixels:100,processing_footprint_pixels:125,auxiliary_pixels_outside_domain:25,policy:'Study <domain> only'}}};
 const html=c.spatialSupportHTML(result,(head,rows)=>head.join('|')+rows.flat().join('|'));
 assert.match(html,/Study &lt;domain&gt;/);assert.match(html,/Auxiliary footprint/);assert.match(html,/Study domain\|100\|Processing footprint\|125\|Auxiliary footprint outside study\|25/);assert.match(html,/not guaranteed usable measurements/);
});
test('older domain results get a targeted rerun notice, without rewriting or flagging already-clipped methods',()=>{
 const c=context(),result={processing_options:{spatial_context:{features:[{properties:{role:'domain'}}]}},extra:{}},before=JSON.stringify(result);
 assert.match(c.spatialSupportHTML(result),/Earlier study-boundary handling/);assert.equal(JSON.stringify(result),before);
 assert.equal(c.spatialSupportHTML({extra:{}}),'');
 assert.equal(c.spatialSupportHTML({...result,extra:{fire_method:{id:'combined'}}}),'');
 assert.equal(c.spatialSupportHTML({...result,extra:{surface_method:{id:'evolving'}}}),'');
 assert.equal(c.spatialSupportHTML({...result,project:'P02'}),'','A domain-only wetland case without auxiliary roles was already clipped');
 assert.equal(c.spatialSupportHTML({...result,project:'P07',processing_options:{...result.processing_options,offset_filter:false,offset_local_filter:false}}),'','The published glacier setup disabled spatial filtering');
});
test('elementary workflows retain shared spatial context when saving a repeatable recipe',()=>{
 const nodes=new Map(),spatial={type:'FeatureCollection',features:[]},c={state:{plans:[],catalog:{},checked:new Set(),localFiles:[],bbox:null},$:k=>nodes.get(k)||null,$$:()=>[],structuredClone,Number,JSON,Blob,URL,setTimeout,document:{},toast(){},options:()=>({resolution:100,min_valid_fraction:.5,spatial_context:spatial,password:'never-retain'})};
 vm.createContext(c);c.state.labWorkflowRules=structuredClone(JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/scientific-blocks.json'),'utf8')).rules);vm.runInContext(read('workflow-contract.js'),c);vm.runInContext(read('workflow-workspace.js'),c);c.resetWorkflowDraft();
 const recipe=c.collectWorkflowRecipe();assert.equal(JSON.stringify(recipe.options.spatial_context),JSON.stringify(spatial));assert.equal('password' in recipe.options,false);
 const html=read('index.html');assert.ok(html.includes('<section class="spatial-context-editor">'));assert.ok(html.includes('id="elementary-context-help"'));assert.ok(html.includes('do not add a classifier or independent validation step'));
});

test('measurement coverage uses the declared study rather than the surrounding rectangle',()=>{
 const c=context(),result={extra:{spatial_support:{domain_pixels:100}}};
 assert.equal(c.layerCoverageText({spatial_scope:'study domain',valid_pixels:75,valid_fraction:.1},result),'75.0% of the study domain has valid values.');
 assert.equal(c.layerCoverageText({spatial_scope:'source quality',valid_pixels:75,valid_fraction:.1},result),'10.0% of the analysis grid has valid values.');
 assert.equal(c.layerCoverageText({valid_fraction:.5},{}),'50.0% of the analysis grid has valid values.');
});
