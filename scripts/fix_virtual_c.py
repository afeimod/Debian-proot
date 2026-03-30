#!/usr/bin/env python3
"""
Excludes the FEX stats shm block from dlls/ntdll/unix/virtual.c on Android.

The block is guarded by #if defined(linux) && defined(__aarch64__) but the
Android NDK defines bare 'linux', so the block compiles and references shm_open.
On Android API 28+, shm_open is in libc but the ntdll.so link step doesn't
pull it in, causing an undefined symbol error.

Fix: add && !defined(__ANDROID__) to the guard so the block is skipped entirely
on Android (FEX stats shm is not needed on Android anyway).

Usage: fix_virtual_c.py <wine-source-dir>
"""
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_virtual_c.py <wine-source-dir>")
        sys.exit(1)

    wine_src = sys.argv[1]
    virtual_c = os.path.join(wine_src, "dlls", "ntdll", "unix", "virtual.c")

    if not os.path.exists(virtual_c):
        print(f"ERROR: {virtual_c} not found")
        sys.exit(1)

    with open(virtual_c) as f:
        src = f.read()

    old = "#if defined(linux) && defined(__aarch64__)\n"
    new = "#if defined(linux) && defined(__aarch64__) && !defined(__ANDROID__)\n"

    if new in src:
        print("fix_virtual_c: already applied, skipping")
        return

    if old not in src:
        print("fix_virtual_c: pattern not found, skipping")
        return

    count = src.count(old)
    src = src.replace(old, new)

    with open(virtual_c, "w") as f:
        f.write(src)

    print(f"fix_virtual_c: added !defined(__ANDROID__) to {count} fex guard(s) in virtual.c")


if __name__ == "__main__":
    main()
