const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const read=name=>fs.readFileSync(path.join(__dirname,'../../frontend',name),'utf8'),inventory=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/processor-layer-inventory.json'),'utf8')).results;
function context(result){const nodes=new Map(),selected=[];const $=key=>{if(!nodes.has(key))nodes.set(key,{value:'',hidden:false,innerHTML:'',textContent:'',setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]},scrollIntoView(){}});return nodes.get(key)};const c={state:{result:structuredClone(result),artifactBase:'/artifacts/',currentJob:{id:'run'}},$: $,esc:String,clearTimeout(){},setTimeout(){},map:{invalidateSize(){}},stopTimeline(){},selectLayer:async i=>{selected.push(i);return true}};vm.createContext(c);vm.runInContext(read('result-views.js'),c);vm.runInContext(read('experience.js'),c);return {c,selected,nodes}}
test('all eight processors have small main result lists with no quality or baseline context mixed in',()=>{for(const result of Object.values(inventory)){const {c}=context(result),groups=c.resultViewGroups();assert.ok(groups.main.length>=1&&groups.main.length<=4,result.project);assert.ok(groups.main.every(l=>!l.id.startsWith('quality_')&&!['count','reference_support','baseline_departure','standardized_departure','los_fit_residual'].includes(l.id)),result.project);assert.equal(groups.time.length,result.layers.filter(l=>l.id.startsWith('observation_')).length);assert.equal(c.initialResultLayer(),groups.main[0].index)}});
test('every saved layer is accounted for, including originals and future advanced outputs',()=>{for(const result of Object.values(inventory)){const {c}=context(result),g=c.resultViewGroups(),ids=new Set(Object.values(g).flat().map(l=>l.id));assert.equal(ids.size,result.layers.length,result.project);for(const layer of result.layers)assert.ok(ids.has(layer.id));}const r=structuredClone(inventory.P04);r.layers.push({id:'future_supported_output',unit:'mm',label:'Future context'});const {c}=context(r),g=c.resultViewGroups();assert.ok(g.advanced.some(l=>l.id==='future_supported_output'))});
test('P04 exposes one rate result and total change; pair and fit diagnostics are separate',()=>{const {c}=context(inventory.P04),g=c.resultViewGroups();assert.deepEqual(Array.from(g.main,l=>l.id),['los_rate_year','los_change']);assert.ok(g.quality.some(l=>l.id==='los_fit_residual'));assert.ok(g.advanced.some(l=>l.id==='pair_0'));assert.deepEqual(Array.from(g.aliases,l=>l.id),['los_rate_month']);c.state.p04RateUnit='cm/month';assert.deepEqual(Array.from(c.resultViewGroups().main,l=>l.id),['los_rate_month','los_change'])});
test('P04 unit selector preserves physical custom limits and requests the matching stored raster',async()=>{const {c,selected}=context(inventory.P04);c.state.layer=c.state.result.layers.find(l=>l.id==='los_rate_year');c.state.displayUnit='cm/year';vm.runInContext("displayMode='custom';displayLow=-24;displayHigh=12",c);await c.switchP05RateUnit('cm/month');assert.equal(c.state.result.layers[selected[0]].id,'los_rate_month');assert.equal(vm.runInContext('displayLow',c),-2);assert.equal(vm.runInContext('displayHigh',c),1);assert.equal(c.state.displayUnit,'cm/month');assert.equal(c.state.p04RateUnit,'cm/month');assert.equal(Number(c.$('#display-low').value),-2);assert.equal(Number(c.$('#display-high').value),1)});
test('failed unit requests restore original limits and unit preference',async()=>{const {c}=context(inventory.P04);c.state.layer=c.state.result.layers.find(l=>l.id==='los_rate_year');c.state.displayUnit='cm/year';c.state.resultCategory='main';c.selectLayer=async()=>false;vm.runInContext("displayMode='custom';displayLow=-24;displayHigh=12",c);await c.switchP05RateUnit('cm/month');assert.equal(vm.runInContext('displayLow',c),-24);assert.equal(vm.runInContext('displayHigh',c),12);assert.equal(c.state.displayUnit,'cm/year');assert.equal(c.state.p04RateUnit,'cm/year')});
test('category switching shows only its own map choices and reveals playback for time exploration',()=>{const {c}=context(inventory.P01);c.mountLayerBrowser();assert.match(c.$('#result-layer-browser').innerHTML,/Main results/);assert.match(c.$('#result-layer-browser').innerHTML,/Quality & reliability/);c.state.resultCategory='quality';c.syncCategoryPicker(c.state.result.layers.find(l=>l.id==='count'));assert.equal(c.$('#observation-player').hidden,true);assert.match(c.$('#summary-choice').innerHTML,/Native samples kept/);assert.doesNotMatch(c.$('#summary-choice').innerHTML,/New water at/);c.state.resultCategory='time';c.syncCategoryPicker(c.state.result.layers.find(l=>l.id==='observation_0'));assert.equal(c.$('#observation-player').hidden,false);assert.equal(c.$('#summary-choice-label').hidden,true)});
test('every exported map has a substantial explanation, including quality and optional method layers',()=>{for(const result of Object.values(inventory)){const {c}=context(result);for(const layer of c.state.result.layers){const text=c.layerExplanation(layer,c.state.result);assert.ok(text.length>45,result.project+' '+layer.id);}}const {c}=context(inventory.P04);assert.match(c.extraLayerExplanation({id:'network_residual'},c.state.result),/not independent accuracy/)});
test('grouped quality and advanced views retain access to every saved layer without the flat catalogue',()=>{for(const result of Object.values(inventory)){const {c,selected}=context(result);const before=JSON.stringify(c.state.result.layers);c.mountLayerBrowser();const groups=c.resultViewGroups();for(const name of ['quality','advanced']){if(!groups[name].length)continue;c.$('#result-category-'+name).onclick();assert.equal(selected.at(-1),groups[name][0].index)}assert.equal(JSON.stringify(c.state.result.layers),before);assert.equal(new Set(Object.values(groups).flat().map(l=>l.id)).size,c.state.result.layers.length)}});

