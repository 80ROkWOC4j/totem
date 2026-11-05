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
      --volume "$repo:/workspaces/totem" --workdir /workspaces/totem)
# Docker runs as root while CI checkouts and restored caches belong to the runner.
# Trust only existing repositories in this mounted workspace, including submodules.
safe_count=0
while IFS= read -r -d '' git_entry; do
    safe_path="/workspaces/totem${git_entry#"$repo"}"
    args+=(--env "GIT_CONFIG_KEY_${safe_count}=safe.directory"
           --env "GIT_CONFIG_VALUE_${safe_count}=${safe_path%/.git}")
    safe_count=$((safe_count + 1))
done < <(find "$repo" -name .git -print0 -prune)
args+=(--env "GIT_CONFIG_COUNT=$safe_count")
if [[ "$engine" == podman ]]; then
    args+=(--userns=keep-id:uid=0,gid=0 --user=0:0)
fi
if [[ $# == 0 ]]; then
    args+=(-it)
    set -- bash
fi
exec "$engine" run "${args[@]}" "$image" "$@"
