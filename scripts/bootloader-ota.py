#!/usr/bin/env python3
"""Prepare two sequential BLE DFU ZIPs: bootloader, then required ZMK reinstall.

This does not transmit or flash anything. The application's flash area is used
to stage a BLE bootloader update, so keep both ZIPs on the phone before starting.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from artifact_names import BOOTLOADER
from ota import package_application, package_bootloader, validate_application, PROFILES
from uf2 import read_uf2, validate_bootloader
from submodules import bootloader_source

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "totem_dongle": ("nice_nano_v2", 0x239A00B3, "TOTEM_DFU", "totem_dongle_central_oled"),
    "totem_left_ble": ("seeeduino_xiao_ble", 0x28860044, "TOTEM_L_DFU", "totem_dongle_left"),
    "totem_left_ble_sense": ("seeeduino_xiao_ble", 0x28860045, "TOTEM_L_DFU", "totem_dongle_left"),
    "totem_right_ble": ("seeeduino_xiao_ble", 0x28860044, "TOTEM_R_DFU", "totem_dongle_right"),
    "totem_right_ble_sense": ("seeeduino_xiao_ble", 0x28860045, "TOTEM_R_DFU", "totem_dongle_right"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=TARGETS)
    parser.add_argument("--application-hex", required=True, type=Path,
                        help="Matching ZMK HEX and adjacent build metadata JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    board, vid_pid, ble_name, app_target = TARGETS[args.target]
    lock = bootloader_source()
    version = lock["version"]
    short_name = BOOTLOADER[args.target]
    artifacts = ROOT / "build/artifacts/bootloader"
    uf2 = artifacts / f"update-{args.target}_bootloader-{version}_nosd.uf2"
    boot_meta = json.loads((artifacts / f"{args.target}.json").read_text())
    if boot_meta["board"] != args.target or boot_meta["source"] != lock:
        parser.error("Rebuild the selected bootloader; its metadata does not match the source lock")
    if hashlib.sha256(uf2.read_bytes()).hexdigest() != boot_meta["sha256"][uf2.name]:
        parser.error("Bootloader UF2 differs from build metadata")
    validate_bootloader(uf2, vid_pid)
    memory = read_uf2(uf2, 0xD663823C)
    image = bytes(memory.get(a, 0xFF) for a in range(0xF4000, 0xFE000))
    if ble_name.encode() + b"\0" not in image or version.encode() not in image:
        parser.error("Bootloader advertising name/version does not match selected target")
    app_hex = args.application_hex.resolve()
    app_meta = json.loads(app_hex.with_suffix(".json").read_text())
    if (app_meta["target"]["artifact-name"] != app_target or
            app_meta["target"]["board"] != board or
            hashlib.sha256(app_hex.read_bytes()).hexdigest() != app_meta["firmware_sha256"]["hex"]):
        parser.error("Application HEX/metadata does not match the selected device")
    validate_application(app_hex, PROFILES[board])
    output = (args.output or ROOT / f"build/bootloader-ota/{args.target}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Validate both packages in temporary storage before exposing either one.
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        restore_hex = work / f"02-{app_target}-restore.hex"
        shutil.copyfile(app_hex, restore_hex)
        application = package_application(restore_hex, board, work / f"{short_name}-02-app.zip")
        bootloader = package_bootloader(uf2, board, vid_pid,
                                       work / f"{short_name}-01-boot.zip")
        for package in (bootloader, application):
            shutil.copyfile(work / package["file"], output / package["file"])
    (output / "manifest.json").write_text(json.dumps({
        "target": args.target, "ble_name": ble_name, "version": version,
        "hardware_tested": False, "requires_application_reinstall": True,
        "bootloader": bootloader, "application": application,
        "application_build": app_meta, "bootloader_build": boot_meta,
        "sequence": [bootloader["file"], application["file"]],
    }, indent=2) + "\n")
    (output / "README.txt").write_text(f"""BOOTLOADER OTA: TWO REQUIRED TRANSFERS, not hardware-verified yet

Target: {args.target}; BLE name: {ble_name}; bootloader: {version}.
Existing SoftDevice {PROFILES[board]['softdevice']} is preserved.
Have BOTH ZIPs on the phone before starting. Do not unzip them.

1. Enter BLE OTA with one reset, select {ble_name}, then send:
   {bootloader['file']}
2. Wait for completion and reboot. The keyboard will remain in BLE DFU because
   the bootloader was staged over its application. This is expected.
3. Rescan/reconnect to {ble_name} and send:
   {application['file']}
4. Verify keyboard input and single-reset OTA entry/exit after completion.

Use the previously successful Android settings: PRN on/12, high MTU off.
Keep the phone close and power stable, including during the reboot/copy step.
No SoftDevice or UICR payload is in the bootloader ZIP; this is legacy DFU.
This path does NOT automatically enforce left/right or USB board identity.
Do not substitute a different device's ZIP. USB recovery remains available
if the existing bootloader is intact; this BLE bootloader path is not yet
hardware-verified. See manifest.json for payload and source hashes.
""")
    print(output)
    print("Send in order:", bootloader["file"], "then", application["file"])


if __name__ == "__main__":
    main()
