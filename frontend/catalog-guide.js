/* Catalog-only guidance: bounds estimate potential coverage, never valid science pixels. */
(function(root){
 'use strict';
 function windows(item){
  const stamps=(item.name||'').match(/\d{8}T\d{6}/g)||[];
  const iso=s=>`${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}T${s.slice(9,11)}:${s.slice(11,13)}:${s.slice(13,15)}Z`;
  const pair=['GUNW','GOFF'].includes(item.product);
  return {pair,reference:pair?(stamps.length>=4?[iso(stamps[0]),iso(stamps[1])]:null):[item.start,item.end],secondary:pair&&stamps.length>=4?[iso(stamps[2]),iso(stamps[3])]:null};
 }
 function label(key){
  const p=key.split('_');
  if(p.length!==6||!['A','D'].includes(p[1]))return key;
  return `Track ${p[0]} · ${p[1]==='A'?'Ascending':'Descending'} · Frame ${p[2]} · ${p[3]} / ${p[4]} · ${p[5]}`;
 }
 function polygons(item){
  return (item.polygons||[]).flat(Infinity).flatMap(text=>{
   if(typeof text!=='string')return [];
   const v=text.trim().split(/\s+/).map(Number);
   if(v.length<6||v.length%2||!v.every(Number.isFinite))return [];
   const ring=[];
   for(let i=0;i<v.length;i+=2){if(Math.abs(v[i])>90||Math.abs(v[i+1])>180)return [];let lon=v[i+1];if(ring.length){const previous=ring[ring.length-1][0];while(lon-previous>180)lon-=360;while(lon-previous< -180)lon+=360}ring.push([lon,v[i]])}
   return [ring];
  });
 }
 function boxes(item){
  const rings=polygons(item);
  if(rings.length)return rings.map(r=>[Math.min(...r.map(p=>p[0])),Math.min(...r.map(p=>p[1])),Math.max(...r.map(p=>p[0])),Math.max(...r.map(p=>p[1]))]);
  return (item.boxes||[]).flatMap(box=>{
   const v=typeof box==='string'?box.trim().split(/\s+/).map(Number):[];
   if(v.length!==4||!v.every(Number.isFinite))return [];
   const [s,w,n,e]=v;
   if(s>=n||s< -90||n>90||w< -180||w>180||e< -180||e>180||w===e)return [];
   return w>e?[[w,s,180,n],[-180,s,e,n]]:[[w,s,e,n]];
  });
 }
 // Union of clipped rectangles, weighted by spherical area. Overlapping dates count once.
 function coverage(rectangles,aoi){
  if(!aoi)return null;
  const [w,s,e,n]=aoi,clip=rectangles.map(b=>[Math.max(w,b[0]),Math.max(s,b[1]),Math.min(e,b[2]),Math.min(n,b[3])]).filter(b=>b[0]<b[2]&&b[1]<b[3]);
  const sin=d=>Math.sin(d*Math.PI/180),xs=[...new Set(clip.flatMap(b=>[b[0],b[2]]))].sort((a,b)=>a-b);
  let area=0;
  for(let j=1;j<xs.length;j++){
   const intervals=clip.filter(b=>b[0]<xs[j]&&b[2]>xs[j-1]).map(b=>[b[1],b[3]]).sort((a,b)=>a[0]-b[0]);
   let lo=null,hi=null,latitude=0;
   for(const [a,b] of intervals){if(lo===null){lo=a;hi=b}else if(a<=hi)hi=Math.max(hi,b);else{latitude+=sin(hi)-sin(lo);lo=a;hi=b}}
   if(lo!==null)latitude+=sin(hi)-sin(lo);
   area+=(xs[j]-xs[j-1])*latitude;
  }
  return Math.max(0,Math.min(100,100*area/((e-w)*(sin(n)-sin(s)))));
 }
 function inside(x,y,ring){
  let yes=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
   const [xi,yi]=ring[i],[xj,yj]=ring[j];
   if((yi>y)!==(yj>y)&&x<(xj-xi)*(y-yi)/(yj-yi)+xi)yes=!yes;
  }
  return yes;
 }
 function areaCoverage(items,aoi){
  if(!aoi)return null;
  const known=items.filter(i=>boxes(i).length);if(!known.length)return null;
  if(!known.some(i=>polygons(i).length))return coverage(known.flatMap(boxes),aoi);
  const center=(aoi[0]+aoi[2])/2;
  const rings=known.flatMap(i=>{const p=polygons(i);return p.length?p:boxes(i).map(b=>[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]])}).map(r=>{
   const shift=360*Math.round((center-r.reduce((n,p)=>n+p[0],0)/r.length)/360);return r.map(p=>[p[0]+shift,p[1]]);
  });
  // Equal-area sample centers: approximate union of catalog polygons, including date-line scenes.
  const size=64,lo=Math.sin(aoi[1]*Math.PI/180),hi=Math.sin(aoi[3]*Math.PI/180);let count=0;
  for(let j=0;j<size;j++){
   const y=Math.asin(lo+(hi-lo)*(j+.5)/size)*180/Math.PI;
   for(let k=0;k<size;k++){const x=aoi[0]+(aoi[2]-aoi[0])*(k+.5)/size;if(rings.some(r=>inside(x,y,r)))count++}
  }
  return 100*count/(size*size);
 }
 function summary(items,aoi){
  const known=items.filter(i=>boxes(i).length),each=known.map(i=>areaCoverage([i],aoi)).filter(v=>v!==null);
  return {known:known.length,total:items.length,percent:areaCoverage(items,aoi),min:each.length?Math.min(...each):null,max:each.length?Math.max(...each):null,dates:new Set(items.map(i=>{const d=windows(i);return d.pair?JSON.stringify([d.reference||i.start,d.secondary||i.end]):i.start})).size};
 }
 function selectionStats(items){
  const known=items.filter(i=>Number.isFinite(i.size_mb)&&i.size_mb>0);
  return {count:items.length,bytes:known.reduce((n,i)=>n+i.size_mb*1e6,0),unknown:items.length-known.length,local:items.filter(i=>i.local).length,oversized:known.filter(i=>i.size_mb*1e6>8*1024**3).length};
 }
 function sizeLabel(stats){return stats.unknown?(stats.bytes?`At least ${(stats.bytes/1024**3).toFixed(2)} GiB`:'Size unavailable'):`${(stats.bytes/1024**3).toFixed(2)} GiB`}
 function rectangleKm2(bbox){if(!bbox)return null;const [w,s,e,n]=bbox;return 6371.0088**2*Math.abs((e-w)*Math.PI/180*(Math.sin(n*Math.PI/180)-Math.sin(s*Math.PI/180)))}
 const helpers={selectionStats,sizeLabel,rectangleKm2,windows,label,boxes,polygons,coverage,areaCoverage,summary};
 if(typeof module!=='undefined'&&module.exports)module.exports=helpers;else root.NisarCatalogGuide=helpers;
})(typeof globalThis!=='undefined'?globalThis:this);
