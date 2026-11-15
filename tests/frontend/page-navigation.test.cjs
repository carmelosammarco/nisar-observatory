const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const read=n=>fs.readFileSync(path.join(__dirname,'../../frontend',n),'utf8');
function setup(){
 let focused=null,prevented=false;
 const element=(tag='H1',shown=true)=>{const attributes=new Map();return {tagName:tag,attributes,shown,querySelectorAll(){return []},closest(){return null},getClientRects(){return this.shown?[{}]:[]},hasAttribute:k=>attributes.has(k),setAttribute:(k,v)=>attributes.set(k,v),removeAttribute:k=>attributes.delete(k),matches:()=>['A','BUTTON','INPUT','SELECT','TEXTAREA','SUMMARY'].includes(tag),focus(){focused=this},scrollIntoView(o){this.scroll=o},addEventListener(_,f){this.click=f}}};
 const hidden=element('H1',false),title=element(),root=element('SECTION');root.querySelectorAll=()=>[hidden,title];
 const skip=element('A'),nav=['explore','projects','examples','settings'].map(n=>Object.assign(element('BUTTON'),{dataset:{view:n}}));
 const c={document:{title:'old',getElementById:n=>n==='skip-to-content'?skip:['explore','projects','examples','analysis'].includes(n)?root:null,querySelector:()=>root,querySelectorAll:()=>nav},window:{matchMedia:()=>({matches:false})}};
 vm.createContext(c);vm.runInContext(read('page-navigation.js')+'\nthis.navigation=PageNavigation;',c);
 return {c,nav,title,root,skip,element,focused:()=>focused,prevented:()=>prevented,clickSkip(){skip.click({preventDefault(){prevented=true}})}};
}
test('navigation announces current page and focuses the visible heading rather than a hidden tutorial index',()=>{
 const t=setup();t.c.navigation.update('examples','Mexico <City>',{moveFocus:true});
 assert.equal(t.c.document.title,'Mexico <City> · NISAR Observatory');assert.equal(t.focused(),t.title);assert.equal(t.title.attributes.get('tabindex'),'-1');
 assert.deepEqual(t.nav.filter(n=>n.attributes.has('aria-current')).map(n=>n.dataset.view),['examples']);
 t.c.navigation.update('projects','Tools');assert.deepEqual(t.nav.filter(n=>n.attributes.has('aria-current')).map(n=>n.dataset.view),['projects']);
});
test('shared settings retains Explore as current section and does not steal focus during same-page updates',()=>{
 const t=setup();t.c.navigation.update('analysis','Area & analysis settings');assert.equal(t.focused(),null);
 assert.equal(t.nav[0].attributes.get('aria-current'),'page');assert.equal(t.c.document.title,'Area & analysis settings · NISAR Observatory');
});
test('skip link moves to content without changing the route or inventing a tab stop',()=>{
 const t=setup();t.c.navigation.init();t.clickSkip();assert.equal(t.prevented(),true);assert.equal(t.focused(),t.title);assert.equal(t.title.attributes.get('tabindex'),'-1');assert.equal(t.title.scroll.block,'start');
});
test('shared focus respects reduced motion and preserves existing keyboard semantics',()=>{
 const t=setup(),button=t.element('BUTTON');t.c.window.matchMedia=()=>({matches:true});
 assert.equal(t.c.navigation.focus(button,{scroll:true}),true);assert.equal(button.attributes.has('tabindex'),false);assert.equal(button.scroll.behavior,'instant');
 const heading=t.element();heading.setAttribute('tabindex','0');t.c.navigation.focus(heading);assert.equal(heading.attributes.get('tabindex'),'0');
});
test('hidden and unavailable destinations cannot receive focus or change navigation metadata',()=>{
 const t=setup();assert.equal(t.c.navigation.focus(t.element('H1',false)),false);t.c.navigation.update('missing','Unknown',{moveFocus:true});assert.equal(t.focused(),null);assert.equal(t.c.document.title,'old');
});
test('shared HTML exposes named navigation, keyboard map guidance and labelled help dialogs',()=>{
 const html=read('index.html'),app=read('app.js');assert.match(html,/<a id="skip-to-content"/);assert.match(html,/<nav aria-label="Workspace">/);assert.match(html,/<main id="main-content" tabindex="-1">/);
 for(const [dialog,title] of [['help-dialog','help-title'],['cache-dialog','cache-title']])assert.match(html,new RegExp(`<dialog id="${dialog}" aria-labelledby="${title}"`));
 assert.match(html,/aria-describedby="map-keyboard-help"/);assert.match(html,/without a mouse/);assert.match(app,/aria-labelledby','inventory-title'/);assert.match(app,/<h2 id="inventory-title">/);assert.match(app,/aria-labelledby','catalog-help-title'/);
 assert.match(app,/\.brand'\)\.onclick=e=>\{e.preventDefault\(\)/);
});
function luminance(hex){const a=hex.match(/\w\w/g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return a[0]*.2126+a[1]*.7152+a[2]*.0722}
function ratio(fg,bg){const a=luminance(fg),b=luminance(bg);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)}
test('shared small-text theme pairs meet a 4.5 contrast target on their actual backgrounds',()=>{
 const css=read('style.css');const pairs=[['526763','f3f4ee'],['526763','ffffff'],['56665e','f9faf4'],['66766c','f9faf4'],['346348','eaf0e4'],['53685b','f9faf4'],['4c6e5b','f3f4ee'],['526a3b','f0f5e9'],['576b52','f3f4ee'],['52694f','e8efe5'],['52694f','edf2e8'],['b4d0bd','143f3c']];
 for(const [fg,bg] of pairs){assert.ok(css.includes('#'+fg));assert.ok(ratio(fg,bg)>=4.5,`${fg} on ${bg}: ${ratio(fg,bg)}`)}
 assert.ok(ratio('71817e','f3f4ee')<4.5,'The original body-copy pair did not pass this check');assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);assert.match(css,/:focus-visible/);
});

test('tool selection uses native keyboard buttons and restores focus after rendering the selected row',()=>{const app=read('app.js');assert.match(app,/<button type="button" class="tool-row/);assert.match(app,/aria-pressed="\$\{p.id===state.selected\}"/);assert.match(app,/row.onclick=\(\)=>\{choose\(\);\$\('\.tool-row.active'\)\?\.focus\?\./);assert.doesNotMatch(app,/row.onkeydown/);});
