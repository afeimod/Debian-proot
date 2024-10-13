#!/bin/bash
clear
echo ""
echo " 开始安装 linbox...感谢mobox开发人员！感谢咔咔龙，小白一枚，deem，Asia，afei等" & sleep 1	
echo -e " 安装x11环境..."
pkg update -y
termux-change-repo

pkg upgrade -y
pkg install x11-repo -y
pkg install termux-x11-nightly -y
pkg install tur-repo -y
pkg install pulseaudio -y
pkg install proot-distro -y
pkg install wget -y
pkg install git -y
proot-distro install debian

echo -e " 安装debian环境..."

proot-distro login debian --shared-tmp -- /bin/bash -c "apt update -y"
proot-distro login debian --shared-tmp -- /bin/bash -c "dpkg --configure -a"
proot-distro login debian --shared-tmp -- /bin/bash -c "apt install nano adduser -y"

proot-distro login debian --shared-tmp -- /bin/bash -c "apt reinstall sudo -y"
read -p "接下来创建用户，需要手动输入密码和信息，确定请回车"
proot-distro login debian --shared-tmp -- /bin/bash -c "adduser afei"
read -p "接下来添加用户权限，请先复制下面代码 afei ALL=(ALL:ALL) ALL 需要手动粘帖到空隙处，然后点击ctrl+o 回车，ctrl+x！确定请回车"
proot-distro login debian --shared-tmp -- /bin/bash -c "nano /etc/sudoers"
read -p "接下来添加kali源，复制等下出现的代码粘贴进文本，确定请回车"
read -p "deb [trusted=yes] https://mirrors.ustc.edu.cn/kali kali-rolling main non-free contrib  请确定已经复制后回车"
proot-distro login debian --shared-tmp -- /bin/bash -c "nano /etc/apt/sources.list"
read -p "接下来安装kali桌面，提示时请输入密码，确定请回车"
echo -e " 创建启动文件debianx11..."

cat <<'EOF' > $PREFIX/bin/debianx11
#!/data/data/com.termux/files/usr/bin/bash
rm -rf $TMPDIR/pulse-* &>/dev/null &
pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" --exit-idle-time=-1

export XDG_RUNTIME_DIR=${TMPDIR}
termux-x11 :0 >/dev/null &

sleep 2


am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity > /dev/null 2>&1
sleep 1

proot-distro login debian --shared-tmp -- /bin/bash -c  'export PULSE_SERVER=127.0.0.1 && export XDG_RUNTIME_DIR=${TMPDIR} && su - afei -c "env DISPLAY=:0 startxfce4"'

exit 0
EOF
cat <<'EOF' > $PREFIX/var/lib/proot-distro/installed-rootfs/debian/usr/chromium.desktop
[Desktop Entry]
Version=1.0
Name=Chromium 网页浏览器
GenericName=网页浏览器
Comment=连接网络
Exec=/usr/bin/chromium %U --no-sandbox
Terminal=false
X-MultipleArgs=false
Type=Application
Icon=chromium
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml_xml;application/x-mimearchive;x-scheme-handler/http;x-scheme-handler/https;
StartupWMClass=chromium
StartupNotify=true
Keywords=browser
EOF
chmod -R u+x $PREFIX/bin

cat <<'EOF' > $PREFIX/var/lib/proot-distro/installed-rootfs/debian/usr/bin/go

sudo apt-get update -y
sudo apt install xfce4 xfce4-goodies -y
sudo apt install firefox-esr -y
sudo apt install chromium chromium-l10n -y
sudo apt install gnome-terminal -y
read -p "接下来安装容器中文环境，选择语言时请选择zh_CN，大概是323，3，注意输入密码，确定请回车"
sudo apt install locales -y
sudo dpkg-reconfigure locales
sudo apt install fonts-wqy-microhei fonts-wqy-zenhei xfonts-wqy
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
echo "在文件管理器添加常用路径书签..."
mkdir -p $HOME/.config/gtk-3.0
touch "$HOME/.config/gtk-3.0/bookmarks"
for newbookmarks in "file:///sdcard" "file:///home"
do
    if ! grep -q "$newbookmarks\$" "$HOME/.config/gtk-3.0/bookmarks"; then
        echo "$newbookmarks" >> "$HOME/.config/gtk-3.0/bookmarks"
    fi
done
mkdir $HOME/桌面/ 2>/dev/null
cp /usr/chromium.desktop $HOME/桌面/
rm /usr/chromium.desktop
EOF
chmod -R u+x $PREFIX/var/lib/proot-distro/installed-rootfs/debian/usr/bin/go
     
echo -e " .."
echo -e " .."
read -p "请在下面出现的绿色用户后输入 go 回车，注意语言选择，没有就选other，确定请回车"
proot-distro login debian --shared-tmp -- /bin/bash -c "su - afei"
