const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../frontend/map-download.js'),'utf8');
function fixture(){
 const nodes=new Map(),downloaded=[];const node=()=>({value:'',textContent:'',hidden:false,setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]}});
 const $=key=>{if(!nodes.has(key))nodes.set(key,node());return nodes.get(key)};
 let finish;const pending=new Promise(resolve=>finish=resolve);
 const c={state:{currentJob:{id:'run'},result:{project:'P03'}},URLSearchParams,$: $,fetch:()=>pending,setTimeout(){},URL:{createObjectURL:()=> 'blob:fixture',revokeObjectURL(){}},document:{body:{append(){}},createElement(){return {click(){downloaded.push({filename:this.download,url:this.href})},remove(){}}}},toast(){throw Error('Status should remain in the page')}};
 vm.createContext(c);vm.runInContext(source,c);c.syncMapImageDownload({id:'first',label:'First map'},'mode=shared');
 return {c,nodes,node,finish,downloaded};
}
test('normal PNG completion releases its button and retains the requested filename',async()=>{
 const {c,finish,downloaded}=fixture(),link=c.$('#map-image-link');
 const pending=link.onclick({preventDefault(){}});assert.equal(link['aria-disabled'],'true');assert.equal(c.state.mapImageExportBusy,true);
 finish({ok:true,blob:async()=>({})});await pending;
 assert.equal(c.state.mapImageExportBusy,false);assert.equal(link['aria-disabled'],undefined);assert.match(c.$('#map-export-status').textContent,/PNG ready/);assert.equal(downloaded[0].filename,'p03_first_map.png');
});
for(const failed of [false,true])test(`switching results during ${failed?'failed':'successful'} PNG export keeps the new button usable`,async()=>{
 const {c,nodes,node,finish,downloaded}=fixture(),old=c.$('#map-image-link');
 const pending=old.onclick({preventDefault(){}});
 nodes.set('#map-image-link',node());nodes.set('#map-export-status',node());c.state.currentJob={id:'other-run'};c.syncMapImageDownload({id:'second',label:'Second map'},'mode=shared');
 const next=c.$('#map-image-link');assert.equal(next['aria-disabled'],'true');assert.match(c.$('#map-export-status').textContent,/Finishing PNG for First map/);
 finish(failed?{ok:false,json:async()=>({detail:'Fixture render error'})}:{ok:true,blob:async()=>({})});await pending;
 assert.equal(c.state.mapImageExportBusy,false);assert.equal(next['aria-disabled'],undefined);assert.match(next.href,/other-run\/P03\/second/);
 assert.match(c.$('#map-export-status').textContent,failed?/Previous PNG export: Fixture render error/:/Previous PNG ready: First map/);
 if(!failed)assert.equal(downloaded[0].filename,'p03_first_map.png');else assert.equal(downloaded.length,0);
});
