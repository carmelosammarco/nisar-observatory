/* Folder selection sends only chosen HDF5 files through the existing safe importer. */
function importCandidates(files){
 const all=Array.from(files||[]),data=all.filter(file=>/\.h5$/i.test(file.name)&&!(file.webkitRelativePath||file.name).split('/').some(part=>part.startsWith('.')));
 return {all,data,ignored:all.length-data.length};
}
function mergeImportedItems(items){
 for(const item of items){
  const catalog=state.catalog[item.product]??={hits:0,items:[]};
  catalog.items=catalog.items.filter(old=>{if(old.name===item.name){state.checked.delete(old.id);state.downloadChecked.delete(old.id);return false}return true});
  catalog.items.push(item);catalog.hits=catalog.items.length;
  catalog.items.filter(old=>old.group!==item.group).forEach(old=>state.checked.delete(old.id));
  state.checked.add(item.id);state.groups[item.product]=item.group;state.tab=item.product;
 }
}
function showImportReport(report){
 let dialog=$('#import-report-dialog');
 if(!dialog){dialog=document.createElement('dialog');dialog.id='import-report-dialog';dialog.setAttribute('aria-labelledby','import-report-title');document.body.append(dialog)}
 const products=Object.entries(report.products).map(([product,count])=>`${count} ${product}`).join(' · ');
 dialog.innerHTML=`<span class="eyebrow">${report.folder?'FOLDER IMPORT':'DATA IMPORT'}</span><h2 id="import-report-title">${report.total===0?'No HDF5 files found':report.loaded?'Your data is loaded':'Import needs attention'}</h2>${report.folder?`<p><b>${esc(report.folder)}</b></p>`:''}<div class="import-report-counts"><div><b>${report.loaded} / ${report.total}</b><span>HDF5 files loaded</span></div><div><b>${report.unique}</b><span>Unique source files</span></div><div><b>${report.ignored}</b><span>Other or hidden files skipped</span></div></div>${products?`<p>${esc(products)}</p>`:''}<p>${report.workspaceKept?'Your workspace changed during import, so it has been kept. Choose Use saved data to load these files into the current area.':report.loaded?'The imported observations are in the table. Review acquisition groups, dates and area coverage, then choose a tool.':'Choose a subset folder containing .h5 files, or correct the file errors below.'}</p>${report.loaded?'<p class="small">One compatible group per product is selected. Other imported groups stay available in the group selector. Repeated copies of a source appear once. Saved-area boundaries still apply; quality is checked when processing runs.</p>':''}${report.errors.length?`<section class="warning-note"><b>${report.errors.length} file${report.errors.length===1?'':'s'} could not be loaded</b><ul>${report.errors.map(error=>`<li><b>${esc(error.name)}</b><br>${esc(error.message)}</li>`).join('')}</ul><p>Successfully imported files have been kept. You can retry the failed files separately.</p></section>`:''}${report.notice?`<p class="warning-note">${esc(report.notice)}</p>`:''}<button type="button" class="primary" id="import-report-close">Continue</button>`;
 $('#import-report-close').onclick=()=>dialog.close();dialog.showModal();
}
async function importDataBatch(files,{folder=false}={}){
 if(state.importing){toast('An import is already running. Wait for it to finish.');return}
 const {all,data,ignored}=importCandidates(files);if(!all.length)return;
 const folderName=folder?(all.find(file=>file.webkitRelativePath)?.webkitRelativePath.split('/')[0]||'Selected folder'):null;
 if(!data.length){showImportReport({folder:folderName,loaded:0,total:0,unique:0,ignored,products:{},errors:[],workspaceKept:false});return}
 state.importing=true;
 for(const selector of ['#import-button','#import-folder-button','#file-input','#folder-input'])if($(selector))$(selector).disabled=true;
 // Invalidate a pending discovery response, so it cannot overwrite the imported rows.
 if(typeof invalidateCatalog==='function')invalidateCatalog();
 const revision=state.areaRevision,catalogVersion=requestVersions.catalog,loaded=[],errors=[];
 let notice='',workspaceKept=false;
 try{
  for(let index=0;index<data.length;index++){
   const file=data[index];$('#catalog-message').textContent=`Importing ${folderName?folderName+' · ':''}${index+1} of ${data.length} HDF5 files: ${file.name}`;
   try{
    const item=await api('/api/import',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Filename':file.name.replace(/\.h5$/i,'.h5')},body:file});loaded.push(item);
   }catch(error){errors.push({name:file.webkitRelativePath||file.name,message:error.message})}
  }
  workspaceKept=revision!==state.areaRevision||catalogVersion!==requestVersions.catalog;
  if(!workspaceKept){
   const firstSubset=loaded.find(item=>item.subset);
   if(firstSubset&&!state.bbox)drawArea(firstSubset.subset_bbox);
   mergeImportedItems(loaded);
  }
  try{await refreshLocalFiles()}catch(error){notice='Files were imported, but the saved-data list could not refresh: '+error.message}
  renderCatalog();
  const unique=[...new Map(loaded.map(item=>[item.name,item])).values()],products={};
  unique.forEach(item=>products[item.product]=(products[item.product]||0)+1);
  $('#catalog-message').textContent=`Import complete · ${loaded.length}/${data.length} HDF5 files loaded · ${ignored} other or hidden files skipped.${workspaceKept?' Use saved data to open them in your current workspace.':''}`;
  showImportReport({folder:folderName,loaded:loaded.length,total:data.length,unique:unique.length,ignored,products,errors,workspaceKept,notice});
 }finally{
  state.importing=false;
  for(const selector of ['#import-button','#import-folder-button','#file-input','#folder-input'])if($(selector))$(selector).disabled=false;
 }
}
