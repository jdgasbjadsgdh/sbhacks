"""Real controller/native callback composition, hotkey persistence and GUI input."""
from pathlib import Path
import configparser
import tempfile
import types
import unittest
from cffi import FFI
from loading_emergency import EmergencyHold,replace_hotkey
from loading_probe_logic import LoadingControl
from loading_probe_native import NativeLoading


NAMES={'F4':61,'F6':63,'F7':64,'F9':66,'F11':68,'J':13,'Escape':41,'Backspace':42}


class Config(types.SimpleNamespace):
    def option(self,key,default=None,type='str'):
        if not hasattr(self,key):setattr(self,key,default)


class Owner:
    def __init__(self):
        self.now=100.0;self.events=[];self.local=[];self.camera=None;self.ffi=FFI()
        self.config=Config(panel_key='F6',arm_key='F7',finish_key='F9',emergency_key='F4',emergency_enabled=True)
        cfg=configparser.ConfigParser(interpolation=None);cfg.read_string('[plugin_loading_probe]\nemergency_key = F4\n[plugin_keybinds]\n')
        self.refs=types.SimpleNamespace(config=cfg,windowW=1280,windowH=720)
        self.lib=types.SimpleNamespace(SDL_GetScancodeFromName=lambda name:NAMES.get(name.decode(),0))
        self.key_names={value:self.ffi.new('char[]',name.encode()) for name,value in NAMES.items()}
        self.lib.SDL_GetScancodeName=lambda code:self.key_names[code]
        self.native=NativeLoading.__new__(NativeLoading);self.native.ffi=self.ffi;self.native.owner=self;self.native.closing=False
        self.native.originals={'io':lambda connection:1,'send':lambda *args:None};self.closed=[]
        self.native.error=lambda gc,error:self.closed.append((gc,error,self.control.state))
        self.c=dict(connection_id=123,socket=9,key=(1,42,3),game=42,world=3,player_id=222,player=True,hp=100,maxhp=100,state=3,zone='forest',music='',gc='gc')
        self.control=LoadingControl(clock=lambda:self.now,emit=self.emit)
        self.emergency=EmergencyHold(self,clock=lambda:self.now)

    def current(self):return self.c
    def emit(self,event,**extra):self.events.append((event,extra))
    def arm(self,preset,local=False):self.local.append(local);return self.control.arm(self.c,preset)
    def finish(self):return self.control.finish(self.c)
    @staticmethod
    def inside(rect,x,y):return rect[0]<=x<rect[0]+rect[2] and rect[1]<=y<rect[1]+rect[3]


