#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo"
python3 scripts/submodules.py init
if [[ ! -d .west ]]; then
    west init -l config
fi
west config manifest.file west.lock.yml
west update --fetch-opt=--filter=tree:0
west zephyr-export
