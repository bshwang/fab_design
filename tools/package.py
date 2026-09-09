"""Rebuild the offline Blender extension using Python 3.11+ standard library."""
from pathlib import Path
import hashlib
import json
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'addon/fab_scene_kit'
output = ROOT / 'dist'
version = tomllib.loads((source / 'blender_manifest.toml').read_text(encoding='utf-8'))['version']
package = output / f'fab_scene_kit-{version}.zip'
output.mkdir(exist_ok=True)
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for file in sorted(source.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts and file.suffix not in {'.pyc', '.blend1', '.blend2'}:
            info = zipfile.ZipInfo(file.relative_to(source).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, file.read_bytes(), compresslevel=9)
manifest = {'package': package.name, 'bytes': package.stat().st_size,
            'sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'version': version,
            'assets': len(json.loads((source / 'data/library/index.json').read_text(encoding='utf-8'))['assets'])}
(output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
files = sorted(p for p in output.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(output / 'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in files), encoding='utf-8')
print(json.dumps(manifest, indent=2))
