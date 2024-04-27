# Debian-proot
本仓库就是代码存储
接下来开始
# 安装termux和termux-x11或者exa-x11
下载 [**termux**](https://github.com/afeimod/Debian-proot/releases/download/termux/Termux_0.118.0+843d88c.apk) 

下载 [**termux-x11**](https://github.com/afeimod/Debian-proot/releases/download/termux/Termux_X11_1.03.00.apk) 

下载 [**exa-x11**](https://github.com/afeimod/Debian-proot/releases/download/termux/Exa.x11_.apk) 

# 安装debian
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
    
*创建用户

    adduser droidmaster
    
