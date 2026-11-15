const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const read=name=>fs.readFileSync(path.join(__dirname,'../../frontend/',name),'utf8'),plans=JSON.parse(fs.readFileSync(path.join(__dirname,'../../docs/tools.json'),'utf8'));
function context(){const nodes={},c={URLSearchParams,state:{plans},esc:String,$:s=>nodes[s]??={value:'',innerHTML:'',removeAttribute(a){delete this[a]}},$$:()=>[],icons:{},referenceTools:['P03','P04','P05']};vm.createContext(c);vm.runInContext(read('tool-experiences.js'),c);c.familyFor=id=>c.toolGroupFor(id)[0];return {c,nodes}}
test('all seven experiences have a question, reading order and interpretation boundary',()=>{const {c}=context();for(const p of plans){const html=c.toolGuideHTML(p);assert.match(html,/1 · Prepare/);assert.match(html,/2 · Start here/);assert.match(html,/3 · Interpret carefully/);assert.ok(html.includes(p.product));assert.ok(c.toolGroupFor(p.id));}assert.match(c.p04SetupPath(),/positive means toward the satellite and negative means away/);assert.match(c.p04SetupPath(),/cannot establish stability/)});
test('catalogue is grouped by question, searchable by input needs and filtered by product',()=>{const {c,nodes}=context(),app=read('app.js');vm.runInContext(app.slice(app.indexOf('function renderProjects(){'),app.indexOf('function showProject(')),c);c.renderProjects();const all=nodes['#project-grid'].innerHTML;assert.equal((all.match(/data-start-tool=/g)||[]).length,7);for(const name of ['Water & wetness','Ground & ice motion','Land & vegetation'])assert.ok(all.includes(name));c.$('#tool-product-filter').value='GOFF';c.renderProjects();assert.equal((nodes['#project-grid'].innerHTML.match(/data-start-tool=/g)||[]).length,1);assert.match(nodes['#project-grid'].innerHTML,/P07/);c.$('#tool-product-filter').value='all';c.$('#tool-search').value='glacier';c.renderProjects();assert.match(nodes['#project-grid'].innerHTML,/P07/);assert.equal((nodes['#project-grid'].innerHTML.match(/data-start-tool=/g)||[]).length,1)});
test('P04 result guide distinguishes a multi-date rate from separate pair intervals',()=>{const {c}=context();let html=c.p04ResultGuide({layers:[{id:'los_rate_year'}],extra:{los_series:[{}],reference_diagnostics:{fixed_pixels:40}}});assert.match(html,/40 shared reference cells/);assert.match(html,/not a direct vertical/);assert.match(html,/reconstructed accumulated change/);html=c.p04ResultGuide({layers:[{id:'range'}],extra:{}});assert.match(html,/not available/);assert.match(html,/must not be added/)});
test('presentation download follows the applied map layer and display parameters',()=>{const {c}=context();vm.runInContext(read('map-download.js'),c);c.state.currentJob={id:'run'};c.state.result={project:'P04'};c.syncMapImageDownload({id:'los_rate_year'},'mode=custom&low=-12&high=3&palette=mexico');const a=c.$('#map-image-link');assert.equal(a.href,'/api/map-image/run/P04/los_rate_year?mode=custom&low=-12&high=3&palette=mexico');assert.match(a.download,/\.png$/);assert.match(a.title,/No basemap/)});

