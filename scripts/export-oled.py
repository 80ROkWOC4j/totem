#!/usr/bin/env python3
"""Export actual bootloader screen.c output as PNG without touching hardware.

Requires Python 3, a native C compiler, and the pinned bootloader checkout
(created by scripts/build-bootloader.py). No imaging packages are required.
Only board_display_draw_page is replaced: the actual renderer and font are
compiled unchanged with the TOTEM dongle board header and version string.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zipfile
from submodules import bootloader_source
import zlib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bootloader"
CONFIG = ROOT / "bootloader-config"

SHIM = """#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "board.h"
#if defined(DISPLAY_PIN_SDA) && defined(DISPLAY_CONTROLLER_SH1106)
#define BOARD_HAS_DISPLAY 1
#define DISPLAY_MONO 1
#else
#error "This exporter targets the TOTEM SH1106 OLED"
#endif
void board_display_draw_page(uint8_t page, const uint8_t *buf, size_t size);
void screen_draw_drag(void);
void screen_draw_ble(void);
void screen_set_title(const char *title);
void screen_set_progress(uint32_t done, uint32_t total);
"""

HARNESS = r"""#include "boards.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t pixels[DISPLAY_HEIGHT][DISPLAY_WIDTH];

void board_display_draw_page(uint8_t page, const uint8_t *buf, size_t size) {
    if (page >= DISPLAY_HEIGHT / 8 || size != DISPLAY_WIDTH) abort();
    for (size_t x = 0; x < size; ++x)
        for (unsigned bit = 0; bit < 8; ++bit)
            pixels[page * 8 + bit][x] = (buf[x] & (1u << bit)) ? 255 : 0;
}

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    if (argv[2][0]) screen_set_title(argv[2]);
    if (!strcmp(argv[1], "ble")) screen_draw_ble();
    else if (!strcmp(argv[1], "usb")) screen_draw_drag();
    else return 2;
    int pct = atoi(argv[3]);
    if (pct >= 0) screen_set_progress((uint32_t)pct, 100);
    printf("P5\n%d %d\n255\n", DISPLAY_WIDTH, DISPLAY_HEIGHT);
    return fwrite(pixels, 1, sizeof(pixels), stdout) == sizeof(pixels) ? 0 : 1;
}
"""

STATES = [
    ("usb-uf2", "usb", "", -1),
    ("ble-ota", "ble", "", -1),
    ("usb-upload-50", "usb", "", 50),
    ("ota-upload-50", "ble", "", 50),
    ("no-firmware-ble", "ble", "NO FIRMWARE", -1),
    ("wrong-file-usb", "usb", "WRONG FILE", -1),
    ("bootloader-update-50", "usb", "BOOTLOADER", 50),
    ("factory-erase", "usb", "ERASE", -1),
]


def png(width, height, pixels):
    """Encode lossless 8-bit grayscale, preserving each monochrome pixel."""
    if len(pixels) != width * height:
        raise ValueError("Incorrect framebuffer size")

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    scanlines = b"".join(b"\0" + pixels[y * width:(y + 1) * width]
                         for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))


def enlarge(width, height, pixels, scale):
    result = bytearray()
    for y in range(height):
        row = b"".join(bytes([p]) * scale for p in pixels[y * width:(y + 1) * width])
        result.extend(row * scale)
    return width * scale, height * scale, bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/oled-export")
    parser.add_argument("--preview", type=Path, help="Also refresh a README overview PNG")
    args = parser.parse_args()
    lock = bootloader_source()
    if not (SOURCE / "src/screen.c").exists():
        parser.error("Run python3 scripts/submodules.py init first")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE,
                                       text=True).strip()
    if revision != lock["revision"]:
        parser.error("Bootloader checkout does not match bootloader-config/source.json")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    exported, frames = [], []
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        (work / "boards.h").write_text(SHIM)
        (work / "capture.c").write_text(HARNESS)
        executable = work / "capture"
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-I", str(work), "-I", str(SOURCE / "src/boards/totem_dongle"),
                        f'-DUF2_VERSION_BASE="{lock["version"]}"',
                        str(SOURCE / "src/screen.c"), str(SOURCE / "src/images.c"),
                        str(work / "capture.c"), "-o", str(executable)], check=True)
        for name, mode, title, progress in STATES:
            # Fresh process per state resets the renderer's static state.
            raw = subprocess.check_output([str(executable), mode, title, str(progress)])
            magic, dimensions, maximum, pixels = raw.split(b"\n", 3)
            width, height = map(int, dimensions.split())
            if (magic, maximum, width, height) != (b"P5", b"255", 128, 64):
                raise ValueError("Unexpected OLED geometry or capture format")
            frames.append((width, height, pixels))
            for scale in (1, 6):
                path = output / f"{name}{'-6x' if scale > 1 else ''}.png"
                path.write_bytes(png(*enlarge(width, height, pixels, scale)))
                exported.append(path)

    # Overview in the same order as STATES: two columns, four rows, at 3x.
    gap, tile_width, tile_height = 12, 128 * 3, 64 * 3
    width, height = tile_width * 2 + gap * 3, tile_height * 4 + gap * 5
    sheet = bytearray([28]) * (width * height)
    for index, frame in enumerate(frames):
        _, _, pixels = enlarge(*frame, 3)
        x = gap + (index % 2) * (tile_width + gap)
        y = gap + (index // 2) * (tile_height + gap)
        for row in range(tile_height):
            start = (y + row) * width + x
            sheet[start:start + tile_width] = pixels[row * tile_width:(row + 1) * tile_width]
    overview = output / "overview.png"
    overview.write_bytes(png(width, height, sheet))
    exported.append(overview)
    sources = [SOURCE / "src/screen.c", SOURCE / "src/images.c",
               SOURCE / "src/boards/totem_dongle/board.h", CONFIG / "source.json",
               Path(__file__).resolve()]
    metadata = output / "manifest.json"
    metadata.write_text(json.dumps({
        "description": "Host rendering of the real OLED page output; not a device screenshot or photograph",
        "bootloader_revision": revision, "version": lock["version"],
        "native_size": [128, 64], "scale_method": "nearest-neighbor",
        "states": [{"file": name + ".png", "mode": mode, "title": title or "TOTEM DONGLE",
                    "progress_percent": progress if progress >= 0 else None}
                   for name, mode, title, progress in STATES],
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sources},
        "png_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in exported},
    }, indent=2) + "\n")
    exported.append(metadata)
    readme = output / "README.txt"
    readme.write_text("""TOTEM bootloader OLED export

Native PNGs: 128 x 64. The -6x PNGs are pixel-preserving enlargements.
overview.png: USB / BLE waiting; USB / BLE at 50%; no firmware / wrong file;
bootloader self-update at 50% / factory erase (left to right, top to bottom).

These are outputs of the real bootloader screen.c and font, with the hardware
page-write callback replaced by an image capture. They are not live screenshots
or photos of the physical panel. Panel color, brightness and optical effects
are not simulated. Display RAM column offset is handled by the physical driver;
the exported image is the logical 128 x 64 framebuffer sent to that driver.
Special titles and progress values are simulated inputs to the real renderer.

Reproduce from the repository root: python3 scripts/export-oled.py
""")
    exported.append(readme)
    archive = output / "totem-bootloader-oled.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in exported:
            bundle.write(path, path.name)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(overview, args.preview)
    print(output)
    print(f"Exported {len(STATES)} states, native and 6x, plus overview and ZIP")


if __name__ == "__main__":
    main()
