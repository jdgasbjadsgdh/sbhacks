"""Exercise real snapshots, UDP transport and per-client native key dispatch."""
import ast
import os
from pathlib import Path
import socket
import sys
import types
import unittest
from unittest.mock import patch

from cffi import FFI

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from loading_multibox import Multibox,room_key
from loading_multibox_native import NativeControls


class Config(types.SimpleNamespace):
    def option(self,key,default,*args):
        if not hasattr(self,key):setattr(self,key,default)


class MultiboxTests(unittest.TestCase):
    def setUp(self):
        windows=Path(os.environ['SBPE_WINDOWS_ROOT'])
        self.ffi=ffi=FFI()
        ffi.cdef((windows/'cdefs/internals.h').read_text())
        ffi.cdef((windows/'cdefs/generated.h').read_text())
        self.now=[100.0];self.active=0;self.events=[[],[],[]];self.saves=[0,0,0]
        self.clock=patch('loading_multibox.time.monotonic',lambda:self.now[0]);self.clock.start()
        probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);probe.bind(('127.0.0.1',0));port=probe.getsockname()[1];probe.close()
        self.boxes=[];self.contexts=[];self.keys=[];self.bindings=[];self.text=[False]*3;self.menu=[False]*3
        for i in range(3):
            stage=ffi.new('struct Stage *');window=ffi.new('int *',i+1)
            refs=types.SimpleNamespace(stage=ffi.new('struct Stage **',stage),window_=[window])
            keys=ffi.new('unsigned char[512]');self.keys.append(keys)
            def keyboard_state(n,keys=keys):n[0]=512;return keys
            lib=types.SimpleNamespace(SDL_GetKeyboardFocus=lambda i=i,window=window:window if self.active==i else ffi.NULL,
                 SDL_IsTextInputActive=lambda i=i:self.text[i],SDL_GetKeyboardState=keyboard_state,
                 SDL_GetScancodeFromName=lambda name:{'A':4,'D':7,'J':13,'L':15,'LEFT':80,'RIGHT':79}.get(name.decode().upper(),0))
            owner=types.SimpleNamespace(config=Config(multibox_port=port,multibox_group_key='offline-three-client-group'),native=None,
                  refs=refs,control=types.SimpleNamespace(state='idle'),bindings=types.SimpleNamespace(visible=False),
                  game_input_blocked=lambda i=i:self.menu[i],save_status=lambda i=i:self.saved(i))
            box=Multibox(owner,ffi,lib,types.SimpleNamespace(getstr=lambda value:'USWest'))
            box.bus.clock=lambda:self.now[0];box.bus.next_election=0
            controls=NativeControls.__new__(NativeControls);controls.ffi=ffi;controls.stage=ffi.NULL;controls.injected={}
            # Different native game bindings in each client, including arrows.
            bindings=[[[97],[100]],[[0x40000050],[0x4000004f]],[[106],[108]]][i]+[[] for _ in range(12)]
            self.bindings.append(bindings);controls.keys=lambda bindings=bindings:bindings
            controls.keyboard=lambda stage,down,key,i=i:self.record(i,down,key)
            box.controls=controls;box.error='';self.boxes.append(box)
            player=ffi.new('struct WorldObject *');player.props.hitpoints=100;player.props.maxhitpoints=100
            player.props.wmp=20;player.props.hmp=40;player.props.xmp=200 if i==0 else 0
            cw=ffi.new('struct ClientWorld *');cw.player=ffi.cast('void *',player)
            connection=ffi.new('struct ServerConnection *')
            context=dict(connection=connection,cw=cw,player=True,game=42,world=100+i,zoneid=7,floor=3)
            # Retain native fixture allocations for the entire trial.
            owner.anchors=(stage,window,player,cw,connection)
            self.contexts.append(context)

    def saved(self,index):self.saves[index]+=1

    def record(self,index,down,key):self.events[index].append((down,key));return 1

    def pump(self,count=12,indices=(0,1,2)):
        for _ in range(count):
            self.now[0]+=.06
            for i in indices:self.boxes[i].update(self.contexts[i],self.active==i)

    def tearDown(self):
        for box in self.boxes:box.close()
        self.clock.stop()

    def test_real_snapshots_shared_actions_use_each_clients_binding(self):
        self.pump();self.assertEqual([len(box.frame['peers']) for box in self.boxes],[3]*3)
        self.assertEqual([box.me['world'] for box in self.boxes],[['uswest',42,7,3]]*3)
        self.assertNotEqual(self.contexts[0]['world'],self.contexts[1]['world'])
        self.boxes[0].action('toggle');self.keys[0][7]=1;self.pump()
        self.assertFalse(self.events[0]);self.assertEqual(self.events[1],[(1,0x4000004f)])
        self.assertEqual(self.events[2],[(1,108)])
        self.keys[0][7]=0;self.pump()
        self.assertEqual(self.events[1][-1],(0,0x4000004f));self.assertEqual(self.events[2][-1],(0,108))
        self.assertTrue(self.boxes[1].diagnostics()['native_controls_ready'])
        self.assertGreater(self.boxes[1].diagnostics()['events_handled'],0)

    def test_sync_starts_from_off_and_captures_requesting_client(self):
        self.pump();self.assertFalse(self.boxes[0].frame['enabled'])
        self.boxes[0].action('sync');self.pump()
        self.assertTrue(all(box.frame['enabled'] for box in self.boxes))
        self.assertIsNone(self.boxes[0].sync)
        for i in (1,2):
            self.assertEqual(self.boxes[i].sync['source'],self.boxes[0].bus.id)
            self.assertTrue(self.boxes[i].desired&2)
        self.assertIn((1,0x4000004f),self.events[1]);self.assertIn((1,108),self.events[2])
        self.boxes[1].owner.anchors[2].props.xmp=200;self.pump()
        self.assertIsNone(self.boxes[1].sync);self.assertEqual(self.boxes[1].desired,0)
        self.boxes[0].action('toggle');self.pump()
        self.assertFalse(any(box.desired for box in self.boxes));self.assertIsNone(self.boxes[2].sync)

    def test_room_change_chat_editor_and_stale_source_release_input(self):
        # Exercise the actual plugin's focus-independent menu guard too.
        tree=ast.parse((ROOT/'plugins/loading_probe.py').read_text())
        methods=next(node for node in tree.body if isinstance(node,ast.ClassDef)).body
        guard=next(node for node in methods if isinstance(node,ast.FunctionDef) and node.name=='game_input_blocked')
        tops=['GameClient'];owner=self.boxes[1].owner
        namespace=dict(ffi=self.ffi,lib=self.boxes[1].lib,
                       util=types.SimpleNamespace(vec2list=lambda vector:tops,getClassName=lambda element:element))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[])),'actual-menu-guard','exec'),namespace)
        self.assertFalse(namespace['game_input_blocked'](owner))
        for name in ('Controls','OptionsDialog','GraphicsOptions','SoundsOptions','GameplayOptions','GameMenu'):
            tops[:]=[name];self.assertTrue(namespace['game_input_blocked'](owner))
        tops[:]=['GameClient'];owner.refs.stage[0].textInputTarget=self.ffi.cast('struct UIElement *',1)
        self.assertTrue(namespace['game_input_blocked'](owner));owner.refs.stage[0].textInputTarget=self.ffi.NULL
        self.pump();self.boxes[0].action('toggle');self.keys[0][7]=1;self.pump()
        self.contexts[1]['floor']=4;self.pump()
        self.assertEqual(self.boxes[1].desired,0);self.assertIn('Other room',self.boxes[1].status)
        self.assertEqual(self.boxes[2].desired,2)
        self.contexts[1]['floor']=3;self.text[1]=True;self.pump();self.assertEqual(self.boxes[1].desired,0)
        self.text[1]=False;self.boxes[1].owner.bindings.visible=True;self.pump();self.assertEqual(self.boxes[1].desired,0)
        self.boxes[1].owner.bindings.visible=False;self.menu[1]=True;self.pump();self.assertEqual(self.boxes[1].desired,0)
        self.menu[1]=False;self.pump();self.assertEqual(self.boxes[1].desired,2)
        # Coordinator continues while its focused source stops reporting.
        self.active=2;self.keys[0][7]=0;self.keys[2][15]=1;self.pump()
        self.assertEqual(self.boxes[1].desired,2)
        self.pump(count=12,indices=(0,1));self.assertEqual(self.boxes[1].desired,0)
        self.assertFalse(self.boxes[1].controls.injected)

    def test_missing_native_support_is_visible_without_breaking_discovery(self):
        self.boxes[1].controls=None;self.boxes[1].error='Shared controls unavailable: missing mapping symbol'
        self.pump();self.assertEqual(len(self.boxes[1].frame['peers']),3)
        self.assertIn('loading-status.txt',self.boxes[1].summary())
        self.assertIn('missing mapping',self.boxes[1].diagnostics()['error']);self.assertGreater(self.saves[1],0)

    def test_room_identity_requires_shared_fields(self):
        self.assertIsNone(room_key(dict(game=42,world=1),'server'))
        self.assertNotEqual(room_key(self.contexts[0],'other'),room_key(self.contexts[1],'USWest'))
        self.assertEqual(room_key(self.contexts[0],'USWest'),room_key(self.contexts[1],' USWEST '))


if __name__=='__main__':unittest.main(verbosity=2)
