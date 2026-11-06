"""Build selection and downloadable contents are independent of compilation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from artifact_names import FIRMWARE, BOOTLOADER


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Scope(unittest.TestCase):
    def test_changes(self):
        classify = load('ci-scope').classify
        for paths, expected in [
            ([], ('none', False)),
            (['README.md', 'README.ko.md', 'images/oled.png', 'keymap-drawer/totem.svg'], ('none', False)),
            (['config/totem.keymap', 'KEYMAP.md'], ('smoke', False)),
            (['config/totem.json'], ('smoke', False)),
            (['config/west.lock.yml', 'config/totem.keymap'], ('full', False)),
            (['firmware/host-names/src/main.c'], ('full', False)),
            (['bootloader', 'bootloader-config/source.json'], ('none', True)),
            (['config/totem.keymap', 'bootloader'], ('smoke', True)),
            (['scripts/ota.py'], ('full', True)),
            (['.devcontainer/Dockerfile'], ('full', True)),
            (['new-build-input'], ('full', True)),
        ]:
            with self.subTest(paths=paths):
                self.assertEqual(classify(paths), expected)


class Downloads(unittest.TestCase):
    def test_minimal_firmware_and_full_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, dest = root / 'source', root / 'download'
            source.mkdir()
            for target, short in FIRMWARE.items():
                for file in (f'{target}.uf2', f'{target}.hex', f'{short}-ota.zip'):
                    (source / file).write_bytes(file.encode())
                (source / f'{target}.json').write_text(json.dumps({
                    'target': {'artifact-name': target}, 'ota': {'file': f'{short}-ota.zip'}}))
            (source / 'oled').mkdir()
            (source / 'oled/preview.png').write_bytes(b'preview')
            dest.mkdir()
            (dest / 'stale.hex').write_bytes(b'old')
            stage = load('stage-artifacts').stage
            stage(source, dest, 'firmware')
            self.assertEqual({p.name for p in dest.iterdir()}, {'uf2', 'ota'})
            self.assertEqual({p.name for p in (dest / 'uf2').iterdir()},
                             {f'{name}.uf2' for name in FIRMWARE.values()})
            self.assertEqual({p.name for p in (dest / 'ota').iterdir()},
                             {f'{name}-ota.zip' for name in FIRMWARE.values()})
            self.assertEqual((dest / 'uf2/left.uf2').read_bytes(), b'totem_dongle_left.uf2')
            stage(source, dest, 'firmware', full=True)
            self.assertTrue((dest / 'recovery/totem_dongle_left.hex').exists())
            self.assertTrue((dest / 'recovery/totem_dongle_left.json').exists())
            self.assertTrue((dest / 'recovery/oled/preview.png').exists())
            self.assertEqual({p.name for p in (dest / 'uf2').iterdir()},
                             {f'{name}.uf2' for name in FIRMWARE})
            self.assertFalse(list((dest / 'recovery').glob('*.uf2')))
            self.assertFalse(list((dest / 'recovery').glob('*-ota.zip')))
            # Switching back to minimal must also discard the recovery files.
            stage(source, dest, 'firmware')
            self.assertFalse((dest / 'recovery').exists())

    def test_minimal_bootloader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, dest = root / 'source', root / 'download'
            source.mkdir()
            for target in BOOTLOADER:
                file = f'update-{target}-version_nosd.uf2'
                (source / file).write_bytes(target.encode())
                (source / f'{target}.json').write_text(json.dumps({'board': target, 'sha256': {file: 'hash'}}))
            load('stage-artifacts').stage(source, dest, 'bootloader')
            self.assertEqual({p.name for p in (dest / 'uf2').iterdir()}, {f'{name}-boot.uf2' for name in BOOTLOADER.values()})
            self.assertEqual((dest / 'uf2/right-sense-boot.uf2').read_bytes(), b'totem_right_ble_sense')
            load('stage-artifacts').stage(source, dest, 'bootloader', full=True)
            self.assertEqual({p.name for p in (dest / 'uf2').iterdir()},
                             {f'update-{target}-version_nosd.uf2' for target in BOOTLOADER})
            self.assertEqual({p.name for p in (dest / 'recovery').iterdir()},
                             {f'{target}.json' for target in BOOTLOADER})
