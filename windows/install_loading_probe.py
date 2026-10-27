"""Install a narrow SBPE 1.7 overlay; preserve unrelated plugins and keybinds."""
import argparse
import configparser
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

ROOT = Path(__file__).resolve().parent
MARKER = '# SBPE_LOADING_PORT_20261022'
MOUSE_MARKER = '# SBPE_LOADING_UI_20261024'


def upgrade_mouse(text):
    old = """def hook_mouseButton(x, y, button, down, userData):
    x = round(x * refs.scaleX)
    y = round(y * refs.scaleY)
    if not _loading_probe_call('mouse', x / refs.scaleX, y / refs.scaleY, button, down):
        ORIGS['mouseButtonCallback'](x, y, button, down, userData)"""
    new = """def hook_mouseButton(x, y, button, down, userData):
    # SBPE_LOADING_UI_20261024
    # The overlay is in window coordinates; scale only unconsumed game input.
    if _loading_probe_call('mouse', x, y, button, down):
        return
    x = round(x * refs.scaleX)
    y = round(y * refs.scaleY)
    ORIGS['mouseButtonCallback'](x, y, button, down, userData)"""
    if MOUSE_MARKER in text:
        if text.count(new) != 1:
            raise ValueError('Loading mouse hook was customized; no files changed')
        return text
    return once(text, old, new)


def add_options(text, section, options):
    lines = text.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('['):
            if inside:
                lines[i:i] = [key+' = '+value+'\n' for key,value in options]
                return ''.join(lines)
            inside = stripped == '['+section+']'
    if not text.endswith('\n'):
        lines.append('\n')
    lines.extend(key+' = '+value+'\n' for key,value in options)
    return ''.join(lines)


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('SBPE source differs from expected 1.7.0; no files changed: '+old[:60])
    return text.replace(old, new, 1)


def patched(root):
    result = {}
    for name in ('remote.py', 'loader.py', 'manager.py'):
        text = (root/name).read_text()
        if MARKER in text:
            if name == 'remote.py':
                revised = upgrade_mouse(text)
                if revised != text:
                    compile(revised, str(root/name), 'exec')
                    result[name] = revised
            continue
        if name == 'remote.py':
            helper = '''# SBPE_LOADING_PORT_20261022
def _loading_probe_call(method, *args):
    plugin = refs.manager._active.get('plugin_loading_probe') if refs.manager else None
    if plugin is None:
        return None
    try:
        return getattr(plugin, method)(*args)
    except Exception:
        logging.exception('Loading plugin callback failed: '+method)
        refs.manager._remove('plugin_loading_probe')
        return None


'''
            text = once(text, '@ffi.def_extern()\ndef hook_DoEvents():', helper+'@ffi.def_extern()\ndef hook_DoEvents():')
            text = once(text, "    ORIGS['XDL_Clear'](refs.stage[0].backgroundColor)", "    ORIGS['XDL_Clear'](refs.stage[0].backgroundColor)\n    _loading_probe_call('beginCamera')")
            text = once(text, "    refs.manager.runCallbacks('onPresent')\n    ORIGS['XDL_Present']()", "    try:\n        refs.manager.runCallbacks('onPresent')\n        ORIGS['XDL_Present']()\n    finally:\n        _loading_probe_call('endCamera')")
            text = once(text, "    ORIGS['mouseButtonCallback'](x, y, button, down, userData)", "    if not _loading_probe_call('mouse', x / refs.scaleX, y / refs.scaleY, button, down):\n        ORIGS['mouseButtonCallback'](x, y, button, down, userData)")
        elif name == 'loader.py':
            insert = '''    # SBPE_LOADING_PORT_20261022
    if conf.getboolean('plugin_loading_probe', 'enabled', fallback=False):
        try:
            from prepare_loading_probe import prepare
            prepare(exepath, SCRIPTPATH)
            logging.info('loading plugin symbols prepared for this game build')
        except Exception as error:
            logging.warning('loading plugin unavailable: %s', error)
            stale_target = os.path.join(SCRIPTPATH, 'loading-probe-target.json')
            if os.path.isfile(stale_target):
                os.unlink(stale_target)

'''
            text = once(text, "    os.environ['SBPE_SYMFILE'] = SYMFILE", insert+"    os.environ['SBPE_SYMFILE'] = SYMFILE")
        else:
            # Plugins without onUnload behave exactly as before.
            if text.count('del self._active[mname]') != 2 or text.count('del self._active[name]') != 1:
                raise ValueError('Unexpected manager removal lifecycle; no files changed')
            text = text.replace('del self._active[mname]', 'self._remove(mname)').replace('del self._active[name]', 'self._remove(name)')
            method = '''    # SBPE_LOADING_PORT_20261022
    def _remove(self, name):
        plugin = self._active.pop(name, None)
        unload = getattr(plugin, 'onUnload', None)
        if callable(unload):
            try:
                unload()
            except Exception:
                report_exception(name+'.onUnload')

'''
            text = once(text, '    def run(self):\n', method+'    def run(self):\n')
        if name == 'remote.py':
            text = upgrade_mouse(text)
        compile(text, str(root/name), 'exec')
        result[name] = text
    config = (root/'config.ini').read_text()
    parser = configparser.ConfigParser(interpolation=None);parser.optionxform = str
    parser.read_string(config)
    used = {value.strip().lower() for _, value in parser.items('plugin_keybinds')} if parser.has_section('plugin_keybinds') else set()
    arm = next((key for key in ('F7', 'F4') if key.lower() not in used), '')
    if not parser.has_section('plugin_loading_probe'):
        panel = next((key for key in ('F6', 'F11') if key.lower() not in used), '')
        finish = '' if 'f9' in used else 'F9'
        config += '\n[plugin_loading_probe]\nenabled = yes\npanel_key = {}\narm_key = {}\nfinish_key = {}\nstage_early_seconds = 360\ncamera_speed = 900\nui_scale = 0\nui_font = TenbyFive\n'.format(panel, arm, finish)
        result['config.ini'] = config
    else:
        additions = [(key, value) for key,value in [('enabled','yes'), ('arm_key',arm), ('ui_scale','0'), ('ui_font','TenbyFive')]
                     if not parser.has_option('plugin_loading_probe', key)]
        if additions:
            result['config.ini'] = add_options(config, 'plugin_loading_probe', additions)
    current = result.get('config.ini', config)
    check = configparser.ConfigParser(interpolation=None);check.read_string(current)
    additions = [(key,value) for key,value in [('multibox_enabled','yes'),('multibox_port','47812'),('multibox_group_key',uuid.uuid4().hex)]
                 if not check.has_option('plugin_loading_probe',key)]
    if additions:
        result['config.ini'] = add_options(current,'plugin_loading_probe',additions)
    current=result.get('config.ini',current)
    check=configparser.ConfigParser(interpolation=None);check.read_string(current)
    occupied=set(used)
    occupied.update(value.strip().lower() for section in check.sections() for key,value in check.items(section,raw=True)
                    if not (section=='plugin_loading_probe' and key=='emergency_key'))
    for key in ('panel_key','arm_key','finish_key'):
        occupied.add(check.get('plugin_loading_probe',key,fallback='').strip().lower())
    additions=[(key,value) for key,value in [('emergency_enabled','yes'),('emergency_key','' if 'f4' in occupied else 'F4')]
               if not check.has_option('plugin_loading_probe',key)]
    if additions:result['config.ini']=add_options(current,'plugin_loading_probe',additions)
    return result


