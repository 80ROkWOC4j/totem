#!/usr/bin/env python3
"""Stage only current build outputs for download, retaining full recovery metadata on request."""
import argparse
import json
from pathlib import Path
import shutil
from artifact_names import FIRMWARE, BOOTLOADER


def stage(source, destination, kind, full=False):
    # Never merge with a previous run's downloadable files.
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    uf2_dir = destination / 'uf2'
    uf2_dir.mkdir()
    if kind == 'firmware':
        ota_dir = destination / 'ota'
        ota_dir.mkdir()
    for metadata in sorted(source.glob('*.json')):
        info = json.loads(metadata.read_text())
        if kind == 'firmware':
            target = info['target']['artifact-name']
            name = target if full else FIRMWARE[target]
            shutil.copy2(source / f'{target}.uf2', uf2_dir / f'{name}.uf2')
            shutil.copy2(source / info['ota']['file'], ota_dir / info['ota']['file'])
        else:
            name = BOOTLOADER[info['board']]
            uf2, = [p for p in info['sha256'] if p.endswith('.uf2')]
            shutil.copy2(source / uf2, uf2_dir / (uf2 if full else f'{name}-boot.uf2'))
    if not any(uf2_dir.iterdir()):
        raise ValueError('No build outputs to publish')
    if full:
        # Keep recovery inputs separate, without duplicating UF2 or OTA payloads.
        recovery = destination / 'recovery'
        recovery.mkdir()
        for pattern in ('*.hex', '*.json', '*.yml'):
            for path in source.glob(pattern):
                shutil.copy2(path, recovery / path.name)
        if (source / 'oled').exists():
            shutil.copytree(source / 'oled', recovery / 'oled')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('firmware', 'bootloader'))
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    source = Path('build/artifacts')
    if args.kind == 'bootloader':
        source /= 'bootloader'
    stage(source, Path('build/download') / args.kind, args.kind, args.full)
