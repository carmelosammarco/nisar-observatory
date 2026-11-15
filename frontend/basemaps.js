/* Background-only controls. Never replace the map or touch science/workspace layers. */
function createBasemapController({map,TileLayer,ImageryTileLayer=TileLayer,select,labels,help,status,storage}){
 const service='https://services.arcgisonline.com/ArcGIS/rest/services/';
 const esri=(name)=>service+name+'/MapServer/tile/{z}/{y}/{x}';
 const esriCredit='<a href="https://www.esri.com/">Esri</a> · HERE · Garmin · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · GIS User Community';
 const choices={
  satellite:{url:esri('World_Imagery')+'?blankTile=false',credit:'Source: Esri · Vantor · Earthstar Geographics · GIS User Community',zoom:23,reference:'Reference/World_Boundaries_and_Places'},
  light:{url:esri('Canvas/World_Light_Gray_Base'),credit:esriCredit,zoom:16,reference:'Canvas/World_Light_Gray_Reference'},
  dark:{url:esri('Canvas/World_Dark_Gray_Base'),credit:esriCredit,zoom:16,reference:'Canvas/World_Dark_Gray_Reference'},
  streets:{url:esri('World_Street_Map'),credit:'Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors, GIS User Community',zoom:19,builtInLabels:true},
  plain:{reference:'Canvas/World_Light_Gray_Reference'}
 };
 const storageKey='nisar.map-background.v1';
 let preference={basemap:'satellite',labels:false},base=null,reference=null,outline=null,baseStyle=null;
 try{const saved=JSON.parse(storage?.getItem(storageKey)||'null');if(saved&&Object.hasOwn(choices,saved.basemap))preference={basemap:saved.basemap,labels:saved.labels===true}}catch{/* Storage is optional, including in private browsing. */}
 const pane=map.createPane('placeNames');pane.style.zIndex=450;pane.style.pointerEvents='none';
 const options={minZoom:0,maxZoom:23,noWrap:true,bounds:[[-85.05112878,-180],[85.05112878,180]]};
 function save(){try{storage?.setItem(storageKey,JSON.stringify(preference))}catch{}}
 function layer(url,extra,imagery=false){
  const Layer=imagery?ImageryTileLayer:TileLayer;
  const value=new Layer(url,{...options,...extra});
  value.on('tileerror',()=>{if(value!==base&&value!==reference)return;status.hidden=false;status.textContent='Some background tiles could not load. Try another background or Plain; your selected area and radar results are kept.'});
  return value.addTo(map);
 }
 function draw(){
  const choice=choices[preference.basemap],changed=baseStyle!==preference.basemap;
  if(changed&&base){map.removeLayer(base);base=null}if(reference){map.removeLayer(reference);reference=null}
  if(changed){status.hidden=true;status.textContent=''}
  const container=map.getContainer();container.classList.toggle('basemap-dark',preference.basemap==='dark');
  container.classList.toggle('basemap-plain',preference.basemap==='plain');
  if(outline){if(preference.basemap==='plain'){if(map.hasLayer(outline))map.removeLayer(outline)}else if(!map.hasLayer(outline))outline.addTo(map)}
  if(changed&&choice.url)base=layer(choice.url,{attribution:choice.credit,maxNativeZoom:choice.zoom},preference.basemap==='satellite');
  baseStyle=preference.basemap;
  if(preference.labels&&choice.reference)reference=layer(esri(choice.reference),{pane:'placeNames',attribution:'Place names: '+esriCredit,maxNativeZoom:16});
  select.value=preference.basemap;labels.disabled=!!choice.builtInLabels;labels.checked=choice.builtInLabels||preference.labels;
  if(typeof refreshMapImageDownload==='function')refreshMapImageDownload();
  help.textContent=choice.builtInLabels?'Streets includes labels in its tiles. Your optional place-name choice returns on other backgrounds.':'Background only · imagery dates may differ from NISAR. The switch controls added place names; some base tiles also contain local labels.';
 }
 select.onchange=()=>{if(Object.hasOwn(choices,select.value)){preference.basemap=select.value;save();draw()}};
 labels.onchange=()=>{if(choices[preference.basemap].builtInLabels)return;preference.labels=labels.checked;save();draw()};
 draw();
 return {setOutline(value){outline=value;if(preference.basemap!=='plain')outline.addTo(map).bringToBack()},getSelection(){return {...preference}}};
}
if(typeof module!=='undefined')module.exports={createBasemapController};
