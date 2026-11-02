"""Fetch pinned fixture data into a dedicated directory. No game is extracted/run."""
import argparse
import configparser
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile
from build_connectivity import upstream

ZIP_SHA = '252b553eb37658f11fda580777972d09d677d24d2771b256bb4fff844c24e7a9'
URL = 'https://github.com/atomizer/sbpe/releases/download/v1.7.0/sbpe-windows-1.7.0.zip'


def prepare(folder):
    if folder.exists():
        raise FileExistsError('Choose a new, dedicated fixture directory')
    data = urllib.request.urlopen(URL, timeout=45).read()
    if hashlib.sha256(data).hexdigest() != ZIP_SHA:
        raise ValueError('Pinned SBPE 1.7.0 fixture archive changed')
    folder.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in ('remote.py', 'loader.py', 'manager.py', 'util.py', 'config.ini', 'build/remote.bin',
                     'cdefs/internals.h', 'cdefs/generated.h'):
            file = folder / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(z.read('config_template.ini' if name == 'config.ini' else name))
    # Deliberately occupied keys and an incomplete old plugin section exercise
    # preserving custom bindings and filling only missing upgrade options.
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(folder / 'config.ini')
    for section in ('plugin_keybinds', 'plugin_loading_probe'):
        if not cfg.has_section(section):cfg.add_section(section)
    cfg.set('plugin_loading_probe', 'enabled', 'yes')
    for key, value in [('sandbox_hacks jump_speed_bonus toggle 2 0', 'F7'), ('fixture panel', 'F6'), ('fixture arm', 'F4')]:
        cfg.set('plugin_keybinds', key, value)
    with (folder / 'config.ini').open('w') as f:cfg.write(f)
    upstream()
    print('Prepared synthetic-test inputs only: ' + str(folder))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    prepare(parser.parse_args().directory.resolve())
