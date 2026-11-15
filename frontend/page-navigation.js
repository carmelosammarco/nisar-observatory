/* Shared keyboard navigation. Never changes recipes, data or the selected map. */
const PageNavigation=(()=>{
 function visible(element){return !!element&&!element.closest('[hidden]')&&element.getClientRects().length>0}
 function focus(element,{scroll=false}={}){
  if(!visible(element))return false;
  if(!element.hasAttribute('tabindex')&&!element.matches('a[href],button,input,select,textarea,summary'))element.setAttribute('tabindex','-1');
  element.focus({preventScroll:true});
  if(scroll)element.scrollIntoView({behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  return true;
 }
 function heading(root){return Array.from(root?.querySelectorAll('h1')||[]).find(visible)||root}
 function update(name,label,{moveFocus=false}={}){
  const root=document.getElementById(name);if(!root)return;
  const section=name==='analysis'?'explore':name;
  for(const button of document.querySelectorAll('.nav[data-view]')){
   if(button.dataset.view===section)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
  }
  document.title=String(label)+' · NISAR Observatory';
  if(moveFocus)focus(heading(root));
 }
 function init(){
  const link=document.getElementById('skip-to-content');
  if(link)link.addEventListener('click',event=>{event.preventDefault();focus(heading(document.querySelector('.view.active')),{scroll:true})});
 }
 return {update,focus,heading,init};
})();
