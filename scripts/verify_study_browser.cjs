/* Real browser journeys against an isolated server owned by verify_scenario_b.py.
 * Requires Playwright and an installed Chrome; no package or browser is downloaded.
 */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const [base,output]=process.argv.slice(2);
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base||'')||!output)throw Error('Pass the isolated loopback server URL and evidence folder.');
fs.mkdirSync(output,{recursive:true});
const cases=['P01_Mozambique','P02_Wheeler_Marsh','P03_Timber_Fire','P04_Mexico_City','P05_Venezuela','P06_Krasheninnikov','P07_Samudra_Tapu'];
async function main(){
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const errors=[],rows=[];let success=false;
 page.on('pageerror',error=>errors.push(error.message));
 const response=async route=>{const r=await page.request.get(base+route);assert.equal(r.status(),200,route);return r.json()};
 async function completed(job){
  await page.waitForFunction(id=>state.currentJob?.id===id&&state.currentJob.status==='completed'&&state.result&&document.querySelector('#study-result-title'),job.id,{timeout:120000});
  const current=await response('/api/jobs/'+job.id);assert.equal(current.status,'completed');
  const pid=Object.keys(current.results)[0];return {job:job.id,pid,result:await response(current.results[pid].url)};
 }
 async function start(button,endpoint){
  const pending=page.waitForResponse(r=>r.url()===base+endpoint&&r.request().method()==='POST');await button.click();
  const r=await pending;assert.equal(r.status(),200,await r.text());return completed(await r.json());
 }
 try{
  assert.deepEqual(await response('/api/jobs'),[],'Browser verification requires an empty isolated runtime.');
  await page.goto(base);await page.locator('#tool-list .tool-row').first().waitFor();
  await page.screenshot({path:path.join(output,'explore.png')});
  await page.locator('.nav[data-view="examples"]').click();await page.locator('#example-grid .example-card').nth(6).waitFor();
  await page.locator('#example-grid img').evaluateAll(images=>Promise.all(images.map(image=>image.decode())));
  await page.locator('#example-grid').screenshot({path:path.join(output,'examples.png')});
  for(const caseId of cases){
   await page.locator('.nav[data-view="examples"]').click();await page.locator('.example-card[data-example="'+caseId+'"]').click();await page.locator('#example-start:not([disabled])').waitFor({timeout:30000});
   assert.ok((await page.locator('.study-story').innerText()).includes('What would confirm it?'));
   if(caseId==='P01_Mozambique')await page.screenshot({path:path.join(output,'tutorial.png')});
   await page.locator('#study-recorded-example').click();await page.locator('#study-result-title').waitFor({timeout:30000});
   await page.waitForFunction(()=>state.layer&&document.querySelector('#save-opening-view')?.disabled);
   const opened=await page.evaluate(()=>({kind:state.currentJob.kind,layer:state.layer.id,palette:state.displayPalette,job:state.currentJob.id}));
   assert.equal(opened.kind,'recorded');
   const def=await response('/api/examples/'+caseId);assert.equal(opened.layer,def.request.display.layer);assert.equal(opened.palette,def.request.display.palette);
   if(caseId!=='P07_Samudra_Tapu'){
    await page.locator('#study-dates').click();
    if(['P03_Timber_Fire','P05_Venezuela'].includes(caseId))await page.locator('#study-observation-status').filter({hasText:'different quantities or viewing groups'}).waitFor();
    else await page.locator('#study-observation-status').filter({hasText:'Actual acquired states'}).waitFor({timeout:30000});
   }
   if(caseId==='P01_Mozambique'){
    await page.locator('#study-result').screenshot({path:path.join(output,'acquired-states.png')});
   }
   if(caseId==='P07_Samudra_Tapu'){
    await page.locator('#study-dates').click();assert.match(await page.locator('#study-observations').innerText(),/One interval is not a time series/);
   }
   await page.locator('#study-return-tutorial').click();await page.locator('#example-start:not([disabled])').waitFor({timeout:30000});
   const guided=await start(page.locator('#example-start'),'/api/run');
   assert.equal(guided.pid,def.tool);
   await page.locator('#study-customize').click();await page.locator('#workflow-run:not([disabled])').waitFor();
   const editable=await start(page.locator('#workflow-run'),'/api/workflows/run');
   assert.equal(editable.pid,'LAB');
   rows.push({case:caseId,recorded:opened,guided:{job:guided.job,pid:guided.pid},editable:{job:editable.job,pid:editable.pid}});
   console.log(caseId+': recorded view, guided run and editable replay complete.');
  }
  // Change one numeric field and click Run directly, without Tab/blur assistance.
  await page.locator('.nav[data-view="examples"]').click();await page.locator('.example-card[data-example="P01_Mozambique"]').click();await page.locator('#example-start:not([disabled])').waitFor();await page.locator('#study-recorded-example').click();await page.locator('#study-result-title').waitFor();
  await page.locator('#study-customize').click();
  await page.locator('#workflow-workspace').getByLabel('Single-channel threshold · dB',{exact:true}).fill('-18');
  const variant=await start(page.locator('#workflow-run'),'/api/workflows/run');
  await page.locator('#study-compare').click();await page.locator('#study-compare-run').click();
  await page.locator('#study-comparison-result h4').filter({hasText:'What changed in the maps?'}).waitFor({timeout:30000});
  await page.locator('#study-experiment-status').filter({hasText:'Same observations'}).waitFor({timeout:30000});
  assert.match(await page.locator('#study-comparison-result').innerText(),/water threshold|threshold_db/);
  await page.locator('#study-comparison').screenshot({path:path.join(output,'experiment-comparison.png')});
  const compared=await page.request.post(base+'/api/studies/compare',{data:{before:'example-P01_Mozambique',before_product:'P01',after:variant.job,after_product:'LAB'}});
  assert.equal(compared.status(),200);const difference=await compared.json();assert.ok(difference.layers.find(l=>l.id==='event').changed_cells>0);
  assert.equal(variant.result.metrics.new_water_candidate_km2,51.4);
  const pendingDownload=page.waitForEvent('download');await page.locator('#study-report').click();const download=await pendingDownload;
  const reportPath=path.join(output,'mozambique-study.html');await download.saveAs(reportPath);
  const report=fs.readFileSync(reportPath,'utf8');assert.ok(report.includes('data:image/png;base64,'));assert.ok(report.includes('What would confirm'));assert.ok(!/<script[\s>]/i.test(report));
  assert.ok(report.includes('Acquired observation summaries'));assert.ok(report.includes('water rule'));
  const reportPage=await browser.newPage({viewport:{width:1280,height:1000}});await reportPage.goto('file://'+reportPath);await reportPage.locator('img').evaluate(image=>image.decode());await reportPage.screenshot({path:path.join(output,'report.png')});await reportPage.close();
  await page.locator('#workflow-name').fill('Scenario B verification · Mozambique −18 dB');
  await page.locator('#workflow-save').click();await page.locator('#workflow-status').filter({hasText:'Saved'}).waitFor();
  const tools=await response('/api/workflows');assert.equal(tools.length,1);
  await page.locator('.nav[data-view="projects"]').click();await page.locator('[data-workflow-load]').click();
  assert.equal(await page.locator('#workflow-name').inputValue(),'Scenario B verification · Mozambique −18 dB');
  assert.equal(await page.locator('#workflow-workspace').getByLabel('Single-channel threshold · dB',{exact:true}).inputValue(),'-18');
  const mobile=[];await page.setViewportSize({width:390,height:844});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  for(const tab of ['explore','projects','examples','mission','runs','settings','about']){
   await page.locator('.nav[data-view="'+tab+'"]').click();
   await page.waitForFunction(id=>document.querySelector('#'+id+'.active'),tab);
   const dimensions=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));
   mobile.push({tab,...dimensions});assert.ok(dimensions.width<=dimensions.viewport+2,tab+' has horizontal page overflow: '+JSON.stringify(dimensions));
  }
  await page.screenshot({path:path.join(output,'about-mobile.png')});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({passed:true,cases:rows,variant:{job:variant.job,pid:variant.pid,new_candidates_km2:variant.result.metrics.new_water_candidate_km2,comparison:difference},saved_tool:tools[0].id,mobile,errors},null,2)+'\n');
  success=true;
 }finally{
  if(!success){await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});console.error('Failure context:',await page.locator('#workflow-status').textContent().catch(()=>''),await page.locator('#toast').textContent().catch(()=>''),errors);}
  await browser.close();
 }
}
main().catch(error=>{console.error(error);process.exitCode=1});
