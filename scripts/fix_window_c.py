#!/usr/bin/env python3
"""
Applies Android-specific changes to dlls/winex11.drv/window.c that cannot
be applied via patch due to line-number drift against bleeding-edge.

Uses exact string replacement verified against bleeding-edge source.

Usage: fix_window_c.py <wine-source-dir>
"""
import sys
import os


def apply(src, description, old, new):
    if new in src:
        print(f"  [{description}] already applied, skipping")
        return src, 0
    if old not in src:
        print(f"  [{description}] pattern not found, skipping")
        return src, 0
    print(f"  [{description}] applied")
    return src.replace(old, new, 1), 1


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_window_c.py <wine-source-dir>")
        sys.exit(1)

    wine_src = sys.argv[1]
    window_c = os.path.join(wine_src, "dlls", "winex11.drv", "window.c")

    if not os.path.exists(window_c):
        print(f"ERROR: {window_c} not found")
        sys.exit(1)

    with open(window_c) as f:
        src = f.read()

    total = 0

    # 1. Guard x11drv_xinput2_enable in sync_window_style (line ~570)
    src, n = apply(src, "xinput2_enable in sync_window_style",
        "        XChangeWindowAttributes( data->display, data->whole_window, mask, &attr );\n"
        "        x11drv_xinput2_enable( data->display, data->whole_window );\n"
        "    }\n"
        "}\n",

        "        XChangeWindowAttributes( data->display, data->whole_window, mask, &attr );\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT2_H\n"
        "        x11drv_xinput2_enable( data->display, data->whole_window );\n"
        "#endif\n"
        "    }\n"
        "}\n"
    )
    total += n

    # 2. Guard x11drv_xinput2_enable in create_whole_window (line ~2644)
    src, n = apply(src, "xinput2_enable in create_whole_window",
        "    window_set_managed( data, is_window_managed( data->hwnd, SWP_NOACTIVATE, FALSE ) );\n"
        "    x11drv_xinput2_enable( data->display, data->whole_window );\n"
        "    set_initial_wm_hints( data->display, data->whole_window );\n",

        "    window_set_managed( data, is_window_managed( data->hwnd, SWP_NOACTIVATE, FALSE ) );\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT2_H\n"
        "    x11drv_xinput2_enable( data->display, data->whole_window );\n"
        "#endif\n"
        "    set_initial_wm_hints( data->display, data->whole_window );\n"
    )
    total += n

    # 3. Guard xinput2_rawinput + xinput2_enable in X11DRV_CreateWindow (line ~2964)
    src, n = apply(src, "xinput2_rawinput in X11DRV_CreateWindow",
        "                /* listen to raw xinput event in the desktop window thread */\n"
        "                data->xinput2_rawinput = TRUE;\n"
        "                x11drv_xinput2_enable( data->display, DefaultRootWindow( data->display ) );\n",

        "                /* listen to raw xinput event in the desktop window thread */\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT2_H\n"
        "                data->xinput2_rawinput = TRUE;\n"
        "                x11drv_xinput2_enable( data->display, DefaultRootWindow( data->display ) );\n"
        "#endif\n"
    )
    total += n

    # 4. Add #ifdef __ANDROID__ class_hints branch in set_initial_wm_hints (line ~1167)
    src, n = apply(src, "android class_hints",
        "    if ((class_hints = XAllocClassHint()))\n"
        "    {\n"
        "        static char steam_proton[] = \"steam_proton\";\n"
        "        const char *app_id = getenv(\"SteamAppId\");\n"
        "        char proton_app_class[128];\n"
        "\n"
        "        if(app_id && *app_id){\n"
        "            snprintf(proton_app_class, sizeof(proton_app_class), \"steam_app_%s\", app_id);\n"
        "            class_hints->res_name = proton_app_class;\n"
        "            class_hints->res_class = proton_app_class;\n"
        "        }else{\n"
        "            class_hints->res_name = steam_proton;\n"
        "            class_hints->res_class = steam_proton;\n"
        "        }\n"
        "\n"
        "        XSetClassHint( display, window, class_hints );\n"
        "        XFree( class_hints );\n"
        "    }\n",

        "    if ((class_hints = XAllocClassHint()))\n"
        "    {\n"
        "#ifdef __ANDROID__\n"
        "        class_hints->res_name = process_name;\n"
        "        class_hints->res_class = process_name;\n"
        "#else\n"
        "        static char steam_proton[] = \"steam_proton\";\n"
        "        const char *app_id = getenv(\"SteamAppId\");\n"
        "        char proton_app_class[128];\n"
        "\n"
        "        if(app_id && *app_id){\n"
        "            snprintf(proton_app_class, sizeof(proton_app_class), \"steam_app_%s\", app_id);\n"
        "            class_hints->res_name = proton_app_class;\n"
        "            class_hints->res_class = proton_app_class;\n"
        "        }else{\n"
        "            class_hints->res_name = steam_proton;\n"
        "            class_hints->res_class = steam_proton;\n"
        "        }\n"
        "#endif\n"
        "        XSetClassHint( display, window, class_hints );\n"
        "        XFree( class_hints );\n"
        "    }\n"
    )
    total += n

    # 5. Guard only _NET_WM_PID (getpid) with #ifndef __ANDROID__.
    # GameNative keeps XdndAware enabled on Android.
    src, n = apply(src, "android _NET_WM_PID guard",
        "    /* set the pid. together, these properties are needed so the window manager can kill us if we freeze */\n"
        "    i = getpid();\n"
        "    XChangeProperty(display, window, x11drv_atom(_NET_WM_PID),\n"
        "                    XA_CARDINAL, 32, PropModeReplace, (unsigned char *)&i, 1);\n"
        "\n"
        "    XChangeProperty( display, window, x11drv_atom(XdndAware),\n"
        "                     XA_ATOM, 32, PropModeReplace, (unsigned char*)&dndVersion, 1 );\n"
        "}\n",

        "#ifndef __ANDROID__\n"
        "    /* set the pid. together, these properties are needed so the window manager can kill us if we freeze */\n"
        "    i = getpid();\n"
        "    XChangeProperty(display, window, x11drv_atom(_NET_WM_PID),\n"
        "                    XA_CARDINAL, 32, PropModeReplace, (unsigned char *)&i, 1);\n"
        "\n"
        "    XChangeProperty( display, window, x11drv_atom(XdndAware),\n"
        "                     XA_ATOM, 32, PropModeReplace, (unsigned char*)&dndVersion, 1 );\n"
        "#endif\n"
        "}\n"
    )
    total += n

    # 6. Add Android _NET_WM_PID and _NET_WM_HWND in set_net_active_window.
    src, n = apply(src, "android set_net_active_window _NET_WM_PID/_NET_WM_HWND",
        "    XFlush( data->display );\n"
        "}\n"
        "\n"
        "BOOL window_has_pending_wm_state",

        "    XFlush( data->display );\n"
        "\n"
        "#ifdef __ANDROID__\n"
        "    DWORD pid = 0;\n"
        "\n"
        "    NtUserGetWindowThread( hwnd, &pid );\n"
        "\n"
        "    XChangeProperty(data->display, window, x11drv_atom(_NET_WM_PID),\n"
        "                    XA_CARDINAL, 32, PropModeReplace, (unsigned char *)&pid, 1);\n"
        "#endif\n"
        "}\n"
        "\n"
        "BOOL window_has_pending_wm_state"
    )
    total += n

    with open(window_c, "w") as f:
        f.write(src)

    print(f"\nDone. Applied {total} fix(es) to window.c")


if __name__ == "__main__":
    main()
