# Environment Variables

This page documents the environment variables in the current `wine/` tree that are actually worth knowing about as a user.

It is not meant to be a dump of every environment-variable read in Wine. I left out test-only knobs, generic OS variables like `PATH` and `HOME`, and third-party library settings that are not useful for normal runtime tuning.

One important limitation: the current local `wine/` tree does not contain the Android patch-only variables like `WINE_ANDROID_ABSOLUTE_MOUSE`, `WINE_ANDROID_DINPUT_COMPAT`, `WINE_INPUT_POLL_DEBUG`, or `WINE_DINPUT_INSTANCE_DEBUG`. Those still exist in repo patch paths, but they are not present in the checked-out source tree this document was based on.

## Start Here

If you only care about the variables most people are likely to touch, start with these:

- `WINEDEBUG`: controls Wine debug logging
- `WINEESYNC`: enables esync
- `WINEFSYNC`: enables fsync
- `WINE_DISABLE_FULLSCREEN_HACK`: disables the X11 fullscreen hack
- `PROTON_DISABLE_HIDRAW` and `PROTON_ENABLE_HIDRAW`: change controller hidraw behavior in `winebus`
- `WINE_HIDE_NVIDIA_GPU`, `WINE_HIDE_AMD_GPU`, `WINE_HIDE_INTEL_GPU`, `WINE_HIDE_VANGOGH_GPU`: change reported GPU identity
- `SteamAppId` and `SteamGameId`: trigger Steam and Proton compatibility paths in a lot of code

## Steam And Proton Variables

### `SteamAppId`

Used in several places, including `winex11.drv`, speech components, and `tabtip`. In practice this is one of the main Steam compatibility variables. It affects things like window class naming and other app-specific behavior.

### `SteamGameId`

This appears in a lot of runtime code, including input, graphics, media, and browser-related paths. It is clearly used as a broad game-specific compatibility switch.

### `SteamDeck`

Seen in `programs/tabtip/tabtip.c`. This is a narrower variable used for Steam Deck-related on-screen keyboard behavior.

### `STEAM_COMPAT_APP_ID`

Seen in MSI package handling. This is another Steam compatibility identifier, but much narrower than `SteamAppId` or `SteamGameId`.

### `STEAM_COMPAT_TRANSCODED_MEDIA_PATH`

Used by Proton TTS and winegstreamer media-converter code. It points those paths at Steam or Proton transcoded media assets.

### `PROTON_DISABLE_HIDRAW`

Used in `winebus.sys`. If you are debugging controller behavior, this is one of the first Proton variables to care about.

### `PROTON_ENABLE_HIDRAW`

Also used in `winebus.sys`. This is the positive override for hidraw support.

### `PROTON_VOICE_FILES`

Used by Proton TTS. This sets an override path for voice files.

## Wine Logging, Debugging, And Tooling

### `WINEDEBUG`

The classic Wine logging switch. It controls debug channels and message filtering.

### `WINE_GDB`

Used by `winedbg`. Lets Wine use a different `gdb` executable than the default.

### `WINE_CRASH_REPORT_DIR`

Used by `winedbg` crash reporting. If you care where crash reports land, this matters.

### `WINEBUILD`

Used by `winegcc`. This is more of a developer-facing variable than a runtime one, but it is still a real Wine variable in the current tree.

### `WINELOADER`

Used by `dbghelp`. Another less common variable, but it can matter when helper code needs an explicit Wine loader path.

## Sync, Loader, And Scheduler Variables

### `WINEESYNC`

Used in the esync paths in both `ntdll` and the server. This is one of the main runtime performance toggles people actually use.

### `WINEFSYNC`

Used in the fsync paths in both `ntdll` and the server. Same category as `WINEESYNC`: common, important, and user-facing.

### `WINE_RAM_REPORTING_BIAS`

Used in `ntdll/unix/loader.c`. This adjusts memory reporting behavior.

### `WINE_SIMULATE_ASYNC_READ`

Used in `ntdll/unix/loader.c`. This enables the async-read simulation path.

### `WINE_SIMULATE_WRITECOPY`

