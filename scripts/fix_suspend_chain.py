#!/usr/bin/env python3
"""
Applies critical suspend-bypass edits directly to source files when
upstream line drift makes test-bylaws patches fail to apply.

Usage: fix_suspend_chain.py <wine-source-dir>
"""
import os
import sys


def apply_once(src, desc, old, new):
    if new in src:
        print(f"  [{desc}] already applied, skipping")
        return src, 0
    if old not in src:
        print(f"  [{desc}] pattern not found")
        return src, -1
    print(f"  [{desc}] applied")
    return src.replace(old, new, 1), 1


def patch_file(path, ops):
    if not os.path.exists(path):
        print(f"ERROR: missing file {path}")
        return False

    with open(path, errors="replace") as f:
        src = f.read()

    changed = 0
    hard_miss = False
    for desc, old, new in ops:
        src, rc = apply_once(src, desc, old, new)
        if rc > 0:
            changed += rc
        elif rc < 0:
            hard_miss = True

    with open(path, "w") as f:
        f.write(src)

    print(f"  -> {os.path.basename(path)} changes: {changed}")
    return not hard_miss


def patch_wow64_process(path):
    if not os.path.exists(path):
        print(f"ERROR: missing file {path}")
        return False

    with open(path, errors="replace") as f:
        src = f.read()

    ok = True

    old = "    return NtSuspendThread( handle, count );\n"
    new = "    return RtlWow64SuspendThread( handle, count );\n"
    src, rc = apply_once(src, "wow64_NtSuspendThread forwards to RtlWow64SuspendThread", old, new)
    if rc < 0:
        ok = False


    with open(path, "w") as f:
        f.write(src)

    return ok


