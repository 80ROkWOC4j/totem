"""Legacy Nordic DFU application packaging for the pinned Adafruit-lineage loader."""
import binascii
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from intelhex import IntelHex
from uf2 import read_uf2, validate_bootloader

PROFILES = {
    "nice_nano_v2": {"softdevice": "S140 6.1.1", "sd_req": 0xB6, "start": 0x26000},
    "seeeduino_xiao_ble": {"softdevice": "S140 7.3.0", "sd_req": 0x123, "start": 0x27000},
}
# The custom bootloader reserves 10 pages; ZMK settings start at 0xEC000.
# Use the stricter bound so neither app data nor the bootloader can be touched.
APP_END = 0xEA000
BOOTLOADER_START = 0xF4000
BOOTLOADER_END = 0xFE000


def package_bootloader(uf2_path, board, vid_pid, output):
    """Legacy bootloader-only DFU. Staging invalidates the installed application.

    Extract only the executable/CF2 range from an already validated self-update
    UF2. Its MBR and UICR blocks must never become part of the BLE payload.
    """
    uf2_path, output = Path(uf2_path).resolve(), Path(output).resolve()
    validate_bootloader(uf2_path, vid_pid)
    memory = read_uf2(uf2_path, 0xD663823C)
    end = max(a for a in memory if BOOTLOADER_START <= a < BOOTLOADER_END) + 1
    payload = bytes(memory.get(a, 0xFF) for a in range(BOOTLOADER_START, end))
    if len(payload) % 4 or not 0 < len(payload) <= BOOTLOADER_END - BOOTLOADER_START:
        raise ValueError("Invalid bootloader payload size")
    profile = PROFILES[board]
    with tempfile.TemporaryDirectory() as directory:
        binary = Path(directory) / "bootloader.bin"
        binary.write_bytes(payload)
        temporary = Path(directory) / "bootloader-ota.zip"
        subprocess.run(["adafruit-nrfutil", "dfu", "genpkg", "--dfu-ver", "0.5",
                        "--dev-type", "0x0052", "--dev-revision", "52840",
                        "--sd-req", hex(profile["sd_req"]),
                        "--bootloader", str(binary), str(temporary)], check=True)
        with zipfile.ZipFile(temporary) as archive:
            manifest = json.loads(archive.read("manifest.json"))["manifest"]
            if set(manifest) != {"bootloader", "dfu_version"} or manifest["dfu_version"] != 0.5:
                raise ValueError("DFU ZIP must contain only the bootloader")
            entry = manifest["bootloader"]
            if archive.read(entry["bin_file"]) != payload:
                raise ValueError("DFU bootloader differs from validated UF2")
            init = archive.read(entry["dat_file"])
            if len(init) != 14:
                raise ValueError("Unexpected legacy bootloader init packet")
            device, revision, _, count, sd, crc = struct.unpack("<HHIHHH", init)
            if (device, revision, count, sd, crc) != (
                    0x52, 52840, 1, profile["sd_req"], binascii.crc_hqx(payload, 0xFFFF)):
                raise ValueError("Invalid bootloader compatibility fields or CRC")
        output.write_bytes(temporary.read_bytes())
    return {"file": output.name, "softdevice": profile["softdevice"],
            "bootloader_bytes": len(payload), "bootloader_start": hex(BOOTLOADER_START),
            "requires_application_reinstall": True,
            "source_uf2_sha256": hashlib.sha256(uf2_path.read_bytes()).hexdigest(),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def validate_application(hex_path, profile):
    fw = IntelHex(str(hex_path))
    if fw.minaddr() != profile["start"] or fw.maxaddr() >= APP_END:
        raise ValueError("Firmware must contain only the expected application region")
    data = fw.tobinstr()
    sp, reset = struct.unpack_from("<II", data)
    if not 0x20000000 < sp <= 0x20040000 or sp % 4:
        raise ValueError("Invalid initial stack pointer")
    if not reset & 1 or not profile["start"] <= (reset & ~1) <= fw.maxaddr():
        raise ValueError("Reset vector is outside the application")
    return data


def package_application(hex_path, board, output=None):
    hex_path = Path(hex_path).resolve()
    profile = PROFILES[board]
    expected = validate_application(hex_path, profile)
    output = Path(output).resolve() if output else hex_path.with_name(hex_path.stem + "-ota.zip")
    # Validate before replacing a previous usable package.
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory) / output.name
        subprocess.run(["adafruit-nrfutil", "dfu", "genpkg", "--dfu-ver", "0.5",
                        "--dev-type", "0x0052", "--sd-req", hex(profile["sd_req"]),
                        "--application", str(hex_path), str(temporary)], check=True)
        with zipfile.ZipFile(temporary) as archive:
            manifest = json.loads(archive.read("manifest.json"))["manifest"]
            if set(manifest) != {"application", "dfu_version"} or manifest["dfu_version"] != 0.5:
                raise ValueError("OTA ZIP must contain an application only")
            app = manifest["application"]
            payload = archive.read(app["bin_file"])
            init = archive.read(app["dat_file"])
            if payload != expected:
                raise ValueError("OTA payload differs from compiled firmware")
            if len(init) != 14:
                raise ValueError("Unexpected legacy init packet length")
            device, _, _, count, sd, crc = struct.unpack("<HHIHHH", init)
            if (device, count, sd, crc) != (0x52, 1, profile["sd_req"],
                                           binascii.crc_hqx(payload, 0xFFFF)):
                raise ValueError("Invalid OTA compatibility fields or CRC")
        output.write_bytes(temporary.read_bytes())
    return {"file": output.name, "softdevice": profile["softdevice"],
            "application_start": hex(profile["start"]), "application_bytes": len(expected),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
