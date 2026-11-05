#!/usr/bin/env python3
"""Render the real ZMK dongle widgets and pinned LVGL with example state inputs.

Requires a completed dongle OLED build, its dependency checkouts, Python 3 and cc.
No device access, firmware changes, or third-party Python packages are needed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "scripts/display-export"
DISPLAY = ROOT / "zmk-dongle-display/boards/shields/dongle_display"
LVGL = ROOT / "modules/lib/gui/lvgl"
spec = importlib.util.spec_from_file_location("oled", ROOT / "scripts/export-oled.py")
oled = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oled)

# transport (0 USB / 1 BLE), zero-based profile, connected, bonded, USB ready,
# dongle/left/right battery %, modifiers, lock indicators, WPM, layer label.
STATES = [
    ("usb-connected", [0, 0, 0, 1, 1, 0, 86, 73, 0, 0, 0, "base"]),
    ("ble-connected", [1, 1, 1, 1, 1, 0, 86, 73, 0, 0, 0, "base"]),
    ("ble-pairing", [1, 2, 0, 0, 1, 0, 86, 73, 0, 0, 0, "device"]),
    ("ble-disconnected", [1, 1, 0, 1, 0, 0, 86, 73, 0, 0, 0, "base"]),
    ("nav-ctrl-shift-caps", [0, 0, 0, 1, 1, 0, 86, 73, 3, 2, 45, "nav_num"]),
    ("low-battery", [1, 0, 1, 1, 1, 0, 9, 18, 0, 0, 0, "base"]),
]
# alias, cached automatic name, editor mode (0 idle / 2 editing), draft, save error.
STATES = [(name, values + ["", "", 0, "", 0]) for name, values in STATES]
STATES[0][1][13] = "cachyos-x8664"
STATES[1][1][13] = "Galaxy Tab S11"
STATES[3][1][13] = "Galaxy Tab S11"
STATES[4][1][13] = "cachyos-x8664"
STATES[5][1][12] = "CustomName"
STATES += [
    ("name-editor", [1, 1, 1, 1, 1, 0, 86, 73, 0, 0, 0, "base", "", "Galaxy Tab S11", 2, "CustomName", 0]),
    ("name-editor-error", [1, 1, 1, 1, 1, 0, 86, 73, 0, 0, 0, "base", "", "Galaxy Tab S11", 2, "CustomName", 1]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build/totem_dongle_central_oled")
    parser.add_argument("--output", type=Path, default=ROOT / "build/status-oled-export")
    parser.add_argument("--preview", type=Path, help="Also refresh a README overview PNG")
    args = parser.parse_args()
    autoconf = args.build_dir.resolve() / "zephyr/include/generated/autoconf.h"
    dts = args.build_dir.resolve() / "zephyr/zephyr.dts"
    for path in (autoconf, dts, DISPLAY / "custom_status_screen.c", LVGL / "src/lvgl.h"):
        if not path.exists():
            parser.error(f"Missing {path}; prepare dependencies and build the dongle OLED target first")
    config = autoconf.read_text()
    panel = re.search(r'oled:.*?\{(.*?)\};', dts.read_text(), re.S)
    if not panel:
        parser.error("Cannot find OLED node in build devicetree")
    def dimension(name):
        return int(re.search(rf'\b{name} = < (0x[0-9a-f]+|\d+) >', panel[1])[1], 0)
    width, height = dimension("width"), dimension("height")
    inverted = bool(re.search(r'\binversion-on;', panel[1]))
    if (width, height) != (129, 64):
        parser.error("This adapter currently supports the TOTEM 129 x 64 logical display")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    widget_names = ["output_status", "output_status_sym", "battery_status", "layer_status",
                    "modifiers", "modifiers_sym", "hid_indicators", "bongo_cat", "bongo_cat_images"]
    sources = [DISPLAY / "custom_status_screen.c"] + [DISPLAY / f"widgets/{n}.c" for n in widget_names]
    host_names = ROOT / "firmware/host-names"
    if "#define CONFIG_TOTEM_HOST_NAMES 1" in config:
        sources += [host_names / "src/widget.c", host_names / "src/core.c"]
    lv_sources = sorted((LVGL / "src").rglob("*.c"))
    frames, exported = [], []
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        # Only kernel/event interfaces are replaced. No drawing code is rewritten.
        includes = set()
        for path in sources + list(DISPLAY.rglob("*.h")):
            includes.update(re.findall(r'#\s*include <((?:zephyr|zmk)/[^>]+)>', path.read_text()))
        for include in includes:
            path = work / include
            path.parent.mkdir(parents=True, exist_ok=True)
            if include == "zmk/display/widgets/layer_status.h":
                path.write_text(f'#include "{DISPLAY}/widgets/layer_status.h"\n')
            else:
                path.write_text('#include "host.h"\n')
        modifiers = work / "dt-bindings/zmk/modifiers.h"
        modifiers.parent.mkdir(parents=True, exist_ok=True)
        modifiers.write_bytes((ROOT / "zmk/app/include/dt-bindings/zmk/modifiers.h").read_bytes())
        host_config = work / "config.h"
        host_config.write_text("\n".join(line for line in config.splitlines()
                                      if re.match(r'#define CONFIG_(LV_|ZMK_|TOTEM_|USB_DEVICE_STACK)', line)) + "\n")
        # Retain Zephyr's printf/memcpy settings; use native heap and manual ticks.
        (work / "lv_conf.h").write_text('''#define LV_CONF_H
#define LV_MEMCPY_MEMSET_STD 1
#define LV_MEM_CUSTOM 1
#define LV_MEM_CUSTOM_INCLUDE "stdlib.h"
#define LV_MEM_CUSTOM_ALLOC malloc
#define LV_MEM_CUSTOM_REALLOC realloc
#define LV_MEM_CUSTOM_FREE free
#define LV_TICK_CUSTOM 0
#define LV_SPRINTF_CUSTOM 1
#define LV_SPRINTF_INCLUDE "stdio.h"
#define lv_snprintf snprintf
#define lv_vsnprintf vsnprintf
''')
        executable = work / "capture"
        command = [os.environ.get("CC", "cc"), "-std=gnu11", "-O1", "-DLV_CONF_INCLUDE_SIMPLE=1",
                   "-include", str(host_config), "-include", str(SUPPORT / "host.h"),
                   f"-DEXPORT_WIDTH={width}", f"-DEXPORT_HEIGHT={height}",
                   f"-DEXPORT_INVERT={int(inverted)}"]
        for include in (work, SUPPORT, DISPLAY, LVGL / "src", host_names / "include"):
            command += ["-I", str(include)]
        command += [str(p) for p in sources + lv_sources + [SUPPORT / "capture.c"]]
        command += ["-lm", "-o", str(executable)]
        result = subprocess.run(command, capture_output=True, text=True)
        (output / "compile.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            parser.error(f"Native compilation failed; see {output / 'compile.log'}")
        for name, values in STATES:
            raw = subprocess.check_output([str(executable), *map(str, values)])
            magic, dimensions, maximum, pixels = raw.split(b"\n", 3)
            if (magic, dimensions, maximum, len(pixels)) != (
                    b"P5", f"{width} {height}".encode(), b"255", width * height):
                raise ValueError("Invalid framebuffer capture")
            frames.append(pixels)
            for scale in (1, 6):
                path = output / f"{name}{'-6x' if scale > 1 else ''}.png"
                path.write_bytes(oled.png(*oled.enlarge(width, height, pixels, scale)))
                exported.append(path)
    gap, tw, th = 12, width * 3, height * 3
    rows = (len(frames) + 1) // 2
    sw, sh = tw * 2 + gap * 3, th * rows + gap * (rows + 1)
    sheet = bytearray([28]) * (sw * sh)
    for index, frame in enumerate(frames):
        _, _, pixels = oled.enlarge(width, height, frame, 3)
        x, y = gap + index % 2 * (tw + gap), gap + index // 2 * (th + gap)
        for row in range(th):
            sheet[(y + row) * sw + x:(y + row) * sw + x + tw] = pixels[row * tw:(row + 1) * tw]
    overview = output / "overview.png"
    overview.write_bytes(oled.png(sw, sh, sheet))
    exported.append(overview)
    revisions = {str(p.relative_to(ROOT)): subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=p, text=True).strip()
        for p in (ROOT / "zmk", ROOT / "zmk-dongle-display", LVGL)}
    manifest = output / "manifest.json"
    provenance = sources + list(DISPLAY.rglob("*.h")) + list((host_names / "include").rglob("*.h")) + lv_sources + [autoconf, dts,
        Path(__file__).resolve(), SUPPORT / "host.h", SUPPORT / "capture.c", ROOT / "scripts/export-oled.py"]
    manifest.write_text(json.dumps({
        "description": "Real ZMK widgets and LVGL; simulated events, not a live device capture",
        "revisions": revisions, "logical_size": [width, height],
        "physical_inversion": inverted, "animation_time_ms": 300,
        "states": dict(STATES),
        "state_fields": ["transport", "profile_zero_based", "connected", "bonded", "usb_ready",
                         "dongle_battery", "left_battery", "right_battery", "modifiers", "locks", "wpm", "layer",
                         "alias", "automatic_name", "editor_mode", "draft", "save_failed"],
        "source_sha256": {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):
                          hashlib.sha256(p.read_bytes()).hexdigest() for p in provenance},
        "png_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in exported},
    }, indent=2) + "\n")
    exported.append(manifest)
    readme = output / "README.txt"
    readme.write_text("""TOTEM normal status OLED export

