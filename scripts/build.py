#!/usr/bin/env python3
"""Build targets from the same matrix locally and in CI."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import yaml
from ota import package_application
from submodules import verify

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default="all", help="artifact-name or all")
    parser.add_argument("--matrix", type=Path, default=ROOT / "build.yaml")
    args = parser.parse_args()
    entries = yaml.safe_load(args.matrix.read_text())["include"]
    entries = [e for e in entries if args.target in ("all", e["artifact-name"])]
    if not entries:
        parser.error("target not found in the selected matrix")
    source_revisions = verify(("zmk", "zmk-dongle-display"))
    # One-shot Podman runs have a fresh home, so register Zephyr on every run.
    subprocess.run(["west", "zephyr-export"], cwd=ROOT, check=True)
    for entry in entries:
        name = entry["artifact-name"]
        build = ROOT / "build" / name
        command = ["west", "build", "-p", "always", "-s", str(ROOT / "zmk/app"),
                   "-d", str(build), "-b", entry["board"]]
        if entry.get("snippet"):
            command += ["-S", entry["snippet"]]
        command += ["--", f"-DZMK_CONFIG={ROOT / 'config'}", f"-DSHIELD={entry['shield']}"]
        command += [f"-DZMK_EXTRA_MODULES={ROOT / 'firmware/host-names'};{ROOT / 'zmk-dongle-display'}"]
        command += shlex.split(entry.get("cmake-args", ""))
        subprocess.run(command, cwd=ROOT, check=True)
        artifacts = ROOT / "build/artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        for ext in ("uf2", "hex"):
            source = build / "zephyr" / f"zmk.{ext}"
            if source.exists():
                shutil.copy2(source, artifacts / f"{name}.{ext}")
        metadata = {"target": entry, "config_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "config_dirty": bool(subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
            "zmk_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT / "zmk", text=True).strip(),
            "source_lock_sha256": sha256(ROOT / "config/west.lock.yml"),
            "source_submodules": source_revisions,
            "container_recipe_sha256": sha256(ROOT / ".devcontainer/Dockerfile"),
            "local_firmware_sha256": {
                str(p.relative_to(ROOT)): sha256(p)
                for directory in (ROOT / "firmware",)
                for p in sorted(directory.rglob("*")) if p.is_file()},
            "firmware_sha256": {ext: sha256(artifacts / f"{name}.{ext}")
                                for ext in ("uf2", "hex")
                                if (artifacts / f"{name}.{ext}").exists()}}
        metadata["ota"] = package_application(artifacts / f"{name}.hex", entry["board"])
        (artifacts / f"{name}.json").write_text(json.dumps(metadata, indent=2) + "\n")
        if "dongle_display" in entry["shield"].split():
            subprocess.run([sys.executable, str(ROOT / "scripts/export-status-oled.py"),
                            "--build-dir", str(build),
                            "--output", str(artifacts / "oled" / name),
                            "--preview", str(ROOT / "images/oled-status.png")],
                           cwd=ROOT, check=True)
    shutil.copy2(ROOT / "config/west.lock.yml", ROOT / "build/artifacts/west.lock.yml")


if __name__ == "__main__":
    main()
