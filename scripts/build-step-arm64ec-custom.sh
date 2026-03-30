#!/bin/bash
# 自定义构建脚本，支持通过环境变量覆盖路径

# 设置默认值，允许外部传入环境变量覆盖
: ${TERMUXFS_ROOT:="$HOME/termuxfs/aarch64"}
: ${TARGET_APP_ID:="com.winlator"}
: ${PROFILE_VERSION:="arm64ec"}
: ${OUTPUT_DIR:="$HOME/compiled-files-aarch64"}

export ARCH="aarch64"
export WIN_ARCH="arm64ec,aarch64,i386"
export OUTPUT_DIR="${OUTPUT_DIR}"

export deps="${TERMUXFS_ROOT}/data/data/com.termux/files/usr"
# 最终安装路径（设备上的实际路径）
export install_dir="/data/data/${TARGET_APP_ID}/files/imagefs/opt/${PROFILE_VERSION}-wine"
# 运行时库路径（设备上的实际路径）
export RUNTIME_PATH="/data/data/${TARGET_APP_ID}/files/imagefs/usr"

# 工具链路径（与原有保持一致）
export TOOLCHAIN="$HOME/Android/Sdk/ndk/27.3.13750724/toolchains/llvm/prebuilt/linux-x86_64/bin"
export LLVM_MINGW_TOOLCHAIN="$HOME/toolchains/llvm-mingw-20250920-ucrt-ubuntu-22.04-x86_64/bin"
export TARGET=aarch64-linux-android28
export PATH="${LLVM_MINGW_TOOLCHAIN}:${PATH}"

export CC="${TOOLCHAIN}/${TARGET}-clang"
export AS="${CC}"
export CXX="${TOOLCHAIN}/${TARGET}-clang++"
export AR="${TOOLCHAIN}/llvm-ar"
export LD="${TOOLCHAIN}/ld"
export RANLIB="${TOOLCHAIN}/llvm-ranlib"
export STRIP="${TOOLCHAIN}/llvm-strip"
export DLLTOOL="${LLVM_MINGW_TOOLCHAIN}/llvm-dlltool"

export PKG_CONFIG_LIBDIR="${deps}/lib/pkgconfig:${deps}/share/pkgconfig"
export ACLOCAL_PATH="${deps}/lib/aclocal:${deps}/share/aclocal"
export CPPFLAGS="-I${deps}/include --sysroot=${TOOLCHAIN}/../sysroot"

export C_OPTS="-Wno-declaration-after-statement -Wno-implicit-function-declaration -Wno-int-conversion"
export CFLAGS="${C_OPTS} ${CFLAGS:-}"
export CXXFLAGS="${C_OPTS} ${CXXFLAGS:-}"
export LDFLAGS="-L${deps}/lib -Wl,-rpath=${RUNTIME_PATH}/lib ${LDFLAGS:-}"

export FREETYPE_CFLAGS="-I${deps}/include/freetype2"
export PULSE_CFLAGS="-I${deps}/include/pulse"
export PULSE_LIBS="-L${deps}/lib/pulseaudio -lpulse"
export SDL2_CFLAGS="-I${deps}/include/SDL2"
export SDL2_LIBS="-L${deps}/lib -lSDL2"
export X_CFLAGS="-I${deps}/include/X11"
export X_LIBS="-landroid-sysvshm"
export GSTREAMER_CFLAGS="-I${deps}/include/gstreamer-1.0 -I${deps}/include/glib-2.0 -I${deps}/lib/glib-2.0/include -I${deps}/glib-2.0/include -I${deps}/lib/gstreamer-1.0/include"
export GSTREAMER_LIBS="-L${deps}/lib -lgstgl-1.0 -lgstapp-1.0 -lgstvideo-1.0 -lgstaudio-1.0 -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgsttag-1.0 -lgstbase-1.0 -lgstreamer-1.0"
export FFMPEG_CFLAGS="-I${deps}/include/libavutil -I${deps}/include/libavcodec -I${deps}/include/libavformat"
export FFMPEG_LIBS="-L${deps}/lib -lavutil -lavcodec -lavformat"

