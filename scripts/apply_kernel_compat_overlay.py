#!/usr/bin/env python3
"""
Overlay core runtime files from a known-good donor build into a newly built output.

Usage:
  apply_kernel_compat_overlay.py <target_root> <donor_root>

Both roots must contain: lib/wine/... files.
"""
import hashlib
import os
import shutil
import sys


FILES = [
    "lib/wine/i386-windows/kernel32.dll",
    "lib/wine/aarch64-windows/kernel32.dll",
    "lib/wine/aarch64-unix/ntdll.so",
]


def sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: apply_kernel_compat_overlay.py <target_root> <donor_root>")
        return 1

    target_root = sys.argv[1]
    donor_root = sys.argv[2]

    changed = 0

    for rel in FILES:
        src = os.path.join(donor_root, rel)
        dst = os.path.join(target_root, rel)

        if not os.path.exists(src):
            print(f"ERROR: donor missing file: {src}")
            return 2
        if not os.path.exists(dst):
            print(f"SKIP: target missing file (not built): {dst}")
            continue

        backup = dst + ".pre-kernel-compat.bak"
        if not os.path.exists(backup):
            shutil.copy2(dst, backup)

        src_hash = sha1(src)
        dst_hash = sha1(dst)
        if src_hash == dst_hash:
            print(f"SKIP (already same): {rel}")
            continue

        shutil.copy2(src, dst)
        new_hash = sha1(dst)
        print(f"OVERLAY: {rel}")
        print(f"  from {src_hash}")
        print(f"  to   {new_hash}")
        changed += 1

    print(f"apply_kernel_compat_overlay: done, changed files = {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
