"""Offline tests. No authentication, game process, Steam or network connections."""
import ast
import configparser
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from loading_probe_logic import LoadingControl
from loading_probe_x86 import call_thunk, callback_thunk
from prepare_loading_probe import pe, functions, prepare, NAMES, OPTIONAL_NAMES, expected_entry
from install_loading_probe import install, patched, MARKER, MOUSE_MARKER


def context(world=1, socket=9, player=False, state=3, zone='forest'):
    return dict(connection_id=123, socket=socket, key=(world, 42, world), game=42,
                world=world, player=player, state=state, zone=zone, music='')


class StateTests(unittest.TestCase):
    def test_preview_and_staged_recovery(self):
        now = [100.0]
        p = LoadingControl(clock=lambda: now[0]);p.arm(context(player=True), 'rush')
        early = dict(context(), key=None, world=None)
        self.assertTrue(p.suppress(early, 22));now[0] += 600;p.frame(early)
        self.assertEqual(p.state, 'holding')
        self.assertTrue(p.preview(early));self.assertFalse(p.preview(early))
        self.assertEqual(p.take_action(early, 123, True), 'asset')
        self.assertEqual(p.state, 'preview_pending');self.assertFalse(p.finish(early))
        self.assertFalse(p.suppress(early, 22));boss = context(5, zone='sc_boss')
        self.assertTrue(p.suppress(boss, 11));self.assertEqual(p.held['type'], 11)
        p.frame(dict(boss, state=2));fresh = context(6, socket=12, zone='sc_boss')
        self.assertFalse(p.suppress(fresh, 22));self.assertTrue(p.suppress(fresh, 11))
        p.finish(fresh);self.assertEqual(p.take_action(fresh, 123, True), 'reconnect')
        self.assertFalse(p.suppress(context(7, socket=13), 11))
        p.arm(context(), 'staged');p.suppress(early, 22)
        now[0] += 359;p.frame(early);self.assertIsNone(p.pending)
        now[0] += 1;p.frame(early);self.assertTrue(p.pending['preview'])
        # A connection replaced before the queued send cannot receive stale ready.
        self.assertIsNone(p.take_action(dict(early, socket=14), 123, True))
        self.assertEqual(p.state, 'preview_pending')
        self.assertFalse(p.suppress(dict(early, socket=14), 22))
        self.assertTrue(p.suppress(context(8, socket=14), 11))
        p.cancel(context(8, socket=14));p.take_action(context(8, socket=14), 123, True)
        p.suppress(context(9, socket=15), 11)
        p.arm(context(), 'rush');p.suppress(early, 22);p.frame(dict(early, state=2))
        self.assertTrue(p.preview(dict(early, state=2)));self.assertIsNone(p.pending)
        p.cancel(early);self.assertEqual(p.state, 'finishing')
        self.assertFalse(p.suppress(context(10), 11));self.assertEqual(p.state, 'done')

    def test_modes_and_recovery(self):
        p = LoadingControl();c = context(player=True)
        self.assertTrue(p.arm(c, 'boss'));self.assertFalse(p.suppress(c, 11))
        c = context(2);self.assertFalse(p.suppress(c, 11))
        c = context(3, zone='sc_boss');self.assertTrue(p.suppress(c, 11))
        started = p.held['started']
        for kind in range(1, 47):
            if kind != 11:
                self.assertFalse(p.suppress(c, kind))
        for i in range(4):
            down = dict(c, state=2);p.frame(down);self.assertEqual(p.state, 'waiting')
            self.assertFalse(p.arm(c, 'rush'))
            c = context(4+i, socket=10+i);self.assertTrue(p.suppress(c, 11));self.assertEqual(p.held['started'], started)
        self.assertTrue(p.finish(c));self.assertFalse(p.finish(c))
        self.assertTrue(p.suppress(c, 11))
        self.assertIsNone(p.take_action(c, 999, True))
        self.assertEqual(p.take_action(c, 123, True), 'reconnect')
        self.assertIsNone(p.take_action(c, 123, True))
        self.assertFalse(p.suppress(context(99, socket=90), 11));self.assertEqual(p.state, 'done')

    def test_early_rush(self):
        p = LoadingControl();p.arm(context(player=True), 'rush')
        c = dict(context(), key=None, world=None)
        self.assertTrue(p.suppress(c, 22));self.assertEqual(p.held['type'], 22)
        changed = dict(c, key=(2,42,2));p.frame(changed);self.assertEqual(p.state, 'holding')
        self.assertTrue(p.finish(changed));self.assertEqual(p.take_action(c, 123, True), 'asset')
        self.assertEqual(p.state, 'finishing');self.assertFalse(p.suppress(context(5), 11));self.assertEqual(p.state, 'done')
        p.arm(context(), 'rush');self.assertTrue(p.suppress(context(6), 11));self.assertEqual(p.held['type'], 11)
        p.finish(context(6));self.assertEqual(p.take_action(context(6), 123, True), 'reconnect')
        p.suppress(context(7), 11);p.arm(context(7), 'rush');p.suppress(c, 22)
        self.assertTrue(p.suppress(context(8), 11));self.assertEqual(p.held['type'], 11)

    def test_manual_loss_cancel_stale(self):
        p = LoadingControl();p.arm(context(), 'any');p.cancel(context());self.assertEqual(p.state, 'idle')
        p.arm(context());p.suppress(context(2), 11);p.frame(dict(context(2), state=2))
        p.finish(dict(context(2), state=2));self.assertIsNone(p.pending);self.assertEqual(p.state, 'reconnecting')
        self.assertFalse(p.suppress(context(3, socket=15), 11));self.assertEqual(p.state, 'done')
        p.arm(context());p.suppress(context(4), 11);p.finish(context(4))
        self.assertIsNone(p.take_action(context(5), 123, True));self.assertIsNone(p.pending)
        p.suppress(context(5), 11);p.arm(context());p.suppress(context(6), 11)
        p.frame(context(6, player=True));self.assertEqual(p.state, 'done')


