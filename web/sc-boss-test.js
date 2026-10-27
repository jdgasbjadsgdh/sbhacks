/* Manual any-map loading test for pinned WebBreak build 1574197275.
 * Withholds only selected unencrypted empty readiness messages. All other
 * outgoing bytes pass unchanged. A held acknowledgment is never replayed:
 * Early rush finishes asset readiness; world-ready holds use native reconnect.
 */
(function (root, factory) {
  'use strict'; var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else if (root.WebBreak && root.WebBreak.sbpe) api.install(root.WebBreak, root);
  else if (Array.isArray(root.WebBreakPlugins)) root.WebBreakPlugins.push(function () { api.install(root.WebBreak, root); });
  else throw new Error('Use the combined WebBreak client.');
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function streamState() { return { header: [], remaining: 0, disabled: false }; }
  function bytesOf(buffer, offset, length) {
    if (ArrayBuffer.isView(buffer)) return new Uint8Array(buffer.buffer, buffer.byteOffset + offset, length);
    return new Uint8Array(buffer, offset, length);
  }
  function join(pieces) {
    var size = pieces.reduce(function (n, p) { return n + p.length; }, 0), out = new Uint8Array(size), at = 0;
    pieces.forEach(function (p) { out.set(p, at); at += p.length; }); return out;
  }
  // Transactional plan: failed native sends never commit parser/hold state.
  // Payloads are forwarded in slices; at most four header bytes are retained.
  function filter(input, previous, dropReady) {
    var next = { header: previous.header.slice(), remaining: previous.remaining, disabled: previous.disabled }, pieces = [], at = 0;
    while (at < input.length) {
      if (next.remaining) {
        var take = Math.min(next.remaining, input.length-at); pieces.push(input.subarray(at, at+take)); at += take; next.remaining -= take; continue;
      }
      while (next.header.length < 5 && at < input.length) next.header.push(input[at++]);
      if (next.header.length < 5) break;
      var h = next.header, type = h[0], length = ((h[1]*16777216)+(h[2]<<16)+(h[3]<<8)+h[4]) >>> 0;
      if (!type || type > 46 || length > 16777216) throw new Error('Outgoing framing unavailable; hold disabled on this connection.');
      if (!((type === 11 || type === 22) && length === 0 && dropReady(type))) pieces.push(new Uint8Array(h));
      next.remaining = length; next.header = [];
    }
    return { state: next, bytes: join(pieces) };
  }
  function isBoss(c) { return !!c && (c.zone.indexOf('_boss') >= 0 || c.music.indexOf('_boss') >= 0); }
  function install(WB, host, runtimeProvider) {
    if (WB.build !== '1574197275') throw new Error('Unsupported WebBreak build.');
    var sbpe = WB.sbpe, mem = WB.mem, util = sbpe.util, doc = host.document;
    var runtime = runtimeProvider || function () { return typeof SOCKFS !== 'undefined' ? SOCKFS : host.SOCKFS; };
    class Plugin extends sbpe.PluginBase {
      onInit() {
        var self = this; this.mode = 'idle'; this.preset = 'any'; this.held = null; this.reconnectSocket = null; this.pending = false; this.unloaded = false; this.finishPending = null;
        this.started = Date.now(); this.events = []; this.streams = new WeakMap(); this.lastSample = 0; this.lastUI = 0;
        this.previewRequested = false; this.fallback = false; this.earlySeconds = 360;
        this.camera = null; this.cameraSaved = null; this.cameraKeys = new Set(); this.cameraDown = new Set();
        this.message = 'Arm for the next map (including SC boss). A disconnect keeps the test held until you finish.';
        this.api = { arm: function () { self.arm(); }, reconnect: function () { self.requestReconnect('manual'); },
          skipRush: function () { self.arm('rush'); }, skipBoss: function () { self.arm('boss'); },
          previewRoom: function () { self.previewRoom(); }, staged: function () { self.arm('staged'); },
          cancel: function () { self.cancel(); }, save: function () { self.save(); }, snapshot: function () { return self.snapshot(); },
          togglePanel: function () { self.togglePanel(); }, hideUI: function () { self.hideUI(); }, freeCamera: function () { self.toggleCamera(); } };
        this.api.armAllRush = function () { self.armAll('rush'); };
        this.api.armAllBoss = function () { self.armAll('boss'); };
        this.initArmGroup();
        WB.scBossTest = this.api; this.makePanel(); this.attachTransport();
        this.key = function (e) {
          var wasDown = self.cameraDown.has(e.code); self.cameraDown.add(e.code);
          if (self.cameraKeys.has(e.code)) { e.preventDefault(); e.stopImmediatePropagation(); return; }
          if (!wasDown && self.camera && self.cameraAvailable(self.current()) && self.cameraInputAllowed(e) && /^(Key[WASD]|Arrow(Left|Right|Up|Down))$/.test(e.code)) {
            self.cameraKeys.add(e.code); e.preventDefault(); e.stopImmediatePropagation(); return;
          }
          if (e.repeat || e.ctrlKey || e.metaKey || e.altKey || (self.refs.stage && self.refs.stage.textInputTarget)) return;
          var tag = e.target && e.target.tagName; if (tag && (/^(TEXTAREA|SELECT)$/.test(tag) || tag==='INPUT' && e.target.type!=='checkbox')) return;
          if (e.code === 'F8' || e.code === 'F9' || e.code === 'F10') {
            e.preventDefault(); e.stopImmediatePropagation();
            if (e.code === 'F8') self.togglePanel();
            else if (e.code === 'F9') { if (self.mode === 'armed') self.cancel(); else self.arm(self.preset); }
            else self.requestReconnect('F10');
          }
        };
        this.keyUp = function (e) { self.cameraDown.delete(e.code); if (self.cameraKeys.delete(e.code)) { e.preventDefault(); e.stopImmediatePropagation(); } };
        this.blur = function () { self.cameraKeys.clear(); self.cameraDown.clear(); };
        this.cameraHooks = [WB.hook('XDL_Clear', function (orig, color) { var result = orig(color); self.beginCamera(); return result; }),
          WB.hook('XDL_Present', function (orig) { try { return orig(); } finally { self.endCamera(); } })];
        host.addEventListener('keydown', this.key, true); host.addEventListener('keyup', this.keyUp, true); host.addEventListener('blur', this.blur);
        this.record('plugin_ready'); this.updateUI();
      }
      initArmGroup() {
        var self=this; this.groupId=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
        this.groupSeen=[];this.applyToAll=false;this.groupStatus='Arm all: other web tabs in this browser profile.';
        if (typeof host.BroadcastChannel !== 'function') { this.groupStatus='Arm all unavailable in this browser.'; return; }
        try {
          this.armChannel=new host.BroadcastChannel('sbpe-loading-arm-v1');
          this.armChannel.onmessage=function(event) {
            var d=event.data;
            if (!d || d.version!==1 || d.sender===self.groupId || typeof d.request!=='string' || d.request.length>96) return;
            if (d.kind==='arm' && ['any','rush','boss','staged'].indexOf(d.preset)>=0) {
              if (self.groupSeen.indexOf(d.request)>=0) return;
              self.groupSeen.push(d.request);if(self.groupSeen.length>64)self.groupSeen.shift();
              self.arm(d.preset,true);
              self.armChannel.postMessage({version:1,kind:'ack',request:d.request,sender:self.groupId,
                accepted:self.mode==='armed'&&self.preset===d.preset});
            } else if (d.kind==='ack' && self.groupRequest===d.request) {
              if (self.groupReplies.indexOf(d.sender)>=0)return;
              self.groupReplies.push(d.sender);if(d.accepted)self.groupAccepted++;else self.groupSkipped++;
              self.groupStatus='Arm all: '+self.groupAccepted+' armed, '+self.groupSkipped+' skipped.';self.updateUI();
            }
          };
        } catch(e) {this.armChannel=null;this.groupStatus='Arm all unavailable: '+String(e);}
      }
      armAll(preset) {
        if(['any','rush','boss','staged'].indexOf(preset)<0)return;
        this.groupRequest=this.groupId+'-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
        this.groupReplies=[];this.arm(preset,true);
        this.groupAccepted=this.mode==='armed'&&this.preset===preset?1:0;this.groupSkipped=this.groupAccepted?0:1;
        this.groupStatus='Arm all: '+this.groupAccepted+' armed locally; waiting for web tabs.';
        if(this.armChannel)this.armChannel.postMessage({version:1,kind:'arm',request:this.groupRequest,sender:this.groupId,preset:preset});
        else this.groupStatus='Armed locally; cross-tab channel unavailable.';
        this.record('arm_all_requested',{preset:preset});this.updateUI();
      }
      current() {
        // Read fresh pointers through the persistent GameClient, rather than
        // using ClientWorld refs cached before a CreateWorld callback.
        var gc = this.refs.GameClient;
        if (this.refs.stage) {
          var top = mem.vec2list(this.refs.stage.children)[0];
          gc = top && mem.className(top) === 'GameClient' ? mem.cast('GameClient', top) : null;
        }
        if (!gc) return null;
        var connection = gc.serverConnection, wc = gc.worldClient, cw = wc && wc.clientWorld, rt = runtime();
        if (!connection || !rt) return null;
        var socket = rt.getSocket(connection.socket), zone = cw ? util.getstr(cw.props.zone) : '', music = cw ? util.getstr(cw.props.music) : '';
        return { connection: connection, socket: socket, game: cw ? cw.props.gameid : null, world: cw ? cw.id : null,
          key: cw ? [cw.address, cw.props.gameid, cw.id, zone, music].join('/') : '', zone: zone, music: music,
          safe: cw ? !!cw.props.safe : true, player: !!(cw && cw.player), own: cw && cw.mySubWorld ? cw.mySubWorld.t : null,
          received: cw && cw.serverSubWorld ? cw.serverSubWorld.maxT : null, cw: cw, gc: gc, view: wc && wc.worldView,
          floor: cw ? cw.props.floor : null, zoneid: cw ? cw.props.zoneid : null, seed: cw ? cw.props.seed : null };
      }
      record(event, extra) {
        if (this.events.length >= 2000) this.events.shift();
        this.events.push(Object.assign({ event: event, epoch_ms: Date.now(), mode: this.mode, visibility: doc.visibilityState }, extra || {}));
      }
      identity(c) { return c ? { game: c.game, world: c.world, zone: c.zone, music: c.music, floor: c.floor, zoneid: c.zoneid, seed: c.seed, local_player: c.player, own_t: c.own, received_t: c.received } : null; }
      cameraAvailable(c) {
        return !!(this.mode === 'holding' && this.held && this.held.type === 11 && c && c.key === this.held.key && c.socket === this.held.socket && c.connection.state === 3 && !c.player && c.view && c.view.worldBounds.w > 0 && c.view.worldBounds.h > 0);
      }
      cameraRoom(c) { return [c.game,c.zone,c.music,c.floor,c.zoneid,c.seed].join('/'); }
      syncCamera(c) {
        var camera=this.camera;if(!camera)return false;
        if((this.mode!=='holding'&&this.mode!=='waiting')||!this.held||camera.holdStarted!==this.held.started||
           c&&c.key===this.held.key&&c.socket===this.held.socket&&c.connection.state===3&&c.player){this.camera=null;return false;}
        if(!this.cameraAvailable(c)){camera.view=null;camera.last=Date.now();return false;}
        if(camera.key!==c.key||camera.view!==c.view.address){
          var room=this.cameraRoom(c);
          if(camera.room!==room){camera.x=c.view.offset.x;camera.y=c.view.offset.y;}
          camera.key=c.key;camera.view=c.view.address;camera.room=room;camera.last=Date.now();
        }return true;
      }
      cameraInputAllowed(e) {
        var tag = e && e.target && e.target.tagName;
        return !(e && (e.ctrlKey || e.metaKey || e.altKey)) && !(tag && /^(INPUT|TEXTAREA|SELECT)$/.test(tag)) &&
          !(this.refs.stage && this.refs.stage.textInputTarget) && !(doc.activeElement && doc.activeElement.isContentEditable);
      }
      toggleCamera() {
        if (this.camera) { this.camera = null; this.record('free_camera_off'); }
        else {
          var c = this.current();
          if (!this.cameraAvailable(c)) { this.message = 'Free camera needs a loaded map with spawn held. The early rush hold has no map yet.'; this.updateUI(); return; }
          this.camera = { key: c.key, view: c.view.address, room: this.cameraRoom(c), holdStarted: this.held.started,
            x: c.view.offset.x, y: c.view.offset.y, last: Date.now() };
          this.record('free_camera_on');
        }
        this.updateUI();
      }
      beginCamera() {
        if (this.cameraSaved) this.endCamera();
        var camera = this.camera, c = this.current(); if (!camera) return;
        if (!this.syncCamera(c)) return;
        var v = c.view, now = Date.now(), dt = Math.max(0, Math.min(.1, (now-camera.last)/1000)); camera.last = now;
        var keys = this.cameraKeys, dx = +(keys.has('KeyD') || keys.has('ArrowRight'))-+(keys.has('KeyA') || keys.has('ArrowLeft')),
          dy = +(keys.has('KeyS') || keys.has('ArrowDown'))-+(keys.has('KeyW') || keys.has('ArrowUp'));
        var speed = 900 * (this.cameraDown.has('ShiftLeft') || this.cameraDown.has('ShiftRight') ? 3 : 1) / (dx && dy ? Math.sqrt(2) : 1);
        if (this.cameraInputAllowed()) { camera.x += dx*speed*dt; camera.y += dy*speed*dt; }
        function axis(n, start, size, view) { return size <= view ? start+(size-view)/2 : Math.max(start, Math.min(start+size-view, n)); }
        camera.x = axis(camera.x, v.worldBounds.x, v.worldBounds.w, v.w); camera.y = axis(camera.y, v.worldBounds.y, v.worldBounds.h, v.h);
        var saved = this.cameraSaved = { key: c.key, address: v.address, initialized: v.offsetsInitialized };
        ['offset','currOffset','goalOffset','targetPos','playerBounds'].forEach(function (name) {
          saved[name] = {}; ['x','y'].concat(name === 'playerBounds' ? ['w','h'] : []).forEach(function (field) { saved[name][field] = v[name][field]; });
        });
        ['x','y','w','h'].forEach(function (field) { v.playerBounds[field] = v.worldBounds[field]; });
        ['offset','currOffset','goalOffset'].forEach(function (name) { v[name].x = Math.round(camera.x); v[name].y = Math.round(camera.y); });
        v.targetPos.x = v.offset.x+Math.trunc(v.w/2); v.targetPos.y = v.offset.y+Math.trunc(v.h/2); v.offsetsInitialized = true;
      }
      endCamera() {
        var saved = this.cameraSaved; this.cameraSaved = null; if (!saved) return;
        var c = this.current(); if (!c || c.key !== saved.key || !c.view || c.view.address !== saved.address) { this.syncCamera(c); return; }
        var v = c.view; Object.keys(saved).forEach(function (name) {
          if (saved[name] && typeof saved[name] === 'object') Object.keys(saved[name]).forEach(function (field) { v[name][field] = saved[name][field]; });
        }); v.offsetsInitialized = saved.initialized;
      }
      arm(preset, local) {
        if(this.applyToAll&&!local){this.armAll(preset||this.preset);return;}
        if (this.mode === 'holding' || this.mode === 'waiting' || this.mode === 'finishing' || this.mode === 'preview_pending' || this.pending || this.mode === 'reconnecting') { this.message = 'Finish this test before arming again.'; this.updateUI(); return; }
        if (!this.attachTransport()) { this.message = 'Game socket runtime is unavailable; hold not armed.'; this.updateUI(); return; }
        var c = this.current();
        if (!c || !c.cw || c.connection.state !== 3 || !c.socket) { this.message = 'Enter a connected game before arming.'; this.updateUI(); return; }
        this.mode = 'armed'; this.preset = preset || 'any'; this.held = null; this.reconnectSocket = null; this.started = Date.now(); this.events = [];
        this.previewRequested = false; this.fallback = false;
        this.message = this.preset === 'rush' ? 'Skip rush armed: wait before map creation where possible. Catch-up is experimental.' : this.preset === 'boss' ? 'Skip boss armed: intermediate rooms pass; the next boss room will be held.' : 'Armed for the next map. F9 cancels the unused arm.';
        this.record('armed', { preset: this.preset, origin: this.identity(c) }); this.updateUI();
      }
      cancel() {
        if (this.mode === 'preview_pending') { this.mode = 'finishing'; this.previewRequested = false; this.message = 'Preview canceled; next map loads normally.'; this.record('preview_canceled'); this.updateUI(); return; }
        if (this.preset === 'staged' && (this.mode === 'holding' || this.mode === 'waiting')) this.preset = 'any';
        if (this.mode === 'holding' || this.mode === 'waiting') { this.requestReconnect('cancel_hold'); return; }
        if (this.pending || this.mode === 'reconnecting') return;
        this.mode = 'idle'; this.message = 'Arm canceled.'; this.record('canceled'); this.updateUI();
      }
      attachTransport() {
        if (this.ops) return true; var rt = runtime(); if (!rt || !rt.websocket_sock_ops || typeof rt.websocket_sock_ops.sendmsg !== 'function') return false;
        var self = this; this.ops = rt.websocket_sock_ops; this.originalSend = this.ops.sendmsg;
        this.send = function (socket, buffer, offset, length, address, port) {
          if (self.unloaded) return self.originalSend.apply(this, arguments);
          var c; try { c = self.current(); } catch (e) { return self.originalSend.apply(this, arguments); }
          if (!c || c.socket !== socket || socket.type !== 1) return self.originalSend.apply(this, arguments);
          if (c.connection.outRC4) {
            // Preserve already consumed bytes if encryption begins while a
            // partial plain header is buffered. Commit only after send succeeds.
            var prior = self.streams.get(socket), buffered = prior && prior.header.length;
            var encryptedResult;
            if (buffered) {
              var complete = join([new Uint8Array(prior.header), bytesOf(buffer, offset, length)]);
              encryptedResult = self.originalSend.call(this, socket, complete, 0, complete.length, address, port);
              if (encryptedResult !== complete.length) throw new Error('Unexpected partial virtual-socket send.');
            } else encryptedResult = self.originalSend.apply(this, arguments);
            self.streams.set(socket, { header: [], remaining: 0, disabled: true });
            if (self.mode === 'armed' || self.mode === 'holding' || self.mode === 'waiting' || self.mode === 'preview_pending') { self.mode = 'idle'; self.message = 'Encrypted connection: readiness hold unavailable; normal traffic retained.'; self.record('hold_unavailable_encrypted'); }
            return buffered ? length : encryptedResult;
          }
          var peers = Object.keys(socket.peers || {}).map(function (k) { return socket.peers[k].socket; });
          if (!peers.some(function (ws) { return ws.readyState === 1; })) return self.originalSend.apply(this, arguments);
          var old = self.streams.get(socket) || streamState();
          if (old.disabled) return self.originalSend.apply(this, arguments);
          var input = bytesOf(buffer, offset, length), mode = self.mode, held = self.held, events = [], plan;
          try {
            plan = filter(input, old, function (type) {
              if (mode === 'preview_pending') {
                if (type !== 11 || !c.cw) return false;
                if (c.player) { mode = 'done'; events.push('preview_not_established'); return false; }
                held = { socket: socket, key: c.key, game: held ? held.game : c.game, started: held ? held.started : Date.now(), lastOwn: c.own, type: 11 };
                mode = 'holding'; events.push('room_preview_ready'); return true;
              }
              if (mode === 'holding' || mode === 'waiting') {
                if(type !== held.type) {
                  if(held.type === 22 && type === 11) {
                    held = { socket: socket, key: c.key, game: held.game, started: held.started, lastOwn: c.own, type: 11 };
                    mode = 'holding'; events.push('early_hold_world_fallback'); return true;
                  }
                  return false;
                }
                if (held.socket === socket && held.key === c.key && !(c.own !== null && held.lastOwn !== null && c.own+100 < held.lastOwn)) return true;
                mode = 'holding';
                held = { socket: socket, key: c.key, game: held.game, started: held.started, lastOwn: c.own, type: type };
                events.push('recovered_readiness_held'); return true;
              }
              if(mode === 'finishing') { if(type === 11) { mode = 'done'; events.push('world_after_early_finish'); } return false; }
              if (mode === 'reconnecting') {
                if(type !== 11)return false;
                if (held && held.socket === socket && held.key === c.key && !(c.own !== null && held.lastOwn !== null && c.own+100 < held.lastOwn)) return true;
                mode = 'done'; events.push('fresh_world_ready'); return false;
              }
              if(mode !== 'armed')return false;
              if(type === 22) { if(self.preset !== 'rush' && self.preset !== 'staged')return false; }
              else {
                if(!c.cw || c.player || (self.preset === 'boss' && !isBoss(c)))return false;
                if(self.preset === 'rush' || self.preset === 'staged')events.push('early_phase_absent_world_fallback');
              }
              mode = 'holding'; held = { socket: socket, key: c.key, game: c.game, started: Date.now(), lastOwn: c.own, type: type };
              events.push(type === 22 ? 'early_asset_readiness_held' : 'map_readiness_held'); return true;
            });
          } catch (e) {
            // Flush any previously buffered header before disabling the gate.
            // No parsed payload/authentication bytes are retained or logged.
            var restored = join([new Uint8Array(old.header), input]);
            var sent = self.originalSend.call(this, socket, restored, 0, restored.length, address, port);
            if (sent !== restored.length) throw new Error('Unexpected partial virtual-socket send.');
            self.streams.set(socket, { header: [], remaining: 0, disabled: true });
            self.message = e.message; if (self.mode === 'armed' || self.mode === 'holding' || self.mode === 'waiting') self.mode = 'idle'; self.record('framing_unavailable'); return length;
          }
          if (plan.bytes.length) {
            var result = self.originalSend.call(this, socket, plan.bytes, 0, plan.bytes.length, address, port);
            if (result !== plan.bytes.length) throw new Error('Unexpected partial virtual-socket send.');
          }
          self.streams.set(socket, plan.state); self.mode = mode; self.held = held;
          events.forEach(function (event) { self.record(event, { world: self.identity(c), same_mission: held ? c.game === held.game : null }); });
          if (events.indexOf('map_readiness_held') !== -1) self.message = 'Loading held. Choose Finish / reconnect when you want a fresh spawn.';
          if (events.indexOf('recovered_readiness_held') !== -1) self.message = 'Connection recovered; still holding. F10 or Finish / reconnect finishes the hold.';
          if (events.indexOf('fresh_world_ready') !== -1) self.message = 'Fresh readiness sent normally. Compare your position with the other account.';
          if(events.indexOf('early_asset_readiness_held') !== -1)self.message = 'Rush: waiting before map creation. F10 / Finish loading continues this load. Compare room with the other account.';
          if(events.indexOf('early_hold_world_fallback') !== -1 || events.indexOf('early_phase_absent_world_fallback') !== -1){self.fallback=true;self.message = 'Early wait unavailable on this entry; holding the loaded map instead.';}
          if(events.indexOf('world_after_early_finish') !== -1)self.message = 'Map selected after early finish. Compare room/floor with the other account.';
          if(events.indexOf('room_preview_ready') !== -1)self.message = 'Room preview ready. Reconnect when you want to spawn.';
          if(events.length)self.updateUI();
          return length;
        };
        this.ops.sendmsg = this.send; return true;
      }
      finishAsset() {
        if(!this.finishPending)return;
        var c=this.current(), socket=this.finishPending, state=this.streams.get(socket);
        if(!c || c.socket !== socket || c.connection.state !== 3) {
          this.finishPending=null;this.pending=false;this.mode=this.previewRequested?'preview_pending':'reconnecting';this.reconnectSocket=socket;
          this.message='Manual finish accepted during recovery; next fresh load may proceed.';this.record('early_finish_connection_changed');this.updateUI();return;
        }
        if(c.connection.outRC4){this.finishPending=null;this.pending=false;this.requestReconnect('early_finish_encryption_changed',true);return;}
        if(state && (state.header.length || state.remaining))return; // never interleave a protocol frame
        try {
          var ready=new Uint8Array([22,0,0,0,0]);
          if(this.originalSend.call(this.ops,socket,ready,0,5)!==5)throw new Error('Incomplete asset-ready send.');
        } catch(e) { this.pending=false;this.finishPending=null;this.previewRequested=false;this.message='Finish loading failed; still held. Try again.';this.record('early_finish_send_failed');this.updateUI();return; }
        this.finishPending=null;this.pending=false;this.mode=this.previewRequested?'preview_pending':'finishing';
        this.message='Early hold finished; waiting for the server-selected map.';this.record('early_asset_ready_released');this.updateUI();
      }
      previewAvailable() { return !!(!this.pending && !this.previewRequested && this.held && this.held.type === 22 && (this.mode === 'holding' || this.mode === 'waiting')); }
      previewRoom() {
        if (!this.previewAvailable()) return;
        this.previewRequested = true; this.record('room_preview_requested');
        var c = this.current();
        if (this.mode === 'waiting' || !c || c.socket !== this.held.socket || c.connection.state !== 3) {
          this.mode = 'preview_pending'; this.message = 'Waiting for a fresh map; spawn stays held.'; this.updateUI(); return;
        }
        this.requestReconnect('preview_room', false, true);
      }
      requestReconnect(reason, forceReconnect, forPreview) {
        if(forceReconnect && this.finishPending){this.finishPending=null;this.pending=false;}
        if (this.pending || (!forceReconnect && (this.mode === 'reconnecting' || this.mode === 'finishing' || this.mode === 'preview_pending'))) return;
        if (!forceReconnect && !forPreview && this.preset === 'staged' && this.previewAvailable()) { this.previewRoom(); return; }
        var c = this.current();
        var peers = c && c.socket ? Object.keys(c.socket.peers || {}).map(function (k) { return c.socket.peers[k].socket; }).filter(function (ws) { return ws.readyState === 1; }) : [];
        if (!peers.length) {
          if (this.mode === 'holding' || this.mode === 'waiting') {
            this.mode = forPreview ? 'preview_pending' : 'reconnecting'; this.reconnectSocket = this.held && this.held.socket;
            this.message = 'Manual finish accepted; the next recovered connection may spawn.';
            this.record('manual_finish_during_recovery', { reason: reason }); this.updateUI(); return;
          }
          this.message = 'No open game connection. Wait for the client to connect.'; this.updateUI(); return;
        }
        if(!forceReconnect && this.mode === 'holding' && this.held && this.held.type === 22) {
          var earlySelf=this;this.pending=true;this.finishPending=c.socket;
          this.record('early_finish_requested',{reason:reason});host.setTimeout(function(){earlySelf.finishAsset();},0);return;
        }
        var self = this; this.pending = true; this.reconnectSocket = c.socket; this.mode = 'reconnecting'; this.message = 'Reconnecting for a fresh load...';
        this.record('reconnect_requested', { reason: reason, world: this.identity(c) }); this.updateUI();
        host.setTimeout(function () {
          self.pending = false;
          // Close only the captured socket. A newer connection is never closed
          // by a delayed button action; native recovery handles the close.
          peers.forEach(function (ws) { if (ws.readyState === 1) ws.close(1000, 'SC loading test'); });
          self.record('socket_close_requested');
        }, 0);
      }
      afterUpdate() {
        this.attachTransport(); var c = this.current(), now = Date.now();
        this.finishAsset();
        if (this.mode === 'holding' && this.held) {
          var peers = c && c.socket ? Object.keys(c.socket.peers || {}).map(function (k) { return c.socket.peers[k].socket; }) : [];
          if (!c || c.socket !== this.held.socket || c.connection.state !== 3 || !peers.some(function (ws) { return ws.readyState === 1; })) {
            this.mode = 'waiting'; this.message = 'Connection lost; hold stays active. Native transport may retry, but fresh readiness remains held until F10.'; this.record('natural_connection_change_hold_retained');
          } else if (c.own !== null) this.held.lastOwn = c.own;
        }
        this.syncCamera(c);
        if (this.preset === 'staged' && this.previewAvailable() && now-this.held.started >= this.earlySeconds*1000) this.previewRoom();
        // Encrypted traffic bypasses the readiness gate. Still finish the UI
        // state once a different connection has produced a local player.
        if (this.mode === 'reconnecting' && !this.pending && c && c.player && c.connection.state === 3 && c.socket && c.socket !== this.reconnectSocket) {
          this.mode = 'done'; this.message = 'Fresh player observed. Compare your position with the other account.';
          this.record('fresh_player_observed', { world: this.identity(c) });
        }
        if (now-this.lastSample >= 1000 && (this.mode === 'holding' || this.mode === 'waiting' || this.mode === 'reconnecting' || this.mode === 'done')) {
          this.lastSample = now; var world = this.identity(c);
          if (c && c.cw && c.cw.player) { var p = mem.cast('WorldObject', c.cw.player.address).props; world.position = { xmp: p.xmp, ymp: p.ymp }; }
          this.record('sample', { world: world });
        }
        if (now-this.lastUI >= 250) { this.lastUI = now; this.updateUI(); }
      }
      makePanel() {
        var self = this, p = this.panel = doc.createElement('section'); p.setAttribute('aria-label', 'SBPE loading test');
        p.style.cssText = 'position:fixed;right:12px;top:clamp(12px,16vh,160px);box-sizing:border-box;width:min(368px,calc(100vw - 24px));max-height:calc(84vh - 24px);overflow:auto;padding:12px;background:#182430f5;color:#fff;border:1px solid #516c80;border-top:3px solid #07d8bb;border-radius:8px;font:13px/1.4 system-ui;z-index:2147483646';
        var header=doc.createElement('div');header.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap';p.appendChild(header);
        var title = doc.createElement('strong'); title.textContent = 'Loading controls'; title.style.fontSize = '17px'; header.appendChild(title);
        this.hideButton=doc.createElement('button');this.hideButton.type='button';this.hideButton.textContent='Hide all UI';
        this.hideButton.title='Hide the loading panel and tab. F8 restores them; the hold stays active.';
        this.hideButton.style.cssText='min-height:29px;padding:4px 9px;border:1px solid #4c697e;border-radius:4px;background:#30434e;color:#fff;font:inherit;cursor:pointer';
        this.hideButton.onclick=this.api.hideUI;header.appendChild(this.hideButton);
        this.status = doc.createElement('div'); this.status.style.cssText = 'white-space:pre-line;color:#ffff8a;margin:6px 0'; this.status.setAttribute('aria-live', 'polite'); p.appendChild(this.status);
        var flow = doc.createElement('small'); flow.textContent = 'SC: Rush hold → Preview room → Reconnect'; flow.style.cssText = 'display:block;color:#b5c8d8;margin-bottom:10px'; p.appendChild(flow);
        var buttons = doc.createElement('div'); buttons.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:10px 12px'; p.appendChild(buttons);
        this.buttons = {};
        [['Rush hold', this.api.skipRush, 'Wait before next map loads.', 'rush'], ['Boss hold', this.api.skipBoss, 'View the next boss; hold spawn.', 'boss'],
         ['Preview room', this.api.previewRoom, 'End early wait; keep spawn held.', 'preview'], ['Reconnect', this.api.reconnect, 'Reconnect for a fresh spawn.', 'finish'],
         ['Free camera', this.api.freeCamera, 'Preview: WASD / arrows; Shift faster.', 'camera'], ['Timed: 360s', this.api.staged, 'Early wait, then auto-preview.', 'staged'],
         ['Cancel hold', this.api.cancel, 'Disarm or finish the hold.', 'cancel'], ['Close panel', this.api.togglePanel, 'Hide UI; keep hold active.', 'close'],
         ['Save log', this.api.save, 'Download this session’s test log.', 'save']].forEach(function (item) {
          var cell = doc.createElement('div'), b = doc.createElement('button'), help = doc.createElement('small');
          b.type = 'button'; b.textContent = item[0]; b.title = item[2]; b.style.cssText = 'width:100%;min-height:29px;padding:5px 7px;border:1px solid #4c697e;border-radius:4px;background:#215c53;color:#fff;font:inherit;cursor:pointer';
          help.textContent = item[2]; help.style.cssText = 'display:block;margin-top:3px;color:#b5c8d8;font-size:10px;line-height:1.35';
          b.onclick = function () { try { item[1](); } catch (e) { self.message = e.message; self.updateUI(); } };
          cell.appendChild(b); cell.appendChild(help); buttons.appendChild(cell); self.buttons[item[3]] = b;
          if (item[3] === 'camera') self.cameraButton = b;
        });
        var groupCheck=doc.createElement('label');groupCheck.style.cssText='display:flex;align-items:center;gap:7px;margin-top:10px;font-size:13px';
        this.groupCheckbox=doc.createElement('input');this.groupCheckbox.type='checkbox';this.groupCheckbox.onchange=function(){self.applyToAll=self.groupCheckbox.checked;};
        groupCheck.appendChild(this.groupCheckbox);var groupText=doc.createElement('span');groupText.textContent='Arm all connected web tabs';groupCheck.appendChild(groupText);p.appendChild(groupCheck);
        this.roomLabel = doc.createElement('div'); this.roomLabel.style.cssText = 'margin-top:10px;color:#88e8bd;white-space:pre-line;font-size:12px'; p.appendChild(this.roomLabel);
        this.groupLabel=doc.createElement('div');this.groupLabel.style.cssText='margin-top:6px;font-size:12px;color:#b5c8d8';p.appendChild(this.groupLabel);
        var hint = doc.createElement('small'); hint.textContent = 'F8 panel / restore UI · F9 arm/cancel · F10 next/finish. Preview can time out. Server chooses spawn; preview is not reserved. Logs remain here until you save or reload.'; hint.style.cssText = 'display:block;color:#b5c8d8;margin-top:8px;font-size:10px'; p.appendChild(hint);
        (doc.body || doc.documentElement).appendChild(p);
        this.tab = doc.createElement('button'); this.tab.type = 'button'; this.tab.textContent = 'Loading controls (F8)';
        this.tab.style.cssText = 'display:none;position:fixed;right:12px;top:clamp(12px,16vh,160px);padding:8px;background:#182430f5;color:#fff;border:1px solid #718699;border-radius:6px;z-index:2147483646;cursor:pointer';
        this.tab.onclick = this.api.togglePanel; (doc.body || doc.documentElement).appendChild(this.tab); this.panelVisible = true;this.uiHidden=false;
      }
      hideUI() { this.uiHidden=true;this.panelVisible=false;this.panel.style.display='none';this.tab.style.display='none'; }
      togglePanel() {
        if(this.uiHidden){this.uiHidden=false;this.panelVisible=true;}
        else this.panelVisible=!this.panelVisible;
        this.panel.style.display=this.panelVisible?'':'none';this.tab.style.display=this.panelVisible?'none':'';
      }
      updateUI() {
        if(this.groupLabel)this.groupLabel.textContent=this.groupStatus;
        var c = this.current(), busy = this.pending || ['holding','waiting','reconnecting','finishing','preview_pending'].indexOf(this.mode) >= 0;
        var canArm = !!(c && c.connection.state === 3 && c.cw && c.socket && !busy);
        this.buttons.rush.disabled = this.buttons.boss.disabled = this.buttons.staged.disabled = !canArm;
        this.buttons.preview.disabled = !this.previewAvailable();
        this.buttons.finish.disabled = this.pending || ['reconnecting','finishing','preview_pending'].indexOf(this.mode) >= 0;
        this.buttons.finish.textContent = this.mode === 'preview_pending' ? 'Waiting for map' : this.held && this.held.type === 22 && this.mode === 'holding' ? (this.preset === 'staged' ? 'Next: preview' : 'Finish loading') : 'Reconnect';
        this.buttons.finish.parentNode && (this.buttons.finish.parentNode.lastChild.textContent = this.held && this.held.type === 22 && !this.previewRequested ? 'Continue loading normally.' : 'Reconnect for a fresh spawn.');
        this.buttons.cancel.disabled = !(['armed','holding','waiting','preview_pending'].indexOf(this.mode) >= 0) || this.pending;
        this.cameraButton.disabled = !this.camera && !this.cameraAvailable(c);
        Object.keys(this.buttons).forEach(function (key) { var b = this.buttons[key]; b.style.opacity = b.disabled ? '.45' : '1'; b.style.cursor = b.disabled ? 'default' : 'pointer'; }, this);
        this.cameraButton.textContent = this.camera ? (this.cameraAvailable(c) ? 'Free camera: ON' : 'Free camera: WAIT') : 'Free camera';
        this.cameraButton.setAttribute('aria-pressed', this.camera ? 'true' : 'false');
        this.cameraButton.title = this.camera ? 'WASD or arrows to pan; Shift moves faster. Click again to turn off.' : 'Available with a loaded map while spawn is held.';
        this.status.textContent = this.mode.toUpperCase() + (this.fallback && (this.mode === 'holding' || this.mode === 'waiting') ? ' / FALLBACK' : '') + ((this.mode === 'holding' || this.mode === 'waiting') && this.held ? ' · '+Math.floor((Date.now()-this.held.started)/1000)+'s' : '')+'\n'+this.message;
        if (this.camera) this.status.textContent += '\nCamera: WASD / arrows · Shift: faster';
        var shown = this.cameraAvailable(c);
        this.roomLabel.textContent = shown ? 'Preview: '+((c.cw.props.title ? util.getstr(c.cw.props.title) : '') || c.zone || c.music || 'unnamed room')+(isBoss(c) ? ' [boss]' : '')+'\n'+(c.floor >= 0 ? 'Floor '+(c.floor+1)+' · ' : '')+'map #'+c.world+' · preview only' : 'Room: not sent by server yet';
        this.tab.textContent = 'Loading controls: '+this.mode.toUpperCase()+' (F8)';
      }
      snapshot() { return { schema: 3, plugin: 'WebBreak rush/boss loading test', preset: this.preset, build: WB.build, started_epoch_ms: this.started, mode: this.mode, events: JSON.parse(JSON.stringify(this.events)) }; }
      save() {
        var url = host.URL.createObjectURL(new host.Blob([JSON.stringify(this.snapshot(), null, 2)], { type: 'application/json' }));
        var a = doc.createElement('a'); a.href = url; a.download = 'sbpe-web-sc-test-'+new Date(this.started).toISOString().replace(/[:.]/g, '-')+'.json';
        doc.body.appendChild(a); a.click(); a.remove(); host.setTimeout(function () { host.URL.revokeObjectURL(url); }, 1000);
      }
      onUnload() {
        try {
          var buffered = this.current(), state = buffered && buffered.socket && this.streams.get(buffered.socket);
          if (this.mode === 'holding' || this.mode === 'waiting' || (state && state.header.length)) this.requestReconnect('plugin_unloaded',true);
        } finally {
          this.endCamera(); this.camera = null; this.cameraHooks.forEach(function (unhook) { unhook(); });
          this.unloaded = true; if (this.ops && this.ops.sendmsg === this.send) this.ops.sendmsg = this.originalSend;
          if(this.armChannel){this.armChannel.onmessage=null;this.armChannel.close();this.armChannel=null;}
          host.removeEventListener('keydown', this.key, true); host.removeEventListener('keyup', this.keyUp, true); host.removeEventListener('blur', this.blur);
          this.panel.remove(); this.tab.remove(); if (WB.scBossTest === this.api) WB.scBossTest = null;
        }
      }
    }
    sbpe.register('sc_boss_test', Plugin); return Plugin;
  }
  return { filter: filter, streamState: streamState, isBoss: isBoss, install: install };
});