class EmergencyTests(unittest.TestCase):
    def test_native_io_closes_once_keeps_arm_and_recovers_held(self):
        o=Owner();e=o.emergency;e.visible=False;e.input({61},True);self.assertEqual(o.local,[True]);self.assertEqual(o.control.state,'armed');self.assertFalse(o.closed)
        e.input({61},True);self.assertEqual(e.trial,1)
        ptr=o.ffi.cast('void *',123);self.assertEqual(o.native.on_io(ptr),0);self.assertEqual(o.closed,[('gc',2,'armed')]);self.assertIsNone(e.pending)
        self.assertEqual(o.native.on_io(ptr),1);self.assertEqual(len(o.closed),1)
        o.c.update(player=False,state=2);o.control.frame(o.c);e.frame(o.c)
        o.c.update(player=False,state=3,socket=10,key=(2,42,4),world=4)
        self.assertTrue(o.control.suppress(o.c,11));e.frame(o.c);self.assertEqual(e.phase,'Holding');self.assertEqual(o.control.state,'holding')
        o.now+=30;e.frame(o.c);self.assertEqual(len(o.closed),1)
        e.resume();self.assertEqual(o.control.state,'reconnecting')
        o.c.update(socket=11,key=(3,42,5),world=5);self.assertFalse(o.control.suppress(o.c,11));o.c.update(player=True,player_id=333,hp=95);e.frame(o.c)
        self.assertEqual(e.phase,'Ready');self.assertIn('100 -> 95',e.message)
        o.c['hp']=90;o.now+=.2;e.frame(o.c);self.assertEqual(e.last_hp,90)

    def test_death_stale_disabled_failure_and_real_loss(self):
        for change in (dict(hp=0),dict(socket=10),dict(key=(8,42,9))):
            o=Owner();self.assertTrue(o.emergency.start());o.c.update(change);self.assertEqual(o.native.on_io(o.ffi.cast('void *',123)),1);self.assertFalse(o.closed);self.assertEqual(o.control.state,'idle')
        o=Owner();o.emergency.start();o.config.emergency_enabled=False;o.emergency.frame(o.c);self.assertIsNone(o.emergency.pending);self.assertEqual(o.control.state,'idle')
        o=Owner();o.emergency.start();o.now+=2.1;o.emergency.frame(o.c);self.assertIsNone(o.emergency.pending)
        o=Owner();o.emergency.start();o.native.originals['io']=lambda connection:0;self.assertEqual(o.native.on_io(o.ffi.cast('void *',123)),0);self.assertFalse(o.closed);self.assertEqual(o.control.state,'armed')
        o=Owner();o.emergency.start();o.c.update(player=False,key=(8,42,9),world=9);self.assertTrue(o.control.suppress(o.c,11));o.now+=3;o.emergency.frame(o.c)
        self.assertIsNone(o.emergency.pending);self.assertEqual(o.emergency.phase,'Holding');self.assertEqual(o.native.on_io(o.ffi.cast('void *',123)),1);self.assertFalse(o.closed)
        o=Owner();o.emergency.start()
        def broken(*args):raise ValueError('fixture native error')
        o.native.error=broken;self.assertEqual(o.native.on_io(o.ffi.cast('void *',123)),1);self.assertEqual(o.control.state,'idle');self.assertEqual(o.emergency.phase,'Not started')

    def test_input_repeat_focus_typing_modifier_conflicts_and_local_only(self):
        o=Owner();e=o.emergency;e.input({61},False);e.input({61},True);self.assertFalse(e.pending)
        e.input(set(),True);e.input({61,224},True);self.assertFalse(e.pending)
        e.input(set(),True);o.refs.config.set('plugin_keybinds','custom toggle 1 0','F4');e.input({61},True);self.assertFalse(e.pending)
        o.refs.config.remove_option('plugin_keybinds','custom toggle 1 0');e.input(set(),True);e.input({61},True);self.assertTrue(e.pending);self.assertEqual(o.local,[True])
        e.input({61},True);self.assertEqual(e.trial,1)
        e.resume();self.assertIsNone(e.pending);self.assertEqual(o.control.state,'idle')

    def test_hotkey_save_preserves_raw_comments_crlf_and_rejects_conflicts(self):
        raw=b'[plugin_loading_probe]\r\nemergency_key = F4\r\n; keep \xff comment\r\n[other]\r\nvalue = exact\r\n'
        updated=replace_hotkey(raw,'J');self.assertEqual(updated,raw.replace(b'= F4',b'= J'))
        with tempfile.TemporaryDirectory() as tmp:
            o=Owner();path=Path(tmp)/'config.ini';path.write_bytes(raw);o.refs.CONFIGFILE=str(path)
            self.assertFalse(o.emergency.persist('F6'));self.assertEqual(path.read_bytes(),raw)
            self.assertTrue(o.emergency.persist('J'));self.assertEqual(path.read_bytes(),updated);self.assertEqual(o.config.emergency_key,'J')
            self.assertEqual(next((Path(tmp)/'loading-probe-backups').iterdir()).read_bytes(),raw)

    def test_panel_close_reopen_and_start_hit_targets(self):
        o=Owner();o.ui={'scale':1};e=o.emergency;panel,tab,s=e.layout();self.assertTrue(e.visible)
        def click(rect):
            x,y=rect[0]+2,rect[1]+2;self.assertTrue(e.mouse(x,y,0,True));self.assertTrue(e.mouse(x,y,0,False))
        click(e.rects['close']);self.assertFalse(e.visible);click(tab);self.assertTrue(e.visible);click(e.rects['start']);self.assertIsNotNone(e.pending)
        click(e.rects['resume']);self.assertIsNone(e.pending)
        click(e.rects['key']);self.assertTrue(e.binding);e.input({41},True);self.assertFalse(e.binding)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.ini';path.write_bytes(b'[plugin_loading_probe]\nemergency_key = F4\n');o.refs.CONFIGFILE=str(path)
            click(e.rects['key']);e.input({13},True);self.assertFalse(e.binding);self.assertEqual(o.config.emergency_key,'J');self.assertIn(b'= J',path.read_bytes())


if __name__=='__main__':unittest.main(verbosity=2)
