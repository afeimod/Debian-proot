环境：ubuntu 24.04 proot

必须：pd login ubuntu ```--no-sysvipc```

# Turnip
构建参数

```meson build64/ -D prefix=~/build -D platforms=x11,wayland -D gallium-drivers=swrast,virgl,zink,freedreno -D vulkan-drivers=freedreno -D egl=enabled -D gles2=enabled -D glvnd=enabled -D glx=dri -D libunwind=disabled -D osmesa=true -D shared-glapi=enabled -D microsoft-clc=disabled -D valgrind=disabled -D gles1=disabled -D freedreno-kmds=kgsl -D buildtype=release```

之所以没有 ```-D dri3=enabled```在mesa25.1.0中已删除

# Panfrost

构建参数

```
meson build -Dprefix=~/panfrost -Dvulkan-drivers=panfrost -Dgallium-drivers=panfrost
```

# Swrast(llvm vulkan)

构建参数

```
meson build -Dprefix=~/swrast -Dglx=xlib -Dgallium-drivers=swrast -Dvulkan-drivers=swrast
```
