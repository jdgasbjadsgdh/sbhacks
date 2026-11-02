"""Build complete Mac/Windows/web ZIPs from this checkout; never run a game."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = '2026.11.02-connectivity.1'
UPSTREAM_COMMIT = 'ec7fe74579ec6ad7a5e663a2a55672de62fc8361'
UPSTREAM_SHA = 'f5de99f6e13ce048ad5e96fd18efcce75d4ba837ba07297fb5fcc029c01488ce'
CLIENT = 'VR1574197275.mvmmoclient.js'
MARKER = '/* WebBreak runtime                                                           */'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upstream():
    path = ROOT / 'web/upstream' / CLIENT
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = 'https://raw.githubusercontent.com/pjrje4/WebBreak/' + UPSTREAM_COMMIT + '/' + CLIENT
        data = urllib.request.urlopen(url, timeout=45).read()
        if hashlib.sha256(data).hexdigest() != UPSTREAM_SHA:
            raise ValueError('Pinned WebBreak download hash differs; no package built')
        path.write_bytes(data)
    if sha(path) != UPSTREAM_SHA:
        raise ValueError('Pinned WebBreak input hash differs')
    return path


def metadata(folder, platform):
    hashes = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    info = dict(version=VERSION, platform=platform, created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                launches_or_restarts_during_install=False,
                validation='Offline native/Windows/web and installer fixtures; live SC early-reentry result pending.',
                sha256=hashes)
    (folder / 'package-info.json').write_text(json.dumps(info, indent=2) + '\n')
    (folder / 'package.sha256').write_text(''.join(v + '  ' + k + '\n' for k, v in hashes.items()))


def tree(source, target):
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', 'test_*',
                                                              'upstream', 'package-info.json', 'package.sha256'))


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    names = {platform: 'SBPE-Connectivity-' + platform + '-2026-11-02' for platform in ('Mac', 'Windows', 'Web')}
    if any((output / (name + '.zip')).exists() for name in names.values()):
        raise FileExistsError('Release archive already exists; choose a new output directory')
    original = upstream().read_text()
    assert original.count(MARKER) == 1 and 'client build 1574197275' in original
    plugin = (ROOT / 'web/sc-boss-test.js').read_text()
    client = original.replace(MARKER, plugin + '\n\n' + MARKER, 1)
    manifest = []
    with tempfile.TemporaryDirectory(prefix='sbpe-connectivity-') as temp:
        stage = Path(temp)
        mac = stage / names['Mac'];tree(ROOT / 'mac', mac)
        subprocess.run(['xcrun', 'clang', '-arch', 'x86_64', '-mmacosx-version-min=10.14', '-march=x86-64',
                        '-std=c11', '-dynamiclib', '-O2', '-Wl,-install_name,@rpath/sbpe-mac.dylib',
                        '-o', str(mac / 'sbpe-mac.dylib'), str(mac / 'src/sbpe.c'),
                        str(mac / 'src/websocket_transport.m'), '-fobjc-arc', '-framework', 'Foundation', '-lz', '-lpthread'], check=True)
        win = stage / names['Windows'];tree(ROOT / 'windows', win)
        web = stage / names['Web'];tree(ROOT / 'web', web)
        (web / 'www.starbreak.com').mkdir()
        (web / 'www.starbreak.com' / CLIENT).write_text(client)
        (web / 'payload-data.js').write_text('window.SBPELoadingPayload = ' + json.dumps(dict(plugin=plugin, client=client), ensure_ascii=True) + ';\n')
        (web / 'webbreak-build-info.json').write_text(json.dumps(dict(connectivity_version=VERSION,
            upstream_commit=UPSTREAM_COMMIT, upstream_sha256=UPSTREAM_SHA,
            combined_sha256=hashlib.sha256(client.encode()).hexdigest(),
            sc_test_initially_armed=False, live_SC_validation='pending', changes_to_original_game_body=False), indent=2) + '\n')
        for platform, folder in [('Mac', mac), ('Windows', win), ('Web', web)]:
            shutil.copy2(ROOT / 'docs/RUSH-AND-SC.md', folder / 'RUSH AND SC.md')
            metadata(folder, platform)
            archive = output / (folder.name + '.zip')
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
                for file in sorted(folder.rglob('*')):
                    if file.is_file():z.write(file, str(file.relative_to(stage)))
            manifest.append(dict(platform=platform.lower(), version=VERSION, file='downloads/' + archive.name,
                                 sha256=sha(archive), bytes=archive.stat().st_size))
            shutil.copytree(folder, output / folder.name)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(''.join(p['sha256'] + '  ' + Path(p['file']).name + '\n' for p in manifest))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output.resolve())