def verify_markers(wine_src):
    checks = [
        ("dlls/wow64/process.c", ["RtlWow64SuspendThread"]),
        ("server/thread.h", ["bypass_proc_suspend"]),
        ("server/thread.c", ["get_effective_proc_suspend", "bypass_proc_suspend"]),
        ("server/process.c", ["!thread->bypass_proc_suspend"]),
        ("dlls/ntdll/unix/thread.c", ["THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE", "SkipLoaderInit"]),
    ]

    ok = True
    for rel, needles in checks:
        path = os.path.join(wine_src, rel)
        if not os.path.exists(path):
            print(f"VERIFY FAIL: {rel} missing")
            ok = False
            continue
        with open(path, errors="replace") as f:
            txt = f.read()
        for n in needles:
            if n not in txt:
                print(f"VERIFY FAIL: marker '{n}' missing in {rel}")
                ok = False
    return ok


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_suspend_chain.py <wine-source-dir>")
        return 1

    wine_src = sys.argv[1]

    thread_h_ops = [
        (
            "add bypass_proc_suspend field",
            "    int                    dbg_hidden;    /* hidden from debugger */\n",
            "    int                    dbg_hidden;    /* hidden from debugger */\n"
            "    int                    bypass_proc_suspend; /* will still run if the process is suspended */\n",
        ),
    ]

    thread_c_ops = [
        (
            "init bypass_proc_suspend",
            "    thread->dbg_hidden      = 0;\n",
            "    thread->dbg_hidden      = 0;\n"
            "    thread->bypass_proc_suspend = 0;\n",
        ),
        (
            "add get_effective_proc_suspend helper",
            "/* check if address looks valid for a client-side data structure (TEB etc.) */\n",
            "static int get_effective_proc_suspend( struct thread *thread )\n"
            "{\n"
            "    return thread->bypass_proc_suspend ? 0 : thread->process->suspend;\n"
            "}\n\n"
            "/* check if address looks valid for a client-side data structure (TEB etc.) */\n",
        ),
        (
            "use effective suspend in suspend_thread",
            "        if (!(thread->process->suspend + thread->suspend++))\n",
            "        if (!(get_effective_proc_suspend( thread ) + thread->suspend++))\n",
        ),
        (
            "use effective suspend in resume_thread",
            "        if (!(thread->suspend + thread->process->suspend)) wake_thread( thread );\n",
            "        if (!(thread->suspend + get_effective_proc_suspend( thread ))) wake_thread( thread );\n",
        ),
        (
            "use effective suspend in check_wait",
            "    if (thread->process->suspend + thread->suspend > 0) return -1;\n",
            "    if (get_effective_proc_suspend( thread ) + thread->suspend > 0) return -1;\n",
        ),
        (
            "use effective suspend in wake_thread_queue_entry",
            "    if (thread->process->suspend + thread->suspend > 0) return 0;  /* cannot acquire locks */\n",
            "    if (get_effective_proc_suspend( thread ) + thread->suspend > 0) return 0;  /* cannot acquire locks */\n",
        ),
        (
            "use effective suspend in thread_timeout",
            "    if (thread->suspend + thread->process->suspend > 0) return;  /* suspended, ignore it */\n",
            "    if (thread->suspend + get_effective_proc_suspend( thread ) > 0) return;  /* suspended, ignore it */\n",
        ),
        (
            "set bypass_proc_suspend in new_thread",
            "        thread->dbg_hidden = !!(req->flags & THREAD_CREATE_FLAGS_HIDE_FROM_DEBUGGER);\n",
            "        thread->dbg_hidden = !!(req->flags & THREAD_CREATE_FLAGS_HIDE_FROM_DEBUGGER);\n"
            "        thread->bypass_proc_suspend = !!(req->flags & THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE);\n",
        ),
        (
            "use effective suspend in init_thread reply",
            "    reply->suspend = (current->suspend || current->process->suspend || current->context != NULL);\n",
            "    reply->suspend = (current->suspend || get_effective_proc_suspend( current ) || current->context != NULL);\n",
        ),
    ]

    process_c_ops = [
        (
            "guard stop_thread with bypass flag",
            "            if (!thread->suspend) stop_thread( thread );\n",
            "            if (!thread->bypass_proc_suspend && !thread->suspend) stop_thread( thread );\n",
        ),
        (
            "guard wake_thread with bypass flag",
            "            if (!thread->suspend) wake_thread( thread );\n",
            "            if (!thread->bypass_proc_suspend && !thread->suspend) wake_thread( thread );\n",
        ),
        (
            "guard suspend_thread with bypass flag",
            "            suspend_thread( thread );\n",
            "            if (!thread->bypass_proc_suspend) suspend_thread( thread );\n",
        ),
        (
            "guard resume_thread with bypass flag",
            "            resume_thread( thread );\n",
            "            if (!thread->bypass_proc_suspend) resume_thread( thread );\n",
        ),
    ]

    ntdll_unix_thread_ops = [
        (
            "extend supported thread flags",
            "    static const ULONG supported_flags = THREAD_CREATE_FLAGS_CREATE_SUSPENDED | THREAD_CREATE_FLAGS_HIDE_FROM_DEBUGGER;\n",
            "    static const ULONG supported_flags = THREAD_CREATE_FLAGS_CREATE_SUSPENDED | THREAD_CREATE_FLAGS_SKIP_THREAD_ATTACH |\n"
            "                                         THREAD_CREATE_FLAGS_HIDE_FROM_DEBUGGER | THREAD_CREATE_FLAGS_SKIP_LOADER_INIT |\n"
            "                                         THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE;\n",
        ),
        (
            "declare wow_teb",
            "    int request_pipe[2];\n"
            "    TEB *teb;\n",
            "    int request_pipe[2];\n"
            "    WOW_TEB *wow_teb;\n"
            "    TEB *teb;\n",
        ),
        (
            "propagate SkipThreadAttach/SkipLoaderInit flags",
            "    set_thread_id( teb, GetCurrentProcessId(), tid );\n\n"
            "    thread_data = (struct ntdll_thread_data *)&teb->GdiTebBatch;\n",
            "    set_thread_id( teb, GetCurrentProcessId(), tid );\n\n"
            "    teb->SkipThreadAttach = !!(flags & THREAD_CREATE_FLAGS_SKIP_THREAD_ATTACH);\n"
            "    teb->SkipLoaderInit = !!(flags & THREAD_CREATE_FLAGS_SKIP_LOADER_INIT);\n"
            "    wow_teb = get_wow_teb( teb );\n"
            "    if (wow_teb) {\n"
            "        wow_teb->SameTebFlags = teb->SameTebFlags;\n"
            "    }\n\n"
            "    thread_data = (struct ntdll_thread_data *)&teb->GdiTebBatch;\n",
        ),
    ]

    ok = True
    ok &= patch_wow64_process(os.path.join(wine_src, "dlls", "wow64", "process.c"))
    ok &= patch_file(os.path.join(wine_src, "server", "thread.h"), thread_h_ops)
    ok &= patch_file(os.path.join(wine_src, "server", "thread.c"), thread_c_ops)
    ok &= patch_file(os.path.join(wine_src, "server", "process.c"), process_c_ops)
    ok &= patch_file(os.path.join(wine_src, "dlls", "ntdll", "unix", "thread.c"), ntdll_unix_thread_ops)

    verified = verify_markers(wine_src)

    if not ok or not verified:
        print("fix_suspend_chain: FAILED to apply full suspend-bypass chain")
        return 2

    print("fix_suspend_chain: suspend-bypass chain looks complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
