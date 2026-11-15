const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../frontend/app.js'),'utf8');
function part(start,end){return source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)))}
function context(){
 const elements=new Map(),removed=[],messages=[];
 const $=key=>{if(!elements.has(key))elements.set(key,{value:'',textContent:'',innerHTML:'',classList:{toggle(){}},scrollIntoView(){}});return elements.get(key)};
 const c={referenceTools:['P03','P04','P05'],state:{bbox:[0,0,1,1],reference:null,catalog:{},checked:new Set(),plans:[{id:'P01',name:'Water extent'}]},requestVersions:{catalog:0,result:0,pixel:0,job:0},$: $, $$:()=>[],toast:m=>messages.push(m),map:{removeLayer:l=>removed.push(l),closePopup(){},fitBounds(){}},overlay:null,areaRectangle:null,refRectangle:null,audioContext:null,audioTimer:null,clearTimeout,renderCatalog(){},autoSelect(){},esc:String,MAP_MAX_ZOOM:23,L:{rectangle(){return {addTo(){return this},getBounds(){return []}}}}};
 c.elements=elements;c.removed=removed;c.messages=messages;
 vm.createContext(c);
 vm.runInContext(part('function invalidateCatalog()','function clearArea()')+part('function drawArea(','function setDraw(')+part('async function discover()','function options()')+part('async function openResult(','function plotResult(')+part('async function inspectPixel(','function implementedMethod('),c);
 return c;
}
test('an old catalog response cannot replace data after the area changes',async()=>{
 const c=context();c.$('#start-date').value='2025-07-30';c.$('#end-date').value='2026-10-16';
 let resolve;c.api=()=>new Promise(r=>resolve=r);
 const pending=c.discover();c.drawArea([10,10,11,11],false);
 resolve({GCOV:{items:[{id:'old-area'}]}});await pending;
 assert.equal(Object.keys(c.state.catalog).length,0);
 assert.equal(c.$('#search-button').disabled,false);
 assert.deepEqual(Array.from(c.state.bbox),[10,10,11,11]);
});
test('changing dates during a search discards the response',async()=>{
 const c=context();c.$('#start-date').value='2025-07-30';c.$('#end-date').value='2026-10-16';
 let resolve;c.api=()=>new Promise(r=>resolve=r);
 const pending=c.discover();c.$('#start-date').value='2026-01-01';resolve({GCOV:{items:[]}});await pending;
 assert.equal(Object.keys(c.state.catalog).length,0);
 assert.match(c.messages.at(-1),/dates changed/);
});
test('opening a workflow with missing inputs removes the previous result overlay',async()=>{
 const c=context(),previous={id:'old-overlay'};
 c.overlay=previous;c.state.result={project:'P01'};c.state.layer={id:'old-layer'};
 c.state.currentJob={results:{P01:{status:'needs_input',message:'Choose more dates.'}}};
 await c.openResult('P01');
 assert.equal(c.overlay,null);assert.equal(c.state.result,null);assert.equal(c.state.layer,null);
 assert.equal(c.removed[0],previous);
 assert.match(c.$('#result-content').innerHTML,/Choose more dates/);
});
test('an old pixel response cannot label a newly selected layer',async()=>{
 const c=context();c.state.result={project:'P01',grid:{resolution_m:100}};c.state.layer={id:'old',label:'Old layer',unit:'m'};c.state.currentJob={id:'run'};
 let resolve;c.api=()=>new Promise(r=>resolve=r);
 const pending=c.inspectPixel({lat:1,lon:2});c.state.layer={id:'new',label:'New layer',unit:'mm'};
 resolve({value:3});await pending;
 assert.equal(c.$('#pixel-value').textContent,'');
});

test('Mexico City chooses the publication rectangle rather than shrinking to a starter window',()=>{
 const c=context(),library=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../docs/mission.json'),'utf8'));
 c.state.library=library;c.setDraw=()=>{};
 vm.runInContext(source.slice(source.indexOf("$('#preset').onchange=e=>{"),source.indexOf(";$('#search-button').onclick=discover",source.indexOf("$('#preset').onchange=e=>{")))+';',c);
 const index=library.presets.findIndex(p=>p.id==='P04');c.$('#preset').onchange({target:{value:String(index)}});
 assert.deepEqual(Array.from(c.state.bbox),[-99.35,19.14,-98.77,19.63]);
 assert.match(c.messages.at(-1),/approximate published map area/);
 for(const [x,y] of [[-99.072,19.436],[-99.1677,19.427],[-98.975,19.27]])assert.ok(x>c.state.bbox[0]&&x<c.state.bbox[2]&&y>c.state.bbox[1]&&y<c.state.bbox[3]);
 const other=library.presets.findIndex(p=>p.id==='P02');c.$('#preset').onchange({target:{value:String(other)}});
 assert.deepEqual(Array.from(c.state.bbox),[-73.13,41.16,-73.08,41.21]);
 assert.match(library.presets[other].name,/Wheeler Marsh paper's area/);
 assert.match(c.messages.at(-1),/Wheeler Marsh/);
});
test('saved-run labels distinguish downloaded extracts, reference checks and tool results',()=>{const c=context();vm.runInContext(part('function runRecordSummary(','async function loadRuns('),c);assert.equal(c.runRecordSummary({kind:'area_download',saved_areas:[{}]}),'1 saved area extract');assert.equal(c.runRecordSummary({kind:'reference',request:{granules:['a','b']}}),'Reference check · 2 selected files');assert.equal(c.runRecordSummary({kind:'analysis',results:{P04:{}}}),'1 tool result');assert.equal(c.runRecordSummary({kind:'download'}),'Complete-original download')});


test('opening a retired workflow keeps its files and gives an explanation instead of crashing',async()=>{
 const c=context();c.renderTools=()=>{};c.state.currentJob={results:{retired:{status:'exploratory'}}};
 await c.openResult('retired');assert.equal(c.state.selected,null);assert.match(c.$('#result-content').innerHTML,/no longer available/);assert.match(c.$('#result-content').innerHTML,/kept on disk/);
});

test('Samudra Tapu keeps the complete research window rather than a small starter crop',()=>{
 const c=context(),library=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../docs/mission.json'),'utf8'));
 c.state.library=library;c.setDraw=()=>{};
 vm.runInContext(source.slice(source.indexOf("$('#preset').onchange=e=>{"),source.indexOf(";$('#search-button').onclick=discover",source.indexOf("$('#preset').onchange=e=>{")))+';',c);
 c.$('#preset').onchange({target:{value:String(library.presets.findIndex(p=>p.id==='P07'))}});
 assert.deepEqual(Array.from(c.state.bbox),[77.36,32.39,77.57,32.56]);assert.match(c.messages.at(-1),/research window/);
});
