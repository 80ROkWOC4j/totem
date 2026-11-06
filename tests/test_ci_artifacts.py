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
            expected = {f'{name}{suffix}' for name in FIRMWARE.values() for suffix in ('.uf2', '-ota.zip')}
            self.assertEqual({p.name for p in dest.iterdir()}, expected)
            self.assertEqual((dest / 'left.uf2').read_bytes(), b'totem_dongle_left.uf2')
            stage(source, dest, 'firmware', full=True)
            self.assertTrue((dest / 'totem_dongle_left.hex').exists())
            self.assertTrue((dest / 'totem_dongle_left.json').exists())
            self.assertTrue((dest / 'oled/preview.png').exists())
            self.assertFalse((dest / 'left.uf2').exists())

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
            self.assertEqual({p.name for p in dest.iterdir()}, {f'{name}-boot.uf2' for name in BOOTLOADER.values()})
            self.assertEqual((dest / 'right-sense-boot.uf2').read_bytes(), b'totem_right_ble_sense')