Actual pinned zmk-dongle-display widget C, images and LVGL fonts/renderer.
Example state inputs only, not live device screenshots or panel photographs.
Host adapters replace ZMK state/events, memory allocation, clock and display I/O.
The build's generated configuration and devicetree supply display settings.
The current OTA branch's base/nav_num/device layer labels are used as examples.

Overview order, left to right then top to bottom:
USB connected / BLE profile 2 connected
BLE profile 3 open for pairing / BLE profile 2 bonded but disconnected
Navigation with Ctrl+Shift and Caps Lock / low left/right batteries
Host-name editor / editor after a simulated storage failure
cachyos-x8664 and Galaxy Tab S11 are example automatic host names.
CustomName is a saved alias in the low-battery example and the editor draft.
USB is present in all examples except ble-disconnected; selecting BLE does
not require unplugging USB. Battery values and host states are simulated.

Native images preserve the configured 129 x 64 logical display, including its
extra column; the physical OLED glass is 128 x 64. No panel crop is guessed.
The devicetree's inversion-on is applied. Optical color/glow is not simulated.
-6x files use nearest-neighbor enlargement. Animation snapshot: 300 ms.
See manifest.json for inputs, dependency revisions and source/image hashes.

Reproduce: python3 scripts/export-status-oled.py
""")
    exported.append(readme)
    archive = output / "totem-status-oled.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in exported:
            bundle.write(path, path.name)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(overview, args.preview)
    print(f"Exported {len(STATES)} normal status screens to {output}")


if __name__ == "__main__":
    main()
