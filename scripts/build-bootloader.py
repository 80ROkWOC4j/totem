#!/usr/bin/env python3
"""Build pinned TOTEM bootloaders; never flash a device."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from uf2 import validate_bootloader
from submodules import bootloader_source

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "bootloader-config"
SOURCE = ROOT / "bootloader"


def run(*args, cwd=SOURCE, **kwargs):
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)


def main():
    lock = bootloader_source()
    boards = sorted(p.name for p in (SOURCE / "src/boards").glob("totem_*") if p.is_dir())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", choices=["all", *boards], default="all", nargs="?")
    args = parser.parse_args()
    compiler = subprocess.check_output(["arm-none-eabi-gcc", "--version"], text=True)
    if lock["toolchain"] not in compiler:
        raise SystemExit("Use scripts/container.sh: bootloader needs ARM GCC " + lock["toolchain"])
    out = ROOT / "build/artifacts/bootloader"
    out.mkdir(parents=True, exist_ok=True)
    selected = boards if args.board == "all" else [args.board]
    for board in selected:
        run("make", f"BOARD={board}", "clean")
        run("make", "-j4", f"BOARD={board}", f"GIT_VERSION={lock['version']}", "all")
        build = SOURCE / "_build" / f"build-{board}"
        files = list(build.glob("update-*_nosd.uf2")) + list(build.glob("*_nosd.hex"))
        if len(files) != 2:
            raise SystemExit("Missing/ambiguous bootloader output")
        vid_pid = (0x239A00B3 if board == "totem_dongle" else
                   0x28860045 if board.endswith("_sense") else 0x28860044)
        validate_bootloader(next(p for p in files if p.suffix == ".uf2"), vid_pid)
        for path in files:
            shutil.copy2(path, out / path.name)
        metadata = {"board": board, "source": lock, "compiler": compiler.splitlines()[0],
                    "config_sha256": {str(p.relative_to(CONFIG)): hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted(CONFIG.rglob("*")) if p.is_file()},
                    "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        (out / f"{board}.json").write_text(json.dumps(metadata, indent=2) + "\n")
        if board == "totem_dongle":
            run(sys.executable, str(ROOT / "scripts/export-oled.py"),
                "--output", str(out / "oled"),
                "--preview", str(ROOT / "images/oled-bootloader.png"), cwd=ROOT)


if __name__ == "__main__":
    main()
