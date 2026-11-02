"""Real loopback peers, compiled-runtime routing and deferred texture regressions."""
import ast
from collections import OrderedDict
import importlib.util
import os
from pathlib import Path
import socket
import struct
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from loading_multibox_bus import Bus
from loading_probe_runtime import MouseBridge
from loading_probe_x86 import call_two_thunk
from loading_multibox_native import NativeControls


class BusTests(unittest.TestCase):
    def test_three_clients_arm_once_controls_stale_and_wrong_group(self):
        temp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);temp.bind(('127.0.0.1',0));port=temp.getsockname()[1];temp.close()
        now=[100.0];nodes=[Bus(port,'test-group-0123456789',clock=lambda:now[0]) for _ in range(3)]
        received=[[],[],[]];frames=[None]*3
        states=[dict(name='Client '+str(i),focus=i==0,held=2 if i==0 else 0,valid=True,world=['server',1,2]) for i in range(3)]
        def pump(n=8,indices=(0,1,2)):
            for _ in range(n):
                now[0]+=.06
                for i in indices:
                    frames[i],commands=nodes[i].tick(states[i]);received[i].extend(commands)
        try:
            pump();self.assertTrue(all(frame and len(frame['peers'])==3 for frame in frames))
            nodes[0].command('enable');pump();self.assertTrue(all(frame['enabled'] for frame in frames))
            self.assertTrue(all(frame['drive']['held']==2 for frame in frames))
            nodes[0].command('arm_rush');pump(15)
            self.assertEqual(received,[['arm_rush'],['arm_rush'],['arm_rush']])
            nodes[2].command('arm_boss');pump(15)
            self.assertEqual(received,[['arm_rush','arm_boss']]*3)
            nodes[0].command('reconnect',nodes[1].id);pump(15)
            self.assertEqual(received[1],['arm_rush','arm_boss','reconnect']);self.assertNotIn('reconnect',received[0])
            wrong=Bus(port,'different-group-0123456789',clock=lambda:now[0])
            try:self.assertIsNone(wrong.decode(nodes[0].encode({'type':'state'})))
            finally:wrong.close()
            pump(10,indices=(1,2));self.assertIsNone(frames[1]);self.assertIsNone(frames[2])
            nodes[0].close();pump(30,indices=(1,2))
            self.assertTrue(frames[1] and frames[2]);self.assertFalse(frames[1]['enabled'])
        finally:
            for node in nodes:
                try:node.close()
                except OSError:pass


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.windows=Path(os.environ['SBPE_WINDOWS_ROOT'])

    def test_mouse_bridge_in_front_of_actual_embedded_handler(self):
        # Use the source embedded in the shipped PE, not the edited remote.py.
        raw=(self.windows/'build/remote.bin').read_bytes()
        begin=raw.index(b'def hook_mouseButton(');end=raw.index(b'\n@ffi.def_extern()',begin)
        source=raw[begin:end].split(b'\x00',1)[0].decode()
        fn=ast.parse(source).body[0];forwarded=[]
        refs=types.SimpleNamespace(scaleX=3.25,scaleY=.8)
        namespace={'refs':refs,'ORIGS':{'mouseButtonCallback':lambda *args:forwarded.append(args)}}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'embedded-mouse','exec'),namespace)
        original=namespace['hook_mouseButton'];calls=[]
        bridge=MouseBridge.__new__(MouseBridge);bridge.active=True
        bridge.mouse=lambda *a:calls.append(a) or (100<=a[0]<200 and 50<=a[1]<100)
        bridge.original=original
        bridge.dispatch(120,70,0,1,None);bridge.dispatch(120,70,0,0,None)
        self.assertEqual(len(calls),2);self.assertFalse(forwarded)
        bridge.dispatch(300,200,0,1,None)
        self.assertEqual(forwarded,[(975,160,0,1,None)])
        bridge.active=False;bridge.dispatch(120,70,0,1,None)
        self.assertEqual(forwarded[-1],(390,56,0,1,None))

    def test_deferred_textures_actual_plaintext(self):
        from cffi import FFI
        ffi=FFI();fake_lib=types.SimpleNamespace(BLENDMODE_BLEND=1)
        sys.modules['_remote']=types.SimpleNamespace(ffi=ffi,lib=fake_lib)
        sys.path.insert(0,str(self.windows))
        spec=importlib.util.spec_from_file_location('actual_ui_util',self.windows/'util.py')
        util=importlib.util.module_from_spec(spec);spec.loader.exec_module(util);sys.modules['util']=util
        textures={};queued=[]
        def create(old,font,size,color,text,outline,outline_color):
            texture=old or len(textures)+1;textures[texture]=text;return texture
        def query(texture,w,h):w[0]=len(textures[texture])*7;h[0]=14
        refs=types.SimpleNamespace(windowW=800,windowH=600,canvasW_=ffi.new('int *',2400),canvasH_=ffi.new('int *',1800),
            scaleX=3,scaleY=3,XDL_CreateTextTexture=create,XDL_QueryTexture=query,
            XDL_DrawTexture=lambda texture,*args:queued.append(texture),XDL_DestroyTexture=lambda texture:None)
        util.refs=refs
        labels=['Loading controls','Rush hold','Logs saved automatically']
        old=util.PlainText()
        for label in labels:old.text=label;old.draw(10,10)
        self.assertEqual([textures[t].decode() for t in queued],[labels[-1]]*3)
        queued.clear()
        sys.path.insert(0,str(ROOT))
        spec=importlib.util.spec_from_file_location('new_ui_plugin',ROOT/'plugins/loading_probe.py')
        plugin=importlib.util.module_from_spec(spec);spec.loader.exec_module(plugin)
        owner=plugin.Plugin.__new__(plugin.Plugin);owner.ui={'scale':1};owner.texts=OrderedDict()
        owner.refs=refs;owner.config=types.SimpleNamespace(ui_font='TenbyFive')
        for label in labels:owner.label(label,10,10)
        self.assertEqual([textures[t].decode() for t in queued],labels)

    def test_native_keyboard_two_argument_thunk(self):
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
        from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EAX
        for offset in (0,4,8,12):
            uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(0x10000,0x70000)
            uc.mem_write(0x10000,call_two_thunk(0x20000))
            uc.mem_write(0x20000,b'\x8b\x01\x03\x44\x24\x04\x03\x44\x24\x08\xc2\x08\x00')
            uc.mem_write(0x30000,struct.pack('<I',100));stack=0x70000+offset
            uc.mem_write(stack,struct.pack('<IIII',0x60000,0x30000,1,37));uc.reg_write(UC_X86_REG_ESP,stack)
            uc.emu_start(0x10000,0x60000,count=100)
            self.assertEqual(uc.reg_read(UC_X86_REG_EAX),138);self.assertEqual(uc.reg_read(UC_X86_REG_ESP),stack+4)

    def test_mirrored_keys_release_original_binding_and_scene_lifetime(self):
        from cffi import FFI
        ffi=FFI();controls=NativeControls.__new__(NativeControls)
        controls.ffi=ffi;controls.injected={};controls.stage=ffi.NULL
        bindings=[[97],[100]]+[[] for _ in range(12)];events=[]
        controls.keys=lambda:bindings
        controls.keyboard=lambda *args:events.append(args)
        stage=ffi.new('int *');next_stage=ffi.new('int *')
        controls.apply(stage,1);controls.apply(stage,1)
        self.assertEqual(events,[(stage,1,97)])
        bindings[0]=[98];controls.apply(stage,0)
        self.assertEqual(events[-1],(stage,0,97))
        controls.apply(stage,2);controls.apply(ffi.NULL,0);controls.close()
        self.assertEqual(events[-1],(stage,1,100));self.assertFalse(controls.injected)
        controls.apply(next_stage,1);controls.close()
        self.assertEqual(events[-2:],[(next_stage,1,98),(next_stage,0,98)])


if __name__=='__main__':unittest.main(verbosity=2)
