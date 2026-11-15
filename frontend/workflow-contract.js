'use strict';
// This interpreter contains no tool-specific dependency rules. The server supplies
// the declarative contract and parameter schemas; recipe JSON cannot supply rules.
function workflowRuleValue(expression,context){
 if(expression===null||typeof expression!=='object'||Array.isArray(expression))return expression;
 if(Object.hasOwn(expression,'var'))return expression.var.split('.').reduce((v,key)=>v&&typeof v==='object'&&Object.hasOwn(v,key)?v[key]:null,context);
 const [op,args]=Object.entries(expression)[0],v=args.map(a=>workflowRuleValue(a,context));
 switch(op){case'all':return v.every(Boolean);case'any':return v.some(Boolean);case'not':return !v[0];case'eq':return v[0]===v[1];case'in':return v[1].includes(v[0]);case'subset':return v[0].every(x=>v[1].includes(x));case'gte':return v[0]!==null&&v[1]!==null&&v[0]>=v[1];case'gt':return v[0]!==null&&v[1]!==null&&v[0]>v[1];case'lte':return v[0]!==null&&v[1]!==null&&v[0]<=v[1];case'if':return v[0]?v[1]:v[2];case'concat':return v.join('');case'max':return Math.max(...v);case'add':return v.reduce((a,b)=>a+b,0);case'fallback':return v[0]??v[1];default:throw Error('Unsupported workflow-rule expression.');}
}
function workflowContractMethod(spec,steps){const ops=steps.map(s=>s.operation);return spec.method_order.find(m=>spec.families[m].detect.some(n=>ops.includes(n)))??null;}
function workflowContractOutputs(spec,method,steps,outputs){
 const choices=Object.fromEntries(Object.entries(outputs?.[method]||{}).map(([k,v])=>[k,Array.isArray(v)?{unit:v[0],label:v[1]}:{...v}])),context={by_operation:Object.fromEntries(steps.map(s=>[s.operation,s.parameters||{}])),operations:steps.map(s=>s.operation)};
 for(const [name,condition]of Object.entries(spec.output_filters?.[method]||{}))if(!workflowRuleValue(condition,context))delete choices[name];
 for(const value of Object.values(choices)){const rule=spec.output_units?.[method]?.[value.unit];if(rule!==undefined)value.unit=workflowRuleValue(rule,context);}
 return choices;
}
function workflowContractApply(spec,op,parameters,product,index,unit,domain,seen){
 const rule=spec.elementary[op],context={parameters,product,index,unit,domain,seen,operation:op};
 if(!rule||!rule.products.includes(product))return {unit,domain,error:`${op} is incompatible with ${product}.`};
 for(const check of [...spec.common_checks,...rule.checks])if(!workflowRuleValue(check.condition,context))return{unit,domain,error:check.message};
 return {unit:workflowRuleValue(rule.set.unit??unit,context),domain:workflowRuleValue(rule.set.domain??domain,context),error:null};
}
function workflowCalendarValid(value,format){
 const date=/^(\d{4})-(\d{2})-(\d{2})/.exec(value);if(!date)return false;
 const y=Number(date[1]),m=Number(date[2]),d=Number(date[3]),days=[31,y%4===0&&(y%100!==0||y%400===0)?29:28,31,30,31,30,31,31,30,31,30,31];if(y<1||y>9999||m<1||m>12||d<1||d>days[m-1])return false;
 if(format==='date')return value.length===10;
 const time=/^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})$/.exec(value);if(!time||Number(time[1])>23||Number(time[2])>59||Number(time[3]||0)>59)return false;
 if(time[4]!=='Z'&&(Number(time[4].slice(1,3))>23||Number(time[4].slice(4,6))>59))return false;return true;
}
function workflowSchemaValid(value,schema){
 if(schema.anyOf&&!schema.anyOf.some(s=>workflowSchemaValid(value,s)))return false;
 if(schema.enum&&!schema.enum.includes(value))return false;
 const t=schema.type;if(t==='null')return value===null;if(t==='boolean'&&typeof value!=='boolean')return false;
 if(['integer','number'].includes(t)){if(typeof value!=='number'||!Number.isFinite(value)||t==='integer'&&!Number.isInteger(value))return false;for(const [key,test]of [['minimum',v=>value>=v],['exclusiveMinimum',v=>value>v],['maximum',v=>value<=v],['exclusiveMaximum',v=>value<v]])if(schema[key]!==undefined&&!test(schema[key]))return false;}
 if(t==='string'){if(typeof value!=='string'||schema.minLength!==undefined&&value.length<schema.minLength||schema.maxLength!==undefined&&value.length>schema.maxLength)return false;}
 if(typeof value==='string'&&schema.format&&!workflowCalendarValid(value,schema.format))return false;
 return true;
}
function workflowParameterIssues(spec,steps){
 const errors=[];for(const [index,step]of steps.entries()){
  const schema=spec.parameter_schemas?.[step.operation];if(!schema)continue;const parameters={...spec.defaults?.[step.operation],...step.parameters};
  for(const key of schema.required||[])if(parameters[key]===undefined)errors.push('Step '+(index+1)+': provide '+key.replaceAll('_',' ')+'.');
  for(const [key,value]of Object.entries(parameters)){if(!schema.properties?.[key]||!workflowSchemaValid(value,schema.properties[key]))errors.push('Step '+(index+1)+': check '+key.replaceAll('_',' ')+' against its allowed type and range.');}
 }
 return errors;
}
function workflowContractStructure(spec,product,rawSteps,outputs){
 if(!spec||spec.version!=='1.0.0'){const message=!spec?'Workflow rules have not loaded. Reload the app before editing or running.':'This interface cannot use the server workflow-rule version. Reload or update the app before editing or running.';return {unit:'unknown',domain:'unknown',issue:message,complete:false,method:null,rows:[],minimum_sources:1,choices:{},errors:[message],parameter_issues:[]};}
 const steps=rawSteps.map(s=>({operation:s.operation,parameters:{...(spec.defaults?.[s.operation]||{}),...(s.parameters||{})}})),ops=steps.map(s=>s.operation),method=workflowContractMethod(spec,steps),errors=[],parameter_issues=[],missing=[],rows=[],internal_indices=[],stage_indices={};let unit=spec.initial_units[product]||'unknown',domain=spec.initial_domains[product]||'unknown',minimum_sources=1;
 if(steps.length>spec.max_steps)errors.push('Maximum 16 steps. Remove a step before adding another.');
 if(!method){
  const seen=[];for(const [i,s]of steps.entries()){
   const before=unit,beforeDomain=domain,mr=spec.elementary[s.operation]?.minimum_sources;if(mr)minimum_sources=workflowRuleValue(mr,{minimum_sources,parameters:s.parameters,domain});
   const next=workflowContractApply(spec,s.operation,s.parameters,product,i,unit,domain,seen);unit=next.unit;domain=next.domain;
   rows.push({input:before,output:unit,domain:beforeDomain,output_domain:domain,scope:'observed measurements',valid:!next.error});if(next.error)errors.push(next.error);seen.push(s.operation);
  }
  return {unit,domain,issue:errors[0]??null,complete:!!steps.length&&ops.at(-1)==='summary'&&!errors.length,method:null,errors,parameter_issues:[],missing:[],rows,minimum_sources,choices:{},internal_indices:[],stage_indices:{},post_indices:[]};
 }
 const family=spec.families[method];minimum_sources=family.minimum;
 if(family.product!==product)errors.push('These scientific blocks require '+family.product+'.');
 const unique=ops.filter(n=>!spec.repeatable.includes(n));if(new Set(unique).size!==unique.length)errors.push('Use one instance of each compound scientific block; compatible map operations can repeat.');
 if(ops.includes('publish')&&ops.at(-1)!=='publish')errors.push('Choose the opening result map must be last.');if(ops.includes('source_smooth')&&ops[0]!=='source_smooth')errors.push('Input smoothing must be first.');
 let index=ops[0]==='source_smooth'?1:0;
 for(const stage of family.stages){const alternatives=stage.filter(n=>n!=='?');if(index<steps.length&&alternatives.includes(ops[index])){stage_indices[ops[index]]=index;if(spec.repeatable.includes(ops[index]))internal_indices.push(index);index++;}else if(!stage.includes('?'))missing.push(alternatives.join(' or '));}
 const publish=steps.find(s=>s.operation==='publish'),choices=workflowContractOutputs(spec,method,steps,outputs),output=publish?publish.parameters.layer:Object.keys(choices)[0]??null,baseUnit=choices[output]?.unit||'measurement';
 if(publish&&!choices[output])errors.push('Choose an available opening result map for this method and units.');
 const post_indices=steps.map((s,i)=>i>=index&&s.operation!=='publish'?i:-1).filter(i=>i>=0);
 for(const i of post_indices)if(!spec.post_ids.includes(ops[i]))errors.push('Restore the scientific dependency order. Only compatible map operations follow the last scientific calculation.');
 for(const [op,checks]of Object.entries(spec.semantic_checks?.[method]||{}))if(Object.hasOwn(stage_indices,op))for(const check of checks)if(!workflowRuleValue(check.condition,{parameters:steps[stage_indices[op]].parameters}))parameter_issues.push(check.message);
 const mr=family.minimum_parameter;if(mr){const q=steps.find(s=>s.operation===mr.operation)?.parameters||{};if(!q[mr.unless])minimum_sources=(q[mr.field]??mr.default)+1;}
 let selectedUnit=baseUnit;
 for(const [i,s]of steps.entries()){
  const op=s.operation;let before=unit,beforeDomain=domain,scope='scientific method stage',error=null,rowUnit;
  if(post_indices.includes(i)){
   before=selectedUnit;beforeDomain='map';scope='selected method output';
   if(spec.post_ids.includes(op)){const next=workflowContractApply(spec,op,s.parameters,product,i,selectedUnit,'map',[]);selectedUnit=next.unit;error=next.error;if(op==='patches'&&spec.patch_prohibited_outputs.includes(output))error='Signed direction classes are not a binary candidate mask. Choose a binary surface map for patch filtering.';}else error='Restore the scientific dependency order before processing.';
   if(error)errors.push(error);rowUnit=selectedUnit;
  }else if(op==='publish'){before=selectedUnit;beforeDomain='map';rowUnit=selectedUnit;scope='selected method output';}
  else if(spec.elementary[op]){const next=workflowContractApply(spec,op,s.parameters,product,i,unit,domain,[]);unit=next.unit;domain=next.domain;error=next.error;if(error)errors.push(error);rowUnit=unit;}
  else{unit=workflowRuleValue(spec.block_units[op]??unit,{parameters:s.parameters});rowUnit=unit;}
  rows.push({input:before,output:rowUnit,domain:beforeDomain,output_domain:scope==='selected method output'?'map':domain,scope,valid:!error});
 }
 const issue=errors[0]??parameter_issues[0]??(missing.length?'Add the missing scientific block: '+missing.map(group=>group.split(' or ').map(name=>spec.titles?.[name]||name).join(' or ')).join(', ')+'. Undo removal to restore the tested sequence.':null);
 return {unit:publish||post_indices.length?selectedUnit:unit,domain:'scientific',issue,complete:!!publish&&ops.at(-1)==='publish'&&!issue,method,errors:[...new Set(errors)],parameter_issues,missing,rows,minimum_sources,choices,output,internal_indices,stage_indices,post_indices};
}
function workflowContractOrder(spec,steps){const method=workflowContractMethod(spec,steps);return method?['source_smooth',...spec.families[method].stages.flatMap(s=>s.filter(n=>n!=='?'))]:[];}
function workflowContractInsert(spec,recipe,operator,outputs){
 const parameters=structuredClone(operator.defaults||{});if(operator.id==='publish')parameters.layer=Object.keys(workflowContractOutputs(spec,workflowContractMethod(spec,recipe.steps),recipe.steps,outputs))[0]||'';
 const order=workflowContractOrder(spec,[...recipe.steps,{operation:operator.id,parameters}]);let at=recipe.steps.findIndex(s=>s.operation==='publish');if(at<0)at=recipe.steps.length;
 if(order.includes(operator.id)&&!recipe.steps.some(s=>s.operation===operator.id)){const next=recipe.steps.findIndex(s=>order.includes(s.operation)&&order.indexOf(s.operation)>order.indexOf(operator.id));if(next>=0)at=next;}
 recipe.steps.splice(at,0,{operation:operator.id,parameters});
 const opening=recipe.steps.find(s=>s.operation==='publish'),choices=workflowContractOutputs(spec,workflowContractMethod(spec,recipe.steps),recipe.steps,outputs);
 if(opening&&!choices[opening.parameters.layer]){opening.parameters.layer=Object.keys(choices)[0]||'';return {opening_changed:true,index:at};}
 return {opening_changed:false,index:at};
}
function workflowContractCompatible(spec,recipe,operators,outputs){
 if(!spec||spec.version!=='1.0.0'||recipe.steps.length>=spec.max_steps)return[];
 const scientific=recipe.steps.some(s=>spec.scientific_ids.includes(s.operation)),ops=recipe.steps.map(s=>s.operation);
 return operators.filter(o=>o.products.includes(recipe.product)).filter(o=>{
  if(scientific){
   if(ops.includes(o.id)&&!spec.repeatable.includes(o.id))return false;
   const trial=structuredClone(recipe);workflowContractInsert(spec,trial,o,outputs);
   const before=workflowContractInspect(spec,recipe.product,recipe.steps,outputs),after=workflowContractInspect(spec,trial.product,trial.steps,outputs);
   if(!spec.post_ids.includes(o.id)&&o.id!=='publish'&&!workflowContractOrder(spec,trial.steps).includes(o.id))return false;
   if(o.id==='publish')return !after.errors.length;
   if(spec.post_ids.includes(o.id)&&before.missing.length)return !after.errors.length;
   // Only a structurally compatible addition is offered; incomplete required blocks
   // may still need parameters. The final check remains authoritative on the server.
   return !after.errors.length&&!after.parameter_issues.some(message=>!before.parameter_issues.includes(message));
  }
  if(spec.scientific_ids.includes(o.id))return !recipe.steps.length&&spec.entry_ids.includes(o.id);
  if(!spec.elementary[o.id]||(o.id==='summary'&&ops.includes('summary')))return false;
  const prefix=recipe.steps.filter(s=>s.operation!=='summary'),parameters={...o.defaults};if(o.id==='summary'&&workflowContractInspect(spec,recipe.product,prefix,outputs).unit==='class')parameters.statistic='frequency';
  return !workflowContractInspect(spec,recipe.product,[...prefix,{operation:o.id,parameters}],outputs).errors.length;
 });
}

function workflowContractInspect(spec,product,steps,outputs){
 const report=workflowContractStructure(spec,product,steps,outputs);if(!spec||spec.version!=='1.0.0')return report;
 const errors=workflowParameterIssues(spec,steps);if(errors.length){report.parameter_issues.push(...errors);report.issue=report.issue||errors[0];report.complete=false;}
 return report;
}