for arg in "$@"
do
  if [ "$arg" == "--build-sysvshm" ];
  then
    # Build android_sysvshm library
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

    if [ -d "$PROJECT_ROOT/android/android_sysvshm" ]; then
        echo "Building android_sysvshm library..."
        cd "$PROJECT_ROOT/android/android_sysvshm"
        ./build-aarch64.sh
        if [ $? -eq 0 ]; then
            echo "android_sysvshm built successfully"
            mkdir -p "$deps/lib"
            cp build-aarch64/libandroid-sysvshm.so "$deps/lib/"
            echo "Copied libandroid-sysvshm.so to $deps/lib/"
        else
            echo "Warning: android_sysvshm build failed"
        fi
        cd "$PROJECT_ROOT"
    fi
  fi

  if [ "$arg" == "--configure" ];
  then
    ./configure \
      --enable-archs=$WIN_ARCH \
      --host=$TARGET \
      --prefix $install_dir \
      --bindir $install_dir/bin \
      --libdir $install_dir/lib \
      --exec-prefix $install_dir \
      --with-mingw=clang \
      --with-wine-tools=./wine-tools \
      --enable-win64 \
      --disable-win16 \
      --enable-nls \
      --disable-amd_ags_x64 \
      --enable-wineandroid_drv=no \
      --disable-tests \
      --with-alsa \
      --without-capi \
      --without-coreaudio \
      --without-cups \
      --without-dbus \
      --without-ffmpeg \
      --with-fontconfig \
      --with-freetype \
      --without-gcrypt \
      --without-gettext \
      --with-gettextpo=no \
      --without-gphoto \
      --with-gnutls \
      --without-gssapi \
      --with-gstreamer \
      --without-inotify \
      --without-krb5 \
      --without-netapi \
      --without-opencl \
      --with-opengl \
      --without-osmesa \
      --without-oss \
      --without-pcap \
      --without-pcsclite \
      --without-piper \
      --with-pthread \
      --with-pulse \
      --without-sane \
      --with-sdl \
      --without-udev \
      --without-unwind \
      --without-usb \
      --without-v4l2 \
      --without-vosk \
      --with-vulkan \
      --without-wayland \
      --without-xcomposite \
      --without-xcursor \
      --without-xfixes \
      --without-xinerama \
      --without-xinput \
      --without-xinput2 \
      --without-xrandr \
      --without-xrender \
      --without-xshape \
      --with-xshm \
      --without-xxf86vm

    echo "Applying patches..."

    PATCHES=(
      # android network patch
      "android_network.patch"
      "dlls_nsiproxy_sys_ip_c.patch"

      # midi support
      "midi_support.patch"

      # sdl patch
      "dlls_winebus_sys_bus_sdl_c.patch"

      # shm_utils
      "dlls_ntdll_unix_esync_c.patch"
      "dlls_ntdll_unix_fsync_c.patch"
      "server_esync_c.patch"
      "server_fsync_c.patch"

      # winex11
      "dlls_winex11_drv_x11drv_h.patch"
      "dlls_winex11_drv_bitblt_c.patch"
      "dlls_winex11_drv_desktop_c.patch"
      "dlls_winex11_drv_mouse_c.patch"
      "dlls_winex11_drv_window_c.patch"
      "dlls_winex11_drv_x11drv_main_c.patch"

      # address space patches
      "dlls_ntdll_unix_virtual_c.patch"
      "loader_preloader_c.patch"

      # syscall Patches
      "dlls_ntdll_unix_signal_x86_64_c.patch"

      # pulse Patches
      "dlls_winepulse_drv_pulse_c.patch"

      # desktop patches
      "programs_explorer_desktop_c.patch"

      # path patches
      "dlls_ntdll_unix_server_c.patch"

      # winlator patches
      "dlls_amd_ags_x64_unixlib_c.patch"
      "dlls_winex11_drv_opengl_c.patch"

      # shortcut patch
      "programs_winemenubuilder_winemenubuilder_c.patch"

      # advapi32 patches
      "dlls_advapi32_advapi_c.patch"

      # browser patches
      "programs_winebrowser_makefile_in.patch"
      "programs_winebrowser_main_c.patch"

      # clipboard patches
      "dlls_user32_makefile_in.patch"
      "dlls_user32_clipboard_c.patch"
      "dlls_win32u_clipboard_c.patch"

      # fexcore patch
      "dlls_ntdll_loader_c.patch"
      "dlls_ntdll_unix_loader_c.patch"
      "dlls_wow64_syscall_c.patch"
      "loader_wine_inf_in.patch"

      # fix build
      "programs_wineboot_wineboot_c.patch"
      "dlls_wdscore_wdscore_spec.patch"

      # 1. Extended State (XSTATE/YMM) Support Patches
      "test-bylaws/dlls_ntdll_unwind_h.patch"
      "test-bylaws/include_winnt_h.patch"

      # 2. Thread Suspension Patches
      "test-bylaws/dlls_ntdll_signal_arm64_c.patch"
      "test-bylaws/dlls_ntdll_signal_arm64ec_c.patch"
      "test-bylaws/dlls_ntdll_signal_x86_64_c.patch"
      "test-bylaws/dlls_ntdll_ntdll_spec.patch"
      "test-bylaws/dlls_ntdll_ntdll_misc_h.patch"
      "test-bylaws/dlls_wow64_process_c.patch"
      "test-bylaws/dlls_wow64_wow64_spec.patch"

      # 3. Process and Virtual Memory Management
      "test-bylaws/dlls_wow64_virtual_c.patch"
      "test-bylaws/server_process_c.patch"
      "test-bylaws/dlls_ntdll_unix_process_c.patch"

      # 4. Server and Threading Infrastructure
      "test-bylaws/server_thread_h.patch"
      "test-bylaws/server_thread_c.patch"
      "test-bylaws/dlls_ntdll_unix_thread_c.patch"

      # 5. Internal Headers
      "test-bylaws/include_winternl_h.patch"

      # 6. Build System (Optional)
#      "test-bylaws/tools_makedep_c.patch"
    )

    for patch in "${PATCHES[@]}"; do
        git apply ./android/patches/$patch
    done
  fi

  if [ "$arg" == "--build" ]
  then
    echo "Building..."
    # 清理输出目录中的旧文件，但保留 OUTPUT_DIR 本身
    rm -rf $OUTPUT_DIR/bin
    rm -rf $OUTPUT_DIR/lib
    rm -rf $OUTPUT_DIR/share
    mkdir -p $OUTPUT_DIR
    make -j$(nproc)

    # 检查 wine 二进制文件是否生成且大小正常
    if [ -f "./wine" ]; then
        echo "wine binary size: $(stat -c %s ./wine) bytes"
        if [ $(stat -c %s ./wine) -lt 1000000 ]; then
            echo "ERROR: wine binary is too small (likely link failure)"
            exit 1
        fi
    else
        echo "ERROR: wine binary not found after build"
        exit 1
    fi
  fi

  if [ "$arg" == "--install" ]
  then
    echo "Installing to $OUTPUT_DIR$install_dir"
    # 清理旧的安装目录
    rm -rf "$OUTPUT_DIR$install_dir"
    # 使用 DESTDIR 安装，文件会被放到 $OUTPUT_DIR$install_dir 下
    make install DESTDIR="$OUTPUT_DIR" -j$(nproc)

    # 检查安装是否成功
    if [ ! -d "$OUTPUT_DIR$install_dir" ]; then
        echo "ERROR: Installation failed, $OUTPUT_DIR$install_dir not found"
        exit 1
    fi

    # 确保 wine 二进制文件存在
    if [ ! -f "$OUTPUT_DIR$install_dir/bin/wine" ]; then
        echo "ERROR: wine binary not found in installed directory"
        exit 1
    fi

    # 输出安装信息
    echo "Installation completed, files in $OUTPUT_DIR$install_dir"
    echo "Total size: $(du -sh $OUTPUT_DIR$install_dir | cut -f1)"

    # 可选：创建符号链接（如果需要）
    # ln -sf wine "$OUTPUT_DIR$install_dir/bin/wine64"
  fi
done