test('an event interval can be the main finding or an acquired frame according to the chosen section',()=>{const {c}=context(inventory.P05),frame=c.state.result.layers.find(l=>l.id==='observation_0');c.state.resultCategory='main';c.syncCategoryPicker(frame);assert.equal(c.state.resultCategory,'main');assert.equal(c.$('#observation-player').hidden,true);c.state.resultCategory='time';c.syncCategoryPicker(frame);assert.equal(c.state.resultCategory,'time');assert.equal(c.$('#observation-player').hidden,false)});
test('unit switching updates the displayed scale and both numeric and image download links together',async()=>{
 const {c}=context(inventory.P04),requests=[];c.toast=message=>{throw new Error(message)};c.requestVersions={pixel:0};c.URLSearchParams=URLSearchParams;c.overlay=null;
 c.map={closePopup(){},removeLayer(){},fitBounds(){}};c.Plotly={relayout(){}};
 c.L={imageOverlay(){return {callbacks:{},once(name,callback){this.callbacks[name]=callback},addTo(){Promise.resolve().then(()=>this.callbacks.load());return this}}}};
 c.api=async url=>{requests.push(url);const parsed=new URL('http://localhost'+url);return {image:'data:image/png;base64,test',min:Number(parsed.searchParams.get('low')),max:Number(parsed.searchParams.get('high')),palette:[[0,0,0],[255,255,255]],clipped_percent:0,mode:'custom',palette_name:'standard',shared_frames:1}};
 vm.runInContext(read('map-download.js'),c);const app=read('app.js');vm.runInContext(app.slice(app.indexOf('async function selectLayer('),app.indexOf('async function inspectPixel(')),c);
 c.state.displayUnit='cm/year';vm.runInContext("displayMode='custom';displayLow=-24;displayHigh=12",c);
 const before=JSON.stringify(c.state.result.layers),annual=c.state.result.layers.findIndex(l=>l.id==='los_rate_year');await c.selectLayer(annual);await c.switchP05RateUnit('cm/month');
 assert.equal(c.state.layer.id,'los_rate_month');assert.equal(c.$('#raster-link').href,'/artifacts/los_rate_month.tif');assert.match(c.$('#map-image-link').href,/los_rate_month\?/);assert.match(requests.at(-1),/low=-2&high=1/);assert.equal(c.$('#display-range-unit').textContent,'cm/month');assert.equal(c.$('#p04-rate-unit').value,'cm/month');assert.equal(c.$('#p04-rate-units').hidden,false);assert.equal(JSON.stringify(c.state.result.layers),before);
});

