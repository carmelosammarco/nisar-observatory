const {test}=require('node:test');
const assert=require('node:assert/strict');
const {createBasemapController}=require('../../frontend/basemaps.js');

function fixture(saved){
 const layers=new Set(),created=[],classes=new Map(),values=new Map();
 if(saved!==undefined)values.set('nisar.map-background.v1',saved);
 const storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
 const map={createPane:()=>({style:{}}),removeLayer:l=>layers.delete(l),hasLayer:l=>layers.has(l),getContainer:()=>({classList:{toggle:(k,v)=>classes.set(k,v)}})};
 class TileLayer{constructor(url,options){this.url=url;this.options=options;this.events={};created.push(this)}on(e,fn){this.events[e]=fn;return this}addTo(){layers.add(this);return this}}
 const controls={select:{},labels:{},help:{},status:{}};
 const controller=createBasemapController({map,TileLayer,...controls,storage});
 const select=name=>{controls.select.value=name;controls.select.onchange()};
 const labels=on=>{controls.labels.checked=on;controls.labels.onchange()};
 return {map,layers,created,classes,values,controller,select,labels,...controls,changeLabels:labels,changeStyle:select};
}

test('all five backgrounds retain unrelated area, reference and radar layers without changing the view',()=>{
 const f=fixture(),area={},reference={},radar={},selection={bbox:[-1,2,3,4],run:'saved'};
 for(const layer of [area,reference,radar])f.layers.add(layer);
 for(const name of ['light','dark','streets','plain','satellite']){
  f.changeStyle(name);
  assert.equal(f.controller.getSelection().basemap,name);
  for(const layer of [area,reference,radar])assert.ok(f.layers.has(layer));
  assert.deepEqual(selection,{bbox:[-1,2,3,4],run:'saved'});
  assert.equal([...f.layers].filter(l=>l.url).length,name==='plain'?0:1);
 }
});

test('place names are separate, noninteractive, above science overlays, and do not reload base tiles',()=>{
 const f=fixture(),base=f.created[0];f.changeLabels(true);
 assert.equal(f.created.length,2);assert.ok(f.layers.has(base));
 const names=f.created[1];assert.equal(names.options.pane,'placeNames');assert.equal(names.options.noWrap,true);
 f.changeLabels(false);assert.ok(f.layers.has(base));assert.ok(!f.layers.has(names));
 f.changeStyle('dark');f.changeLabels(true);
 assert.match(f.created.at(-1).url,/World_Dark_Gray_Reference/);
});

test('Streets includes its own labels and restores the optional label preference on other backgrounds',()=>{
 const f=fixture();f.changeStyle('streets');assert.equal(f.labels.disabled,true);assert.equal(f.labels.checked,true);assert.match(f.help.textContent,/includes labels/);
 assert.equal(f.controller.getSelection().labels,false);f.changeStyle('light');assert.equal(f.labels.disabled,false);assert.equal(f.labels.checked,false);
 f.changeLabels(true);f.changeStyle('streets');f.changeStyle('satellite');assert.equal(f.labels.checked,true);
});

test('Plain is tile-free with names off and hides the fallback country outline, including late loading',()=>{
 const f=fixture();f.changeStyle('plain');
 const outline={addTo(){f.layers.add(this);return this},bringToBack(){return this}};
 f.controller.setOutline(outline);assert.ok(!f.layers.has(outline));assert.equal(f.layers.size,0);assert.equal(f.classes.get('basemap-plain'),true);
 f.changeStyle('light');assert.ok(f.layers.has(outline));f.changeStyle('plain');assert.ok(!f.layers.has(outline));
 f.changeLabels(true);assert.equal(f.layers.size,1);assert.match([...f.layers][0].url,/Reference/);
});

test('background preference survives reload; corrupt or unavailable storage falls back safely',()=>{
 let f=fixture();f.changeStyle('dark');f.changeLabels(true);
 let g=fixture(f.values.get('nisar.map-background.v1'));assert.deepEqual(g.controller.getSelection(),{basemap:'dark',labels:true});
 for(const saved of ['bad','{"basemap":"__proto__"}','{"basemap":"unknown"}'])assert.deepEqual(fixture(saved).controller.getSelection(),{basemap:'satellite',labels:false});
});

test('tile failures give a helpful message; late failures from removed layers are ignored',()=>{
 const f=fixture(),old=f.created[0];old.events.tileerror();assert.equal(f.status.hidden,false);assert.match(f.status.textContent,/radar results are kept/);
 f.changeStyle('plain');assert.equal(f.status.hidden,true);old.events.tileerror();assert.equal(f.status.hidden,true);
});

test('all providers are HTTPS, non-repeating and allow existing radar zoom through overzoom',()=>{
 const f=fixture();for(const name of ['satellite','light','dark','streets']){f.changeStyle(name);const layer=f.created.at(-1);assert.match(layer.url,/^https:/);assert.equal(layer.options.maxZoom,23);assert.equal(layer.options.noWrap,true);assert.ok(layer.options.maxNativeZoom<=23);assert.ok(layer.options.attribution)}
});
