"""Bootloader DFU must exclude MBR/UICR and require the correct chip/SoftDevice."""
import binascii
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ota import package_bootloader


class BootloaderPackaging(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.uf2 = self.root / "bootloader.uf2"
        self.output = self.root / "bootloader-ota.zip"
        self.blocks = {a: bytearray(b"\xff" * 256)
                       for a in (0, 0xF4000, 0xFD800, 0x10001000)}
        struct.pack_into("<II", self.blocks[0xF4000], 0, 0x20040000, 0xF4101)
        struct.pack_into("<8I", self.blocks[0xFD800], 0,
                         0x1E9E10F1, 0x20227A79, 2, 100,
                         208, 0x28860045, 209, 0xADA52840)
        struct.pack_into("<II", self.blocks[0x10001000], 0x14, 0xF4000, 0xFE000)

    def write(self):
        data = bytearray()
        for index, (addr, payload) in enumerate(sorted(self.blocks.items())):
            block = bytearray(512)
            struct.pack_into("<8I", block, 0, 0x0A324655, 0x9E5D5157, 0x2000,
                             addr, 256, index, len(self.blocks), 0xD663823C)
            block[32:288] = payload
            struct.pack_into("<I", block, 508, 0x0AB16F30)
            data.extend(block)
        self.uf2.write_bytes(data)

    def test_bootloader_only_roundtrip(self):
        self.write()
        result = package_bootloader(self.uf2, "seeeduino_xiao_ble", 0x28860045, self.output)
        self.assertTrue(result["requires_application_reinstall"])
        with zipfile.ZipFile(self.output) as z:
            manifest = json.loads(z.read("manifest.json"))["manifest"]
            self.assertEqual(set(manifest), {"bootloader", "dfu_version"})
            entry = manifest["bootloader"]
            payload = z.read(entry["bin_file"])
            self.assertEqual(len(payload), 0xFD900 - 0xF4000)
            self.assertEqual(payload[:256], self.blocks[0xF4000])
            self.assertEqual(payload[-256:], self.blocks[0xFD800])
            self.assertEqual(set(payload[256:-256]), {255})
            device, revision, _, count, sd, crc = struct.unpack("<HHIHHH", z.read(entry["dat_file"]))
            self.assertEqual((device, revision, count, sd, crc),
                             (0x52, 52840, 1, 0x123, binascii.crc_hqx(payload, 0xFFFF)))

    def test_reject_other_usb_identity(self):
        self.write()
        with self.assertRaises(ValueError):
            package_bootloader(self.uf2, "seeeduino_xiao_ble", 0x28860044, self.output)
        self.assertFalse(self.output.exists())

    def test_reject_softdevice_payload(self):
        self.blocks[0x1000] = bytearray(256)
        self.write()
        with self.assertRaises(ValueError):
            package_bootloader(self.uf2, "seeeduino_xiao_ble", 0x28860045, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
