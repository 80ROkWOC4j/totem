#!/usr/bin/env python3
"""Select independent firmware/bootloader jobs from changed repository paths."""
import sys


def classify(files):
    firmware = 'none'
    bootloader = False
    for path in files:
        if (path.endswith('.md') or path.startswith(('docs/', 'images/', 'keymap-drawer/'))
                or path in ('keymap_drawer.config.yaml', '.github/workflows/draw.yml', '.gitignore')):
            continue
        if path.startswith('config/') and path.endswith(('.keymap', '.json')):
            if firmware == 'none':
                firmware = 'smoke'
        elif (path == 'bootloader' or path.startswith(('bootloader/', 'bootloader-config/'))
              or path in ('scripts/build-bootloader.py', 'scripts/bootloader-ota.py',
                          'scripts/export-oled.py', 'tests/test_bootloader_ota.py',
                          'tests/test_reset_policy.c')):
            bootloader = True
        elif (path in ('zmk', 'zmk-dongle-display', 'build.yaml', 'scripts/build.py',
                       'scripts/setup.sh', 'scripts/freeze.py', 'scripts/export-status-oled.py')
              or path.startswith(('config/', 'firmware/', 'zmk/', 'zmk-dongle-display/',
                                      '.github/build-matrices/', 'tests/test_host_names'))):
            firmware = 'full'
        else:
            # Shared tooling and unknown paths get both jobs to avoid silently
            # missing a newly introduced build dependency.
            firmware, bootloader = 'full', True
    return firmware, bootloader


if __name__ == '__main__':
    firmware, bootloader = classify(sys.stdin.read().splitlines())
    print(f'firmware={firmware}')
    print(f'bootloader={str(bootloader).lower()}')
