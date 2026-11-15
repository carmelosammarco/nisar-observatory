// Batch bridge for independent Python/browser contract parity tests.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const context={structuredClone};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../../frontend/workflow-contract.js'),'utf8'),context);
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const reports=input.cases.map(row=>context.workflowContractInspect(input.rules,row.product,row.steps,input.outputs));
process.stdout.write(JSON.stringify(reports));
