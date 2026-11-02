"""Run the real plugin update handler and settings editor against temporary INIs."""
import ast
from pathlib import Path
import tempfile
import types
import unittest
from test_emergency_windows import Owner,NAMES
from loading_keybinds import KeybindPanel,ACTIONS,replace_binding

NAMES.update({'F1':58,'F2':59,'F3':60,'F5':62,'F8':65,'F10':67,'F12':69,'D':7})
ROOT=Path(__file__).resolve().parent


class KeybindTests(unittest.TestCase):
    def owner(self,path):
        o=Owner();o.ui={'scale':1};o.old_keys=set();o.refs.CONFIGFILE=str(path);o.bindings=KeybindPanel(o)
        return o

    def test_all_actions_persist_and_preserve_comments_conflicts_clear(self):
        raw=b'; keep \xff\r\n[plugin_loading_probe]\r\nemergency_key = F4\r\npanel_key = F6\r\n[other]\r\nkeep = exact\r\n'
        for option,_ in ACTIONS:
            updated=replace_binding(raw,option,'F1');self.assertIn(b'keep = exact\r\n',updated);self.assertIn((option+' = F1\r\n').encode(),updated)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.ini';path.write_bytes(raw);o=self.owner(path);editor=o.bindings
            self.assertFalse(editor.save('rush_key','F4'));self.assertEqual(path.read_bytes(),raw)
            o.refs.config['plugin_keybinds']['custom toggle yes no']='F2';self.assertFalse(editor.save('boss_key','F2'));self.assertEqual(path.read_bytes(),raw)
            self.assertTrue(editor.save('emergency_key',''));self.assertTrue(editor.save('rush_key','F4'))
            self.assertEqual(o.config.rush_key,'F4');self.assertEqual(o.config.emergency_key,'');self.assertIn(b'; keep \xff\r\n',path.read_bytes());self.assertEqual(len(list((Path(tmp)/'loading-probe-backups').iterdir())),2)

    def test_actual_plugin_dispatch_and_no_fire_from_capture_key(self):
        source=ast.parse((ROOT/'plugins/loading_probe.py').read_text())
        cls=next(node for node in source.body if isinstance(node,ast.ClassDef) and node.name=='Plugin')
        method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='afterUpdate')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.ini';path.write_text('[plugin_loading_probe]\nemergency_key = F4\n');o=self.owner(path)
            keys=o.ffi.new('uint8_t[512]')
            def state(count):count[0]=512;return keys
            o.lib.SDL_GetKeyboardState=state;o.allowed=True;o.input_allowed=lambda:o.allowed;o.sync_camera=lambda c:None;o.beginCamera=lambda:None;o.multibox=None
            o.toggle_panel=lambda:o.events.append(('panel',{}));o.arm_selected=lambda:o.arm(o.control.preset);o.preview=lambda:o.events.append(('preview',{}));o.toggle_camera=lambda:o.events.append(('camera',{}))
            namespace={'ffi':o.ffi,'lib':o.lib};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual-plugin-afterUpdate','exec'),namespace)
            update=types.MethodType(namespace['afterUpdate'],o)
            def press(*codes):
                for i in range(512):keys[i]=i in codes
                update()
            self.assertTrue(o.bindings.save('rush_key','F1'));press(58);self.assertEqual((o.control.state,o.control.preset),('armed','rush'));self.assertEqual(o.local[-1],False)
            o.control.cancel(o.c);press();self.assertTrue(o.bindings.save('boss_key','F2'));press(59);self.assertEqual(o.control.preset,'boss');o.control.cancel(o.c);press()
            self.assertTrue(o.bindings.save('preview_key','F3'));press(60);self.assertEqual(o.events[-1][0],'preview');press()
            self.assertTrue(o.bindings.save('camera_key','F5'));press(62);self.assertEqual(o.events[-1][0],'camera');press()
            mirrored=[];o.multibox=types.SimpleNamespace(update=lambda c,allowed:mirrored.append(allowed))
            o.bindings.open('emergency_key');press(7);self.assertEqual(o.config.emergency_key,'D');self.assertIsNone(o.emergency.pending)
            self.assertEqual((o.dx,o.dy),(0,0))
            self.assertFalse(mirrored[-1])
            o.bindings.visible=False;press(7);self.assertIsNone(o.emergency.pending);press();press(7);self.assertIsNotNone(o.emergency.pending);self.assertEqual(o.local[-1],True)

    def test_pagination_modal_mouse_escape_and_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.ini';path.write_text('[plugin_loading_probe]\n');o=self.owner(path);e=o.bindings;e.open()
            for width,height in [(300,300),(320,380),(800,600),(1280,720),(3840,2160)]:
                o.refs.windowW,o.refs.windowH=width,height;r=e.layout();x,y,w,h=r['panel'];self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0);self.assertLessEqual(x+w,width);self.assertLessEqual(y+h,height)
                for rect in e.rects.values():self.assertGreaterEqual(rect[1],y);self.assertLessEqual(rect[1]+rect[3],y+h)
            o.refs.windowW,o.refs.windowH=320,380;r=e.layout();self.assertGreater(r['pages'],1)
            def click(rect):
                x,y=rect[0]+2,rect[1]+2;self.assertTrue(e.mouse(x,y,0,True));self.assertTrue(e.mouse(x,y,0,False))
            click(e.rects['next']);self.assertEqual(e.page,1);e.layout();option=r['rows'][-1][0]
            self.assertTrue(e.mouse(0,0,0,True));self.assertTrue(e.mouse(0,0,0,False));self.assertTrue(e.visible)
            e.open('emergency_key');self.assertTrue(e.input({41},True));self.assertIsNone(e.target);self.assertTrue(e.visible)
            e.input(set(),True);e.input({41},True);self.assertFalse(e.visible)


if __name__=='__main__':unittest.main(verbosity=2)
