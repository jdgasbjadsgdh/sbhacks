"""Rush/boss/any-map loading controls and local free camera for Windows SBPE."""
import json
import logging
import math
import os
import time
from collections import OrderedDict
from _remote import ffi, lib
from manager import PluginBase
import util
from loading_probe_logic import LoadingControl
from loading_probe_native import NativeLoading
from loading_probe_ui import panel_layout
from loading_probe_runtime import MouseBridge
from loading_multibox import Multibox
from loading_emergency import EmergencyHold
from loading_keybinds import KeybindPanel,ACTIONS


class Plugin(PluginBase):
    def onInit(self):
        self.lib,self.ffi = lib,ffi
        self.config.option('panel_key', 'F11')
        self.config.option('finish_key', 'F9')
        self.config.option('arm_key', '')
        self.config.option('stage_early_seconds', 360, 'float')
        self.config.option('camera_speed', 900, 'float')
        self.config.option('ui_scale', 0, 'float')
        self.config.option('ui_font', 'TenbyFive')
        self.visible, self.captured, self.pressed = True, set(), None
        self.camera = self.saved = None
        self.old_keys = set()
        self.record = None
        self.serial = 0
        self.texts = OrderedDict()
        self.ui = None
        self.apply_all = False
        self.control = LoadingControl(emit=self.emit)
        self.control.preset = 'rush'
        self.native = None
        self.multibox = None
        self.emergency = None
        self.bindings = None
        self.error = ''
        self.mouse_bridge = None
        self.input_error = ''
        try:
            self.mouse_bridge = MouseBridge(self.refs, ffi, lib, self.mouse)
        except Exception as error:
            self.input_error = 'Mouse bridge unavailable: '+str(error)
            logging.warning(self.input_error)
        try:
            self.native = NativeLoading(self.refs, ffi, lib, self)
        except Exception as error:
            self.error = 'Loading hooks unavailable: '+str(error)
            logging.warning(self.error)
        self.multibox = Multibox(self, ffi, lib, util)
        self.emergency = EmergencyHold(self)
        self.bindings = KeybindPanel(self)
        self.save_status()

    @staticmethod
    def address(pointer):
        return int(ffi.cast('uintptr_t', pointer))

    def current(self):
        stage = self.refs.stage[0]
        if stage == ffi.NULL:
            return None
        tops = util.vec2list(stage.asUIElementContainer.children)
        if not tops or util.getClassName(tops[0]) != 'GameClient':
            return None
        gc = ffi.cast('struct GameClient *', tops[0])
        conn, wc = gc.serverConnection, gc.worldClient
        if conn == ffi.NULL:
            return None
        cw = wc.clientWorld if wc != ffi.NULL else ffi.NULL
        result = {'gc': gc, 'connection': conn, 'connection_id': self.address(conn),
                  'cw': cw, 'wc': wc,
                  'state': int(conn.state), 'socket': int(conn.socket), 'key': None,
                  'world': None, 'game': None, 'player': False, 'zone': '', 'music': '', 'view': ffi.NULL}
        if cw != ffi.NULL:
            props = cw.asWorld.props
            result.update(world=int(cw.asWorld.id), game=int(props.gameid), player=cw.player != ffi.NULL,
                          zone=util.getstr(props.zone), music=util.getstr(props.music), view=wc.worldView,
                          title=util.getstr(props.title) if props.title != ffi.NULL else '', floor=int(props.floor),
                          zoneid=int(props.zoneid), seed=int(props.seed))
            result['key'] = (self.address(cw), result['game'], result['world'])
            if cw.player != ffi.NULL:
                player=ffi.cast('struct WorldObject *',cw.player)
                result.update(player_id=self.address(cw.player),hp=int(player.props.hitpoints),maxhp=int(player.props.maxhitpoints))
        return result

    def emit(self, event, **extra):
        if event == 'armed':
            if self.record:
                self.record.close()
            directory = os.path.join(self.refs.SCRIPTPATH, 'loading-tests')
            os.makedirs(directory, exist_ok=True)
            self.serial += 1
            name = 'windows-{}-{}-{}.jsonl'.format(time.strftime('%Y%m%d-%H%M%S'), os.getpid(), self.serial)
            path = os.path.join(directory, name)
            self.record = os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w')
        if self.record:
            try:
                value = dict(event=event, epoch_ms=int(time.time()*1000), state=self.control.state)
                value.update(extra)
                self.record.write(json.dumps(value)+'\n')
                self.record.flush()
                if self.record.tell() > 8*1024*1024:
                    self.record.close();self.record = None
            except OSError:
                logging.exception('Loading log write failed')
                self.record = None

    def arm(self, preset, local=False):
        if not local and self.apply_all:
            if self.multibox and self.multibox.bus:
                self.multibox.bus.command('arm_'+preset)
                self.control.message = 'Arm requested for all connected clients: '+preset
            else:self.control.message = 'Cannot arm all: multibox connection is unavailable.'
            return
        if not self.native:
            self.control.message = 'Loading unavailable. See the error below; reinstall and launch with run.bat.'
            return
        try:
            self.control.early_seconds = max(1, min(1800, self.config.stage_early_seconds))
            self.control.arm(self.current(), preset)
        except OSError as error:
            self.control.state = 'idle'
            self.control.message = 'Could not start local log: '+str(error)

    def afterUpdate(self):
        c = self.current()
        self.control.frame(c)
        self.sync_camera(c)
        n = ffi.new('int *')
        keys = lib.SDL_GetKeyboardState(n)
        held = set(i for i in range(n[0]) if keys[i])
        allowed = self.input_allowed()
        if self.emergency:self.emergency.frame(c)
        editing = self.bindings.input(held,allowed) if self.bindings else False
        capturing = self.emergency.input(held,allowed and not editing) if self.emergency else False
        capturing = capturing or editing
        for option, action in ((self.config.panel_key, self.toggle_panel),
                               (self.config.arm_key, self.arm_selected),
                               (self.config.finish_key, self.finish),
                               (self.config.rush_key, lambda:self.arm('rush')),
                               (self.config.boss_key, lambda:self.arm('boss')),
                               (self.config.preview_key,self.preview),
                               (self.config.camera_key,self.toggle_camera),
                               (self.config.staged_key,lambda:self.arm('staged')),
                               (self.config.cancel_key,lambda:self.control.cancel(self.current()))):
            code = lib.SDL_GetScancodeFromName(option.encode()) if option else 0
            if allowed and not capturing and code and code in held and code not in self.old_keys:
                action()
        self.old_keys = held
        movement_allowed=allowed and not capturing
        self.dx = int(bool(held & {7, 79}))-int(bool(held & {4, 80})) if movement_allowed else 0
        self.dy = int(bool(held & {22, 81}))-int(bool(held & {26, 82})) if movement_allowed else 0
        self.fast = bool(held & {225, 229}) and movement_allowed
        if self.multibox:self.multibox.update(c,movement_allowed)
        # The shipped remote.bin embeds its original callbacks. Keep camera
        # ownership inside this plugin as well, so source-only updates work.
        self.beginCamera()

    def input_allowed(self):
        return lib.SDL_GetKeyboardFocus()==self.refs.window_[0] and not self.game_input_blocked()

    def game_input_blocked(self):
        # Followers must accept native world controls while unfocused, but
        # never while their own chat or settings own keyboard input.
        if lib.SDL_IsTextInputActive():return True
        stage_ref=getattr(self.refs,'stage',None)
        if stage_ref is not None and stage_ref[0]!=ffi.NULL:
            if stage_ref[0].textInputTarget:return True
            for element in util.vec2list(stage_ref[0].asUIElementContainer.children):
                if util.getClassName(element) in ('Controls','OptionsDialog','Graphics','Sound','GraphicsOptions','SoundsOptions','GameplayOptions','GameMenu'):return True
        return False

    def finish(self):
        if not self.native:
            self.control.message = 'Loading unavailable. See the error below; reinstall and launch with run.bat.'
            return
        if self.native:
            self.camera = None
            self.control.finish(self.current())

    def toggle_panel(self):
        self.visible = not self.visible

    def arm_selected(self):
        if self.control.state == 'armed':
            self.control.cancel(self.current())
        else:
            self.arm(self.control.preset)

    def preview(self):
        self.control.preview(self.current())

    def camera_available(self, c):
        if not c or not self.native or self.control.state != 'holding' or not self.control.held or self.control.held['type'] != 11:
            return False
        v = c['view']
        return bool(self.control.same(c, self.control.held) and c['state'] == 3 and not c['player'] and
                    v != ffi.NULL and v.worldBounds.w > 0 and v.worldBounds.h > 0)

    @staticmethod
    def camera_room(c):
        return tuple(c.get(k) for k in ('game','zone','music','floor','zoneid','seed'))

    def sync_camera(self, c):
        camera = self.camera
        if not camera:return False
        held = self.control.held
        if (not self.native or self.control.state not in ('holding','waiting') or not held or
                held['started'] != camera['hold_started'] or
                c and self.control.same(c,held) and c['state'] == 3 and c['player']):
            self.camera = None
            return False
        if not self.camera_available(c):
            camera['view'] = None;camera['last'] = time.monotonic()
            return False
        v = c['view']
        if camera['key'] != c['key'] or camera['view'] != self.address(v):
            room = self.camera_room(c)
            if camera['room'] != room:camera.update(x=float(v.offset.x),y=float(v.offset.y))
            camera.update(view=self.address(v),key=c['key'],room=room,last=time.monotonic())
        return True

    def toggle_camera(self):
        if self.camera:
            self.camera = None
            self.emit('free_camera_off')
            return
        c = self.current()
        if not self.camera_available(c):
            self.control.message = 'Free camera needs a loaded map with spawn held.'
            return
        v = c['view']
        self.camera = dict(view=self.address(v), key=c['key'], room=self.camera_room(c),
                           hold_started=self.control.held['started'], x=float(v.offset.x), y=float(v.offset.y), last=time.monotonic())
        self.emit('free_camera_on')

    def beginCamera(self):
        if self.saved:
            self.endCamera()
        if not self.camera:
            return
        c = self.current()
        if not self.sync_camera(c):return
        v, camera = c['view'], self.camera
        now = time.monotonic();dt = max(0, min(.1, now-camera['last']));camera['last'] = now
        speed = max(50, min(6000, self.config.camera_speed))*(3 if getattr(self, 'fast', False) else 1)
        dx, dy = getattr(self, 'dx', 0), getattr(self, 'dy', 0)
        if dx and dy:
            speed /= math.sqrt(2)
        camera['x'] += dx*speed*dt;camera['y'] += dy*speed*dt
        for axis, size, viewport in (('x', 'w', v.asUIElement.w), ('y', 'h', v.asUIElement.h)):
            start, extent = getattr(v.worldBounds, axis), getattr(v.worldBounds, size)
            camera[axis] = start+(extent-viewport)/2 if extent <= viewport else max(start, min(start+extent-viewport, camera[axis]))
        saved = {'view': self.address(v), 'key': c['key'], 'initialized': bool(v.offsetsInitialized)}
        for name in ('offset', 'currOffset', 'goalOffset', 'targetPos', 'playerBounds'):
            point = getattr(v, name)
            saved[name] = {field: getattr(point, field) for field in ('x', 'y', 'w', 'h') if field in ('x', 'y') or name == 'playerBounds'}
        self.saved = saved
        for field in ('x', 'y', 'w', 'h'):
            setattr(v.playerBounds, field, getattr(v.worldBounds, field))
        for name in ('offset', 'currOffset', 'goalOffset'):
            point = getattr(v, name);point.x = round(camera['x']);point.y = round(camera['y'])
        v.targetPos.x = v.offset.x+v.asUIElement.w//2;v.targetPos.y = v.offset.y+v.asUIElement.h//2
        v.offsetsInitialized = True

    def endCamera(self):
        saved, self.saved = self.saved, None
        if not saved:
            return
        c = self.current()
        if not c or c['key'] != saved['key'] or self.address(c['view']) != saved['view']:
            self.sync_camera(c)
            return
        v = c['view']
        for name, values in saved.items():
            if isinstance(values, dict):
                for field, value in values.items():
                    setattr(getattr(v, name), field, value)
        v.offsetsInitialized = saved['initialized']

    def layout(self):
        self.ui = panel_layout(self.refs.windowW, self.refs.windowH, self.config.ui_scale,
                               reserve=self.multibox.reserve() if self.multibox else 0)
        if not self.ui:
            return None
        return self.ui['panel'], self.ui['buttons'], self.ui['tab']

    def change_scale(self, direction):
        scale = self.ui['scale'] if self.ui else 1
        self.config.ui_scale = max(1, min(3, round(scale+direction*.2, 2)))

    def save_status(self):
        # No account, authentication, packet or world data is included.
        try:
            path = os.path.join(self.refs.SCRIPTPATH, 'loading-status.txt')
            with open(path, 'w', encoding='utf-8') as stream:
                stream.write('Windows Emergency hold 2026.10.24-emergency.3\n')
                stream.write('Emergency shortcut: '+(self.config.emergency_key or 'GUI only')+'\n')
                stream.write((self.error or 'Native hooks initialized')+'\n')
                stream.write((self.input_error or 'Compiled-runtime mouse bridge ready')+'\n')
                stream.write('Use the complete installer, then launch SBPE with run.bat.\n')
                stream.write('Panel key: {} | Arm key: {} | Finish key: {}\n'.format(
                    self.config.panel_key or 'GUI', self.config.arm_key or 'GUI', self.config.finish_key or 'GUI'))
                for option,label in ACTIONS:stream.write(label+': '+(getattr(self.config,option) or 'Unbound')+'\n')
                if self.multibox:
                    for key,value in sorted(self.multibox.diagnostics().items()):stream.write('Multibox '+key+': '+str(value)+'\n')
            logging.info('Loading status saved to loading-status.txt')
        except (OSError, TypeError, AttributeError):
            logging.warning('Could not save loading-status.txt')

    @staticmethod
    def inside(rect, x, y):
        a, b, w, h = rect
        return a <= x < a+w and b <= y < b+h

    def mouse(self, x, y, button, down):
        if self.bindings and self.bindings.mouse(x,y,button,down):return True
        if self.emergency and self.emergency.mouse(x,y,button,down):return True
        if self.multibox and self.multibox.mouse(x,y,button,down):return True
        layout = self.layout()
        if not down and button in self.captured:
            self.captured.remove(button)
            if button != 0:
                return True
            action, self.pressed = self.pressed, None
            if layout and action is not None:
                panel, buttons, tab = layout
                rect = buttons[action] if action < 8 else self.ui['sizes'][action-8] if action < 10 else tab if action == 10 else self.ui['all'] if action == 11 else self.ui['keys']
                if self.inside(rect, x, y):
                    if action < 2:
                        self.arm(('rush', 'boss')[action])
                    elif action == 2:
                        self.preview()
                    elif action == 3:
                        self.finish()
                    elif action == 4:
                        self.toggle_camera()
                    elif action == 5:
                        self.arm('staged')
                    elif action == 6:
                        self.control.cancel(self.current())
                    elif action < 8 or action == 10:
                        self.toggle_panel()
                    elif action == 11:
                        self.apply_all = not self.apply_all
                    elif action == 12:
                        self.bindings.open()
                    else:
                        self.change_scale(-1 if action == 8 else 1)
            return True
        if not layout or not down:
            return False
        panel, buttons, tab = layout
        if not self.inside(panel if self.visible else tab, x, y):
            return False
        self.captured.add(button)
        if button == 0:
            rects = buttons+ self.ui['sizes']
            self.pressed = (12 if self.inside(self.ui['keys'],x,y) else 11 if self.inside(self.ui['all'],x,y) else next((i for i, rect in enumerate(rects) if self.inside(rect,x,y)),None)) if self.visible else 10
        return True

    def measure(self, value, size):
        method = getattr(self.refs, 'XDL_CalculateTextWidth', None)
        if method:
            return method(self.config.ui_font.encode(), size, 0xffffffff, value.encode(), 1)
        return len(value)*size*.58

    def fit(self, value, size, width):
        if self.measure(value, size) <= width:
            return value
        while value and self.measure(value+'...', size) > width:
            value = value[:-1]
        return value+'...'

    def lines(self, value, size, width):
        result = [];line = ''
        for word in value.split():
            trial = (line+' '+word).strip()
            if line and self.measure(trial, size) > width:
                result.append(line);line = word
            else:
                line = trial
            while self.measure(line, size) > width:
                part = self.fit(line, size, width)
                count = max(1, len(part)-3);result.append(line[:count]);line = line[count:]
        if line:result.append(line)
        return result

    def label(self, value, x, y, size=14, centered=False, width=None, color=0xffffff):
        size = max(12, round(size*self.ui['scale']))
        if width is not None:value = self.fit(str(value), size, width)
        key = (value, size, self.config.ui_font, color)
        if key not in self.texts:
            text = util.PlainText(size=size, font=self.config.ui_font, outlineSize=1,
                                  color=color, screenCoords=True)
            text.text = value;self.texts[key] = text
            if len(self.texts) > 128:self.texts.popitem(last=False)
        text = self.texts[key];self.texts.move_to_end(key)
        text.draw(round(x), round(y), anchorX=.5 if centered else 0, anchorY=.5 if centered else 0)

    def onPresent(self):
        layout = self.layout()
        if not layout:
            if self.bindings and self.bindings.visible:
                self.ui={'scale':1};width,height=self.refs.canvasW_[0],self.refs.canvasH_[0]
                self.refs.canvasW_[0],self.refs.canvasH_[0]=self.refs.windowW,self.refs.windowH
                try:self.bindings.draw()
                finally:self.refs.canvasW_[0],self.refs.canvasH_[0]=width,height;self.endCamera()
            else:self.endCamera()
            return
        panel, buttons, tab = layout
        ui = self.ui;s = ui['scale'];pad = ui['pad']
        width, height = self.refs.canvasW_[0], self.refs.canvasH_[0]
        self.refs.canvasW_[0], self.refs.canvasH_[0] = self.refs.windowW, self.refs.windowH
        try:
            if self.bindings and self.bindings.visible:return
            if not self.visible:
                self.refs.XDL_FillRect(*tab, 0xff27394b, 1)
                self.label('Load: {} ({})'.format('UNAVAILABLE' if self.error else self.control.state.upper(), self.config.panel_key or 'GUI'), tab[0]+pad, tab[1]+6*s, width=tab[2]-2*pad)
                return
            self.refs.XDL_FillRect(*panel, 0xff182430, 1)
            self.label('Loading controls v6', panel[0]+pad, panel[1]+pad, 19, width=panel[2]-2*pad-128*s)
            keys_rect=ui['keys'];self.refs.XDL_FillRect(*keys_rect,0xff365268,1)
            self.label('Keys',keys_rect[0]+keys_rect[2]/2,keys_rect[1]+keys_rect[3]/2,13,True,width=keys_rect[2]-4*s)
            for rect,name in zip(ui['sizes'], ('A-', 'A+')):
                self.refs.XDL_FillRect(*rect, 0xff365268, 1)
                self.label(name, rect[0]+rect[2]/2, rect[1]+rect[3]/2, 13, True)
            state = 'UNAVAILABLE' if self.error else self.control.state.upper()+(' / FALLBACK' if self.control.fallback and self.control.state in ('holding', 'waiting') else '')
            if not self.error and self.control.state in ('holding', 'waiting') and self.control.held:
                state += ' | {}s'.format(int(time.monotonic()-self.control.held['started']))
            self.label(state, panel[0]+pad, panel[1]+40*s, 14, width=panel[2]-2*pad, color=0xffb0a0 if self.error else 0xffff80)
            self.label('SC: Rush hold > Preview room > Reconnect', panel[0]+pad, panel[1]+59*s, 12, width=panel[2]-2*pad)
            c = self.current()
            can_arm = bool(self.native and c and c['state'] == 3 and self.control.state not in ('holding', 'waiting', 'reconnecting', 'finishing', 'preview_pending'))
            early = bool(self.control.held and self.control.held.get('type') == 22 and not self.control.preview_requested)
            finish = 'Waiting for map' if self.control.state == 'preview_pending' else 'Next: preview' if early and self.control.preset == 'staged' else 'Finish loading' if early else 'Reconnect'
            camera_label = ('Free camera: ON' if self.camera_available(c) else 'Free camera: WAIT') if self.camera else 'Free camera'
            names = ['Rush hold', 'Boss hold', 'Preview room', finish, camera_label, 'Timed: {}s'.format(int(self.control.early_seconds)), 'Cancel hold', 'Close panel']
            helpers = ['Wait before map loads.', 'Hold in the next boss.', 'View map; keep held.', 'Continue loading.' if early else 'Reconnect to spawn.', 'WASD/arrows; Shift fast.', 'Wait, then preview.', 'Disarm or finish hold.', 'Hide UI; hold stays on.']
            for i, (rect, name) in enumerate(zip(buttons, names)):
                enabled = bool(i == 7 or self.native and not (
                    i in (0, 1, 5) and not can_arm or i == 4 and not (self.camera or self.camera_available(c)) or
                    i == 2 and not self.control.preview_available() or i == 3 and self.control.state == 'preview_pending'))
                color = (0xff21675d if i in (0, 1, 4, 5) else 0xff315b86) if enabled else 0xff303a40
                self.refs.XDL_FillRect(*rect, color, 1)
                self.label(name, rect[0]+rect[2]/2, rect[1]+rect[3]/2, 14, True, width=rect[2]-8*s)
                self.label(helpers[i], rect[0], rect[1]+rect[3]+2*s, 12, width=rect[2])
            all_rect = ui['all']
            self.refs.XDL_FillRect(*all_rect,0xff294e43 if self.apply_all else 0xff27394b,1)
            self.label(('[x] ' if self.apply_all else '[ ] ')+'Arm all clients',all_rect[0]+4*s,all_rect[1]+3*s,13,width=all_rect[2]-8*s)
            x = panel[0]+pad;info = ui['footer']+29*s;space = panel[2]-2*pad
            hint = '{} panel | {} arm | {} finish'.format(self.config.panel_key or 'GUI', self.config.arm_key or 'GUI', self.config.finish_key or 'GUI')
            if self.error:
                self.label('Loading hooks failed; controls are disabled.', x, info, 13, width=space, color=0xffb0a0)
                message = self.error.replace('Loading hooks unavailable: ', '')
                size = max(12, round(12*s));lines = self.lines(message, size, space)
                if ui['compact']:
                    self.label(message, x, info+19*s, 12, width=space)
                    self.label('Full error: loading-status.txt / remote.log', x, info+38*s, 12, width=space)
                else:
                    for i,line in enumerate(lines[:4]):self.label(line, x, info+(20+i*16)*s, 12, width=space)
                    self.label('Reinstall the complete update; launch run.bat.', x, info+88*s, 12, width=space)
                    self.label('Full error: loading-status.txt / remote.log', x, info+106*s, 12, width=space)
                    self.label(hint, x, info+124*s, 12, width=space)
                return
            shown = self.camera_available(c)
            room = 'Preview: '+(c.get('title') or c.get('zone') or c.get('music') or 'unnamed room') if shown else 'Room: not sent by server yet'
            self.label(room, x, info, 13, width=space)
            if ui['compact']:
                self.label(self.input_error or self.control.message, x, info+19*s, 12, width=space)
                self.label(hint, x, info+38*s, 12, width=space)
            else:
                detail = 'Floor {} | map #{} | preview only'.format(c.get('floor', -1)+1, c['world']) if shown and c.get('floor', -1) >= 0 else 'Server chooses the room on recovery.'
                self.label(detail, x, info+20*s, 12, width=space)
                lines = self.lines(self.input_error or self.control.message, max(12, round(12*s)), space)
                for i,line in enumerate(lines[:2]):self.label(line, x, info+(40+i*17)*s, 12, width=space)
                self.label(hint, x, info+81*s, 12, width=space)
                self.label('Server chooses spawn; preview is not reserved.', x, info+104*s, 12, width=space)
                self.label('Logs saved automatically in loading-tests/', x, info+124*s, 12, width=space)
        finally:
            try:
                if self.bindings and self.bindings.visible:self.bindings.draw()
                else:
                    if self.multibox and self.visible:self.multibox.draw()
                    if self.emergency:self.emergency.draw()
            finally:
                self.refs.canvasW_[0], self.refs.canvasH_[0] = width, height
                self.endCamera()

    def onUnload(self):
        if self.emergency:self.emergency.cancel('Plugin unloading; queued emergency cancelled.')
        if self.mouse_bridge:self.mouse_bridge.close()
        if self.multibox:self.multibox.close()
        self.endCamera()
        self.camera = None
        self.texts.clear()
        if self.native:
            self.native.close()
        if self.record:
            self.record.close();self.record = None
