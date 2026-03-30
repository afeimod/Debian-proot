#!/usr/bin/env python3
"""
Disable fsync on Android in both ntdll and wineserver sources.

The upstream/GameNative fsync patches can drift against bleeding-edge, which
leaves the Linux futex_waitv probe active on Android and causes repeated
"futexes not supported on this platform" runtime noise. This script enforces
the intended Android guard deterministically after patch application.

Usage: fix_fsync.py <wine-source-dir>
"""
from __future__ import annotations

import os
import sys


def replace_once(src: str, old: str, new: str, description: str) -> tuple[str, int]:
    if new in src:
        print(f"  [{description}] already applied, skipping")
        return src, 0
    if old not in src:
        print(f"  [{description}] pattern not found, skipping")
        return src, 0
    print(f"  [{description}] applied")
    return src.replace(old, new, 1), 1


def patch_file(path: str, replacements: list[tuple[str, str, str]]) -> int:
    if not os.path.exists(path):
        print(f"ERROR: {path} not found")
        return -1

    with open(path, encoding="utf-8") as f:
        src = f.read()

    total = 0
    for description, old, new in replacements:
        src, n = replace_once(src, old, new, description)
        total += n

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)

    return total


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: fix_fsync.py <wine-source-dir>")
        return 1

    wine_src = sys.argv[1]
    ntdll_fsync = os.path.join(wine_src, "dlls", "ntdll", "unix", "fsync.c")
    server_fsync = os.path.join(wine_src, "server", "fsync.c")

    total = 0
    total_ntdll = patch_file(
        ntdll_fsync,
        [
            (
                "ntdll shm_utils include",
                "#include \"unix_private.h\"\n#include \"fsync.h\"\n",
                "#include \"unix_private.h\"\n#include \"fsync.h\"\n#ifdef __ANDROID__\n#include \"../../../android/shm_utils/shm_utils.h\"\n#endif\n",
            ),
            (
                "ntdll do_fsync android guard",
                "#ifdef __linux__\n",
                "#if defined(__linux__) && !defined(__ANDROID__)\n",
            )
        ],
    )
    if total_ntdll < 0:
        return 2
    total += total_ntdll

    total_server = patch_file(
        server_fsync,
        [
            (
                "server shm_utils include",
                "#include \"handle.h\"\n#include \"request.h\"\n#include \"fsync.h\"\n",
                "#include \"handle.h\"\n#include \"request.h\"\n#include \"fsync.h\"\n#ifdef __ANDROID__\n#include \"../android/shm_utils/shm_utils.h\"\n#endif\n",
            ),
            (
                "server do_fsync android guard",
                "#ifdef __linux__\n",
                "#if defined(__linux__) && !defined(__ANDROID__)\n",
            )
        ],
    )
    if total_server < 0:
        return 3
    total += total_server

    print(f"\nDone. Applied {total} fsync fix(es)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
