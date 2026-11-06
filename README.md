# TOTEM

English | [한국어](README.ko.md)

ZMK firmware repository for TOTEM keyboards, with optional OLED dongle, Bluetooth OTA bootloader, and Bluetooth host-name display/editing.

## Keymap & Pairing

Edit [`config/totem.keymap`](config/totem.keymap); GitHub Actions updates the keymap diagram automatically.

![TOTEM keymap layers](keymap-drawer/totem.svg)

- **Dongle pairing**: When using a dongle, the left and right halves connect to it automatically. Pair `TOTEM-Dongle` on the host only for Bluetooth typing; wired USB needs no pairing.
- **Profiles**: The dongle supports up to 5 host profiles. Switch paired devices with `BT 1`–`BT 5` and clear a saved pairing with `BT_CLR`.

## Build

Prebuilt UF2 files and OTA ZIPs are available under **Artifacts** in [GitHub Actions](https://github.com/80ROkWOC4j/totem/actions).

A Dev Container is configured for local builds—set `"dev.containers.dockerPath": "podman"` to build easily:

```sh
./scripts/container.sh ./scripts/setup.sh
./scripts/container.sh python3 scripts/build.py all
./scripts/container.sh python3 scripts/build-bootloader.py all
```

Replace `all` with a target name to build a single target:

- **Firmware** ([`build.yaml`](build.yaml)): `totem_dongle_central_oled`, `totem_dongle_left`, `totem_dongle_right` (with dongle) or `totem_left`, `totem_right` (standalone)
- **Bootloader**: `totem_dongle`, `totem_left_ble`, `totem_right_ble`, `totem_left_ble_sense`, `totem_right_ble_sense`

Outputs are generated in `build/artifacts/` (and `build/artifacts/bootloader/` for bootloaders).

### CI builds and downloads

Downloads are split into **firmware-uf2** (USB installation) and **firmware-ota**
(phone OTA packages). **bootloader-uf2** is separate. Manual full builds also
provide **firmware-recovery** and **bootloader-recovery** for HEX, metadata and
previews; these do not duplicate the install files. Full-build UF2 files retain
original build filenames: extract each recovery archive and its matching UF2
archive into the same local artifacts directory when preparing bootloader OTA.


Documentation, images and drawing-only changes skip firmware builds. Keymap/layout
changes build the two smoke targets (standalone left and OLED dongle central).
Firmware/configuration dependencies build all firmware targets; bootloader changes
build the five bootloaders independently. Shared tooling or unknown build inputs
build both. A new branch is compared with its merge base on `main`.

Automatic downloads expire after 7 days and contain only UF2 and application OTA
ZIPs (bootloader downloads contain only UF2). Manual downloads last 30 days.
**Build All Firmware** also builds bootloaders and retains HEX, metadata, source
locks and OLED previews for recovery and debugging. Single-target manual builds
remain minimal. Existing downloads keep their original expiry dates.

| Device | Application OTA file |
| --- | --- |
| Dongle | `dongle-ota.zip` |
| Left / right with dongle | `left-ota.zip` / `right-ota.zip` |
| Left / right standalone | `left-solo-ota.zip` / `right-solo-ota.zip` |

Minimal downloads use matching short UF2 names (`left.uf2`, `left-solo.uf2`, etc.).
Bootloader UF2 names are `dongle-boot.uf2`, `left-boot.uf2`, `right-boot.uf2`,
`left-sense-boot.uf2` and `right-sense-boot.uf2`. Match the installed board identity.
Build target names and recovery HEX/JSON filenames stay unchanged. The outer
Actions artifact name includes the run number and source commit; keep versions
in separate phone folders to avoid mixing identically named OTA files.

## Bootloader & OTA

The custom bootloader (`2.6.0-totem2`) runs independently of the ZMK firmware.

| Action | Behavior |
| --- | --- |
| **Single reset** | Enter BLE OTA after 500 ms (reset once again or wait 6 min idle to return to firmware) |
| **Double reset** (< 500 ms) | Enter USB UF2 drive mode |
| **Power on without valid firmware** | USB UF2 if attached to a USB data host (not a charger), otherwise BLE OTA |

The dongle OLED shows bootloader mode, version, upload progress, or `NO FIRMWARE` / `WRONG FILE` (halves have no display). Interrupted transfers have no rollback—restart the transfer from the beginning.

### 1. Initial USB Bootloader Installation

Match `INFO_UF2.TXT`, USB VID:PID, and SoftDevice version before flashing. Some non-Sense XIAO boards ship with a Sense bootloader—match the **installed `INFO_UF2.TXT` identity**, not the printed board name.

| Installed `INFO_UF2.TXT` (`VID:PID`) | Bootloader target | SoftDevice |
| --- | --- | --- |
| `nRF52840-nicenano` (`239a:00b3`) | `totem_dongle` | S140 6.1.1 |
| `nRF52840-SeeedXiao-v1` (`2886:0044`) | `totem_left_ble` / `totem_right_ble` | S140 7.3.0 |
| `Seeed_XIAO_nRF52840_Sense` or `nRF52840-SeeedXiaoSense-v1` (`2886:0045`) | `totem_left_ble_sense` / `totem_right_ble_sense` | S140 7.3.0 |

1. Connect one device at a time over USB and double-press reset to prepare for flashing.
2. Drag and drop `update-<target>_bootloader-2.6.0-totem2_nosd.uf2` onto the drive.
3. After reboot, double-reset again to confirm `2.6.0-totem2` in `INFO_UF2.TXT`, then install the ZMK firmware `<firmware>.uf2`.

### 2. Android BLE OTA Update

Install Nordic [nRF Device Firmware Update](https://play.google.com/store/apps/details?id=no.nordicsemi.android.dfu) and set **Packets Receipt Notifications (PRN) = ON (12)** and **Request high MTU = OFF**. Copy `*-ota.zip` files to the phone without extracting.

| Device | BLE OTA name | Dongle firmware target | Standalone firmware target |
| --- | --- | --- | --- |
| Dongle | `TOTEM_DFU` | `totem_dongle_central_oled` | — |
| Left | `TOTEM_L_DFU` | `totem_dongle_left` | `totem_left` |
| Right | `TOTEM_R_DFU` | `totem_dongle_right` | `totem_right` |

Press reset once on the target device, select its BLE OTA name in the DFU app (do not pair OTA names in OS Bluetooth settings), and upload the matching `<firmware>-ota.zip`. Update each device separately; left and right halves share hardware IDs and cannot reject a file meant for the other side, so double-check the filename.

### 3. Bootloader Update over BLE (Two Sequential Transfers)

Updating the bootloader over BLE overwrites part of the firmware region, so **you must also reinstall the firmware when updating the bootloader over OTA**:

```sh
./scripts/container.sh python3 scripts/bootloader-ota.py totem_right_ble_sense \
  --application-hex build/artifacts/totem_dongle_right.hex
```

Upload `<device>-01-boot.zip` generated in `build/bootloader-ota/<target>/`, wait for the device to reboot into DFU mode, rescan, and upload `<device>-02-app.zip`.

## OLED & Bluetooth Host Names

The dongle OLED displays names for the selected Bluetooth profile in the order **`saved alias → automatic host name → BT 1 … BT 5`** (shown for the selected profile even while USB output is active). Names support up to **24 ASCII characters** (scrolling if longer; unsupported characters such as Korean appear as `?`). Names and aliases persist across power cycles and clear on `BT_CLR`.

### Editing an Alias on the Keyboard

Requires the OLED dongle and a paired profile (host may be offline):

1. Select the profile on the `DEVICE` layer and release all keys.
2. Hold both layer thumbs, hold **`Q` (`BT name`) for ≥ 0.8 s**, then release all keys to open `BT n NAME` (if overridden in ZMK Studio, bind `Edit BT host name (hold)`).
3. Type using physical QWERTY positions regardless of OS language/keymap (`-`/`_` on outer left Ctrl; saving empty restores automatic naming; 60 s idle cancels):

| Thumb key (left → right) | Editor action | OLED |
| --- | --- | --- |
| Left GUI | Cancel | `ESC` |
| Symbol layer | Backspace | `<` |
| Navigation layer (hold) | Top-row digits `1–0` | `#` |
| Space | Space | `_` |
| Right Shift (hold) | Uppercase / `_` | `^` |
| Right Alt | Save | `OK` |

![Connection states and host-name editor](images/oled-status.png)

![Bootloader modes, transfer progress and errors](images/oled-bootloader.png)

Previews above are rendered from firmware drawing code. Builds refresh `images/` and bundle full PNG sets under `build/artifacts/` (standalone export: `python3 scripts/export-oled.py` and `python3 scripts/export-status-oled.py`).

## Sources & Dependency Maintenance

Started by merging Totem/dongle configurations from [`Keycoon/zmk-config-totem`](https://github.com/Keycoon/zmk-config-totem) (`b66b405`) and [`a741725193/zmk-sofle-dongle`](https://github.com/a741725193/zmk-sofle-dongle) (`d3f2f76`).

| Submodule | Fork | Notes |
| --- | --- | --- |
| `zmk/` | [`80ROkWOC4j/zmk`](https://github.com/80ROkWOC4j/zmk) | ZMK 0.3 / Zephyr 3.5 + battery curve (`f181b36`) + host-name hooks (local module `firmware/host-names/`) |
| `zmk-dongle-display/` | [`80ROkWOC4j/zmk-dongle-display`](https://github.com/80ROkWOC4j/zmk-dongle-display) | Upstream v0.3 (`c6c4be1`) + name-widget hook |
| `bootloader/` | [`80ROkWOC4j/nRF52_Bootloader`](https://github.com/80ROkWOC4j/nRF52_Bootloader) | Forked from [`meshtastic/nRF52_Bootloader` 2.6.0](https://github.com/meshtastic/nRF52_Bootloader/releases/tag/2.6.0) (`e75ad3f`, ARM GCC `12.3.Rel1`), Adafruit `nice_nano` 0.6.0 & Seeed XIAO board defs (`bootloader-config/LICENSE.upstream`), single-reset OTA policy via NOLOAD RAM at `0x20008010` |

### Product Details
- `Keycoon/zmk-config-totem`
  - store: https://aliexpress.com/item/1005009718551409.html
  - doc: https://suns-shave-80u.craft.me/NDKH6lhuW8BzBi
  - repo: https://github.com/Keycoon/zmk-config-totem
  - base commit: `b66b405ff4aef822955360d705966ebfa996ea2c`
- `a741725193/zmk-sofle-dongle`
  - store: https://aliexpress.com/item/1005011640674919.html
  - doc: https://ae-pic-a1.aliexpress-media.com/kf/Se2ead0612b7448f2b4678e32ee36c0ecD.pdf
  - repo: https://github.com/a741725193/zmk-sofle-dongle
  - base commit: `d3f2f764d5324af0dbac1a680fabf33d930e6026`

### Updating Dependencies

1. Push changes to the fork, then stage the new commit (`git add zmk`, `zmk-dongle-display`, or `bootloader`). Preserve the battery-curve customization when changing the `zmk/` base.
2. When updating `bootloader/`, also update `revision` and `version` in [`bootloader-config/source.json`](bootloader-config/source.json).
3. [`config/west.lock.yml`](config/west.lock.yml) pins only Zephyr and transitive west modules. If ZMK's `app/west.yml` changes, reflect it in [`config/west.yml`](config/west.yml) and refresh the lock inside `./scripts/container.sh`:

```sh
west config manifest.file west.yml
west update --fetch-opt=--filter=tree:0
python3 scripts/freeze.py
west config manifest.file west.lock.yml
./scripts/setup.sh
```
