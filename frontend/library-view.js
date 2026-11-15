/* Readable views of the existing research library. No credentials or persistent state. */
(function(root){
 'use strict';
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const suppliedReferences=new Set(['/assets/library/sources/nisar-earth-science-poster.pdf','/assets/library/sources/nisar-interferometry-slides.pdf','/assets/library/sources/nisar-science-handbook-2019.pdf']);
 const handbook='/assets/library/sources/nisar-science-handbook-2019.pdf';
 const handbookFigures=new Set(['sweepsar','insar-motion','inundation-workflow'].map(n=>'/assets/library/handbook/'+n+'.png'));
 function safeUrl(value){if(suppliedReferences.has(value))return value;if(typeof value==='string'&&value.startsWith(handbook+'#page=')){const page=value.slice((handbook+'#page=').length);if(/^[1-9]\d{0,2}$/.test(page)&&Number(page)<=139)return value;return null}try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:null}catch{return null}}
 function matches(section,query){return `${section.title} ${section.body||''}`.toLowerCase().includes(query.toLowerCase().trim())}
 function sourceMatches(source,query){return `${source.id} ${source.author||''} ${source.title} ${source.url}`.toLowerCase().includes(query.toLowerCase().trim())}
 const local={selected:0,query:'',library:null};
 function art(route){
  if(route==='01')return '<img src="/assets/library/nisar-spacecraft.png" alt="NASA/JPL-Caltech illustration of NISAR with its reflector and solar arrays" loading="lazy">';
  if(route==='02')return '<svg viewBox="0 0 300 130" role="img" aria-label="Conceptual path from archive through processing to a map"><path d="M68 66H232" stroke="currentColor" stroke-width="2" stroke-dasharray="5 5"/><g fill="none" stroke="currentColor" stroke-width="1.5"><rect x="23" y="39" width="60" height="54" rx="9"/><rect x="120" y="26" width="60" height="80" rx="9"/><rect x="217" y="39" width="60" height="54" rx="9"/><path d="M35 52h36M35 63h36M35 74h23M132 43h36M132 56h36M132 69h36M132 82h24M227 83l14-25 10 12 15-20"/></g><g fill="currentColor" font-size="8" font-family="system-ui"><text x="28" y="119">ARCHIVE</text><text x="123" y="119">PROCESS</text><text x="224" y="119">EXPLORE</text></g></svg>';
  if(route==='03')return '<svg viewBox="0 0 300 130" role="img" aria-label="Conceptual study notes connecting observation, method, finding and limits"><g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M34 31h145v78H34zM47 20h145v78M60 9h145v78"/><path d="M52 49h90M52 62h62M52 75h80M52 88h43"/><circle cx="239" cy="49" r="25"/><path d="M257 68l20 25M228 49l8 8 15-18"/></g></svg>';
  return '<svg viewBox="0 0 300 130" role="img" aria-label="Illustration of a linked reference library"><g fill="none" stroke="currentColor" stroke-width="1.5"><path d="M57 26h85l8 9 8-9h85v73h-85l-8 9-8-9H57zM150 35v69M72 44h59M72 58h59M72 72h45M169 44h59M169 58h59M169 72h45"/><path d="M223 18l24-12M237 30l22-1"/></g></svg>';
 }
 function inline(text,sources){
  const raw=String(text??''),pattern=/https?:\/\/[^\s<>]+|\[\d+(?:[ ,–—-]+\d+)*\]/g;let html='',start=0;
  for(const match of raw.matchAll(pattern)){
   html+=escape(raw.slice(start,match.index));const token=match[0];
   if(token.startsWith('http')){const url=safeUrl(token);html+=url?`<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(token)}</a>`:escape(token)}
   else{
    const ids=token.match(/\d+/g)||[];
    // Do not invent citations within a range: preserve range syntax as written.
    if(/[–—-]/.test(token))html+=escape(token);
    else html+=`<span class="library-citations">${ids.map(id=>{const s=sources.find(s=>String(s.id)===id),url=s&&safeUrl(s.url);return url?`<a href="${escape(url)}" target="_blank" rel="noopener noreferrer" title="${escape(s.title)}" aria-label="Reference ${id}: ${escape(s.title)}">[${id}]</a>`:`[${escape(id)}]`}).join(' ')}</span>`;
   }
   start=match.index+token.length;
  }
  return (html+escape(raw.slice(start))).replace(/\n/g,'<br>');
 }
 function readingMinutes(section){return Math.max(1,Math.ceil((section.body||'').split(/\s+/).length/200))}
 function studyGroups(section){
  const groups=[];
  for(const block of section.blocks||[]){if(block.type==='heading'&&/^R\d{2}\s/.test(block.text))groups.push({title:block.text,blocks:[]});else if(groups.length)groups.at(-1).blocks.push(block)}
  return groups;
 }
 function renderStudies(section,sources){return `<p class="study-topic-intro">${inline(section.intro||'',sources)}</p>`+studyGroups(section).map(study=>{
  const id=study.title.match(/^R\d+/)[0],title=study.title.replace(/^R\d+\s+/,''),meta=study.blocks[0]?.text||'';
  return `<section class="library-study"><div class="study-kicker"><span>${id}</span><span>${inline(meta,sources)}</span></div><h3>${escape(title)}</h3><dl>${study.blocks.slice(1).map(b=>{
   const url=safeUrl(b.text);if(url)return `<div class="study-paper"><dt>Original source</dt><dd><a href="${escape(url)}" target="_blank" rel="noopener noreferrer">Read the paper or agency article ↗</a></dd></div>`;
   const split=b.text.indexOf(':');return split>0?`<div class="${b.text.startsWith('Limits:')?'study-limit':b.text.startsWith('Reported finding:')?'study-finding':''}"><dt>${escape(b.text.slice(0,split))}</dt><dd>${inline(b.text.slice(split+1).trim(),sources)}</dd></div>`:`<div><dd>${inline(b.text,sources)}</dd></div>`;
  }).join('')}</dl></section>`;
 }).join('')}
 function renderBlocks(section,index,sources){
  if(section.kind==='studies')return renderStudies(section,sources);
  const blocks=section.blocks?.length?section.blocks:[{type:'text',text:section.body}];let html='';
  for(let n=0;n<blocks.length;n++){
   const b=blocks[n];
   if(b.type==='heading'){html+=`<h3 id="library-heading-${index}-${n}" tabindex="-1">${inline(b.text,sources)}</h3>`;continue}
   if(b.type==='code'){html+=`<figure class="library-code"><figcaption><span>Python example · from the guide</span><button type="button" data-copy-code="${n}">Copy code</button></figcaption><pre tabindex="0"><code>${escape(b.text)}</code></pre><p>Illustrative example; review current archive settings before running. No code is executed in this page.</p></figure>`;continue}
   if(b.type==='figure'){
    if(!handbookFigures.has(b.src)){html+=`<p>${escape(b.caption||b.alt||'Figure unavailable')}</p>`;continue}
    const source=sources.find(s=>s.id===b.source),page=Number.isInteger(b.page)?b.page:null,url=source&&safeUrl(source.url+(page?'#page='+page:''));
    html+=`<figure class="library-handbook-figure"><a href="${escape(b.src)}" target="_blank" rel="noopener noreferrer" aria-label="Open figure: ${escape(b.alt)}"><img src="${escape(b.src)}" alt="${escape(b.alt)}" loading="lazy"></a><figcaption>${inline(b.caption,sources)}${url?`<a class="handbook-page-link" href="${escape(url)}" target="_blank" rel="noopener noreferrer">Open original${page?' · PDF page '+page:''} ↗</a>`:''}</figcaption></figure>`;continue;
   }
   if(b.type==='table'){
    html+=`<div class="library-table-scroll" role="region" aria-label="Table: ${escape(section.title)}" tabindex="0"><table class="library-table"><caption>${escape(section.title)}</caption><thead><tr>${(b.rows[0]||[]).map(c=>`<th scope="col">${inline(c,sources)}</th>`).join('')}</tr></thead><tbody>${b.rows.slice(1).map(row=>`<tr>${row.map((c,i)=>`<${i===0?'th scope="row"':'td'}>${inline(c,sources)}</${i===0?'th':'td'}>`).join('')}</tr>`).join('')}</tbody></table></div>`;continue;
   }
   const next=blocks[n+1],url=next?.type==='text'&&safeUrl(next.text);
   if(url){html+=`<a class="library-reference" href="${escape(url)}" target="_blank" rel="noopener noreferrer"><span>${inline(b.text,[])}</span><span aria-hidden="true">↗</span></a>`;n++;continue}
   html+=`<p>${inline(b.text,sources)}</p>`;
  }
  return html;
 }
 function feature(section){
  if(section.guide==='01'&&/plain language/.test(section.title))return `<figure class="library-feature spacecraft"><div>${art('01')}</div><figcaption>NISAR spacecraft illustration · NASA/JPL-Caltech. <a href="https://www.jpl.nasa.gov/press-kits/nisar/mission-overview/spacecraft/" target="_blank" rel="noopener noreferrer">Official spacecraft guide ↗</a></figcaption></figure>`;
  if(/complete product family|Input product depth/.test(section.title))return '<figure class="library-feature flow"><img src="/assets/library/product-flow.png" alt="Conceptual product paths from raw echoes to complex images, scattering products, paired products and soil moisture" loading="lazy"><figcaption>Conceptual product dependency summary, created for the team guides. Consult each product specification for the precise workflow.</figcaption></figure>';
  if(section.guide==='02')return `<div class="library-visual-note"><div>${art('02')}</div><p><b>Separate the steps.</b> Finding a file, transferring its arrays, processing a result and publishing a map are different architecture decisions.</p></div>`;
  if(section.guide==='03'&&section.kind!=='studies')return `<div class="library-visual-note evidence"><div>${art('03')}</div><p><b>Read findings with their boundaries.</b> Actual NISAR observations, earlier radar missions and simulations provide different kinds of evidence.</p></div>`;
  return '';
 }
 function missionChapters(lib,query=''){return lib.sections.map((s,index)=>({...s,index})).filter(s=>s.guide==='01'&&matches(s,query))}
 function render(lib,filter=''){
  local.library=lib;local.query=filter;
  const host=document.querySelector('#library-content');if(!host)return;
  const chapters=missionChapters(lib,local.query),total=missionChapters(lib).length;
  if(!chapters.some(s=>s.index===local.selected))local.selected=chapters[0]?.index??null;
  const current=lib.sections[local.selected],selectedPosition=chapters.findIndex(s=>s.index===local.selected);
  const rail=`<nav class="library-rail" aria-label="Mission chapters"><div class="library-rail-heading"><span class="eyebrow">${local.query?'SEARCH THE MISSION GUIDE':'MISSION'}</span><strong>${chapters.length} ${local.query?'matching chapters':'chapters to explore'}</strong></div><div class="library-chapters">${chapters.map((s,i)=>`<button type="button" data-library-chapter="${s.index}" ${s.index===local.selected?'aria-current="page"':''}><span class="chapter-number">${String(i+1).padStart(2,'0')}</span><span>${escape(s.title)}</span></button>`).join('')}</div><div class="library-rail-foot">Select a chapter to read it in full.<br>Numbered citations open the original references.</div></nav>`;
  let article='';
  if(!chapters.length)article=`<div class="library-empty"><span class="eyebrow">MISSION GUIDE</span><h3 tabindex="-1" id="library-article-title">No mission chapters found.</h3><p>Try “GCOV”, “download”, “polarization” or “handbook”.</p><button type="button" id="library-clear-search">Clear search</button></div>`;
  else{
   const subheadings=(current.blocks||[]).map((b,n)=>({...b,n})).filter(b=>b.type==='heading');
   article=`<header class="library-article-header"><div class="article-metadata"><span>MISSION & DATA</span><span>~${readingMinutes(current)} min read</span></div><h3 id="library-article-title" tabindex="-1">${escape(current.title)}</h3></header>${feature(current)}${subheadings.length?`<div class="library-on-page"><span>IN THIS CHAPTER</span>${subheadings.map(b=>`<button type="button" data-library-heading="library-heading-${local.selected}-${b.n}">${escape(b.text)} ↓</button>`).join('')}</div>`:''}<div class="library-prose">${renderBlocks(current,local.selected,lib.sources)}</div><footer class="library-reading-footer"><button type="button" data-read-step="-1" ${selectedPosition<=0?'disabled':''}>← Previous chapter</button><span>${selectedPosition+1} / ${chapters.length}</span><button type="button" data-read-step="1" ${selectedPosition>=chapters.length-1?'disabled':''}>Next chapter →</button></footer>`;
  }
  host.innerHTML=`<div class="library-reading-layout">${rail}<article class="library-article" aria-labelledby="library-article-title">${article}</article></div>`;
  const moveToArticle=()=>{const title=document.querySelector('#library-article-title');title?.focus({preventScroll:true});title?.scrollIntoView({behavior:'smooth',block:'start'})};
  host.querySelectorAll('[data-library-chapter]').forEach(b=>b.onclick=()=>{local.selected=Number(b.dataset.libraryChapter);render(lib,local.query);moveToArticle()});
  host.querySelectorAll('[data-read-step]').forEach(b=>b.onclick=()=>{local.selected=chapters[selectedPosition+Number(b.dataset.readStep)].index;render(lib,local.query);moveToArticle()});
  host.querySelectorAll('[data-library-heading]').forEach(b=>b.onclick=()=>{const heading=document.getElementById(b.dataset.libraryHeading);heading?.focus({preventScroll:true});heading?.scrollIntoView({behavior:'smooth',block:'start'})});
  host.querySelectorAll('[data-copy-code]').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(current.blocks[Number(b.dataset.copyCode)].text);b.textContent='Copied ✓'}catch{b.textContent='Select the code below to copy'}});
  const clear=host.querySelector('#library-clear-search');if(clear)clear.onclick=()=>{document.querySelector('#library-search').value='';render(lib)};
  document.querySelector('#library-search').placeholder=`Search ${total} mission chapters…`;
 }
 const api={render,missionChapters,renderBlocks,studyGroups,safeUrl,matches,sourceMatches,inline,escape};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NisarLibrary=api;
})(typeof globalThis!=='undefined'?globalThis:this);
