#!/usr/bin/env python3
"""Freeze active projects with the west version bundled in the ZMK 3.5 image."""
from pathlib import Path

from west.manifest import Manifest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = Manifest.from_topdir(str(ROOT))
    active = {p.name: p for p in manifest.projects
              if p.name != "manifest" and manifest.is_active(p)}
    data = manifest.as_dict()
    projects = []
    for spec in data["manifest"]["projects"]:
        project = active.get(spec["name"])
        if project is None:
            continue
        # Fail before writing if west update has not fetched every active project.
        spec["revision"] = project.sha("manifest-rev")
        projects.append(spec)
    data["manifest"]["projects"] = projects
    output = ROOT / "config/west.lock.yml"
    temporary = output.with_suffix(".tmp")
    temporary.write_text(yaml.safe_dump(data, sort_keys=False))
    temporary.replace(output)
    print(f"Locked {len(projects)} active projects.")


if __name__ == "__main__":
    main()
