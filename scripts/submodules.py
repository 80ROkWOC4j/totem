#!/usr/bin/env python3
"""Initialize or verify the Git-owned firmware sources without patching them."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("zmk", "zmk-dongle-display", "bootloader")


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=ROOT if cwd is None else cwd, text=True).strip()


def pinned_revision(name):
    # The index also supports reviewing a newly staged gitlink before committing TOTEM.
    entry = git("ls-files", "--stage", "--", name).split()
    if len(entry) != 4 or entry[0] != "160000" or entry[2] != "0":
        raise RuntimeError(f"{name}: expected one staged submodule entry")
    return entry[1]


def source_url(name):
    return git("config", "--file", str(ROOT / ".gitmodules"), f"submodule.{name}.url")


def verify(names=SOURCES):
    revisions = {}
    for name in names:
        if name not in SOURCES:
            raise ValueError(f"Unknown source: {name}")
        expected = pinned_revision(name)
        if not (ROOT / name / ".git").exists():
            raise RuntimeError(f"{name}: run python3 scripts/submodules.py init")
        actual = git("rev-parse", "HEAD", cwd=ROOT / name)
        if actual != expected:
            raise RuntimeError(f"{name}: HEAD {actual} differs from the staged gitlink {expected}")
        revisions[name] = actual
        for line in git("submodule", "status", "--recursive", cwd=ROOT / name).splitlines():
            # git() strips the first leading space; initialized clean rows begin with a SHA.
            if line and line[0] in "-+U":
                raise RuntimeError(f"{name}: nested submodule is uninitialized or differs: {line}")
    return revisions


def bootloader_source():
    config = json.loads((ROOT / "bootloader-config/source.json").read_text())
    revision = verify(("bootloader",))["bootloader"]
    if config["revision"] != revision or config["url"].removesuffix(".git") != source_url("bootloader").removesuffix(".git"):
        raise RuntimeError("Update bootloader-config/source.json to match the bootloader gitlink/URL")
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "check"))
    args = parser.parse_args()
    if args.action == "init":
        subprocess.run(["git", "submodule", "sync", "--recursive"], cwd=ROOT, check=True)
        subprocess.run(["git", "submodule", "update", "--init", "--recursive", "--checkout"],
                       cwd=ROOT, check=True)
    for name, revision in verify().items():
        print(f"{name}: {revision}")
    bootloader_source()


if __name__ == "__main__":
    main()
