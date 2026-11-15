const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const view=require('../../frontend/library-view.js');
const lib=JSON.parse(fs.readFileSync(path.join(__dirname,'../../docs/mission.json'),'utf8'));
test('background content remains intact and renders safely',()=>{
 assert.equal(lib.sections.length,47);assert.equal(lib.sources.length,101);
 lib.sections.forEach((s,i)=>{const html=view.renderBlocks(s,i,lib.sources);assert.ok(html.length>0,s.title);assert.doesNotMatch(html,/<details|<summary/i)});
});
test('tables have real headers, row labels and scrollable containers',()=>{
 const s=lib.sections.find(s=>s.title==='Hardware and the path from echo to product');
 const html=view.renderBlocks(s,2,lib.sources);
 assert.match(html,/<thead>/);assert.match(html,/<th scope="col">Component/);assert.match(html,/<th scope="row">Shared reflector/);assert.match(html,/library-table-scroll/);
});
test('all 32 studies expose findings, limits and original links as readable cards',()=>{
 const sections=lib.sections.filter(s=>s.kind==='studies');
 assert.equal(sections.length,10);
 const ids=sections.flatMap(view.studyGroups).map(s=>s.title.match(/^R\d+/)[0]);
 assert.equal(ids.length,32);assert.equal(new Set(ids).size,32);
 assert.ok(sections.some(s=>s.title==='Floods and wetlands'));
 assert.ok(sections.every(s=>!s.title.includes('Research annotations')));
 for(const s of sections){const html=view.renderBlocks(s,0,lib.sources);assert.match(html,/library-study/);assert.match(html,/study-limit/);assert.match(html,/Reported finding/);assert.match(html,/Read the paper or agency article/)}
});
test('code blocks preserve their actual newlines and render with safe copy controls',()=>{
 const examples=lib.sections.flatMap(s=>(s.blocks||[]).filter(b=>b.type==='code'));
 assert.equal(examples.length,5);assert.ok(examples.every(b=>b.text.split('\n').length>=10));
 const s=lib.sections.find(s=>s.title==='Optional code recipes for discovery and download'),html=view.renderBlocks(s,0,lib.sources);
 assert.match(html,/<pre tabindex="0"><code>from pathlib import Path\nimport json/);assert.match(html,/data-copy-code/);
});
test('unsafe links and markup cannot become active library HTML',()=>{
 assert.equal(view.safeUrl('javascript:alert(1)'),null);assert.equal(view.safeUrl('data:text/html,hello'),null);
 const html=view.renderBlocks({title:'Example',blocks:[{type:'text',text:'<img src=x onerror=alert(1)> [1]'}]},0,[{id:1,title:'Unsafe',url:'javascript:alert(1)'}]);
 assert.doesNotMatch(html,/<img|href="javascript:/);assert.match(html,/&lt;img/);
});
test('citations link to their original source and search includes chapter bodies',()=>{
 const html=view.inline('See [1, 2].',lib.sources);assert.match(html,/https:\/\/science.nasa.gov/);assert.match(html,/Reference 1/);
 assert.ok(view.matches(lib.sections.find(s=>s.title==='Hardware and the path from echo to product'),'SweepSAR'));assert.ok(view.sourceMatches(lib.sources[0],'NASA'));assert.ok(!view.matches(lib.sections[2],'unfindable012345'));
});

test('supplied PDF references allow only the registered local sources',()=>{
 assert.equal(view.safeUrl('/assets/library/sources/nisar-earth-science-poster.pdf'),'/assets/library/sources/nisar-earth-science-poster.pdf');
 for(const url of ['/assets/library/sources/../../private.pdf','/data/private.pdf','//example.com/a.pdf','/assets/library/sources/nisar-earth-science-poster.pdf?next=evil']) assert.equal(view.safeUrl(url),null);
 const html=view.inline('Supplied poster [99] and historical slides [100].',lib.sources);
 assert.match(html,/href="\/assets\/library\/sources\/nisar-earth-science-poster.pdf"/);
 assert.match(html,/historical teaching slides/);
});


test('handbook figures retain attribution, original page links and packaged readable images',()=>{
 const chapters=lib.sections.filter(s=>s.blocks?.some(b=>b.type==='figure'));assert.equal(chapters.length,3);
 for(const section of chapters){const html=view.renderBlocks(section,0,lib.sources);assert.match(html,/library-handbook-figure/);assert.match(html,/Open original · PDF page/);for(const block of section.blocks.filter(b=>b.type==='figure')){assert.equal(block.source,53);assert.ok(block.alt.length>60);assert.match(block.caption,/Figure \d+-\d+/);assert.ok(fs.existsSync(path.join(__dirname,'../../frontend',block.src)));assert.ok(fs.statSync(path.join(__dirname,'../../frontend',block.src)).size>10000)}}
});
test('only bounded handbook page anchors and known figure paths are allowed',()=>{
 const source='/assets/library/sources/nisar-science-handbook-2019.pdf';
 for(const page of [1,27,49,84,139])assert.equal(view.safeUrl(source+'#page='+page),source+'#page='+page);
 for(const suffix of ['#page=0','#page=140','#page=27&evil=1','?page=27','#page=1/../../private'])assert.equal(view.safeUrl(source+suffix),null);
 const html=view.renderBlocks({blocks:[{type:'figure',src:'https://outside.test/tracker.png',alt:'Not a registered figure',caption:'Unknown figure'}]},0,lib.sources);assert.doesNotMatch(html,/<img|outside.test/);
});
test('historical handbook is separated from current facts and implemented wetland behavior',()=>{
 const historic=lib.sections.find(s=>s.title==='Reading the science handbook today');assert.match(historic.body,/August 2019 Version 1/);assert.match(historic.body,/January 2022 was the planned/);assert.match(historic.body,/Actual launch: 30 July 2025/);assert.match(historic.body,/9.4 cm/);assert.match(historic.body,/not accuracy certificates/);
 const water=lib.sections.find(s=>s.title==='Scattering, polarization and water');assert.match(water.body,/complete framework is not implemented/);assert.match(water.body,/Never divide dB values/);assert.match(water.body,/does not establish flood causation/);
 const errors=lib.sections.find(s=>s.title==='Uncertainty, calibration and validation');assert.match(errors.body,/not 96% confidence/);assert.match(errors.body,/independent reference/);
 assert.doesNotMatch(lib.sections.find(s=>s.title==='L-band data in this app').body,/only a limited S-band sample/);
});


test('Mission library navigation and search contain only mission chapters',()=>{
 const chapters=view.missionChapters(lib);assert.equal(chapters.length,17);assert.ok(chapters.every(s=>s.guide==='01'));
 const sample={sections:[{guide:'01',title:'Missiononly123',body:'Radar'},{guide:'02',title:'Architectureonly123',body:'CMR'},{guide:'03',title:'Researchonly123',body:'CMR'}]};
 assert.equal(view.missionChapters(sample,'only123').length,1);assert.equal(view.missionChapters(sample,'Architectureonly123').length,0);assert.equal(view.missionChapters(sample,'Researchonly123').length,0);
});
test('rendered library has no route cards or hidden-category search escape',()=>{
 const vm=require('node:vm'),script=fs.readFileSync(path.join(__dirname,'../../frontend/library-view.js'),'utf8');
 const host={innerHTML:'',querySelectorAll(){return []},querySelector(){return null}},search={};
 const c={module:{exports:{}},URL,document:{querySelector:s=>s==='#library-content'?host:search}};vm.createContext(c);vm.runInContext(script,c);
 c.module.exports.render(lib);assert.match(host.innerHTML,/aria-label="Mission chapters"/);assert.doesNotMatch(host.innerHTML,/data-library-route|library-routes|library-quick-routes|source-directory/);assert.equal(search.placeholder,'Search 17 mission chapters…');
 const title=lib.sections.find(s=>s.guide==='02').title;c.module.exports.render(lib,title);assert.match(host.innerHTML,/No mission chapters found/);assert.doesNotMatch(host.innerHTML,/data-library-chapter=/);
});


test('consolidated reading order keeps essentials, transfer choices and reproducible examples',()=>{
 const chapters=view.missionChapters(lib);
 assert.equal(chapters[0].title,'The mission in plain language');
 assert.equal(chapters.at(-1).title,'Reading the science handbook today');
 const at=title=>chapters.findIndex(s=>s.title===title);
 assert.ok(at('What radar values show')<at('The complete product family'));
 assert.ok(at('Uncertainty, calibration and validation')<at('Find data and connect your account'));
 const inventory=chapters.find(s=>s.title.startsWith('Regional availability:'));
 assert.match(inventory.body,/15 October 2026/);assert.match(inventory.body,/146,578/);assert.match(inventory.body,/CMR-Hits/);
 const transfer=chapters.find(s=>s.title==='Choose how to retrieve data');
 assert.match(transfer.body,/Save selected area/);assert.match(transfer.body,/HDF5 reads chunks/);assert.match(transfer.body,/Direct S3/);
 const code=chapters.find(s=>s.title==='Optional code recipes for discovery and download');
 assert.equal(code.blocks.filter(b=>b.type==='code').length,4);
 const paragraphs=chapters.flatMap(s=>s.blocks.filter(b=>b.type==='text').map(b=>b.text));
 assert.equal(new Set(paragraphs).size,paragraphs.length,'mission paragraphs should not be repeated');
 const sources=new Set(lib.sources.map(s=>Number(s.id)));
 for(const chapter of chapters){
  assert.doesNotMatch(chapter.body,/Guide 2|\[101\]|live CMR catalog snapshot/);
  for(const match of chapter.body.matchAll(/\[(\d+(?:, \d+)*)\]/g))for(const id of match[1].split(', '))assert.ok(sources.has(Number(id)),`Missing source ${id} in ${chapter.title}`);
 }
});
