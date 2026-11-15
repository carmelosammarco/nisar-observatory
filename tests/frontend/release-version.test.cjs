const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
test('visible release version follows the running backend health response',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../frontend/app.js'),'utf8');
 const line=source.split('\n').find(x=>x.startsWith('async function refreshConnection()'));
 const fields={'.version':{},'#rail-connect':{classList:{toggle() {}}},'#rail-connect span':{}};
 const ctx={api:async()=>({version:'9.8.7',earthdata_connected:false,storage_warning_count:0}),$:s=>fields[s],state:{}};
 vm.createContext(ctx);vm.runInContext(line,ctx);await ctx.refreshConnection();
 assert.equal(fields['.version'].textContent,'EXPLORATORY RELEASE 9.8.7');
 assert.equal(fields['#rail-connect span'].textContent,'Earthdata disconnected');
 const html=fs.readFileSync(path.join(__dirname,'../../frontend/index.html'),'utf8');
 assert.doesNotMatch(html,/EXPLORATORY RELEASE \d+\.\d+\.\d+/);
});
