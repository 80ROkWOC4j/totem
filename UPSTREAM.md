# Upstream References

This repository started from a minimal merge of Totem-specific files from:

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

The intent here is to maintain a standalone Totem-focused config repo with:

- a single shared keymap
- non-dongle firmware targets
- dongle firmware targets

## Custom ZMK Source

Three customized repositories are Git submodules configured in `.gitmodules`:

| Path | Fork | Custom branch |
| --- | --- | --- |
| `zmk/` | [80ROkWOC4j/zmk](https://github.com/80ROkWOC4j/zmk) | `codex/totem-ota` |
| `zmk-dongle-display/` | [80ROkWOC4j/zmk-dongle-display](https://github.com/80ROkWOC4j/zmk-dongle-display) | `codex/totem-ota` |
| `bootloader/` | [80ROkWOC4j/nRF52_Bootloader](https://github.com/80ROkWOC4j/nRF52_Bootloader) | `codex/totem-ota` |

Git submodule entries pin exact commits, not moving branch tips. The ZMK fork
extends the existing battery-curve base `f181b366e52716e98f76d6365f755b5a865e6bdb`
with host-name event and bond hooks. The display fork extends upstream v0.3
at `c6c4be11c5ede722086a2a1f355cec9c101b9390` with the name-widget hook.
The original ZMK 0.3 baseline and Zephyr 3.5 toolchain remain unchanged.

`config/west.lock.yml` pins only Zephyr and the remaining transitive dependencies.
Git-owned sources are absent from both west manifests; ZMK is the explicit app
source and the build supplies the display path via `ZMK_EXTRA_MODULES`.
When updating ZMK, review its `app/west.yml` and update `config/west.yml` as needed.
The host-name implementation stays in `firmware/host-names/` as a local module.
No source patches are applied during setup/build. Firmware metadata records
the source commits and local module hashes. See [host names](docs/HOST-NAMES.md).

## Custom Bootloader

The bootloader fork starts from Meshtastic's Adafruit/OTAFIX-derived
[nRF52 Bootloader 2.6.0](https://github.com/meshtastic/nRF52_Bootloader/releases/tag/2.6.0)
at `e75ad3fa39acb7ea902b5eb7c3bce5fff56157de`, preserving its submodule revisions.
`bootloader-config/source.json` records the custom commit/version and upstream
provenance; its custom revision must match the Git submodule entry.
This is a bootloader-only dependency; no Meshtastic application is installed.
ARM GCC 12.3.Rel1 is pinned separately from the ZMK SDK in the container.

The nice!nano board identity/pins originate from Adafruit nRF52 Bootloader
0.6.0 (`src/boards/nice_nano`); OLED pins match this repository's dongle overlay.
XIAO definitions derive from the pinned bootloader's BLE and Sense boards,
with the display bus disabled and reset as the only button input. Original
license notices are retained in those files and `bootloader-config/LICENSE.upstream`.
The fork's committed reset policy enables single-reset OTA only for TOTEM boards, keeps
double-reset USB entry, and uses a validated NOLOAD RAM record to cancel an
update wait with reset. `2.6.0-totem1` incorrectly used GPREGRET2, which a
physical pin reset clears. `2.6.0-totem2` reserves eight bytes at `0x20008010`,
above SoftDevice RAM and the upstream fault record. Existing peer-data and
double-reset addresses, flash layout and SoftDevice versions stay unchanged.

## Updating dependencies

Commit and push changes to the dependency fork, then stage its selected commit
in TOTEM with `git add zmk`, `git add zmk-dongle-display`, or `git add bootloader`.
For the bootloader, also update the matching revision/version in
`bootloader-config/source.json`. Submodule commits must be fetchable by other users.

If a ZMK update changes transitive dependencies, match `config/west.yml` to its
`app/west.yml`, then enter `./scripts/container.sh` and refresh the lock:

```sh
west config manifest.file west.yml
west update --fetch-opt=--filter=tree:0
python3 scripts/freeze.py
west config manifest.file west.lock.yml
./scripts/setup.sh
```

Review the submodule pointers and manifests, then verify all five firmware builds.
Preserve the ZMK battery customization when changing its base revision.

This file is documentation only. It does not imply any licensing grant from the upstream repositories.
