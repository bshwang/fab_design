"""Check artifact integrity and portability without importing Blender."""
from pathlib import Path, PurePosixPath
import ast
import base64
import hashlib
import json
import re
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'addon/fab_scene_kit'
manifest = json.loads((ROOT / 'dist/manifest.json').read_text(encoding='utf-8'))
package = ROOT / 'dist' / manifest['package']
assert package.stat().st_size == manifest['bytes']
assert hashlib.sha256(package.read_bytes()).hexdigest() == manifest['sha256']
with zipfile.ZipFile(package) as archive:
    assert archive.testzip() is None
    names = set(archive.namelist())
    files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.blend1', '.blend2'}}
    assert names == files, 'Source/package file lists differ'
    for name in names:
        rel = PurePosixPath(name)
        assert not rel.is_absolute() and '..' not in rel.parts and ':' not in name
        assert archive.read(name) == (source / name).read_bytes(), name
        if name.endswith('.py'):
            ast.parse(archive.read(name).decode('utf-8'), filename=name)
index = json.loads((source / 'data/library/index.json').read_text(encoding='utf-8'))
extension = tomllib.loads((source / 'blender_manifest.toml').read_text(encoding='utf-8'))
assert extension['version'] == index['version'] == manifest['version']
assert len(index['assets']) == manifest['assets'] == 52
assert {p.stem for p in (source / 'data/library/previews').glob('*.png')} == set(index['assets'])
assert {p.name for p in (source / 'data/templates').glob('*.blend')} == {'blank.blend', 'overview.blend', 'example.blend'}
catalog = ROOT / 'dist' / f'FAB_Scene_Kit_Asset_Catalog_{manifest["version"]}.html'
html = catalog.read_text(encoding='utf-8')
assert '__VERSION__' not in html and '__CATALOG_DATA__' not in html
data = json.loads(re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>', html, re.S)[1])
assert data['version'] == manifest['version']
assert {a['id'] for a in data['assets']} == set(index['assets'])
for asset in data['assets']:
    assert base64.b64decode(asset['image'].split(',')[1], validate=True) == (source / 'data/library/previews' / (asset['id'] + '.png')).read_bytes()
assert len(data['images']) == 4
for image in data['images'].values():
    assert base64.b64decode(image.split(',')[1], validate=True).startswith(b'\xff\xd8\xff')
manual = ROOT / 'dist' / f'FAB_Scene_Kit_User_Manual_{manifest["version"]}_KO.html'
manual_html = manual.read_text(encoding='utf-8')
assert not re.search(r'\{\{[^}]+\}\}|__VERSION__', manual_html)
manual_images = re.findall(r'<img[^>]+src="data:image/(png|jpeg);base64,([^"]+)"', manual_html)
assert len(manual_images) == 14
for kind, encoded in manual_images:
    raw = base64.b64decode(encoded, validate=True)
    assert raw.startswith(b'\x89PNG\r\n\x1a\n' if kind == 'png' else b'\xff\xd8\xff')
assert len(re.findall(r'<section class="chapter"', manual_html)) == 11
assert len(re.findall(r'<a href="#[^"]+" data-target=', manual_html)) == 11
assert "connect-src 'none'" in manual_html
for line in (ROOT / 'dist/SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest() == digest, name
print(json.dumps({'version': manifest['version'], 'package_files': len(files), 'assets': len(index['assets']), 'templates': 3, 'catalog_embedded_images': 56, 'manual_embedded_images': len(manual_images), 'checksums': 'passed', 'source_matches_package': True}, indent=2))
