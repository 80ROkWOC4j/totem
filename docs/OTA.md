# Bootloader and OTA

OTA runs in the custom bootloader, independently of the ZMK application.
See [UPSTREAM.md](../UPSTREAM.md) for sources and versions.

## Reset button behavior

| Starting state | Action | Result |
| --- | --- | --- |
| Powered off, valid firmware | Power on | Normal firmware |
| Normal firmware | Reset once | BLE OTA after 500 ms |
| Any state | Reset twice within 500 ms | USB UF2 |
| Update mode, valid firmware | Reset once or wait 6 minutes without activity | Normal firmware |
| Update mode | Complete an update | New firmware starts |
| No valid firmware | Power on with USB host attached | USB UF2 recovery |
| No valid firmware | Power on without USB host | BLE OTA recovery |

`2.6.0-totem2` fixes single-reset exit from update mode. On `totem1`, power-cycle
if reset does not return to normal firmware. Hardware verification is listed below.
A charger supplies power but does not count as a USB host.

The dongle OLED shows the mode, version and upload progress, or `NO FIRMWARE` /
`WRONG FILE`. Halves have no mode display, and the dongle cannot show their
bootloader state. Interrupted application transfers must restart from the
beginning; there is no rollback to the previous image.

## Build

Run from the repository root with [Podman](../README.md#build):

```sh
./scripts/container.sh ./scripts/setup.sh
./scripts/container.sh python3 scripts/build-bootloader.py all
./scripts/container.sh python3 scripts/build.py all
```

Applications go to `build/artifacts/`; bootloaders go to its `bootloader/`
subdirectory. Builds do not flash devices. JSON metadata records source and
output hashes; `config_dirty: true` indicates a working-tree build.

## First installation over USB

Match `INFO_UF2.TXT`, USB VID/PID and the installed SoftDevice before flashing.
Keep a known-good application UF2 available.

| Installed identity | Bootloader target | SoftDevice |
| --- | --- | --- |
| nice!nano, `239a:00b3`, `nRF52840-nicenano` | `totem_dongle` | S140 6.1.1 |
| XIAO, `2886:0044`, `nRF52840-SeeedXiao-v1` | `totem_left_ble` / `totem_right_ble` | S140 7.3.0 |
| XIAO Sense, `2886:0045`, `Seeed_XIAO_nRF52840_Sense` or `nRF52840-SeeedXiaoSense-v1` | `totem_left_ble_sense` / `totem_right_ble_sense` | S140 7.3.0 |

Some non-Sense boards ship with a Sense bootloader: match the installed identity,
not the printed board name. Both tested halves use the older Sense identity.
Stop if the SoftDevice differs. Left/right targets share USB IDs, so the loader
cannot reject a file intended for the other half.

1. Connect one device over USB and double-reset.
2. Copy its `update-*_bootloader-2.6.0-totem2_nosd.uf2` to the drive. This preserves
   the SoftDevice; do not substitute a full SoftDevice/bootloader ZIP or raw HEX.
   Keep power connected.
3. After restart, double-reset and confirm `2.6.0-totem2` in `INFO_UF2.TXT`.
4. Copy the matching application UF2 from the table below.

## Android OTA

Use Nordic's [nRF Device Firmware Update](https://play.google.com/store/apps/details?id=no.nordicsemi.android.dfu).
Copy application ZIPs to the phone without extracting them.

| Device | OTA name | Application for the dongle setup |
| --- | --- | --- |
| Dongle | `TOTEM_DFU` | `totem_dongle_central_oled` |
| Left | `TOTEM_L_DFU` | `totem_dongle_left` |
| Right | `TOTEM_R_DFU` | `totem_dongle_right` |

Use `<application>.uf2` for USB or `<application>-ota.zip` for OTA.

1. Power the target, press reset once and select its OTA name in the app.
2. Select its application ZIP and start the transfer.
3. Wait for completion and check normal keyboard operation.

Update each device separately; the dongle does not forward updates to halves.
Keep the phone nearby and the app in the foreground. Start with **PRN enabled
at 12 packets and Request high MTU disabled**. These settings were recommended
before the successful Galaxy Z Flip6 retry; the earlier attempt timed out with
high MTU on and PRN off. The exact timeout cause was not established.

Packages use legacy Nordic DFU with CRC validation, not signed Secure DFU.
Enter OTA only when updating. The protocol cannot distinguish left from right;
select the correct file.

## Bootloader update over BLE (two transfers)

A bootloader transfer overwrites part of the application, so **send the bootloader,
then reinstall the matching application**. Keep both ZIPs on the phone before starting.

Build both targets first, then prepare a pair (right Sense example):

```sh
./scripts/container.sh python3 scripts/bootloader-ota.py totem_right_ble_sense \
  --application-hex build/artifacts/totem_dongle_right.hex
```

The tool validates the target and build metadata and writes
`build/bootloader-ota/totem_right_ble_sense/`:

- `01-*-bootloader-ota.zip`: bootloader only; preserves the SoftDevice.
- `02-*-restore-ota.zip`: matching application.
- `manifest.json` and `README.txt`: hashes and transfer order.

Send `01-...zip` to `TOTEM_R_DFU`, wait for completion/reboot, then rescan and
send `02-...zip` to the same device. Remaining in DFU between transfers is expected.
Use PRN 12, high MTU off and stable power. An interrupted bootloader staging
transfer can also leave the application needing reinstallation.
Bootloader OTA packages are generated only by this explicit command.

## Normal Bluetooth pairing

The halves connect to the dongle automatically. For Bluetooth typing, pair
`TOTEM-Dongle` with the host; USB typing needs no Bluetooth pairing. Select OTA
names only inside the DFU app.

The dongle supports **five host profiles**, plus its two halves. In the default
keymap, hold both layer thumbs to open DEVICE: Y/U/I/O/P select profiles 0–4.
The outer-right apostrophe position runs `BT_CLR` for the selected profile.
Then forget the keyboard on that host and pair again. Occupied profiles are not
automatically overwritten; clearing one preserves the other profiles and halves.

## Export OLED screens

Builds automatically include PNGs, 6x enlargements, an overview and a ZIP:

| Build | Images under `build/artifacts/` | ZIP |
| --- | --- | --- |
| OLED dongle application | `oled/totem_dongle_central_oled/` | `totem-status-oled.zip` |
| Dongle bootloader | `bootloader/oled/` | `totem-bootloader-oled.zip` |

Builds also refresh `docs/images/` previews locally; CI uploads images without
committing previews. To export separately, use Python 3 and a native C compiler
on the host after setup (and an OLED application build for the second command):

```sh
python3 scripts/export-oled.py
python3 scripts/export-status-oled.py
```

Defaults are `build/oled-export/` and `build/status-oled-export/`.
Use `--output DIR` to change the destination or `--preview FILE.png` to refresh
an overview. Scenarios are defined in each script's `STATES` list.

These are firmware-rendered examples, not device captures. The bootloader image
is 128×64; the application preserves its 129×64 logical framebuffer and captures
animations at 300 ms. Manifests record sources, example inputs and image hashes.

## Hardware verification status (2026-11-06)

| Device | Confirmed | Pending |
| --- | --- | --- |
| Dongle | `totem1`, S140 6.1.1; OLED modes; Android application OTA | Install `totem2` and check reset exit |
| Left | `totem2`, S140 7.3.0; USB installation; battery OTA entry/exit and reconnection | Its own BLE firmware transfer |
| Right | S140 7.3.0; reported successful two-transfer `totem2` update | Independent version readback and reset-exit check |

USB recovery after interrupted OTA was verified; BLE-only recovery remains
untested. Complete post-OTA keymap/input checks remain pending. Normal PC
Bluetooth pairing succeeded, but connection timeouts were unresolved; USB was
used instead. All five application and bootloader targets build locally;
remote GitHub Actions has not been run for these changes.
