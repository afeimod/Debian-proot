# Debian-proot
本仓库就是代码存储
接下来开始
# 安装termux和termux-x11或者exa-x11
下载 [**termux**](https://github.com/afeimod/Debian-proot/releases/download/termux/Termux_0.118.0+843d88c.apk) 

下载 [**termux-x11**](https://github.com/afeimod/Debian-proot/releases/download/termux/Termux_X11_1.03.00.apk) 

下载 [**exa-x11**](https://github.com/afeimod/Debian-proot/releases/download/termux/Exa_x11_v0.012.apk) 

# 半自动安装debian(推荐)
*给termux存储权限输入下面代码回车:

    wget -O 1.sh https://raw.githubusercontent.com/afeimod/Debian-proot/refs/heads/main/debianxfce.sh && chmod +x ./1.sh && ./1.sh
    
# 手动安装debian
*给termux存储权限输入下面代码回车:

    termux-setup-storage
    
*安装x11依赖

    pkg install wget -y
    pkg update -y
    pkg install x11-repo -y
    pkg install termux-x11-nightly -y
    
*安装proot-distro和debian本体

    pkg install proot-distro -y
    proot-distro install debian  
    
# 进入debian，创建用户
*升级并安装nano

    proot-distro login debian
    apt update -y
    apt install nano adduser -y
    apt install sudo -y
    
# 接下来安装xfce4
*本体

    sudo apt install xfce4 xfce4-goodies -y

    按要求选择chinese

    
    
    
*接下来是一些软件和东西可以选择不装，建议装

    sudo apt install cinnamon -y
    sudo apt install dbus-x11 nano gnome gnome-shell gnome-terminal gnome-tweaks gnome-software nautilus gnome-shell-extension-manager gedit tigervnc-tools gnupg2 -y
    
*安装360浏览器(选装)
   
    curl http://$(curl https://browser.360.cn/se/linux/ | grep "arm" | head -n 1 | cut -d "'" -f 2) -O

    sudo apt install ./browser360-cn-stable_10.6.1000.37-1_arm64.deb
    
*如果报错就卸载
   
    sudo apt remove browser360-cn-stable
    
*也可以后期输入proot-distro login debian进入用户再安装

*解决黑屏

    apt install dbus-x11
    
# 安装中文环境(不要退出用户)

    sudo apt update
    sudo apt install locales
    sudo dpkg-reconfigure locales
    314
    3
    sudo apt install fonts-wqy-microhei fonts-wqy-zenhei xfonts-wqy
    exit

*安装声音(退出用户)

    pkg install pulseaudio -y
    
# 接下来建立一个启动文件比如startx11放在home或者usr/bin
文本是

    #!/data/data/com.termux/files/usr/bin/bash
    pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" --exit-idle-time=-1

    export XDG_RUNTIME_DIR=${TMPDIR}
    termux-x11 :0 >/dev/null &

    sleep 2


    am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity > /dev/null 2>&1
    sleep 1

    proot-distro login debian --shared-tmp -- /bin/bash -c  'export PULSE_SERVER=127.0.0.1 && export XDG_RUNTIME_DIR=${TMPDIR} && su - root -c "env DISPLAY=:0 startxfce4"'

    exit 0

*然后给权限

    chmod +x 位置加名字

*位置加名字 为启动命令最好放在usr/bin，方便直接名字启动

# 想使用exa-x11就新建下面代码的启动文件比如startexa

    #!/data/data/com.termux/files/usr/bin/bash
    mv /data/data/com.termux/files/usr/tmp /data/data/com.termux/files/usr/tmp2
    ln -s /data/user/0/com.exa.x11/files/image/tmp /data/data/com.termux/files/usr/tmp
    pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" --exit-idle-time=-1

    export XDG_RUNTIME_DIR=${TMPDIR}
    termux-x11 :1 >/dev/null &

    sleep 2

    proot-distro login debian --shared-tmp -- /bin/bash -c  'export PULSE_SERVER=127.0.0.1 && export XDG_RUNTIME_DIR=${TMPDIR} && su - root -c "env DISPLAY=:0 startxfce4"'

    exit 0
    


    


    
    
