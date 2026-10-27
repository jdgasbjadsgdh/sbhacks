/* Local WebBreak override update; no browser reload or network access. */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SBPELoadingInstaller = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var fileName = 'VR1574197275.mvmmoclient.js';
  var runtime = '/* WebBreak runtime                                                           */';
  var start = '/* Manual any-map loading test for pinned WebBreak build 1574197275.';
  var end = 'return { filter: filter, streamState: streamState, isBoss: isBoss, install: install };\n});';
  function update(text, plugin) {
    if (!text.startsWith('/*@WebBreak-patched*/') || !text.includes('client build 1574197275') || text.split(runtime).length !== 2)
      throw new Error('Choose a WebBreak 1574197275 override. This file was not changed.');
    var first = text.indexOf(start);
    if (first < 0) return text.replace(runtime, plugin+'\n\n'+runtime);
    if (text.indexOf(start, first+1) >= 0) throw new Error('Multiple loading plugins found. No changes made.');
    var last = text.indexOf(end, first);
    if (last < 0 || last > text.indexOf(runtime)) throw new Error('Unrecognized loading plugin. No changes made.');
    return text.slice(0, first)+plugin.trimEnd()+text.slice(last+end.length);
  }
  async function install(directory, payload) {
    var domain = directory.name === 'www.starbreak.com' ? directory : await directory.getDirectoryHandle('www.starbreak.com', {create:true});
    var existing = null;
    try { existing = await domain.getFileHandle(fileName); }
    catch (e) { if (e.name !== 'NotFoundError') throw e; }
    var previous = existing ? await (await existing.getFile()).text() : null;
    var next = previous === null ? payload.client : update(previous, payload.plugin);
    if (next === previous) return {changed:false, file:fileName};
    var backup = null;
    if (previous !== null) {
      backup = fileName+'.sbpe-backup-'+new Date().toISOString().replace(/[:.]/g,'-');
      var backupFile = await domain.getFileHandle(backup, {create:true}), saved = await backupFile.createWritable();
      await saved.write(previous); await saved.close();
    }
    var target = existing || await domain.getFileHandle(fileName, {create:true});
    var writer = await target.createWritable();
    try { await writer.write(next); await writer.close(); }
    catch (e) { await writer.abort().catch(function () {}); throw e; }
    return {changed:true, file:fileName, backup:backup};
  }
  return {update:update, install:install, fileName:fileName};
});