class X86Tests(unittest.TestCase):
    def test_real_machine_code(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP
        for outbound in (False, True):
            for argument in (False, True):
                for misalign in (0, 4, 8, 12):
                    uc = Uc(UC_ARCH_X86, UC_MODE_32);uc.mem_map(0x10000, 0x70000)
                    obj, target, entry, stop, stack = 0x30000, 0x20000, 0x10000, 0x60000, 0x70000+misalign
                    if outbound:
                        machine = b'\x8b\x01'+(b'\x03\x44\x24\x04\xc2\x04\x00' if argument else b'\xc3')
                        thunk = call_thunk(target, argument)
                        frame = [stop, obj]+([8] if argument else [])
                    else:
                        machine = b'\x8b\x4c\x24\x04\x8b\x01'+(b'\x03\x44\x24\x08' if argument else b'')+b'\xc3'
                        thunk = callback_thunk(target, argument)
                        frame = [stop]+([8] if argument else [])
                        uc.reg_write(UC_X86_REG_ECX, obj)
                    uc.mem_write(entry, thunk);uc.mem_write(target, machine)
                    uc.mem_write(obj, struct.pack('<I', 100));uc.mem_write(stack, struct.pack('<'+'I'*len(frame), *frame))
                    uc.reg_write(UC_X86_REG_ESP, stack)
                    keep = {UC_X86_REG_EBX: 0x1234, UC_X86_REG_ESI: 0x5678, UC_X86_REG_EDI: 0xabcd, UC_X86_REG_EBP: 0xef12}
                    for register, value in keep.items():uc.reg_write(register, value)
                    uc.emu_start(entry, stop, count=100)
                    self.assertEqual(uc.reg_read(UC_X86_REG_EAX), 108 if argument else 100)
                    expected_stack = stack+4+(4 if argument and not outbound else 0)
                    self.assertEqual(uc.reg_read(UC_X86_REG_ESP), expected_stack)
                    for register, value in keep.items():self.assertEqual(uc.reg_read(register), value)


def synthetic_pe(coff=True, relocate=False, mixed=False):
    names = list(NAMES.values())
    dwarf_names=names+list(OPTIONAL_NAMES.values()) if mixed else names
    # Tiny DWARF 4 tree with exact linkage names and absolute low_pc values.
    abbrev = bytes([1, 0x11, 1, 0, 0, 2, 0x2e, 0, 0x6e, 8, 0x11, 1, 0, 0, 0])
    dies = b'\x01'+b''.join(b'\x02'+name.encode()+b'\0'+struct.pack('<I', 0x401000+i*32) for i, name in enumerate(dwarf_names))+b'\0'
    payload = struct.pack('<HI', 4, 0)+b'\x04'+dies
    info = struct.pack('<I', len(payload))+payload
    sections = [('.text', bytes(range(192))), ('.debug_info', info), ('.debug_abbrev', abbrev)]
    if relocate:
        text = bytearray(sections[0][1]);struct.pack_into('<I', text, 4, 0x403000)
        sections[0] = ('.text', bytes(text))
        sections.append(('.reloc', struct.pack('<IIHH', 0x1000, 12, 0x3004, 0)))
    data = bytearray(0x1000);data[:2] = b'MZ';struct.pack_into('<I', data, 0x3c, 0x80);data[0x80:0x84] = b'PE\0\0'
    symbols = 0xb00;strings = bytearray(b'\0'*4);name_offsets = {}
    for name in [n for n, _ in sections]+names:
        name_offsets[name] = len(strings);strings.extend(name.encode()+b'\0')
    struct.pack_into('<I', strings, 0, len(strings))
    struct.pack_into('<HHIIIHH', data, 0x84, 0x14c, len(sections), 0, symbols, len(names) if coff else 0, 0xe0, 0)
    struct.pack_into('<H', data, 0x98, 0x10b);struct.pack_into('<I', data, 0x98+28, 0x400000)
    if relocate:
        struct.pack_into('<I', data, 0x98+92, 16)
        struct.pack_into('<II', data, 0x98+96+5*8, 0x4000, 12)
    for i, (name, body) in enumerate(sections):
        raw = 0x400+i*0x200
        encoded = name.encode() if len(name)<=8 else ('/'+str(name_offsets[name])).encode()
        struct.pack_into('<8sIIII', data, 0x178+i*40, encoded, len(body), 0x1000+i*0x1000, len(body), raw)
        data[raw:raw+len(body)] = body
    if coff:
        for i, name in enumerate(names):
            struct.pack_into('<IIIhHBB', data, symbols+i*18, 0, name_offsets[name], i*32, 1, 0x20, 2, 0)
    at = symbols+(len(names)*18 if coff else 0);data[at:at+len(strings)] = strings
    return bytes(data)


class ResolveTests(unittest.TestCase):
    def test_multibox_methods_in_dwarf_with_loading_methods_in_coff(self):
        data=synthetic_pe(mixed=True);base,sections,symbols,count=pe(data)
        found=functions(data,base,sections,symbols,count)
        self.assertEqual(found,dict(send=0x1000,io=0x1020,error=0x1040,keyboard=0x1060,mapping=0x1080))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'game.exe';path.write_bytes(data)
            manifest=prepare(str(path),folder)
            self.assertEqual(set(manifest['functions']),set(NAMES)|set(OPTIONAL_NAMES))
        # Missing optional methods must not disable the loading plugin.
        del sections['.debug_info'];del sections['.debug_abbrev']
        self.assertEqual(functions(data,base,sections,symbols,count),dict(send=0x1000,io=0x1020,error=0x1040))

    def test_aslr_entry_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'game.exe';path.write_bytes(synthetic_pe(relocate=True))
            target = prepare(str(path), folder);entry = target['functions']['send']
            self.assertEqual(target['image_base'], 0x400000)
            self.assertEqual(entry['relocations'], [{'offset':4,'value':0x403000}])
            original = bytes.fromhex(entry['entry_hex'])
            self.assertEqual(expected_entry(entry,0x400000,0x400000),original)
            relocated = expected_entry(entry,0x400000,0x620000)
            self.assertEqual(struct.unpack_from('<I',relocated,4)[0],0x623000)
            self.assertEqual(relocated[:4]+relocated[8:],original[:4]+original[8:])
            damaged = bytearray(relocated);damaged[15] ^= 1
            self.assertNotEqual(bytes(damaged),expected_entry(entry,0x400000,0x620000))
            bad = dict(entry,relocations=[{'offset':4,'value':0x403001}])
            with self.assertRaises(ValueError):expected_entry(bad,0x400000,0x620000)
            partial = {'entry_hex':original[:6].hex(),'relocations':entry['relocations']}
            self.assertEqual(expected_entry(partial,0x400000,0x620000),relocated[:6])

    def test_exact_coff_and_dwarf(self):
        for coff in (True, False):
            data = synthetic_pe(coff);base, sections, symbols, count = pe(data)
            self.assertEqual(functions(data, base, sections, symbols, count), {'send': 0x1000, 'io': 0x1020, 'error': 0x1040})
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'game.exe';path.write_bytes(data)
                manifest = prepare(str(path), folder)
                self.assertEqual(manifest['game_sha256'], hashlib.sha256(data).hexdigest())
                self.assertEqual(manifest['functions']['send']['entry_hex'], data[0x400:0x418].hex())
        with self.assertRaises(ValueError):pe(b'not a game')

    def test_python36(self):
        for path in ROOT.rglob('*.py'):
            if 'loading_probe_vendor' not in path.parts:
                ast.parse(path.read_text(), filename=str(path), feature_version=(3, 6))


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.windows = Path(os.environ.get('SBPE_WINDOWS_ROOT', str(ROOT.parent)))

    def test_installer_and_unload(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('remote.py', 'loader.py', 'manager.py', 'config.ini'):
                (root/name).write_text((self.windows/name).read_text())
            original = (root/'config.ini').read_text();install(root)
            result = (root/'config.ini').read_text();self.assertTrue(result.startswith(original))
            cfg = configparser.ConfigParser();cfg.read_string(result)
            self.assertEqual(cfg.get('plugin_loading_probe', 'panel_key'), 'F11')
            self.assertEqual(cfg.get('plugin_loading_probe', 'finish_key'), 'F9')
            self.assertEqual(cfg.get('plugin_loading_probe', 'arm_key'), '')
            self.assertEqual(cfg.get('plugin_keybinds', 'sandbox_hacks jump_speed_bonus toggle 2 0'), 'F7')
            for name in ('remote.py', 'loader.py', 'manager.py'):
                text = (root/name).read_text();self.assertIn(MARKER, text);compile(text, name, 'exec')
            self.assertIn(MOUSE_MARKER,(root/'remote.py').read_text())
            install(root);self.assertEqual(result, (root/'config.ini').read_text())
            spec = importlib.util.spec_from_file_location('test_patched_manager', str(root/'manager.py'))
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            refs = types.SimpleNamespace(config=cfg)
            manager = module.Manager(str(root/'plugins'), refs);removed=[]
            manager._active['a'] = types.SimpleNamespace(onUnload=lambda: removed.append('a'))
            manager._active['b'] = object();manager._remove('a');manager._remove('b')
            self.assertEqual(removed, ['a']);self.assertFalse(manager._active)

    def test_upgrade_partial_config_and_real_mouse_route(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('remote.py','loader.py','manager.py','config.ini'):
                (root/name).write_text((self.windows/name).read_text())
            config = (root/'config.ini').read_text()
            config = config[:config.index('[plugin_loading_probe]')]+'[plugin_loading_probe]\npanel_key = F11\n'
            (root/'config.ini').write_text(config)
            changes = patched(root)
            cfg=configparser.ConfigParser();cfg.read_string(changes['config.ini'])
            self.assertTrue(cfg.getboolean('plugin_loading_probe','enabled'))
            self.assertEqual(cfg.get('plugin_loading_probe','panel_key'),'F11')
            source = changes['remote.py'];self.assertIn(MOUSE_MARKER,source)
            fn = next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='hook_mouseButton')
            fn.decorator_list=[];calls=[];forwarded=[]
            refs=types.SimpleNamespace(scaleX=3.5,scaleY=.75)
            namespace={'refs':refs,'ORIGS':{'mouseButtonCallback':lambda *a:forwarded.append(a)},'_loading_probe_call':lambda *a:calls.append(a) or a[1]==100}
            isolated=ast.Module(body=[fn],type_ignores=[]);exec(compile(ast.fix_missing_locations(isolated),'mouse-route','exec'),namespace)
            namespace['hook_mouseButton'](100,80,0,1,None)
            self.assertEqual(calls[-1],('mouse',100,80,0,1));self.assertFalse(forwarded)
            namespace['hook_mouseButton'](150,80,0,1,None)
            self.assertEqual(forwarded[-1],(525,60,0,1,None))
            # Explicitly disabled/blank user choices must not be re-enabled.
            (root/'config.ini').write_text(config+'enabled = no\narm_key =\n')
            cfg.read_string(patched(root)['config.ini'])
            self.assertFalse(cfg.getboolean('plugin_loading_probe','enabled'));self.assertEqual(cfg.get('plugin_loading_probe','arm_key'),'')

    def test_actual_struct_camera_gui(self):
        from cffi import FFI
        ffi = FFI();ffi.cdef((self.windows/'cdefs/internals.h').read_text());ffi.cdef((self.windows/'cdefs/generated.h').read_text())
        fake_lib = types.SimpleNamespace(SDL_IsTextInputActive=lambda: False, SDL_GetKeyboardFocus=lambda: ffi.NULL)
        sys.modules['_remote'] = types.SimpleNamespace(ffi=ffi, lib=fake_lib)
        sys.path.insert(0, str(self.windows))
        import manager
        labels=[]
        class FixtureText:
            def __init__(self, **kwargs):
                self.text='';self.size=kwargs.get('size',13)
            def draw(self, x, y, **kwargs):
                labels.append((self.text,self.size,x,y,kwargs))
        fake_util = types.SimpleNamespace(PlainText=FixtureText)
        sys.modules['util'] = fake_util
        spec = importlib.util.spec_from_file_location('fixture_loading_plugin', str(ROOT/'plugins/loading_probe.py'))
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.NativeLoading = lambda *args: types.SimpleNamespace(close=lambda: None)
        cfg = configparser.ConfigParser();cfg.add_section('plugin_loading_probe');cfg.set('plugin_loading_probe','multibox_enabled','no');cfg.set('plugin_loading_probe','emergency_enabled','no')
        rects=[]
        class Refs(dict):
            __getattr__ = dict.get
            __setattr__ = dict.__setitem__
        refs = Refs(windowW=800, windowH=600, canvasW_=ffi.new('int *', 2400), canvasH_=ffi.new('int *', 1800), XDL_FillRect=lambda *args: rects.append(args))
        p = module.Plugin(refs, cfg['plugin_loading_probe']);p.onInit();p.control.emit=lambda *args, **kwargs: None
        view = ffi.new('struct WorldView *');view.asUIElement.w=800;view.asUIElement.h=600
        view.worldBounds.x=-200;view.worldBounds.w=4000;view.worldBounds.h=3000
        view.offset.x=100;view.offset.y=200;view.playerBounds.w=2000;view.playerBounds.h=2000
        c = context();c['view'] = view;p.current=lambda: c
        p.arm('any');c['key']=(2,42,2);p.control.suppress(c, 11)
        before = bytes(ffi.buffer(view));p.toggle_camera();self.assertIsNotNone(p.camera)
        p.dx, p.dy, p.fast = 1, 0, False;p.camera['last']-=.1;p.beginCamera()
        self.assertGreater(view.offset.x,100);self.assertEqual(view.targetPos.x,view.offset.x+400)
        p.endCamera();self.assertEqual(bytes(ffi.buffer(view)),before)
        p.camera['x']=1e9;p.camera['y']=-1e9;p.beginCamera();self.assertEqual(view.offset.x,3000);self.assertEqual(view.offset.y,0);p.endCamera()
        p.onPresent();self.assertEqual(len(rects),13);self.assertEqual(refs.canvasW_[0],2400)
        self.assertTrue(all(label[1]>=12 for label in labels))
        cached = dict(p.texts);p.onPresent()
        for key,text in cached.items():self.assertIs(p.texts[key],text)
        keys_rect=p.ui['keys'];self.assertTrue(p.mouse(keys_rect[0]+3,keys_rect[1]+3,0,True));self.assertTrue(p.mouse(keys_rect[0]+3,keys_rect[1]+3,0,False));self.assertTrue(p.bindings.visible)
        labels.clear();rects.clear();p.onPresent();self.assertIn('Keybinds',[v[0] for v in labels]);self.assertEqual(refs.canvasW_[0],2400)
        self.assertNotIn('Loading controls v6',[v[0] for v in labels])
        if os.environ.get('SBPE_UI_DIRECTORY'):
            output=Path(os.environ['SBPE_UI_DIRECTORY']);output.mkdir(exist_ok=True,parents=True)
            (output/'keybinds-800x600.json').write_text(json.dumps(dict(width=800,height=600,rects=rects,labels=labels)))
        close_rect=p.bindings.rects['close'];self.assertTrue(p.mouse(close_rect[0]+3,close_rect[1]+3,0,True));self.assertTrue(p.mouse(close_rect[0]+3,close_rect[1]+3,0,False));self.assertFalse(p.bindings.visible)
        if os.environ.get('SBPE_UI_ARTIFACT'):
            from xml.sax.saxutils import escape
            svg=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="800" height="600" fill="#09233a"/>']
            for x,y,w,h,color,blend in rects:
                svg.append('<rect x="{}" y="{}" width="{}" height="{}" fill="#{:06x}"/>'.format(x,y,w,h,color & 0xffffff))
            for value,size,x,y,anchors in labels:
                centered=anchors.get('anchorX')==.5
                svg.append('<text x="{}" y="{}" fill="white" font-family="monospace" font-size="{}" text-anchor="{}">{}</text>'.format(x,y+(size//3 if centered else size),size,'middle' if centered else 'start',escape(value)))
            Path(os.environ['SBPE_UI_ARTIFACT']).write_text('\n'.join(svg+['</svg>']))

        panel, buttons, tab = p.layout();close=buttons[-1];x,y=close[0]+5,close[1]+5
        self.assertTrue(p.mouse(x,y,0,True));self.assertTrue(p.mouse(x,y,0,False));self.assertFalse(p.visible)
        self.assertTrue(p.mouse(tab[0]+5,tab[1]+5,0,True));self.assertTrue(p.mouse(tab[0]+5,tab[1]+5,0,False));self.assertTrue(p.visible)
        self.assertFalse(p.mouse(1,1,0,True));self.assertFalse(p.mouse(tab[0]+5,tab[1]+5,0,False))
        c['player']=True;p.beginCamera();self.assertIsNone(p.camera)
        c['player']=False;p.control.state='holding';p.toggle_camera();p.camera.update(x=700,y=500);p.dx=p.dy=0
        c['state']=2;p.control.frame(c);c['view']=ffi.NULL;p.beginCamera()
        self.assertIsNotNone(p.camera);self.assertIsNone(p.camera['view']);self.assertIsNone(p.saved)
        recovered=ffi.new('struct WorldView *');ffi.memmove(recovered,view,ffi.sizeof('struct WorldView'))
        recovered.offset.x=20;recovered.offset.y=30;recovered_before=bytes(ffi.buffer(recovered))
        c.update(state=3,key=(3,42,3),world=3,socket=12,view=recovered);p.control.suppress(c,11);p.beginCamera()
        self.assertEqual((recovered.offset.x,recovered.offset.y),(700,500));p.endCamera()
        self.assertEqual(bytes(ffi.buffer(recovered)),recovered_before);self.assertEqual(bytes(ffi.buffer(view)),before)
        c.update(key=(4,42,4),world=4,seed=1);p.control.suppress(c,11);p.beginCamera()
        self.assertEqual((recovered.offset.x,recovered.offset.y),(20,30));p.endCamera()
        c['state']=2;p.control.frame(c);p.beginCamera();self.assertIsNotNone(p.camera)
        p.toggle_camera();self.assertIsNone(p.camera)
        c.update(state=3,key=(5,42,5),world=5,socket=13);p.control.suppress(c,11);p.beginCamera();self.assertIsNone(p.camera)
        p.toggle_camera();self.assertIsNotNone(p.camera);p.finish();self.assertIsNone(p.camera)
        # First keyboard arm selects the early Rush hold, with no GUI prerequisite.
        p.control.state='idle';p.control.preset='rush';p.arm_selected()
        self.assertEqual((p.control.state,p.control.preset),('armed','rush'))
        # Draw and hit areas share one layout, even at a larger UI scale.
        p.control.state='idle';p.config.ui_scale=1.5;p.visible=True
        panel,buttons,tab=p.layout();r=buttons[0];x,y=r[0]+5,r[1]+5
        self.assertTrue(p.mouse(x,y,0,True));self.assertTrue(p.mouse(x,y,1,True));self.assertTrue(p.mouse(x,y,1,False))
        self.assertTrue(p.mouse(x,y,0,False));self.assertEqual(p.control.preset,'rush')
        # Initialization failure remains clearly visible; Close and A+ still work.
        p.native=None;p.error='Loading hooks unavailable: '+('A native method differs from the expected game build. '*3)
        labels.clear();rects.clear();p.onPresent()
        self.assertIn('UNAVAILABLE',[v[0] for v in labels]);self.assertTrue(all(v[1]>=12 for v in labels))
        for width,height,scale in [(320,380,1),(800,600,1),(1280,720,1.5),(1920,1080,0),(3840,2160,0)]:
            refs.windowW,refs.windowH=width,height;p.config.ui_scale=scale;labels.clear();rects.clear();p.onPresent()
            panel,buttons,tab=p.layout()
            self.assertGreaterEqual(panel[0],0);self.assertLessEqual(panel[0]+panel[2],width)
            self.assertGreaterEqual(panel[1],0);self.assertLessEqual(panel[1]+panel[3],height)
            for r in buttons:
                self.assertGreaterEqual(r[1],panel[1]);self.assertLess(r[1]+r[3],p.ui['footer'])
            self.assertTrue(all(v[1]>=12 for v in labels))
            if os.environ.get('SBPE_UI_DIRECTORY'):
                output=Path(os.environ['SBPE_UI_DIRECTORY']);output.mkdir(exist_ok=True,parents=True)
                (output/('error-{}x{}.json'.format(width,height))).write_text(json.dumps(dict(width=width,height=height,rects=rects,labels=labels)))
        p.error='';p.native=types.SimpleNamespace(close=lambda:None);p.control.state='idle'
        if os.environ.get('SBPE_UI_DIRECTORY'):
            for width,height,scale in [(800,600,1),(1280,720,1.5),(3840,2160,0)]:
                refs.windowW,refs.windowH=width,height;p.config.ui_scale=scale;labels.clear();rects.clear();p.onPresent()
                (output/('normal-{}x{}.json'.format(width,height))).write_text(json.dumps(dict(width=width,height=height,rects=rects,labels=labels)))
        # The auxiliary panel and arm-all checkbox share physical hit/draw
        # coordinates, with enough room reserved at small and Retina sizes.
        from loading_multibox import Multibox
        p.config.multibox_enabled=True
        boxes=Multibox.__new__(Multibox);boxes.owner=p;boxes.page=0;boxes.error=''
        boxes.captured=False;boxes.pressed=None;boxes.rects={}
        boxes.bus=types.SimpleNamespace(id='main',close=lambda:None);boxes.controls=None
        boxes.frame={'enabled':False,'peers':[dict(id='main',name='Main',hold='idle',hp=114,maxhp=114),dict(id='other',name='Follower',hold='armed',hp=80,maxhp=100)]}
        p.multibox=boxes
        for width,height in [(800,600),(1280,720),(1920,1080),(3840,2160)]:
            refs.windowW,refs.windowH=width,height;p.config.ui_scale=0;labels.clear();rects.clear();p.onPresent()
            panel,buttons,tab=p.layout();boxpanel,rows,pages=boxes.layout()
            self.assertGreater(boxpanel[1],panel[1]+panel[3]);self.assertLessEqual(boxpanel[1]+boxpanel[3],height)
            allrect=p.ui['all'];self.assertLess(allrect[1]+allrect[3],panel[1]+panel[3])
            self.assertTrue(p.mouse(allrect[0]+5,allrect[1]+5,0,True));self.assertTrue(p.mouse(allrect[0]+5,allrect[1]+5,0,False))
            self.assertTrue(p.apply_all);p.apply_all=False
            if os.environ.get('SBPE_UI_DIRECTORY'):
                (output/('multibox-{}x{}.json'.format(width,height))).write_text(json.dumps(dict(width=width,height=height,rects=rects,labels=labels)))
        p.config.emergency_enabled=True
        for width,height in [(800,600),(1280,720),(3840,2160)]:
            refs.windowW,refs.windowH=width,height;labels.clear();rects.clear();p.onPresent()
            emergency_panel,emergency_tab,scale=p.emergency.layout()
            self.assertGreaterEqual(emergency_panel[0],0);self.assertLessEqual(emergency_panel[0]+emergency_panel[2],width)
            self.assertLessEqual(emergency_panel[1]+emergency_panel[3],height)
            self.assertTrue(all(v[1]>=12 for v in labels))
            if os.environ.get('SBPE_UI_DIRECTORY'):
                (output/('emergency-{}x{}.json'.format(width,height))).write_text(json.dumps(dict(width=width,height=height,rects=rects,labels=labels)))
        p.onUnload()
        self.assertFalse(p.texts)


if __name__ == '__main__':
    unittest.main(verbosity=2)