test('date-index pixel values show dates and intervals instead of decimal indices',()=>{
 const c={};vm.createContext(c);vm.runInContext(read('result-views.js'),c);
 assert.equal(c.resultValueText(4,{id:'first_change',unit:'observation index'},{extra:{first_change_calendar:[{index:4,date:'2026-08-17T08:49:24Z'}]}}),'2026-08-17 · observation index 4');
 assert.equal(c.resultValueText(1,{id:'largest_step',unit:'observation index'},{extra:{step_calendar:[{index:1,start:'2026-06-18',end:'2026-06-30'}]}}),'2026-06-18 → 2026-06-30 · observation index 1');
 assert.equal(c.resultValueText(-3,{unit:'dB'},{}),'-3.0000 dB');
});

test('brightness and signed departure keep distinct display ranges even though both use dB',()=>{
 const c={};vm.createContext(c);vm.runInContext(read('result-views.js'),c);
 const brightness={id:'observation_0',unit:'dB',kind:'continuous'},change={id:'latest_departure',unit:'dB',kind:'diverging'};
 assert.notEqual(c.resultDisplayQuantity(brightness,{}),c.resultDisplayQuantity(change,{}));
 assert.equal(c.resultDisplayQuantity(brightness,{}),c.resultDisplayQuantity({...brightness,id:'observation_4'},{}));
 assert.equal(c.resultDisplayQuantity(brightness,{extra:{fire_method:{id:'combined'}}}),'combined-change-magnitude');
});

test('P07 separates filtered radar norm from signed rates and keeps raw diagnostics advanced',()=>{
 const {c}=context(inventory.P07),r=c.state.result;
 r.layers.push({id:'radar_magnitude',unit:'m/year',kind:'continuous',label:'Filtered radar-plane magnitude'},{id:'radar_filtered_1',unit:'m/year',kind:'continuous',label:'Dated filtered norm'},{id:'other_filtered_1',unit:'m/year',kind:'diverging',label:'Filtered other component'});
 const g=c.resultViewGroups(r);assert.equal(g.main[0].id,'radar_magnitude');assert.ok(g.advanced.some(l=>l.id==='radar_filtered_1'));assert.match(c.extraLayerExplanation(g.main[0],r),/not horizontal glacier speed/);
 assert.notEqual(c.resultDisplayQuantity({id:'value',unit:'m/year'},r),c.resultDisplayQuantity(g.main[0],r));
});

test('horizontal P07 leads with physical estimate, keeps radar diagnostics and classifies every layer',()=>{
 const r=structuredClone(inventory.P07);r.extra??={};r.extra.horizontal_velocity={};r.layers.push(...['horizontal_speed','horizontal_change','horizontal_east_0','horizontal_north_0','horizontal_bearing_0','horizontal_condition_0','horizontal_vertical_sensitivity_0','radar_observation_0'].map(id=>({id,label:id,unit:'m/year',kind:'continuous'})));
 const {c}=context(r),g=c.resultViewGroups();assert.equal(g.main[0].id,'horizontal_speed');assert.ok(g.quality.some(l=>l.id==='horizontal_condition_0'));assert.ok(g.quality.some(l=>l.id==='horizontal_vertical_sensitivity_0'));assert.ok(g.advanced.some(l=>l.id==='horizontal_east_0'));
 for(const id of ['horizontal_speed','horizontal_east_0','horizontal_north_0','horizontal_bearing_0','horizontal_condition_0','horizontal_vertical_sensitivity_0'])assert.ok(c.extraLayerExplanation({id},r).length>45,id);
 assert.equal(new Set(Object.values(g).flat().map(l=>l.id)).size,r.layers.length);
});

test('saved GOFF geometry is preferred over a smaller radar-only duplicate',()=>{
 const {c}=context(inventory.P07);const old={product:'GOFF',size_mb:4},prepared={product:'GOFF',size_mb:5,viewing_geometry:{available:true}};
 assert.equal(c.preferSavedSource(prepared,old),true);assert.equal(c.preferSavedSource(old,prepared),false);assert.equal(c.preferSavedSource({...old,size_mb:3},old),true);
});




