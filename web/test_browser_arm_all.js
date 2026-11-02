'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || undefined});
 try{
  const context=await browser.newContext(),isolated=await browser.newContext(),errors=[];
  async function setup(ctx,name){
   const page=await ctx.newPage();page.on('pageerror',e=>errors.push(String(e)));
   await page.route('http://sbpe-fixture.test/**',r=>r.fulfill({body:'<!doctype html><body style="background:#123"></body>',contentType:'text/html'}));
   await page.goto('http://sbpe-fixture.test/'+name);
   await page.evaluate(()=>{
    const heap=new ArrayBuffer(1<<20);
    for(const [n,T] of Object.entries({HEAPU8:Uint8Array,HEAP8:Int8Array,HEAPU16:Uint16Array,HEAP16:Int16Array,HEAPU32:Uint32Array,HEAP32:Int32Array,HEAPF32:Float32Array,HEAPF64:Float64Array}))window[n]=new T(heap);
   });
   await page.addScriptTag({content:fs.readFileSync(__dirname+'/upstream/VR1574197275.mvmmoclient.js','utf8').split('WebBreak.symbols=')[0]});
   await page.evaluate(()=>{
    const WB=WebBreak;WB.sbpe.config.load();WB.sbpe.refs.manager=new WB.sbpe.Manager();WB.sbpe.refs.stage=null;
    let at=4096;const obj=t=>{const p=at;at=(at+WB.mem.sizeOf(t)+7)&~7;return WB.mem.cast(t,p);};
    const ptr=(o,k,v)=>HEAPU32[o.addressOf(k)>>2]=v;
    const gc=obj('GameClient'),wc=obj('WorldClient'),cw=obj('ClientWorld'),conn=obj('ServerConnection');
    ptr(gc,'serverConnection',conn.address);ptr(gc,'worldClient',wc.address);ptr(wc,'clientWorld',cw.address);
    const zone=at;at+=16;HEAPU8.set(new TextEncoder().encode('sc_boss'),zone);HEAPU8[zone+11]=7;ptr(cw.props,'zone',zone);
    cw.id=3;cw.props.gameid=42;conn.state=3;conn.socket=9;WB.sbpe.refs.GameClient=gc;
    const ws={readyState:1,close(){this.readyState=3;}},socket={type:1,peers:{game:{socket:ws}}};
    window.SOCKFS={getSocket:()=>socket,websocket_sock_ops:{sendmsg(s,b,o,n){return n;}}};
    window.fixture={ready(){SOCKFS.websocket_sock_ops.sendmsg(socket,new Uint8Array([11,0,0,0,0]),0,5);}};
   });
   await page.addScriptTag({path:__dirname+'/sc-boss-test.js'});
   return page;
  }
  const a=await setup(context,'a'),b=await setup(context,'b'),c=await setup(context,'c'),d=await setup(isolated,'isolated');
  await b.evaluate(()=>WebBreak.scBossTest.hideUI());
  const state=page=>page.evaluate(()=>({mode:WebBreak.scBossTest.snapshot().mode,preset:WebBreak.scBossTest.snapshot().preset}));
  await a.getByRole('button',{name:'Rush hold',exact:true}).click();assert.equal((await state(b)).mode,'idle');
  await a.getByRole('checkbox',{name:'Arm all connected web tabs'}).check();
  await a.getByRole('button',{name:'Boss hold',exact:true}).click();
  await b.waitForFunction(()=>WebBreak.scBossTest.snapshot().mode==='armed');
  await c.waitForFunction(()=>WebBreak.scBossTest.snapshot().mode==='armed');
  for(const page of [a,b,c])assert.equal((await state(page)).preset,'boss');
  assert(await b.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;return p.uiHidden&&p.panel.style.display==='none'&&p.tab.style.display==='none';}));
  assert.equal((await state(d)).mode,'idle');
  await c.evaluate(()=>fixture.ready());assert.equal((await state(c)).mode,'holding');
  await a.getByRole('button',{name:'Timed: 360s',exact:true}).click();
  await b.waitForFunction(()=>WebBreak.scBossTest.snapshot().preset==='staged');
  assert.equal((await state(c)).mode,'holding');assert.equal((await state(c)).preset,'boss');
  await a.waitForFunction(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.groupStatus==='Arm all: 2 armed, 1 skipped.');
  const count=await b.evaluate(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.events.filter(e=>e.event==='armed').length);
  await a.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;p.armChannel.postMessage({version:1,kind:'arm',request:p.groupRequest,sender:p.groupId,preset:'staged'});});
  await b.waitForTimeout(50);
  assert.equal(await b.evaluate(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.events.filter(e=>e.event==='armed').length),count);
  await a.getByRole('checkbox',{name:'Arm all connected web tabs'}).uncheck();
  await a.keyboard.press('F9');assert.equal((await state(a)).mode,'idle');assert.equal((await state(b)).mode,'armed');
  assert.deepEqual(errors,[]);
  console.log('PASS: real Chromium BroadcastChannel between three same-profile tabs; opt-in checkbox, Rush/Boss/Timed arming, exact-once commands, active hold retained, unchecked local controls, keyboard after checkbox focus, separate browser profile isolated. No real game/server accessed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
