'use strict';
// An isolated headless page using the actual WebBreak ABI/manager and real DOM.
// This never opens, reloads or connects to the user's StarBreak browser.
const fs = require('node:fs'), assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const browser = await chromium.launch({headless: true,
    executablePath: process.env.CHROME_PATH || undefined});
  try {
    const page = await browser.newPage({viewport: {width: 1280, height: 900}}), errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    await page.setContent('<!doctype html><title>Isolated SBPE SC fixture</title><body style="background:#123"></body>');
    await page.evaluate(() => {
      const heap = new ArrayBuffer(1<<20);
      for (const [name, Type] of Object.entries({HEAPU8:Uint8Array,HEAP8:Int8Array,HEAPU16:Uint16Array,HEAP16:Int16Array,
        HEAPU32:Uint32Array,HEAP32:Int32Array,HEAPF32:Float32Array,HEAPF64:Float64Array})) window[name] = new Type(heap);
    });
    const upstream = fs.readFileSync(__dirname+'/upstream/VR1574197275.mvmmoclient.js','utf8');
    await page.addScriptTag({content: upstream.split('WebBreak.symbols=')[0]});
    await page.evaluate(() => {
      const WB=window.WebBreak;WB.sbpe.config.load();WB.sbpe.refs.manager=new WB.sbpe.Manager();WB.sbpe.refs.stage=null;
      let at=4096;const obj=type=>{const p=at;at=(at+WB.mem.sizeOf(type)+7)&~7;return WB.mem.cast(type,p);};
      const pointer=(o,key,p)=>{HEAPU32[o.addressOf(key)>>2]=p;};
      const str=value=>{const p=at;at+=16;HEAPU8.set(new TextEncoder().encode(value),p);HEAPU8[p+11]=value.length;return p;};
      const gc=obj('GameClient'),wc=obj('WorldClient'),cw=obj('ClientWorld'),conn=obj('ServerConnection'),view=obj('WorldView');
      pointer(gc,'serverConnection',conn.address);pointer(gc,'worldClient',wc.address);pointer(wc,'clientWorld',cw.address);
      pointer(wc,'worldView',view.address);pointer(view,'world',cw.address);view.w=800;view.h=600;view.worldBounds.w=4000;view.worldBounds.h=3000;view.playerBounds.w=4000;view.playerBounds.h=3000;
      pointer(cw.props,'zone',str('sc_boss'));pointer(cw.props,'music',str(''));cw.id=3;cw.props.gameid=42;conn.state=3;conn.socket=9;
      WB.sbpe.refs.GameClient=gc;window.sent=[];window.fixtureCloseCount=0;
      const ws={readyState:1,close(){this.readyState=3;window.fixtureCloseCount++;}};
      const socket={type:1,peers:{game:{socket:ws}}};
      window.SOCKFS={getSocket:()=>socket,websocket_sock_ops:{sendmsg(s,b,o,n){window.sent.push(Array.from(new Uint8Array(b.buffer,b.byteOffset+o,n)));return n;}}};
      window.fixture={gc,wc,cw,conn,view,socket,ws,ready(){SOCKFS.websocket_sock_ops.sendmsg(socket,new Uint8Array([11,0,0,0,0]),0,5);},assetReady(){SOCKFS.websocket_sock_ops.sendmsg(socket,new Uint8Array([22,0,0,0,0]),0,5);}};
    });
    await page.addScriptTag({path: __dirname+'/sc-boss-test.js'});
    assert.equal(await page.getByText('SBPE spawn timing observer',{exact:true}).count(),0);
    const panel=page.getByRole('region',{name:'SBPE loading test'});
    assert(await panel.getByText('Warning: Boss hold and Preview room kick after about 10 seconds.', {exact:true}).isVisible());
    await panel.getByRole('button',{name:'Boss hold',exact:true}).click();
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'armed');
    await page.evaluate(()=>fixture.ready());
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'holding');
    assert.equal(await page.evaluate(()=>sent.length),0);
    await panel.getByRole('button',{name:'Free camera',exact:true}).click();
    await page.keyboard.down('ArrowRight');
    assert(await page.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;p.camera.last-=100;p.beginCamera();const moved=fixture.view.offset.x>0;p.endCamera();return moved&&fixture.view.offset.x===0;}));
    await panel.getByRole('button',{name:'Free camera: ON',exact:true}).click();await page.keyboard.up('ArrowRight');
    await panel.getByRole('button',{name:'Close panel',exact:true}).click();
    assert.equal(await panel.isVisible(),false);
    await page.getByRole('button',{name:'Loading controls:',exact:false}).click();assert.equal(await panel.isVisible(),true);
    await page.keyboard.press('F8');assert.equal(await panel.isVisible(),false);
    await page.keyboard.press('F8');assert.equal(await panel.isVisible(),true);
    await panel.getByRole('button',{name:'Free camera',exact:true}).click();
    await page.evaluate(()=>{WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.camera.x=600;});
    const beforeHide=await page.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;return [p.mode,p.held.type,p.camera.x,sent.length,fixtureCloseCount];});
    const covered=await panel.boundingBox();
    await page.evaluate(()=>{
      window.gameClicks=0;const game=document.createElement('button');game.setAttribute('aria-label','Game click fixture');
      game.style.cssText='position:fixed;inset:0;width:100%;height:100%;background:transparent;border:0;z-index:0';
      game.onclick=()=>window.gameClicks++;document.body.prepend(game);
    });
    await panel.getByRole('button',{name:'Hide all UI',exact:true}).click();
    assert.equal(await panel.isVisible(),false);
    assert.equal(await page.getByRole('button',{name:'Loading controls:',exact:false,includeHidden:true}).isVisible(),false);
    await page.mouse.click(covered.x+20,covered.y+20);assert.equal(await page.evaluate(()=>gameClicks),1);
    assert.deepEqual(await page.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;return [p.mode,p.held.type,p.camera.x,sent.length,fixtureCloseCount];}),beforeHide);
    await page.keyboard.down('ArrowRight');
    assert(await page.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;p.camera.last-=100;p.beginCamera();const moved=fixture.view.offset.x>600;p.endCamera();p.camera.x=600;return moved;}));
    await page.keyboard.up('ArrowRight');
    await page.evaluate(()=>{fixture.conn.state=2;WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.afterUpdate();});
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'waiting');
    assert.equal(await page.evaluate(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.cameraButton.disabled),false);
    await page.evaluate(()=>{fixture.conn.state=3;fixture.cw.id++;fixture.ready();});
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'holding');
    assert(await page.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;p.beginCamera();const kept=!!p.camera&&fixture.view.offset.x===600;p.endCamera();p.updateUI();return kept&&fixture.view.offset.x===0;}));
    assert.equal(await page.evaluate(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.cameraButton.textContent),'Free camera: ON');
    assert.equal(await page.evaluate(()=>sent.length),0);
    assert.equal(await panel.isVisible(),false); // recovery/updateUI does not unhide it
    await page.keyboard.press('Control+F8');assert.equal(await panel.isVisible(),false);
    await page.evaluate(()=>{WebBreak.sbpe.refs.stage={textInputTarget:1};});
    await page.keyboard.press('F8');assert.equal(await panel.isVisible(),false);
    await page.evaluate(()=>{WebBreak.sbpe.refs.stage=null;window.dispatchEvent(new KeyboardEvent('keydown',{code:'F8',repeat:true}));window.dispatchEvent(new KeyboardEvent('keyup',{code:'F8'}));});
    assert.equal(await panel.isVisible(),false);
    await page.keyboard.press('F8');assert.equal(await panel.isVisible(),true);
    if(process.argv[2])await page.screenshot({path:process.argv[2]});
    await panel.getByRole('button',{name:'Hide all UI',exact:true}).click();
    await page.keyboard.press('F10'); // finish remains available with all UI hidden
    await page.waitForFunction(()=>fixtureCloseCount===1);
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'reconnecting');
    await page.evaluate(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.afterUpdate());
    assert.equal(await page.evaluate(()=>WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test.camera),null);
    await page.evaluate(()=>{const p=WebBreak.sbpe.refs.manager._active.plugin_sc_boss_test;p.mode='idle';p.held=null;});
    await page.keyboard.press('F9');
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'armed');
    assert.equal(await panel.isVisible(),false);
    await page.keyboard.press('F8');assert.equal(await panel.isVisible(),true);
    await page.keyboard.press('F10');
    assert.equal(await page.evaluate(()=>fixtureCloseCount),1); // closed connection cannot be closed twice
    await panel.getByRole('button',{name:'Cancel hold',exact:true}).click();
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'idle');
    await page.evaluate(()=>{fixture.ws.readyState=1;sent.length=0;});
    await panel.getByRole('button',{name:'Rush hold',exact:true}).click();
    await page.evaluate(()=>{HEAPU32[fixture.gc.addressOf('worldClient')>>2]=0;fixture.assetReady();});
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'holding');
    await panel.getByRole('button',{name:'Finish loading',exact:true}).click();
    await page.waitForFunction(()=>WebBreak.scBossTest.snapshot().mode==='finishing');
    assert.deepEqual(await page.evaluate(()=>sent),[[22,0,0,0,0]]);
    assert.equal(await page.evaluate(()=>fixtureCloseCount),1);
    await page.evaluate(()=>{HEAPU32[fixture.gc.addressOf('worldClient')>>2]=fixture.wc.address;fixture.ready();});
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'done');
    await panel.getByRole('button',{name:'Rush hold',exact:true}).click();
    await page.evaluate(()=>{HEAPU32[fixture.gc.addressOf('worldClient')>>2]=0;fixture.assetReady();});
    await panel.getByRole('button',{name:'Preview room',exact:true}).click();
    await page.waitForFunction(()=>WebBreak.scBossTest.snapshot().mode==='preview_pending');
    assert.equal(await panel.getByRole('button',{name:'Waiting for map',exact:true}).isDisabled(),true);
    await page.evaluate(()=>{HEAPU32[fixture.gc.addressOf('worldClient')>>2]=fixture.wc.address;fixture.cw.id++;fixture.ready();});
    assert.equal(await page.evaluate(()=>WebBreak.scBossTest.snapshot().mode),'holding');
    assert.equal(await page.evaluate(()=>fixtureCloseCount),1);
    assert.equal(await panel.getByText('Room: not sent by server yet',{exact:true}).count(),0);
    if(process.argv[2])await page.screenshot({path:process.argv[2]});
    const downloadEvent=page.waitForEvent('download');
    await panel.getByRole('button',{name:'Save log',exact:true}).click();
    assert((await downloadEvent).suggestedFilename().startsWith('sbpe-web-sc-test-'));
    assert.equal(await page.locator('input:not([type="checkbox"])').count(),0);
    assert.equal(await page.getByRole('checkbox',{name:'Arm all connected web tabs'}).count(),1);
    const box=await panel.boundingBox();assert(box.x>=0&&box.y>=0&&box.x+box.width<=1280&&box.y+box.height<=900);
    await page.setViewportSize({width:400,height:480});
    const smallBox=await panel.boundingBox();assert(smallBox.x>=0&&smallBox.y>=0&&smallBox.x+smallBox.width<=400&&smallBox.y+smallBox.height<=480);
    const hideBox=await panel.getByRole('button',{name:'Hide all UI',exact:true}).boundingBox();
    assert(hideBox.x>=smallBox.x&&hideBox.x+hideBox.width<=smallBox.x+smallBox.width);
    await panel.getByRole('button',{name:'Close panel',exact:true}).click();assert.equal(await panel.isVisible(),false);
    await page.getByRole('button',{name:'Loading controls:',exact:false}).click();assert.equal(await panel.isVisible(),true);
    await page.evaluate(()=>{WebBreak.sbpe.refs.manager._remove('plugin_sc_boss_test');});
    assert.equal(await page.locator('section').count(),0);assert.deepEqual(errors,[]);
    console.log('PASS: real Chromium with actual WebBreak ABI/manager; full UI/tab hiding, game click passthrough, unchanged hold/transport, hidden freecam and recovery, F8 chat/modifier/repeat guards and restore, F9/F10 while hidden; normal collapse/tab, JSON download, small-screen header/layout and unload. No user browser/game touched.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
