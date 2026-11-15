const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');
function context(catalog){
 const fields=new Map(),$=k=>{if(!fields.has(k))fields.set(k,{innerHTML:'',textContent:'',checked:false,addEventListener(){}});return fields.get(k)};
 const c={state:{tab:'GOFF',selected:'P07',catalog,groups:{},checked:new Set(),downloadChecked:new Set()},$: $, $$:()=>[],esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),renderInputGuide(){},autoSelect(){},groupItems:()=>[],guide:{summary:()=>({known:0})},coverageVisible:true,percentage:String,catalogHelp(){},updateSelection(){},showCoverage(){}};
 vm.createContext(c);vm.runInContext(app.slice(app.indexOf('function catalogDiagnosticsHTML('),app.indexOf('function updateSelection(')),c);return c;
}
test('failed discovery displays unknown availability without a false zero-file result',()=>{
 const c=context({GOFF:{error:'NASA catalog index closed',items:[],hits:null,error_details:{service:'NASA CMR',code:'index_closed',http_status:400,request_id:'id-1'}}});c.renderCatalog();
 assert.match(c.$('#catalog-tabs').innerHTML,/GOFF <span>Unavailable/);
 assert.match(c.$('#catalog-content').innerHTML,/availability is unknown/);
 assert.doesNotMatch(c.$('#catalog-content').innerHTML,/No matching science files/);
 assert.match(c.$('#catalog-message').innerHTML,/Search diagnostics/);
 assert.match(c.$('#catalog-message').innerHTML,/NASA request ID: id-1/);
});
test('a successful empty search still reports zero, and another product failure does not hide it',()=>{
 const c=context({GOFF:{hits:0,items:[]},GCOV:{error:'unavailable',items:[]}});c.renderCatalog();
 assert.match(c.$('#catalog-tabs').innerHTML,/GOFF <span>0/);
 assert.match(c.$('#catalog-message').innerHTML,/0 intersecting catalog records/);
 assert.match(c.$('#catalog-content').innerHTML,/No matching science files/);
});
test('diagnostic fields are HTML escaped',()=>{
 const c=context({});assert.match(c.catalogDiagnosticsHTML({request_id:'<script>bad</script>'}),/&lt;script&gt;/);
 assert.doesNotMatch(c.catalogDiagnosticsHTML({code:'<img>'}),/<img>/);
});
