const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');
function context(){
 let active=false;const timers=[],calls=[],bounds={south:19.14,west:-99.4,north:19.65,east:-98.75};
 const explore={id:'explore',classList:{toggle(_,value){active=value},contains(){return active}}};
 const c={state:{pendingAreaFit:true},$:s=>s==='#explore'?explore:{},$$:s=>s==='.view'?[explore]:[],titles:{explore:'Explore Earth',examples:'Examples'},history:{replaceState(){}},setTimeout:f=>timers.push(f),map:{invalidateSize:o=>calls.push(['size',o]),fitBounds:(b,o)=>calls.push(['fit',b,o])},areaRectangle:{getBounds:()=>bounds},MAP_MAX_ZOOM:23,refreshLocalFiles:async()=>{},renderCatalog(){},renderExamples(){},toast(){},window:{scrollTo(){}}};
 vm.createContext(c);vm.runInContext(source.slice(source.indexOf('function view('),source.indexOf('const WORLD_BOUNDS=')),c);
 return {c,timers,calls,bounds};
}
test('prepared example fits the selected rectangle after the map becomes visible',()=>{
 const {c,timers,calls,bounds}=context();c.view('explore');assert.equal(calls.length,0);timers.shift()();
 assert.deepEqual(calls.map(x=>x[0]),['size','fit']);assert.equal(calls[1][1],bounds);assert.equal(calls[0][1].pan,true);assert.equal(calls[1][2].animate,false);assert.equal(c.state.pendingAreaFit,false);
});
test('a hidden map keeps the pending fit until the workspace is opened',()=>{
 const {c,timers,calls}=context();c.view('explore');c.view('examples');timers.shift()();assert.equal(calls.length,0);assert.equal(c.state.pendingAreaFit,true);
 c.view('explore');timers.shift()();assert.equal(calls.filter(x=>x[0]==='fit').length,1);
});
test('returning to an already viewed workspace preserves the user zoom and pan',()=>{
 const {c,timers,calls}=context();c.view('explore');timers.shift()();c.view('examples');c.view('explore');timers.shift()();assert.equal(calls.filter(x=>x[0]==='fit').length,1);
});

test('hidden map resize notifications do not invalidate its center; visible resize preserves it',()=>{
 let notify;const node={clientWidth:0,clientHeight:0},calls=[];const c={$:()=>node,map:{invalidateSize:o=>calls.push(o)},ResizeObserver:class{constructor(cb){notify=cb}observe(){}}};vm.createContext(c);
 const line=source.split('\n').find(l=>l.includes('new ResizeObserver'));vm.runInContext(line,c);notify();assert.equal(calls.length,0);node.clientWidth=1000;node.clientHeight=410;notify();assert.equal(calls.length,1);assert.equal(calls[0].pan,true);assert.equal(calls[0].animate,false);
});
