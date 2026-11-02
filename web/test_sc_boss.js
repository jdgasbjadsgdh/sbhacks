'use strict';
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const {filter,streamState,install} = require('./sc-boss-test.js');
const frame = (type, body=[]) => new Uint8Array([type,0,0,body.length>>8,body.length&255,...body]);
const join = chunks => new Uint8Array(Buffer.concat(chunks.map(x=>Buffer.from(x))));
const sample = join([frame(15,[1,11,0,0]),frame(11),frame(14,[11,0,0,0,0]),frame(13)]);
const expected = join([frame(15,[1,11,0,0]),frame(14,[11,0,0,0,0]),frame(13)]);
for(let chunk=1;chunk<=sample.length;chunk++) {
  let state=streamState(), parts=[], removed=0;
  for(let i=0;i<sample.length;i+=chunk){const p=filter(sample.subarray(i,i+chunk),state,()=>{removed++;return true;});state=p.state;parts.push(p.bytes);}
  assert.deepEqual(join(parts),expected);assert.equal(removed,1);assert.equal(state.header.length,0);assert.equal(state.remaining,0);
}
let same=filter(sample,streamState(),()=>false);assert.deepEqual(same.bytes,sample);
// Load the actual upstream memory ABI/PluginBase/manager and virtual-socket
// sendmsg implementation. No original game, authentication or network runs.
const upstream=fs.readFileSync(__dirname+'/upstream/VR1574197275.mvmmoclient.js','utf8');
const memory=new ArrayBuffer(1<<20);const errors={EINVAL:28,ENOTCONN:53,EAGAIN:6};
const context=vm.createContext({console:{log(){},warn(){},error(e){throw new Error(String(e));}},
 HEAPU8:new Uint8Array(memory),HEAP8:new Int8Array(memory),HEAPU16:new Uint16Array(memory),HEAP16:new Int16Array(memory),
 HEAPU32:new Uint32Array(memory),HEAP32:new Int32Array(memory),HEAPF32:new Float32Array(memory),HEAPF64:new Float64Array(memory),
 performance:{now:()=>1000},window:{addEventListener(){}},document:{addEventListener(){}},TextDecoder,TextEncoder,
 FS:{ErrnoError:class extends Error{}},ERRNO_CODES:errors});
