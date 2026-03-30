#!/usr/bin/env python3
"""
Applies Android-specific changes to dlls/winex11.drv/mouse.c that are too
fragile to rely on via patch application against bleeding-edge.

This keeps the intended GameNative mouse behavior while avoiding malformed
preprocessor output from fuzzy patch application.

Usage: fix_mouse_c.py <wine-source-dir>
"""
import os
import sys


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
        print("Usage: fix_mouse_c.py <wine-source-dir>")
        sys.exit(1)

    wine_src = sys.argv[1]
    mouse_c = os.path.join(wine_src, "dlls", "winex11.drv", "mouse.c")

    if not os.path.exists(mouse_c):
        print(f"ERROR: {mouse_c} not found")
        sys.exit(1)

    with open(mouse_c, encoding="utf-8", errors="replace") as f:
        src = f.read()

    total = 0

    src, n = apply(src, "clip state declarations and xinput2 guard",
        "static RECT clip_rect;\n"
        "static Cursor create_cursor( HANDLE handle );\n\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT2_H\n"
        "static BOOL xinput2_available;\n",

        "static RECT clip_rect;\n"
        "static POINT clip_center;  /* center of clipping rect for relative motion synthesis */\n"
        "static POINT clip_center_root;  /* same point in X root coordinates for warping / deltas */\n"
        "static BOOL needs_relative_motion;  /* TRUE when game wants clipping but xinput2 unavailable */\n"
        "static Cursor create_cursor( HANDLE handle );\n\n"
        "#if defined(HAVE_X11_EXTENSIONS_XINPUT2_H) && !defined(__ANDROID__)\n"
        "static BOOL xinput2_available;\n"
    )
    total += n

    src, n = apply(src, "send flags helper",
        "#undef MAKE_FUNCPTR\n"
        "#endif\n\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT_H\n",

        "#undef MAKE_FUNCPTR\n"
        "#endif\n\n"
        "/* When XInput2 is available, explorer.exe centralises WM_INPUT generation via\n"
        " * SEND_HWMSG_NO_MSG raw events, so game processes must suppress their own raw\n"
        " * input dispatch to avoid duplicates (SEND_HWMSG_NO_RAW = legacy only).\n"
        " * When XInput2 is absent there is no explorer.exe raw input pipeline, so each\n"
        " * process must generate WM_INPUT itself alongside the legacy message. */\n"
        "#if defined(HAVE_X11_EXTENSIONS_XINPUT2_H) && !defined(__ANDROID__)\n"
        "static inline UINT get_send_mouse_flags(void)\n"
        "{\n"
        "    return xinput2_available ? SEND_HWMSG_NO_RAW : 0;\n"
        "}\n"
        "#else\n"
        "static inline UINT get_send_mouse_flags(void) { return 0; }\n"
        "#endif\n\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT_H\n"
    )
    total += n

    src, n = apply(src, "xinput2 implementation guard comment",
        "#else /* HAVE_X11_EXTENSIONS_XINPUT2_H */\n",
        "#else /* defined(HAVE_X11_EXTENSIONS_XINPUT2_H) && !defined(__ANDROID__) */\n"
    )
    total += n

    src, n = apply(src, "xinput2 implementation endif comment",
        "#endif /* HAVE_X11_EXTENSIONS_XINPUT2_H */\n",
        "#endif /* defined(HAVE_X11_EXTENSIONS_XINPUT2_H) && !defined(__ANDROID__) */\n"
    )
    total += n

    src, n = apply(src, "grab_clipping_window",
        "static BOOL grab_clipping_window( const RECT *clip )\n"
        "{\n"
        "#ifdef HAVE_X11_EXTENSIONS_XINPUT2_H\n"
        "    struct x11drv_thread_data *data = x11drv_thread_data();\n"
        "    Window clip_window;\n"
        "    HCURSOR cursor;\n"
        "    POINT pos;\n\n"
        "    /* don't clip in the desktop process */\n"
        "    if (NtUserGetWindowThread( NtUserGetDesktopWindow(), NULL ) == GetCurrentThreadId()) return TRUE;\n"
        "    /* don't clip the cursor if the X input focus is on another process window */\n"
        "    if (!is_current_process_focused()) return TRUE;\n\n"
        "    if (!data) return FALSE;\n"
        "    if (!(clip_window = init_clip_window())) return TRUE;\n\n"
        "    if (keyboard_grabbed)\n"
        "    {\n"
        "        WARN( \"refusing to clip to %s\\n\", wine_dbgstr_rect(clip) );\n"
        "        return FALSE;\n"
        "    }\n"
        "    if (!xinput2_available)\n"
        "    {\n"
        "        WARN( \"XInput2 not supported, refusing to clip to %s\\n\", wine_dbgstr_rect(clip) );\n"
        "        NtUserClipCursor( NULL );\n"
        "        return TRUE;\n"
        "    }\n\n"
        "    /* enable XInput2 unless we are already clipping */\n"
        "    if (!data->clipping_cursor) x11drv_xinput2_enable( data->display, DefaultRootWindow( data->display ) );\n\n"
        "    TRACE( \"clipping to %s win %lx\\n\", wine_dbgstr_rect(clip), clip_window );\n\n"
        "    if (!data->clipping_cursor) XUnmapWindow( data->display, clip_window );\n"
        "    pos = virtual_screen_to_root( clip->left, clip->top );\n"
        "    XMoveResizeWindow( data->display, clip_window, pos.x, pos.y,\n"
        "                       max( 1, clip->right - clip->left ), max( 1, clip->bottom - clip->top ) );\n"
        "    XMapWindow( data->display, clip_window );\n\n"
        "    /* if the rectangle is shrinking we may get a pointer warp */\n"
        "    if (!data->clipping_cursor || clip->left > clip_rect.left || clip->top > clip_rect.top ||\n"
        "        clip->right < clip_rect.right || clip->bottom < clip_rect.bottom)\n"
        "        data->warp_serial = NextRequest( data->display );\n\n"
        "    if (!XGrabPointer( data->display, clip_window, False,\n"
        "                       PointerMotionMask | ButtonPressMask | ButtonReleaseMask,\n"
        "                       GrabModeAsync, GrabModeAsync, clip_window, None, CurrentTime ))\n"
        "        clipping_cursor = TRUE;\n\n"
        "    SERVER_START_REQ( set_cursor )\n"
        "    {\n"
        "        req->flags = 0;\n"
        "        wine_server_call( req );\n"
        "        if (reply->prev_count < 0) cursor = 0;\n"
        "        else cursor = wine_server_ptr_handle( reply->prev_handle );\n"
        "    }\n"
        "    SERVER_END_REQ;\n\n"
        "    set_window_cursor( clip_window, cursor );\n\n"
        "    if (!clipping_cursor)\n"
        "    {\n"
        "        x11drv_xinput2_disable( data->display, DefaultRootWindow( data->display ) );\n"
        "        return FALSE;\n"
        "    }\n"
        "    clip_rect = *clip;\n"
        "    data->clipping_cursor = TRUE;\n"
        "    return TRUE;\n"
        "#else\n"
        "    WARN( \"XInput2 was not available at compile time\\n\" );\n"
        "    return FALSE;\n"
        "#endif\n"
        "}\n",

        "static BOOL grab_clipping_window( const RECT *clip )\n"
        "{\n"
        "    struct x11drv_thread_data *data = x11drv_thread_data();\n"
        "    Window clip_window;\n"
        "    HCURSOR cursor;\n"
        "    POINT pos;\n\n"
        "    /* don't clip in the desktop process */\n"
        "    if (NtUserGetWindowThread( NtUserGetDesktopWindow(), NULL ) == GetCurrentThreadId()) return TRUE;\n"
        "    /* don't clip the cursor if the X input focus is on another process window */\n"
        "    if (!is_current_process_focused()) return TRUE;\n\n"
        "    if (!data) return FALSE;\n"
        "    if (!(clip_window = init_clip_window())) return TRUE;\n\n"
        "    if (keyboard_grabbed)\n"
        "    {\n"
        "        WARN( \"refusing to clip to %s\\n\", wine_dbgstr_rect(clip) );\n"
        "        return FALSE;\n"
        "    }\n"
        "#if defined(HAVE_X11_EXTENSIONS_XINPUT2_H) && !defined(__ANDROID__)\n"
        "    if (!xinput2_available)\n"
        "#endif\n"
        "    {\n"
        "        WARN( \"XInput2 not available, enabling relative motion for %s\\n\", wine_dbgstr_rect(clip) );\n"
        "        clip_rect = *clip;\n"
        "        clip_center.x = (clip->left + clip->right) / 2;\n"
        "        clip_center.y = (clip->top + clip->bottom) / 2;\n"
        "        clip_center_root = virtual_screen_to_root( clip_center.x, clip_center.y );\n"
        "        needs_relative_motion = TRUE;\n"
        "        XWarpPointer( data->display, None, root_window, 0, 0, 0, 0, clip_center_root.x, clip_center_root.y );\n"
        "        data->warp_serial = NextRequest( data->display );\n"
        "        XFlush( data->display );\n"
        "        return TRUE;\n"
        "    }\n\n"
        "    /* enable XInput2 unless we are already clipping */\n"
        "    if (!data->clipping_cursor) x11drv_xinput2_enable( data->display, DefaultRootWindow( data->display ) );\n\n"
        "    TRACE( \"clipping to %s win %lx\\n\", wine_dbgstr_rect(clip), clip_window );\n\n"
        "    if (!data->clipping_cursor) XUnmapWindow( data->display, clip_window );\n"
        "    pos = virtual_screen_to_root( clip->left, clip->top );\n"
        "    XMoveResizeWindow( data->display, clip_window, pos.x, pos.y,\n"
        "                       max( 1, clip->right - clip->left ), max( 1, clip->bottom - clip->top ) );\n"
        "    XMapWindow( data->display, clip_window );\n\n"
        "    /* if the rectangle is shrinking we may get a pointer warp */\n"
        "    if (!data->clipping_cursor || clip->left > clip_rect.left || clip->top > clip_rect.top ||\n"
        "        clip->right < clip_rect.right || clip->bottom < clip_rect.bottom)\n"
        "        data->warp_serial = NextRequest( data->display );\n\n"
        "    if (!XGrabPointer( data->display, clip_window, False,\n"
        "                       PointerMotionMask | ButtonPressMask | ButtonReleaseMask,\n"
        "                       GrabModeAsync, GrabModeAsync, clip_window, None, CurrentTime ))\n"
        "        clipping_cursor = TRUE;\n\n"
        "    SERVER_START_REQ( set_cursor )\n"
        "    {\n"
        "        req->flags = 0;\n"
        "        wine_server_call( req );\n"
        "        if (reply->prev_count < 0) cursor = 0;\n"
        "        else cursor = wine_server_ptr_handle( reply->prev_handle );\n"
        "    }\n"
        "    SERVER_END_REQ;\n\n"
        "    set_window_cursor( clip_window, cursor );\n\n"
        "    if (!clipping_cursor)\n"
        "    {\n"
        "        x11drv_xinput2_disable( data->display, DefaultRootWindow( data->display ) );\n"
        "        return FALSE;\n"
        "    }\n"
        "    clip_rect = *clip;\n"
        "    data->clipping_cursor = TRUE;\n"
        "    return TRUE;\n"
        "}\n"
    )
    total += n

    src, n = apply(src, "ungrab relative motion cleanup",
        "    clipping_cursor = FALSE;\n"
        "    data->clipping_cursor = FALSE;\n"
        "    x11drv_xinput2_disable( data->display, DefaultRootWindow( data->display ) );\n",

        "    clipping_cursor = FALSE;\n"
        "    data->clipping_cursor = FALSE;\n"
        "    needs_relative_motion = FALSE;\n"
        "    clip_center_root.x = clip_center_root.y = 0;\n"
        "    x11drv_xinput2_disable( data->display, DefaultRootWindow( data->display ) );\n"
    )
    total += n

    src, n = apply(src, "send_mouse_input flags when hwnd is null",
        "        struct x11drv_thread_data *thread_data = x11drv_thread_data();\n"
        "        if (!thread_data->clipping_cursor || thread_data->clip_window != window) return;\n"
        "        NtUserSendHardwareInput( hwnd, SEND_HWMSG_NO_RAW, input, 0 );\n"
        "        return;\n",

        "        struct x11drv_thread_data *thread_data = x11drv_thread_data();\n"
        "        if (!thread_data->clipping_cursor || thread_data->clip_window != window) return;\n"
        "        NtUserSendHardwareInput( hwnd, get_send_mouse_flags(), input, 0 );\n"
        "        return;\n"
    )
    total += n

    src, n = apply(src, "send_mouse_input flags normal path",
        "    NtUserSendHardwareInput( hwnd, SEND_HWMSG_NO_RAW, input, 0 );\n",
        "    NtUserSendHardwareInput( hwnd, get_send_mouse_flags(), input, 0 );\n"
    )
    total += n

    src, n = apply(src, "android cursor hide/show guard",
        "    pXFixesHideCursor( data->display, root_window );\n"
        "    XWarpPointer( data->display, root_window, root_window, 0, 0, 0, 0, pos.x, pos.y );\n"
        "    data->warp_serial = NextRequest( data->display );\n"
        "    pXFixesShowCursor( data->display, root_window );\n",

        "#ifndef __ANDROID__\n"
        "    pXFixesHideCursor( data->display, root_window );\n"
        "#endif\n"
        "    XWarpPointer( data->display, root_window, root_window, 0, 0, 0, 0, pos.x, pos.y );\n"
        "    data->warp_serial = NextRequest( data->display );\n"
        "#ifndef __ANDROID__\n"
        "    pXFixesShowCursor( data->display, root_window );\n"
        "#endif\n"
    )
    total += n

    src, n = apply(src, "motion notify relative motion synthesis",
        "BOOL X11DRV_MotionNotify( HWND hwnd, XEvent *xev )\n"
        "{\n"
        "    XMotionEvent *event = &xev->xmotion;\n"
        "    INPUT input;\n\n"
        "    TRACE( \"hwnd %p/%lx pos %d,%d is_hint %d serial %lu\\n\",\n"
        "           hwnd, event->window, event->x, event->y, event->is_hint, event->serial );\n\n"
        "    input.mi.dx          = event->x;\n"
        "    input.mi.dy          = event->y;\n"
        "    input.mi.mouseData   = 0;\n"
        "    input.mi.dwFlags     = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;\n"
        "    input.mi.time        = EVENT_x11_time_to_win32_time( event->time );\n"
        "    input.mi.dwExtraInfo = 0;\n\n"
        "    if (is_old_motion_event( event->serial ))\n"
        "    {\n"
        "        TRACE( \"pos %d,%d old serial %lu, ignoring\\n\", event->x, event->y, event->serial );\n"
        "        return FALSE;\n"
        "    }\n"
        "    map_event_coords( hwnd, event->window, event->root, event->x_root, event->y_root, &input );\n"
        "    send_mouse_input( hwnd, event->window, event->state, &input );\n"
        "    return TRUE;\n"
        "}\n",

        "BOOL X11DRV_MotionNotify( HWND hwnd, XEvent *xev )\n"
        "{\n"
        "    XMotionEvent *event = &xev->xmotion;\n"
        "    INPUT input;\n\n"
        "    TRACE( \"hwnd %p/%lx pos %d,%d is_hint %d serial %lu\\n\",\n"
        "           hwnd, event->window, event->x, event->y, event->is_hint, event->serial );\n\n"
        "    if (is_old_motion_event( event->serial ))\n"
        "    {\n"
        "        TRACE( \"pos %d,%d old serial %lu, ignoring\\n\", event->x, event->y, event->serial );\n"
        "        return FALSE;\n"
        "    }\n\n"
        "    input.mi.mouseData   = 0;\n"
        "    input.mi.time        = EVENT_x11_time_to_win32_time( event->time );\n"
        "    input.mi.dwExtraInfo = 0;\n\n"
        "    /* Synthesize relative motion when game wants clipping but xinput2 unavailable */\n"
        "    if (needs_relative_motion && hwnd)\n"
        "    {\n"
        "        struct x11drv_thread_data *thread_data = x11drv_thread_data();\n"
        "        int dx = event->x_root - clip_center_root.x;\n"
        "        int dy = event->y_root - clip_center_root.y;\n\n"
        "        if (dx == 0 && dy == 0)\n"
        "            return FALSE;\n\n"
        "        input.mi.dx      = dx;\n"
        "        input.mi.dy      = dy;\n"
        "        input.mi.dwFlags = MOUSEEVENTF_MOVE;\n\n"
        "        /* Warp cursor back to center and ignore the synthetic recenter event. */\n"
        "        XWarpPointer( event->display, None, root_window, 0, 0, 0, 0, clip_center_root.x, clip_center_root.y );\n"
        "        thread_data->warp_serial = NextRequest( event->display );\n"
        "        XFlush( event->display );\n\n"
        "        send_mouse_input( hwnd, event->window, event->state, &input );\n"
        "        return TRUE;\n"
        "    }\n\n"
        "    input.mi.dx          = event->x;\n"
        "    input.mi.dy          = event->y;\n"
        "    input.mi.dwFlags     = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;\n\n"
        "    map_event_coords( hwnd, event->window, event->root, event->x_root, event->y_root, &input );\n"
        "    send_mouse_input( hwnd, event->window, event->state, &input );\n"
        "    return TRUE;\n"
        "}\n"
    )
    total += n

    with open(mouse_c, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)

    print(f"\nDone. Applied {total} fix(es) to mouse.c")


if __name__ == "__main__":
    main()
