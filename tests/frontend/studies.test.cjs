const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function context(){const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;')};vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/studies.js'),'utf8'),c);return c;}
test('all seven stories retain hypotheses, alternatives and controlled-experiment guidance',()=>{
 const c=context();
 for(const method of ['P01','P02','P03','P04','P05','P06','P07']){
  const m={story:{question:'What changed?',context:'A dated study',audience:'People',driver:'A hypothesis',alternatives:['Another cause'],confirm:'Independent observations',use:'Closer inspection',exercise:'Change one setting'}};
  const html=vm.runInContext('StudyExperience.storyHTML('+JSON.stringify(m)+')',c);
  for(const text of ['Explore the recorded result','Run it yourself','Other explanations','What would confirm','previously','one setting','does not inherit'])assert.ok(html.includes(text),method+' '+text);
 }
});
test('study narrative and comparison tables escape saved text',()=>{
 const c=context(),m={story:{question:'<script>',context:'<img>',audience:'<iframe>',driver:'<script>',alternatives:['<img>'],confirm:'<script>',use:'<script>',exercise:'<script>'}};
 const html=vm.runInContext('StudyExperience.storyHTML('+JSON.stringify(m)+')',c);
 assert.ok(!html.includes('<script>'));assert.ok(html.includes('&lt;script>'));
 const report={meaning:'<script>',settings:[{setting:'<img>',before:'<script>',after:'<script>'}],layers:[{label:'<script>',unit:'cm',available:false,reason:'Different grids <img>'}]};
 const table=vm.runInContext('StudyExperience.comparisonHTML('+JSON.stringify(report)+')',c);
 assert.ok(!table.includes('<script>'));assert.match(table,/Not calculated/);assert.match(table,/Different grids &lt;img>/);
});
test('comparison explains categorical differences without inventing numerical class magnitude',()=>{
 const c=context(),report={meaning:'Common support',settings:[],layers:[{label:'Candidates',unit:'class',available:true,common_cells:40,quantity_type:'category agreement',changed_percent:25}]};
 const html=vm.runInContext('StudyExperience.comparisonHTML('+JSON.stringify(report)+')',c);
 assert.match(html,/25.00% changed category/);assert.doesNotMatch(html,/Mean change/);assert.match(html,/Display styles are excluded/);
});
