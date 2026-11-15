const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const experience=fs.readFileSync(path.join(__dirname,'../../frontend/experience.js'),'utf8'),app=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');
test('new exploration clears client state but preserves saved inventory and makes no server mutation',()=>{
 const fields=new Map(),saved=[{id:'saved'}],calls=[];
 const $=key=>{if(!fields.has(key))fields.set(key,{value:'old',checked:true,hidden:false,open:true,innerHTML:''});return fields.get(key)};
 const c={state:{job:'active',poll:7,localFiles:saved,selected:'P01',groups:{GCOV:'old'}},requestVersions:{job:0},$: $, $$:()=>[],clearTimeout(){},clearArea(){calls.push('clear');c.state.catalog={};c.state.checked=new Set();c.state.result=null;c.state.bbox=null},renderTools(){},view:v=>calls.push(v),toast:m=>calls.push(m),api(){throw Error('No server writes permitted in reset')}};
 vm.createContext(c);{const appSource=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');vm.runInContext(appSource.slice(appSource.indexOf('function resetSearchDates()'),appSource.indexOf('let coverageLayer=')),c);}vm.runInContext(experience,c);c.newExploration();
 assert.equal(c.state.job,null);assert.equal(c.state.selected,null);assert.equal($('#run-selected').disabled,true);assert.equal($('#run-selected').innerHTML,'Choose a tool to continue');assert.equal(c.state.localFiles,saved);assert.equal($('#tool-list').scrollTop,0);assert.equal(c.requestVersions.job,1);assert.equal($('#job-progress').hidden,true);assert.ok(calls.includes('clear'));
});
test('next frame replaces the visible overlay only after its image loads',async()=>{
 const fields=new Map(),removed=[],old={name:'old'},layer={id:'observation_1',label:'Next',unit:'class',kind:'binary',bounds:[[0,0],[1,1]],raster:'next.tif'},result={project:'P01',layers:[layer],series:[]};let incoming;
 const $=key=>{if(!fields.has(key))fields.set(key,{value:'.9',textContent:'',innerHTML:''});return fields.get(key)};
 const c={state:{result,layer:{id:'old'},currentJob:{id:'job'},artifactBase:'/artifacts/'},requestVersions:{pixel:0},overlay:old,map:{closePopup(){},removeLayer:l=>removed.push(l)},$: $, $$:()=>[],URLSearchParams,resultFrames:()=>[],syncResultNavigation(){},stopTimeline(){},toast(){},esc:String,Plotly:{relayout(){}},api:async()=>({image:'data:image/png;base64,test',min:0,max:1,palette:[[1,2,3],[4,5,6],[7,8,9]],clipped_percent:0}),L:{imageOverlay(){incoming={listeners:{},once(event,cb){this.listeners[event]=cb},addTo(){return this}};return incoming}}};
 vm.createContext(c);{const appSource=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');vm.runInContext(appSource.slice(appSource.indexOf('function resetSearchDates()'),appSource.indexOf('let coverageLayer=')),c);}vm.runInContext("let previewVersion=0,displayMode='shared',displayLow=null,displayHigh=null;"+app.slice(app.indexOf('async function selectLayer('),app.indexOf('async function inspectPixel(')),c);
 const pending=c.selectLayer(0);for(let n=0;n<5&&!incoming;n++)await Promise.resolve();
 assert.equal(c.overlay,old);assert.equal(c.state.layer.id,'old');assert.equal(removed.length,0);
 incoming.listeners.load();assert.equal(await pending,true);assert.equal(c.overlay,incoming);assert.equal(c.state.layer,layer);assert.equal(removed[0],old);
});
test('changing units resets custom limits and changing palettes fetches a distinct preview',async()=>{
 const fields=new Map(),queries=[],messages=[];const $=key=>{if(!fields.has(key))fields.set(key,{value:'.9',innerHTML:'',textContent:''});return fields.get(key)};
 const layer={id:'los_rate_month',label:'Monthly rate',unit:'cm/month',kind:'diverging',bounds:[[0,0],[1,1]],raster:'rate.tif'},result={project:'P04',layers:[layer],series:[]};
 const c={state:{result,layer:null,currentJob:{id:'job'},artifactBase:'/artifacts/',displayPalette:'mexico',displayUnit:'cm/year'},requestVersions:{pixel:0},overlay:null,map:{closePopup(){},removeLayer(){}},$: $, $$:()=>[],URLSearchParams,resultFrames:()=>[],syncResultNavigation(){},stopTimeline(){},toast:m=>messages.push(m),esc:String,Plotly:{relayout(){}},api:async url=>{queries.push(url);return {image:'data:image/png;base64,test',min:-2,max:2,palette:[[1,2,3],[4,5,6],[7,8,9]],palette_name:'mexico',mode:'shared',clipped_percent:0}},L:{imageOverlay(){return {listeners:{},once(event,cb){this.listeners[event]=cb},addTo(){queueMicrotask(()=>this.listeners.load());return this}}}}};
 vm.createContext(c);{const appSource=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');vm.runInContext(appSource.slice(appSource.indexOf('function resetSearchDates()'),appSource.indexOf('let coverageLayer=')),c);}vm.runInContext("let previewVersion=0,displayMode='custom',displayLow=-30,displayHigh=30;"+app.slice(app.indexOf('async function selectLayer('),app.indexOf('async function inspectPixel(')),c);
 assert.equal(await c.selectLayer(0),true);assert.match(queries[0],/mode=shared/);assert.match(queries[0],/palette=mexico/);assert.doesNotMatch(queries[0],/low=/);assert.match(messages[0],/Units changed/);
 c.state.displayPalette='standard';assert.equal(await c.selectLayer(0),true);assert.equal(queries.length,2);assert.match(queries[1],/palette=standard/);
});

test('an unavailable map clears the old overlay and shows the reason without an error toast',async()=>{
 const fields=new Map(),removed=[],old={},l={id:'recovery',label:'First later dry observation',unit:'observation index',raster:'recovery.tif'},result={project:'P01',layers:[l]},reason='Recovery cannot be assessed: no acquisition after the comparison date is selected.';
 const $=k=>{if(!fields.has(k))fields.set(k,{textContent:'',innerHTML:'',hidden:false});return fields.get(k)};
 const c={state:{result,currentJob:{id:'run'},artifactBase:'/artifacts/'},requestVersions:{pixel:0},overlay:old,map:{closePopup(){},removeLayer:l=>removed.push(l)},$: $,URLSearchParams,resultFrames:()=>[],syncResultNavigation(){},stopTimeline(){},Plotly:{relayout(){}},api:async()=>({available:false,reason,valid_pixels:0}),toast(){throw Error('Empty scientific result is not an error')},L:{imageOverlay(){throw Error('Do not invent an image')}}};vm.createContext(c);
 vm.runInContext("let previewVersion=0,displayMode='shared',displayLow=null,displayHigh=null;"+app.slice(app.indexOf('async function selectLayer('),app.indexOf('async function inspectPixel(')),c);
 assert.equal(await c.selectLayer(0),true);assert.equal(c.overlay,null);assert.equal(c.state.layer,l);assert.equal(removed[0],old);assert.equal($('#frame-status').textContent,reason);assert.equal($('#map-image-link').hidden,true);assert.equal($('#raster-link').href,'/artifacts/recovery.tif');assert.equal($('#display-low').disabled,true);
});

test('settings return preserves the chosen tool; sidebar Explore intentionally clears it',()=>{
 const back={dataset:{view:'explore'},classList:{contains:()=>false}},nav={dataset:{view:'explore'},classList:{contains:n=>n==='nav'}},calls=[];
 const c={state:{selected:'P07'},$$:()=>[back,nav],openExploreFromNavigation(){c.state.selected=null;calls.push("explore")},view:n=>calls.push(n)};
 vm.createContext(c);vm.runInContext(app.slice(app.indexOf("$$('[data-view]').forEach"),app.indexOf("$('#rail-connect').onclick")),c);
 back.onclick();assert.equal(c.state.selected,'P07');assert.equal(calls.at(-1),'explore');nav.onclick();assert.equal(c.state.selected,null);
});

test('sidebar leaves examples for a clean exploration but ordinary navigation preserves a draft',()=>{const calls=[],c={state:{exampleWorkspace:true},$:()=>({classList:{contains:()=>false}}),resetExamplesView(){calls.push('invalidate-example')},newExploration(o){calls.push('clean');assert.equal(o.quiet,true)},clearToolSelection(){calls.push('clear-tool')},view(n){calls.push(n)}};vm.createContext(c);vm.runInContext(app.slice(app.indexOf('function openExploreFromNavigation'),app.indexOf('function clearToolSelection')),c);c.openExploreFromNavigation();assert.deepEqual(calls,['invalidate-example','clean']);calls.length=0;c.state.exampleWorkspace=false;c.openExploreFromNavigation();assert.deepEqual(calls,['clear-tool','explore'])});