vm.runInContext(upstream.split('WebBreak.symbols=')[0],context);
const WB=context.WebBreak;WB.sbpe.config.load();WB.sbpe.refs.manager=new WB.sbpe.Manager();
const views=WB.mem;let at=4096;function obj(type){const p=at;at=(at+views.sizeOf(type)+7)&~7;return views.cast(type,p);}
function pointer(o,key,value){context.HEAPU32[o.addressOf(key)>>2]=value;}
function string(value){const p=at;at+=16;context.HEAPU8.set(Buffer.from(value),p);context.HEAPU8[p+11]=value.length;return p;}
class Element{constructor(tag){this.tagName=tag.toUpperCase();this.style={};this.children=[];}setAttribute(){}appendChild(e){e.parent=this;this.children.push(e);return e;}remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}click(){}}
const timers=[],listeners=new Map();const doc={body:new Element('body'),visibilityState:'visible',createElement:t=>new Element(t)};
const host={document:doc,setTimeout:fn=>{timers.push(fn);return timers.length;},addEventListener:(k,fn)=>listeners.set(k,fn),removeEventListener:k=>listeners.delete(k),URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},Blob};
const gc=obj('GameClient'),wc=obj('WorldClient'),cw=obj('ClientWorld'),conn=obj('ServerConnection'),own=obj('ClientSubWorld'),foreign=obj('ForeignSubWorld');
pointer(gc,'serverConnection',conn.address);pointer(gc,'worldClient',wc.address);pointer(wc,'clientWorld',cw.address);pointer(wc,'serverConnection',conn.address);
pointer(cw,'mySubWorld',own.address);pointer(cw,'serverSubWorld',foreign.address);cw.id=3;cw.props.gameid=42;conn.state=3;conn.socket=9;
const forest=string('forest'),boss=string('sc_boss'),empty=string('');pointer(cw.props,'zone',forest);pointer(cw.props,'music',empty);
WB.sbpe.refs.GameClient=gc;WB.sbpe.refs.stage=null;
const sent=[],closed=[];let failSend=false;
function peer(name){return {readyState:1,OPEN:1,CLOSING:2,CLOSED:3,CONNECTING:0,send(data){if(failSend)throw new Error('injected send failure');sent.push(new Uint8Array(data));},close(code,why){this.readyState=3;closed.push([name,code,why]);}};}
let ws=peer('first'),socket={type:1,peers:{game:{socket:ws}},daddr:'test.invalid',dport:2049};
const sockets=new Map([[9,socket]]),ops={getPeer:s=>Object.values(s.peers)[0]};
context.SOCKFS={websocket_sock_ops:ops};
const begin=upstream.indexOf('sendmsg:(function(sock,')+'sendmsg:'.length,end=upstream.indexOf('),recvmsg:',begin)+1;
ops.sendmsg=vm.runInContext(upstream.slice(begin,end),context);const original=ops.sendmsg;
const runtime={websocket_sock_ops:ops,getSocket:fd=>sockets.get(fd)};
install(WB,host,()=>runtime);const p=WB.sbpe.refs.manager._active.plugin_sc_boss_test;assert(p);assert(WB.scBossTest);
p.rushRetryEnabled=false; // Legacy suite; default-enabled retry exercised below.
const send=bytes=>ops.sendmsg(socket,bytes,0,bytes.length);
pointer(cw,'player',obj('WorldObject').address);
WB.scBossTest.arm();assert.equal(p.mode,'armed');const before=Buffer.from(memory);
send(frame(11));assert.equal(p.mode,'armed');assert.deepEqual(sent.pop(),frame(11)); // existing character/room unaffected
assert.deepEqual(Buffer.from(memory),before); // plugin never changes the game heap
pointer(cw,'player',0);pointer(cw.props,'zone',boss);send(sample);assert.equal(p.mode,'holding');assert.deepEqual(sent.pop(),expected);
// Local free camera changes only camera fields during a draw and restores the
// actual upstream heap before the next update. Network gate remains untouched.
const view=obj('WorldView');pointer(wc,'worldView',view.address);pointer(view,'world',cw.address);
view.w=800;view.h=600;view.worldBounds.x=-200;view.worldBounds.y=0;view.worldBounds.w=4000;view.worldBounds.h=3000;
view.playerBounds.w=2000;view.playerBounds.h=2000;view.offset.x=100;view.offset.y=200;
const cameraBefore=Buffer.from(memory);WB.scBossTest.freeCamera();assert(p.camera);
let prevented=0;const key=(code,extra={})=>Object.assign({code,preventDefault(){prevented++;},stopImmediatePropagation(){}},extra);
listeners.get('keydown')(key('KeyD'));p.camera.last-=100;p.beginCamera();assert(view.offset.x>100);assert.equal(view.targetPos.x,view.offset.x+400);
assert.equal(p.mode,'holding');assert.equal(sent.length,0);p.endCamera();assert.deepEqual(Buffer.from(memory),cameraBefore);
WB.scBossTest.freeCamera();assert.equal(p.camera,null);listeners.get('keyup')(key('KeyD'));assert.equal(prevented,2);
WB.scBossTest.freeCamera();p.camera.x=1e9;p.camera.y=-1e9;p.beginCamera();assert.equal(view.offset.x,3000);assert.equal(view.offset.y,0);p.endCamera();
pointer(cw,'player',obj('WorldObject').address);p.afterUpdate();assert.equal(p.camera,null);pointer(cw,'player',0);
WB.scBossTest.freeCamera();assert(p.camera);cw.id++;p.beginCamera();assert(p.camera);assert.equal(p.camera.view,null);cw.id--;
conn.state=2;p.afterUpdate();assert.equal(p.mode,'waiting');assert(p.camera);p.beginCamera();assert.equal(p.cameraSaved,null);
const recoveredView=obj('WorldView');context.HEAPU8.set(context.HEAPU8.slice(view.address,view.address+views.sizeOf('WorldView')),recoveredView.address);
recoveredView.offset.x=20;recoveredView.offset.y=30;const recoveredBefore=Buffer.from(memory);
pointer(wc,'worldView',recoveredView.address);conn.state=3;cw.id++;send(frame(11));assert.equal(p.mode,'holding');
p.camera.x=700;p.camera.y=500;p.beginCamera();assert.equal(recoveredView.offset.x,700);assert.equal(recoveredView.offset.y,500);p.endCamera();
const afterRecovery=Buffer.from(memory);const expectedRecovery=Buffer.from(recoveredBefore);
// Pointer/id changes are native fixture changes, not camera mutations.
assert.deepEqual(afterRecovery.subarray(recoveredView.address,recoveredView.address+views.sizeOf('WorldView')),expectedRecovery.subarray(recoveredView.address,recoveredView.address+views.sizeOf('WorldView')));
cw.props.seed++;cw.id++;send(frame(11));p.beginCamera();assert.equal(recoveredView.offset.x,20);assert.equal(recoveredView.offset.y,30);p.endCamera();
conn.state=2;p.afterUpdate();assert(p.camera);WB.scBossTest.freeCamera();assert.equal(p.camera,null);
conn.state=3;cw.id++;send(frame(11));p.beginCamera();assert.equal(p.camera,null);
pointer(wc,'worldView',view.address);
send(frame(11));assert.equal(sent.length,0); // duplicate old readiness remains discarded
send(frame(15,[3,4]));assert.deepEqual(sent.pop(),frame(15,[3,4])); // native time passes normally
WB.scBossTest.reconnect();WB.scBossTest.reconnect();assert.equal(p.mode,'reconnecting');assert.equal(timers.length,1);assert.equal(closed.length,0);
send(frame(11));assert.equal(sent.length,0); // old ready is not released while close is queued
timers.shift()();assert.equal(closed.length,1);
ws=peer('fresh');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);own.t=0;cw.id=4;
send(frame(11));assert.equal(p.mode,'done');assert.deepEqual(sent.pop(),frame(11));assert.equal(closed.length,1);
assert(p.events.some(e=>e.event==='fresh_world_ready'&&e.same_mission===true));
// Any map may be held. Natural losses retain the same hold indefinitely;
// fresh sockets and even different recovered rooms never authorize readiness.
pointer(cw.props,'zone',forest);cw.props.safe=1;
WB.scBossTest.arm();send(frame(11));assert.equal(p.mode,'holding');const started=p.held.started;
for(let i=0;i<4;i++){
  conn.state=2;p.afterUpdate();assert.equal(p.mode,'waiting');
  WB.scBossTest.arm();assert.equal(p.mode,'waiting');
  conn.state=3;ws=peer('natural-'+i);socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;
  send(frame(11));assert.equal(p.mode,'holding');assert.equal(sent.length,0);assert.equal(p.held.started,started);
  send(frame(15,[4,5]));assert.deepEqual(sent.pop(),frame(15,[4,5]));
}
assert.equal(timers.length,0);assert.equal(closed.length,1);
// Explicit F10 while already disconnected authorizes the next fresh load,
// without an extra close and without waiting for a world/player to exist.
ws.readyState=3;conn.state=2;p.afterUpdate();assert.equal(p.mode,'waiting');
WB.scBossTest.reconnect();assert.equal(p.mode,'reconnecting');assert.equal(timers.length,0);
conn.state=3;ws=peer('manual-after-loss');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;
send(frame(11));assert.equal(p.mode,'done');assert.deepEqual(sent.pop(),frame(11));
// A world/socket replacement before afterUpdate also remains held.
WB.scBossTest.arm();send(frame(11));assert.equal(p.mode,'holding');
ws=peer('race');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;
send(frame(11));assert.equal(p.mode,'holding');assert.equal(sent.length,0);
WB.scBossTest.reconnect();timers.shift()();
ws=peer('after-race');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;
send(frame(11));assert.equal(p.mode,'done');sent.pop();cw.props.safe=0;
// A failed send commits neither hold nor parser state; retry behaves once.
WB.scBossTest.skipBoss();pointer(cw.props,'zone',forest);cw.id++;send(frame(11));assert.equal(p.mode,'armed');sent.pop();
pointer(cw.props,'zone',boss);cw.id++;send(frame(11));assert.equal(p.mode,'holding');
WB.scBossTest.reconnect();timers.shift()();ws=peer('boss-fresh');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;send(frame(11));sent.pop();
// Rush holds earlier with no WorldClient, survives recovery, and finishes via
// asset readiness (not a reconnect). Frame boundaries and send failures matter.
WB.scBossTest.skipRush();pointer(gc,'worldClient',0);send(frame(22));assert.equal(p.held.type,22);assert.equal(p.mode,'holding');
WB.scBossTest.freeCamera();assert.equal(p.camera,null);assert(p.message.includes('no map'));
const earlyStart=p.held.started;
conn.state=2;p.afterUpdate();assert.equal(p.mode,'waiting');conn.state=3;
ws=peer('early-recovery');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);send(frame(22));assert.equal(p.mode,'holding');assert.equal(p.held.started,earlyStart);
const closedBefore=closed.length;const timeFrame=frame(15,[8,9]);send(timeFrame.subarray(0,2));
WB.scBossTest.reconnect();timers.shift()();assert.equal(p.mode,'holding');assert(p.finishPending); // cannot interleave partial header
send(timeFrame.subarray(2));assert.deepEqual(sent.pop(),timeFrame);
failSend=true;p.afterUpdate();assert.equal(p.mode,'holding');assert.equal(p.pending,false);failSend=false;
WB.scBossTest.reconnect();timers.shift()();assert.equal(p.mode,'finishing');assert.deepEqual(sent.pop(),frame(22));assert.equal(closed.length,closedBefore);
pointer(gc,'worldClient',wc.address);cw.id++;send(frame(11));assert.equal(p.mode,'done');assert.deepEqual(sent.pop(),frame(11));
// If the earlier phase is absent, the UI/event explicitly reports fallback.
WB.scBossTest.skipRush();cw.id++;send(frame(11));assert.equal(p.held.type,11);assert(p.events.some(e=>e.event==='early_phase_absent_world_fallback'));
WB.scBossTest.reconnect();timers.shift()();ws=peer('fallback-fresh');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;send(frame(11));sent.pop();
// Manual preview releases asset readiness exactly once and still blocks spawn.
WB.scBossTest.skipRush();pointer(gc,'worldClient',0);send(frame(22));
const previewCloses=closed.length;WB.scBossTest.previewRoom();timers.shift()();
assert.equal(p.mode,'preview_pending');assert.deepEqual(sent.pop(),frame(22));
WB.scBossTest.reconnect();assert.equal(timers.length,0);
pointer(gc,'worldClient',wc.address);cw.id++;send(frame(11));
assert.equal(p.mode,'holding');assert.equal(p.held.type,11);assert.equal(sent.length,0);
assert.equal(closed.length,previewCloses);assert(p.events.some(e=>e.event==='room_preview_ready'));
conn.state=2;p.afterUpdate();conn.state=3;ws=peer('preview-recovery');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);
send(frame(22));assert.deepEqual(sent.pop(),frame(22));cw.id++;send(frame(11));assert.equal(sent.length,0);
WB.scBossTest.reconnect();timers.shift()();ws=peer('preview-spawn');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;send(frame(11));sent.pop();
// Timed early hold advances only into preview; recovery never replays an old ready.
WB.scBossTest.staged();pointer(gc,'worldClient',0);send(frame(22));p.held.started-=361000;p.afterUpdate();
assert(p.finishPending);conn.state=2;timers.shift()();assert.equal(p.mode,'preview_pending');
conn.state=3;ws=peer('staged-recovery');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);
send(frame(22));sent.pop();pointer(gc,'worldClient',wc.address);cw.id++;send(frame(11));assert.equal(p.mode,'holding');assert.equal(sent.length,0);
WB.scBossTest.cancel();timers.shift()();ws=peer('after-staged');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;send(frame(11));sent.pop();
WB.scBossTest.arm();failSend=true;assert.throws(()=>send(sample));assert.equal(p.mode,'armed');failSend=false;send(sample);assert.equal(p.mode,'holding');assert.deepEqual(sent.pop(),expected);
// Cancel an active hold reconnects, rather than sending the aged readiness.
WB.scBossTest.cancel();assert.equal(p.mode,'reconnecting');timers.shift()();
ws=peer('encrypted');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);send(frame(11));sent.pop();
WB.scBossTest.arm();pointer(conn,'outRC4',obj('RC4_CTX').address);send(frame(11));assert.equal(p.mode,'idle');assert.deepEqual(sent.pop(),frame(11));pointer(conn,'outRC4',0);
// Encryption starting after a partial header preserves every consumed byte,
// including when the first flush fails and is retried.
ws=peer('partial');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);
const partial=frame(15,[7,8]);send(partial.subarray(0,2));assert.equal(sent.length,0);
pointer(conn,'outRC4',obj('RC4_CTX').address);failSend=true;
assert.throws(()=>send(partial.subarray(2)));assert.equal(p.streams.get(socket).header.length,2);
failSend=false;assert.equal(send(partial.subarray(2)),partial.length-2);assert.deepEqual(sent.pop(),partial);
assert.equal(p.streams.get(socket).header.length,0);
// Reconnect now is also available during ordinary play.
WB.scBossTest.reconnect();p.afterUpdate();assert.equal(p.mode,'reconnecting');timers.shift()();assert.equal(closed.at(-1)[0],'partial');
// A fresh encrypted connection can finish by observing its new player even
// though no plain WORLD_CREATED was available to the stream parser.
ws=peer('fresh-encrypted');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);
pointer(cw,'player',obj('WorldObject').address);p.afterUpdate();assert.equal(p.mode,'done');
assert(p.events.some(e=>e.event==='fresh_player_observed'));
assert(!JSON.stringify(WB.scBossTest.snapshot()).includes('test.invalid'));
// Default-on Rush reentry closes once after update, keeps fresh readiness held,
// and never closes newer sockets, spawned players or a manual finish instead.
assert.equal(p.rushRetryAttempted,false);p.rushRetryEnabled=true;
function retryFixture(zone='sc_boss') {
  p.mode='done';p.pending=false;p.finishPending=null;
  conn.state=3;pointer(conn,'outRC4',0);pointer(cw,'player',0);pointer(gc,'worldClient',wc.address);
  pointer(cw.props,'zone',string(zone));cw.id++;
  ws=peer('rush-retry');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);
  WB.scBossTest.skipRush();send(frame(11));assert.equal(p.held.type,11);
  const before=closed.length;p.afterUpdate();assert(p.rushRetry);assert.equal(closed.length,before);
  assert.equal(timers.length,1);return before;
}
for(const zone of ['sc_boss','forest_boss','ice_boss','cave_boss','jungle_boss','hulk_boss','dino_boss','temple_boss']){
  const n=retryFixture(zone);timers.shift()();assert.equal(closed.length,n+1);assert.equal(p.mode,'waiting');
  ws=peer('early-fresh');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);
  pointer(gc,'worldClient',0);send(frame(22));assert.equal(p.held.type,22);assert.equal(p.mode,'holding');assert.equal(sent.length,0);
  p.afterUpdate();assert.equal(timers.length,0);assert.equal(closed.length,n+1);
  WB.scBossTest.previewRoom();timers.shift()();assert.deepEqual(sent.pop(),frame(22));
  pointer(gc,'worldClient',wc.address);cw.id++;send(frame(11));p.afterUpdate();assert.equal(timers.length,0);assert.equal(p.held.type,11);
}
let n=retryFixture();timers.shift()();
ws=peer('assets-still-absent');socket={type:1,peers:{game:{socket:ws}}};sockets.set(9,socket);cw.id++;
send(frame(11));p.afterUpdate();assert.equal(timers.length,0);assert.equal(closed.length,n+1);
for(const change of ['world','socket','player','peer','cancel','finish','loss']){
  n=retryFixture();
  if(change==='world')cw.id++;
  if(change==='socket'){socket={type:1,peers:{game:{socket:peer('newer')}}};sockets.set(9,socket);}
  if(change==='player')pointer(cw,'player',obj('WorldObject').address);
  if(change==='peer')socket.peers.game.socket=peer('replacement-peer');
  if(change==='loss')ws.readyState=3;
  if(change==='cancel')WB.scBossTest.cancel();
  if(change==='finish')WB.scBossTest.reconnect();
  timers.shift()();assert.equal(closed.length,n);
  if(change==='cancel'||change==='finish'){assert.equal(timers.length,1);timers.shift()();assert.equal(closed.length,n+1);}
}
p.mode='done';pointer(cw,'player',0); // unload has no active hold to finish
WB.sbpe.refs.manager._remove('plugin_sc_boss_test');assert.equal(ops.sendmsg,original);assert.equal(doc.body.children.length,0);assert.equal(listeners.size,0);
console.log('PASS: any-boss Rush early reentry, recovered asset gate, no automatic retry loop, late preview, stale socket/world/peer/player, manual finish/cancel and natural-loss races.');
console.log('PASS: rush/boss presets, intermediate boss-room passthrough, no-world early asset hold/recovery, boundary-safe exact-once manual asset continuation, failed-send retry, explicit rush fallback; any-map outgoing stream gate across every chunk boundary; only empty readiness omitted; actual upstream virtual send, ABI/manager; existing room/time/input/acks unchanged; repeated natural losses retain hold; manual finish while disconnected; readiness-before-update race; exact-once queued manual close; no stale ready replay, send-failure rollback, encrypted-socket refusal; camera-only draw writes restore the heap; camera availability/reset, input capture and cleanup.');
