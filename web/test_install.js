'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const core=require('./install-core.js'), plugin=fs.readFileSync(__dirname+'/sc-boss-test.js','utf8');
const runtime='/* WebBreak runtime                                                           */';
const base='/*@WebBreak-patched*/\n// client build 1574197275\nconst customSetting="keep me";\n'+runtime+'\n// original game retained';
const next=core.update(base,plugin);assert(next.includes('const customSetting="keep me";'));
const once=core.update(next,plugin);assert.equal(core.update(once,plugin),once);
assert.equal(once.slice(once.indexOf(runtime)),base.slice(base.indexOf(runtime)));
assert.throws(()=>core.update('unrelated file',plugin));
assert.throws(()=>core.update(next.replace('return { filter: filter, streamState:', 'return { changed: filter, streamState:'),plugin));
function directory(name){
 const files=new Map(),dirs=new Map();return {name,files,dirs,
  async getDirectoryHandle(key,options){if(!dirs.has(key)){if(!options.create)throw Object.assign(new Error(),{name:'NotFoundError'});dirs.set(key,directory(key));}return dirs.get(key);},
  async getFileHandle(key,options={}){if(!files.has(key)){if(!options.create)throw Object.assign(new Error(),{name:'NotFoundError'});files.set(key,'');}
   return {async getFile(){return {async text(){return files.get(key);}};},async createWritable(){let pending;return {async write(value){pending=value;},async close(){files.set(key,pending);},async abort(){}};}};}
 };
}
(async()=>{
 const root=directory('Overrides'),payload={client:once,plugin};let result=await core.install(root,payload);
 const domain=root.dirs.get('www.starbreak.com');assert.equal(domain.files.get(core.fileName),once);assert(result.changed&&!result.backup);
 domain.files.set(core.fileName,base);result=await core.install(root,payload);assert.equal(domain.files.get(result.backup),base);
 result=await core.install(domain,payload);const stable=domain.files.get(core.fileName);result=await core.install(domain,payload);assert(!result.changed);assert.equal(domain.files.get(core.fileName),stable);
 domain.files.set(core.fileName,'unrelated');await assert.rejects(()=>core.install(root,payload));assert.equal(domain.files.get(core.fileName),'unrelated');
 console.log('PASS: new web install, bounded in-place update, unrelated settings/game body preserved, backup, direct domain-folder selection, idempotence and unsupported-file refusal.');
})().catch(e=>{console.error(e);process.exitCode=1;});