test('PNG background option follows current style, labels and radar opacity without touching the numeric link',()=>{
 const {c}=context();vm.runInContext(read('map-download.js'),c);c.state.currentJob={id:'run'};c.state.result={project:'P04'};
 c.$('#raster-link').href='/unchanged-numeric.tif';c.$('#export-background').checked=true;c.$('#basemap-select').value='dark';c.$('#basemap-labels').checked=true;c.$('#layer-opacity').value='.65';
 c.syncMapImageDownload({id:'los_rate_year'},'mode=custom&low=-30&high=30&palette=rainbow');
 let url=c.$('#map-image-link').href;assert.match(url,/basemap=dark/);assert.match(url,/place_names=true/);assert.match(url,/overlay_opacity=0.65/);assert.match(url,/palette=rainbow/);
 c.$('#basemap-select').value='light';c.$('#basemap-labels').checked=false;c.refreshMapImageDownload();assert.match(c.$('#map-image-link').href,/basemap=light&place_names=false/);
 assert.equal(c.$('#raster-link').href,'/unchanged-numeric.tif');
 c.$('#export-background').checked=false;c.$('#export-background').onchange();assert.ok(!c.$('#map-image-link').href.includes('basemap='));
 c.state.result=null;c.state.currentJob=null;assert.doesNotThrow(()=>c.refreshMapImageDownload());
});

test('current view captures the camera at refresh time and restores result-only extent cleanly',()=>{
 const {c}=context();vm.runInContext(read('map-download.js'),c);c.state.currentJob={id:'run'};c.state.result={project:'P04'};
 let camera={sw:{x:10,y:20},ne:{x:30,y:40}};
 c.map={getBounds:()=>({getSouthWest:()=>camera.sw,getNorthEast:()=>camera.ne}),options:{crs:{project:p=>p}}};
 c.$('#png-extent').value='view';c.syncMapImageDownload({id:'los_rate_year'},'mode=custom&low=-30&high=30&palette=rainbow');
 let url=new URL('http://localhost'+c.$('#map-image-link').href);assert.equal(url.searchParams.get('extent'),'view');assert.equal(url.searchParams.get('view_bbox'),'10,20,30,40');assert.equal(url.searchParams.get('low'),'-30');
 camera={sw:{x:5,y:15},ne:{x:25,y:35}};c.refreshMapImageDownload();url=new URL('http://localhost'+c.$('#map-image-link').href);assert.equal(url.searchParams.get('view_bbox'),'5,15,25,35');
 c.$('#png-extent').value='result';c.$('#png-extent').onchange();assert.ok(!c.$('#map-image-link').href.includes('view_bbox'));
});

test('all seven result guides answer the same six questions using actual findings and source dates',()=>{
 const {c}=context();c.esc=s=>String(s??'').replaceAll('<','&lt;');
 for(const p of plans){const r={project:p.id,extra:{},sources:[{start:'2026-01-01T00:00:00Z',end:'2026-01-13T00:00:00Z',product:p.product}],grid:{resolution_m:80},report:{findings:['Measured 2.5 km² <script>'],validation:'Case agreement is not general accuracy.'}};
 const html=c.resultReadingGuideHTML(r);assert.equal((html.match(/class="result-reading-question"/g)||[]).length,6);assert.match(html,/2026-01-01 → 2026-01-13 UTC/);assert.match(html,/2.5 km² &lt;script>/);assert.match(html,/not native sensor resolution/);assert.match(html,/GeoTIFF is unchanged/);assert.match(html,/independent environmental accuracy/);assert.match(html,/Case agreement is not general accuracy/);}
 const old=c.resultReadingGuideHTML({project:'LAB',extra:{}});assert.match(old,/No automatic finding was recorded/);assert.match(old,/not available in this saved record/);
});
test('saved result guide takes precedence and elementary/modified workflows do not inherit case accuracy',()=>{
 const {c}=context();const r={project:'LAB',reading_guide:{measurement:'Saved exact interpretation',colours:'Saved units',checks:'Saved checks',cannot:'Saved limit',validation:'No independent truth'},extra:{workflow_output_statistics:{median:1}}};
 const html=c.resultReadingGuideHTML(r);assert.match(html,/Saved exact interpretation/);assert.match(html,/new experiment/);
 assert.match(c.resultReadingGuide({project:'P07',extra:{}}).measurement,/radar-component/);
 assert.match(c.resultReadingGuide({project:'P04',extra:{}}).measurement,/pair interval/);
});