Also in `ntdll/unix/loader.c`. This changes write-copy simulation behavior.

### `WINE_UNIX_PC_AS_NTDLL`

Another loader-side variable. It affects how the Unix program counter is treated relative to ntdll.

### `WINE_FSYNC_SIMULATE_SCHED_QUANTUM`

Used in the loader-side fsync tuning code. This is a scheduler simulation knob, not a mainstream user variable.

### `WINE_ALERT_SIMULATE_SCHED_QUANTUM`

Same general category as the previous one, but for alertable wait behavior.

### `WINE_FSYNC_YIELD_TO_WAITERS`

Changes fsync waiter-yield behavior.

### `WINE_FSYNC_HELP_SIMULATED_PULSE`

Changes how the simulated pulse helper path behaves in fsync-related code.

### `WINE_CPU_TOPOLOGY`

Used in `ntdll/unix/system.c`. This overrides reported CPU topology.

### `WINE_LOGICAL_CPUS_AS_CORES`

Also in `ntdll/unix/system.c`. This makes Wine treat logical CPUs as physical cores for topology reporting.

### `WINEPRELOADRESERVE`

Used in `ntdll/unix/virtual.c`. This controls preload address-space reservation.

### `WINE_LD_PRELOAD`

Used in the same virtual-memory area. It is a helper variable for preload handling when `LD_PRELOAD` is not already set.

### `WINESTEAMNOEXEC`

A Steam-related loader variable. Niche, but real.

## Graphics And GPU Variables

### `WINE_D3D_CONFIG`

Used by `wined3d`. This is a configuration string for D3D behavior.

### `WINE_DISABLE_FULLSCREEN_HACK`

Used in `winex11.drv/opengl.c`. This is one of the more useful graphics variables because it directly disables the X11 fullscreen hack.

### `WINE_GL_VENDOR_REPORT_AMD`

Used in the X11 OpenGL path. It changes vendor reporting toward AMD compatibility.

### `WINE_HIDE_NVIDIA_GPU`

Used in both `win32u` and Vulkan reporting. Hides NVIDIA GPU identity from selected paths.

### `WINE_HIDE_AMD_GPU`

Same idea, but for AMD.

### `WINE_HIDE_INTEL_GPU`

Same idea, but for Intel.

### `WINE_HIDE_VANGOGH_GPU`

Special-case GPU identity override for Van Gogh.

### `WINE_HIDE_APU`

Used in the AGS path. More specialized than the others, but still clearly user-facing.

## Media And Runtime Component Variables

### `WINE_DO_NOT_CREATE_DXGI_DEVICE_MANAGER`

Used by `mfplat`. This disables DXGI device manager creation.

### `WINE_ENABLE_GST_LIVE_LATENCY`

Used by winegstreamer. This enables live-latency behavior.

### `WINE_GST_REGISTRY_DIR`

Lets winegstreamer use a different GStreamer registry directory.

### `WINE_GECKO_MAIN_THREAD`

Used in `mshtml`. This forces Gecko-related work onto the main-thread path.

### `WINE_MONO_AOT`

Used by `mscoree`. Controls Mono AOT behavior.

### `WINE_MONO_TRACE`

Used by `mscoree`. Enables Mono trace output.

### `WINE_MONO_VERBOSE`

Used by `mscoree`. Enables Mono verbose output.

### `WINE_MONO_OVERRIDES`

Used by `mscoree`. Sets Mono override options.

## Other Real Runtime Variables

### `WINE_DISABLE_EAC_ALT_DOWNLOAD`

Used in `ws2_32`. This disables the alternate EAC download path referenced there.

### `WINE_DBGHELP_OLD_PDB`

Used in `dbghelp`. Keeps the older PDB reader path.

### `WINEBUSCONFIG`

Used in `winebus.sys`. A winebus configuration string.

## Probably Not Worth Documenting Further

There are more environment-variable reads in the full source tree, but most of the remaining ones fall into one of these buckets:

- test harness variables
- generic host environment variables
- third-party library variables from bundled dependencies
- very narrow one-off developer knobs that are unlikely to help an end user

That is why this file is curated instead of exhaustive.
