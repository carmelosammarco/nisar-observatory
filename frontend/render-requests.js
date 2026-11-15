/* One server render at a time; obsolete previews stop fetching/retrying.
 * A disconnected request cannot interrupt an already running native server call.
 */
let activeMapPreviewRequest=null;
function cancelMapPreviewRequest(){activeMapPreviewRequest?.abort();activeMapPreviewRequest=null}
function beginMapPreviewRequest(){cancelMapPreviewRequest();activeMapPreviewRequest=new AbortController();return activeMapPreviewRequest}
function renderWait(milliseconds,signal){
 return new Promise((resolve,reject)=>{
  if(signal?.aborted){reject(new DOMException('Preview superseded.','AbortError'));return}
  const abort=()=>{clearTimeout(timer);signal?.removeEventListener('abort',abort);reject(new DOMException('Preview superseded.','AbortError'))};
  const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve()},milliseconds);
  signal?.addEventListener('abort',abort,{once:true});
 });
}
async function fetchRenderedMap(url,{signal,onWaiting,...options}={}){
 const deadline=Date.now()+60000;let retrying=false;
 for(;;){
  if(signal?.aborted)throw new DOMException('Preview superseded.','AbortError');
  if(retrying&&Date.now()>=deadline)throw new Error('Map preparation is still busy. Please try again in a moment.');
  const response=await fetch(url,{...options,signal});
  if(response.status!==429||response.headers.get('X-NISAR-Render-Busy')!=='1'||Date.now()>=deadline)return response;
  // Consume the small busy response before another attempt; no queued images.
  await response.text();onWaiting?.();
  const retry=Number(response.headers.get('Retry-After'));
  retrying=true;
  await renderWait(Math.min(Math.max(0,deadline-Date.now()),2000,Math.max(250,Number.isFinite(retry)?retry*1000:1000)),signal);
 }
}
const MAP_PREVIEW_CACHE_BYTES=32*1024*1024,MAP_PREVIEW_CACHE_ENTRIES=24;
function mapPreviewBytes(display){return 8192+2*((display.image?.length||0)+(display.validity_image?.length||0)+JSON.stringify({...display,image:undefined,validity_image:undefined}).length)}
function getMapPreview(key){
 const cache=state.previewCache,display=cache?.get(key);
 if(display){cache.delete(key);cache.set(key,display)}
 return display;
}
function cacheMapPreview(key,display){
 const cache=state.previewCache??=new Map();cache.delete(key);
 if(mapPreviewBytes(display)>MAP_PREVIEW_CACHE_BYTES)return;
 cache.set(key,display);
 let bytes=0;for(const item of cache.values())bytes+=mapPreviewBytes(item);
 while(cache.size>MAP_PREVIEW_CACHE_ENTRIES||bytes>MAP_PREVIEW_CACHE_BYTES){const oldest=cache.keys().next().value;bytes-=mapPreviewBytes(cache.get(oldest));cache.delete(oldest)}
}
