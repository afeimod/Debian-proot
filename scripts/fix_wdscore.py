#!/usr/bin/env python3
import os
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_wdscore.py <wine-source-dir>")
        return 1

    wine_src = os.path.abspath(sys.argv[1])
    path = os.path.join(wine_src, "dlls", "wdscore", "wdscore.spec")

    if not os.path.exists(path):
        print(f"SKIP: {path} not found")
        return 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    kept = []
    removed = []

    for line in lines:
        # Match the upstream GameNative patch intent exactly: drop every
        # wdscore.spec entry that exports a CDynamicArray template symbol.
        if "CDynamicArray" in line:
            removed.append(line.rstrip("\n"))
            continue
        kept.append(line)

    if not removed:
        print("OK: no CDynamicArray exports found in wdscore.spec")
        return 0

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(kept)

    print(f"FIXED: removed {len(removed)} wdscore.spec lines")
    for line in removed:
        print(f"  removed: {line}")

    remaining = [line.rstrip("\n") for line in kept if "CDynamicArray" in line]
    if remaining:
        print("ERROR: wdscore.spec still contains CDynamicArray entries")
        for line in remaining:
            print(f"  remaining: {line}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
