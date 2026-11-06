#!/usr/bin/env python3
"""Merge requested firmware targets with the firmware required for bootloader OTA."""
import argparse
from pathlib import Path
import yaml

RESTORE_TARGETS = ('totem_dongle_central_oled', 'totem_dongle_left', 'totem_dongle_right')


def resolve(requested, all_targets, firmware, bootloader):
    entries = {entry['artifact-name']: entry for entry in requested if firmware}
    if bootloader:
        available = {entry['artifact-name']: entry for entry in all_targets}
        for name in RESTORE_TARGETS:
            entries.setdefault(name, available[name])
    return {'include': list(entries.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', required=True, type=Path)
    parser.add_argument('--firmware', choices=('true', 'false'), required=True)
    parser.add_argument('--bootloader', choices=('true', 'false'), required=True)
    parser.add_argument('--output', type=Path, default=Path('build/ci-matrix.yaml'))
    args = parser.parse_args()
    matrix = resolve(yaml.safe_load(args.matrix.read_text())['include'],
                     yaml.safe_load(Path('build.yaml').read_text())['include'],
                     args.firmware == 'true', args.bootloader == 'true')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(matrix, sort_keys=False))
