#!/usr/bin/env python3
"""
Append optional patch filenames into build-step-arm64ec.sh's PATCHES array.

Usage:
  inject_optional_patches.py <build-script> <patch1> [patch2 ...]
"""
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: inject_optional_patches.py <build-script> <patch1> [patch2 ...]")
        return 1

    path = Path(sys.argv[1])
    patches = sys.argv[2:]
    lines = path.read_text(encoding="utf-8").splitlines()

    start = None
    end = None
    for idx, line in enumerate(lines):
        if "PATCHES=(" in line:
            start = idx
            continue
        if start is not None and line.strip() == ")":
            end = idx
            break

    if start is None or end is None:
        print("PATCHES array not found")
        return 2

    existing = set()
    for line in lines[start + 1:end]:
        stripped = line.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            existing.add(stripped.strip('"'))

    additions = [f'        "{patch}"' for patch in patches if patch not in existing]
    if additions:
        lines[end:end] = additions
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Injected {len(additions)} optional patch(es) into {path}")
    else:
        print("Optional patches already present, no change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
