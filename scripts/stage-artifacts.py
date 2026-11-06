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
    if full:
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return
    for metadata in sorted(source.glob('*.json')):
        info = json.loads(metadata.read_text())
        if kind == 'firmware':
            target = info['target']['artifact-name']
            shutil.copy2(source / f'{target}.uf2', destination / f'{FIRMWARE[target]}.uf2')
            shutil.copy2(source / info['ota']['file'], destination / info['ota']['file'])
        else:
            name = BOOTLOADER[info['board']]
            uf2, = [p for p in info['sha256'] if p.endswith('.uf2')]
            shutil.copy2(source / uf2, destination / f'{name}-boot.uf2')
    if not any(destination.iterdir()):
        raise ValueError('No build outputs to publish')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('firmware', 'bootloader'))
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    source = Path('build/artifacts')
    if args.kind == 'bootloader':
        source /= 'bootloader'
    stage(source, Path('build/download') / args.kind, args.kind, args.full)
