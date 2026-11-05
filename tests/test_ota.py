"""Reject application images that could overwrite the radio stack or settings."""
import sys
from pathlib import Path
import struct
import tempfile
import unittest

from intelhex import IntelHex

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ota import APP_END, PROFILES, package_application, validate_application


class ApplicationValidation(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "app.hex"
        self.profile = PROFILES["nice_nano_v2"]
        self.start = self.profile["start"]
        self.fw = IntelHex()
        self.fw.frombytes(struct.pack("<II", 0x20040000, self.start + 9) + bytes(8),
                          offset=self.start)

    def write(self):
        self.fw.write_hex_file(str(self.path))
        return self.path

    def test_package_roundtrip(self):
        result = package_application(self.write(), "nice_nano_v2")
        self.assertEqual(result["application_bytes"], 16)
        self.assertEqual(result["softdevice"], "S140 6.1.1")

    def test_other_softdevice_layout(self):
        with self.assertRaises(ValueError):
            validate_application(self.write(), PROFILES["seeeduino_xiao_ble"])

    def test_reject_protected_regions(self):
        for address in (0, self.start - 1, APP_END, 0xF4000, 0x10001014):
            with self.subTest(address=hex(address)):
                self.fw[address] = 0
                with self.assertRaises(ValueError):
                    validate_application(self.write(), self.profile)
                del self.fw[address]

    def test_invalid_vectors(self):
        for sp, reset in ((0, self.start + 9), (0x20040004, self.start + 9),
                          (0x20040000, self.start + 8), (0x20040000, 0xF4001)):
            with self.subTest(sp=sp, reset=reset):
                self.fw.frombytes(struct.pack("<II", sp, reset), offset=self.start)
                with self.assertRaises(ValueError):
                    validate_application(self.write(), self.profile)


if __name__ == "__main__":
    unittest.main()
