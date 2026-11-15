const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');
test('download and selected-tool counts remain independent without a bulk-run total',()=>{
 const items=(product,n)=>Array.from({length:n},(_,i)=>({id:product+i,product,local:false}));
 const catalog={GCOV:{items:items('GCOV',8)},GUNW:{items:items('GUNW',4)},SME2:{items:items('SME2',4)}};
 const nodes={'#selection-summary':{},'#download-button':{}};
 const c={state:{catalog,tab:'GCOV',selected:'P01',plans:[{id:'P01',name:'Flood Memory'},{id:'P04',name:'Sinking City Atlas'}],checked:new Set(Object.values(catalog).flatMap(c=>c.items.map(i=>i.id))),downloadChecked:new Set(catalog.GCOV.items.map(i=>i.id))},$:s=>nodes[s],renderInputGuide:()=>{},productFor:id=>id==='P01'?'GCOV':'GUNW',esc:String,NisarCatalogGuide:{selectionStats:items=>({count:items.length}),sizeLabel:s=>`${s.count} GiB`,rectangleKm2:()=>20}};
 vm.createContext(c);vm.runInContext(app.slice(app.indexOf('function updateSelection(){'),app.indexOf('async function inspectFile(')),c);c.updateSelection();
 assert.match(nodes['#selection-summary'].innerHTML,/8 GCOV files/);assert.doesNotMatch(nodes['#selection-summary'].innerHTML,/Run all|across all products/);assert.match(nodes['#download-button'].textContent,/Download 8 new GCOV/);
 c.state.selected='P04';c.updateSelection();assert.match(nodes['#selection-summary'].innerHTML,/4 GUNW files/);assert.match(nodes['#selection-summary'].innerHTML,/Sinking City Atlas uses only/);assert.match(nodes['#download-button'].textContent,/Download 8 new GCOV/);
});

test('Explore exposes no bulk-run control or execution path',()=>{const html=fs.readFileSync(path.join(__dirname,'../../frontend/index.html'),'utf8');assert.doesNotMatch(html,/id="run-all"|Running all eight/);assert.doesNotMatch(app,/run-all|async function run\(all=|panorama-selection/);assert.match(app,/const projects=\[state.selected\]/)});
