#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
engine=${CONTAINER_ENGINE:-podman}
if ! command -v "$engine" >/dev/null; then
    echo "Install $engine first." >&2
    exit 1
fi
image=localhost/totem-zmk:dev
"$engine" build -t "$image" -f "$repo/.devcontainer/Dockerfile" "$repo"
args=(--rm --security-opt=label=disable
      --volume "$repo:/workspaces/totem" --workdir /workspaces/totem
      --env GIT_CONFIG_COUNT=1 --env GIT_CONFIG_KEY_0=safe.directory
      --env GIT_CONFIG_VALUE_0=/workspaces/totem)
if [[ "$engine" == podman ]]; then
    args+=(--userns=keep-id:uid=0,gid=0 --user=0:0)
fi
if [[ $# == 0 ]]; then
    args+=(-it)
    set -- bash
fi
exec "$engine" run "${args[@]}" "$image" "$@"
