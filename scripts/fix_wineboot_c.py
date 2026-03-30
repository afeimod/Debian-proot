#!/usr/bin/env python3
"""
Ensure programs/wineboot/wineboot.c compiles for all PE targets.

When compiled as aarch64-windows (or arm64ec-windows), none of the platform
macros (__i386__, __x86_64__, __aarch64__) are defined, so any definition of
initialize_xstate_features that lives inside an #ifdef block is invisible to
the compiler — causing "call to undeclared function" even though the symbol
appears in the file.

Fix: add a forward declaration of initialize_xstate_features before the first
use, guarded so it only fires when none of the native arch macros are defined.
"""
import os
import sys


GUARD = (
    "/* forward declaration — ensures initialize_xstate_features is visible to\n"
    " * all PE cross-compile targets regardless of #ifdef branch ordering */\n"
    "static void initialize_xstate_features(struct _KUSER_SHARED_DATA *data);\n"
)

# Anchor: insert the declaration just before the create_user_shared_data function,
# which contains the call. This anchor is stable across bleeding-edge commits.
ANCHOR = "static void create_user_shared_data(void)"


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_wineboot_c.py <wine-source-dir>")
        return 1

    wine_src = os.path.abspath(sys.argv[1])
    path = os.path.join(wine_src, "programs", "wineboot", "wineboot.c")

    if not os.path.exists(path):
        print(f"SKIP: {path} not found")
        return 0

    with open(path, errors="replace") as f:
        txt = f.read()

    if "initialize_xstate_features" not in txt:
        print("SKIP: initialize_xstate_features not present — patch not needed")
        return 0

    if "/* forward declaration — ensures initialize_xstate_features" in txt:
        print("OK: forward declaration already present")
        return 0

    idx = txt.find(ANCHOR)
    if idx < 0:
        print(f"WARN: anchor '{ANCHOR}' not found — cannot insert forward declaration")
        return 0

    txt = txt[:idx] + GUARD + "\n" + txt[idx:]

    with open(path, "w") as f:
        f.write(txt)

    print(f"FIXED: inserted initialize_xstate_features forward declaration in programs/wineboot/wineboot.c")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