def install(root):
    root = Path(root).resolve()
    package_info = ROOT/'package-info.json'
    if package_info.is_file():
        for name, expected in json.loads(package_info.read_text())['sha256'].items():
            source = ROOT/name
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError('Package integrity check failed; extract a fresh complete download: '+name)
    changes = patched(root)  # validate every patch before writing any file
    backup = root/'loading-probe-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    payload = ['loading_probe_logic.py', 'loading_probe_native.py', 'loading_probe_x86.py', 'loading_probe_ui.py', 'loading_probe_runtime.py',
               'loading_multibox.py','loading_multibox_bus.py','loading_multibox_native.py','loading_emergency.py','loading_keybinds.py',
               'prepare_loading_probe.py', 'plugins/loading_probe.py']
    for name in payload:
        if not (ROOT/name).is_file():
            raise ValueError('Incomplete download; extract the entire package: '+name)
    if not (ROOT/'loading_probe_vendor/elftools/__init__.py').is_file():
        raise ValueError('The bundled symbol reader is missing; extract the entire package.')
    backup.mkdir(parents=True)
    for name in list(changes)+payload:
        source = root/name
        if source.is_file():
            dest = backup/name;dest.parent.mkdir(parents=True, exist_ok=True);shutil.copy2(str(source), str(dest))
    for name in payload:
        source = ROOT/name;dest = root/name
        if source.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True);shutil.copy2(str(source), str(dest)+'.new');os.replace(str(dest)+'.new', str(dest))
    vendor = root/'loading_probe_vendor'
    if (ROOT/'loading_probe_vendor').resolve() != vendor.resolve() and not vendor.exists():
        shutil.copytree(str(ROOT/'loading_probe_vendor'), str(vendor))
    for name, text in changes.items():
        dest = root/name;dest.with_suffix(dest.suffix+'.new').write_text(text);os.replace(str(dest)+'.new', str(dest))
    print('Loading plugin installed. Backup: '+str(backup))
    print('No game launched or restarted. Start SBPE normally on Windows when ready.')


if __name__ == '__main__':
    arguments = argparse.ArgumentParser();arguments.add_argument('--root', default=str(ROOT.parent))
    install(arguments.parse_args().root)
