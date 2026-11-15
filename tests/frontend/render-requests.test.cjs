const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../frontend/render-requests.js'),'utf8');
function context(extra={}){const c={state:{previewCache:new Map()},AbortController,DOMException,URL,Date,setTimeout,clearTimeout,...extra};vm.createContext(c);vm.runInContext(source,c);return c}
const response=(status,busy='1',retry='0')=>({status,headers:{get:key=>key==='X-NISAR-Render-Busy'?busy:retry},text:async()=>''});
test('only explicit local render-busy responses are retried, with original request settings',async()=>{
 const calls=[],responses=[response(429),response(200)];let waits=0;
 const c=context({fetch:async(...args)=>{calls.push(args);return responses.shift()}});
 c.renderWait=async()=>{};
 const controller=new AbortController(),r=await c.fetchRenderedMap('/api/visualization/run/P01/event',{signal:controller.signal,headers:{accept:'application/json'},onWaiting:()=>waits++});
 assert.equal(r.status,200);assert.equal(waits,1);assert.equal(calls.length,2);assert.equal(calls[0][1].signal,controller.signal);assert.equal(calls[1][1].headers.accept,'application/json');assert.equal('onWaiting' in calls[1][1],false);
 for(const [status,busy] of [[422,'1'],[503,'1'],[429,null]]){let count=0;c.fetch=async()=>{count++;return response(status,busy)};assert.equal((await c.fetchRenderedMap('/api/map-image/x')).status,status);assert.equal(count,1)}
});
test('admission waiting has a bounded deadline and does not retry forever',async()=>{
 let now=0,count=0;const c=context({Date:{now:()=>now},fetch:async()=>{count++;return response(429)}});
 c.renderWait=async()=>{now+=30000};await assert.rejects(c.fetchRenderedMap('/api/map-image/x'),/still busy/);assert.equal(count,2);
});
test('superseding a map preview aborts its wait and avoids a stale follow-up fetch',async()=>{
 let calls=0,waiting;const reached=new Promise(resolve=>waiting=resolve);
 const c=context({fetch:async()=>{calls++;return response(429)}}),first=c.beginMapPreviewRequest();
 const pending=c.fetchRenderedMap('/api/visualization/a',{signal:first.signal,onWaiting:waiting});
 await reached;const second=c.beginMapPreviewRequest();
 await assert.rejects(pending,error=>error.name==='AbortError');assert.equal(first.signal.aborted,true);assert.equal(second.signal.aborted,false);assert.equal(calls,1);
 c.cancelMapPreviewRequest();assert.equal(second.signal.aborted,true);
});
test('aborted requests and cancelled timers do not issue network calls',async()=>{
 let calls=0;const c=context({fetch:async()=>{calls++}}),controller=new AbortController();controller.abort();
 await assert.rejects(c.fetchRenderedMap('/api/visualization/a',{signal:controller.signal}),{name:'AbortError'});
 await assert.rejects(c.renderWait(10000,controller.signal),{name:'AbortError'});assert.equal(calls,0);
});
test('preview cache is bounded, uses recency, and never retains an oversized image',()=>{
 const c=context();for(let i=0;i<24;i++)c.cacheMapPreview(String(i),{image:'small',min:i});
 assert.equal(c.state.previewCache.size,24);c.getMapPreview('0');c.cacheMapPreview('next',{image:'new'});
 assert.equal(c.state.previewCache.has('0'),true);assert.equal(c.state.previewCache.has('1'),false);
 c.state.previewCache.clear();const image='a'.repeat(3*1024*1024);for(let i=0;i<20;i++)c.cacheMapPreview(String(i),{image});
 assert.ok(c.state.previewCache.size<20);let bytes=0;for(const display of c.state.previewCache.values())bytes+=c.mapPreviewBytes(display);assert.ok(bytes<=32*1024*1024);
 c.cacheMapPreview('huge',{image:'a'.repeat(17*1024*1024)});assert.equal(c.state.previewCache.has('huge'),false);
});
test('validity masks and category metadata count towards the preview cache budget',()=>{
 const c=context(),image='a'.repeat(4*1024*1024),validity_image='b'.repeat(4*1024*1024);
 c.cacheMapPreview('first',{image,validity_image,categories:[{label:'No data',value:0,opacity:0}]});c.cacheMapPreview('second',{image,validity_image});
 assert.equal(c.state.previewCache.size,1);assert.equal(c.state.previewCache.has('second'),true);
});
test('real preview selection replaces stale waits, caches only the latest image and clears on reset',async()=>{
 const app=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8'),nodes=new Map(),messages=[],calls=[];
 const $=key=>{if(!nodes.has(key))nodes.set(key,{value:'',textContent:'',innerHTML:'',hidden:false});return nodes.get(key)};
 let ready;const waiting=new Promise(resolve=>ready=resolve),layers=['first','second'].map(id=>({id,label:id,kind:'continuous',unit:'dB',raster:id+'.tif',bounds:[[0,0],[1,1]]}));
 const display={image:'data:image/png;base64,test',min:0,max:2,palette:[[1,2,3],[4,5,6]],mode:'shared',clipped_percent:0};
 const c=context({$: $,URLSearchParams,queueMicrotask,requestVersions:{pixel:0,result:0},overlay:null,map:{closePopup(){},removeLayer(){}},resultFrames:()=>[],syncResultNavigation(){},stopTimeline(){},toast:m=>messages.push(m),esc:String,Plotly:{relayout(){}},
  L:{imageOverlay(){return {events:{},once(name,fn){this.events[name]=fn},addTo(){queueMicrotask(()=>this.events.load());return this}}}},
  fetch:async url=>{calls.push(url);if(url.includes('/first?'))return {...response(429),text:async()=>{ready();return ''}};return {ok:true,status:200,json:async()=>display}}
 });
 c.state.result={project:'P06',layers};c.state.currentJob={id:'run'};c.state.artifactBase='/api/artifacts/run/P06/';
 vm.runInContext(app.slice(app.indexOf('async function api('),app.indexOf('function toast(')),c);
 vm.runInContext("let previewVersion=0,displayMode='shared',displayLow=null,displayHigh=null;"+app.slice(app.indexOf('async function selectLayer('),app.indexOf('async function inspectPixel(')),c);
 const first=c.selectLayer(0);await waiting;const second=c.selectLayer(1);
 assert.equal(await first,false);assert.equal(await second,true);assert.equal(c.state.layer.id,'second');assert.equal(c.state.previewCache.size,1);assert.ok([...c.state.previewCache.keys()][0].startsWith('second?'));assert.equal(messages.length,0);
 assert.equal(await c.selectLayer(1),true);assert.equal(calls.length,2,'Cached current preview should not issue another request');
 vm.runInContext(app.slice(app.indexOf('function clearMapResult('),app.indexOf('function clearArea(')),c);
 const active=c.beginMapPreviewRequest();c.clearMapResult();assert.equal(active.signal.aborted,true);assert.equal(c.state.previewCache.size,0);assert.equal(c.state.result,null);
});
test('application API does not retry mutations or unrelated failures',async()=>{
 const app=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');let calls=0;
 const c=context({fetch:async()=>{calls++;return {ok:false,status:429,json:async()=>({detail:'Do not retry this mutation'})}}});
 vm.runInContext(app.slice(app.indexOf('async function api('),app.indexOf('function toast(')),c);
 await assert.rejects(c.api('/api/run',{method:'POST',body:'{}'}),/Do not retry this mutation/);assert.equal(calls,1);
});
