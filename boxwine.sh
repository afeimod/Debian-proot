#!/bin/bash
#作者：段小洋（QQ：1745789127）
#时间：2024年4月26日
#描述：帮助小白朋友们快速在容器里面配置box86/box64和wine这三种组件实现运行windows程序。

set -euo pipefail
shopt -s failglob

function tips() {
    printf "\e[97m$@\n\e[0m"
    return 0
}
function err() {
    printf "\e[91m$@\n\e[0m"
    exit 1
}

function detect_chroot_00() {
  if [ -d /proc/1/root ]; then
    INITROOTINODE=$(stat -c %i /proc/1/root)
    PROOTROOTINODE=$(stat -c %i /proc/$PPID/root)
    if [ $INITROOTINODE -ne $PROOTROOTINODE ]; then
      return 0
    else
      return 1
    fi
  else
    return 0
  fi
}
function detect_chroot_01() {
  PSNAME=`grep "Name:" /proc/$PPID/status|cut -d: -f2|sed 's/^[[:space:]]*\t*//g'`
  if [ "$PSNAME" == "proot" ];then
    :
  else
    detect_chroot_00 || err "你应该在容器里面运行此脚本！"
  fi
}

function is_root_and_check_distro() {
  if [ `id -u` -ne 0 ];then
    err "运行此脚本需要root权限！"
  fi
  if ! command -v apt;then
    err "当前系统中没有找到apt！本脚本目前只支持debian系发行版本。"
  fi
}

function check_dependences() {
  DEPLIST=("curl" "wget" "gnupg" "tar" "xz-utils")
  tips "正在更新系统软件索引中..."
  apt update || err "这一步失败了！"
  tips "正在安装所需的依赖软件包..."
  for pkgname in ${DEPLIST[@]};do
    apt install -y $pkgname || err "某一个软件包安装失败了！"
  done
}

function install_box_from_android() {
    # Check if the file already exists
    if [ ! -f "/usr/lib/i386-linux-gnu/libstdc++.so.6" ]; then
        #Install box86
        tips "正在安装box86..."
        {
            wget https://ryanfortner.github.io/box86-debs/box86.list -O /etc/apt/sources.list.d/box86.list
            wget -qO- https://ryanfortner.github.io/box86-debs/KEY.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/box86-debs-archive-keyring.gpg
            dpkg --add-architecture armhf
            apt-get update -y
            apt-get install box86-android:armhf -y
        } || err "无法安装box86！"
        #Install box64
        tips "正在安装box64..."
        {
            wget https://ryanfortner.github.io/box64-debs/box64.list -O /etc/apt/sources.list.d/box64.list
            wget -qO- https://ryanfortner.github.io/box64-debs/KEY.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/box64-debs-archive-keyring.gpg
            apt update -y && apt install box64-android -y
        } || err "无法安装box64！"
    else
        tips "文件 /usr/lib/i386-linux-gnu/libstdc++.so.6 已存在，跳过安装 box86-android 软件包。"
    fi
}

function check_additional_dependences() {
  DEPLIST=("nano" "cabextract" "libfreetype6" "libfreetype6:armhf" "libfontconfig" "libfontconfig:armhf" "libxext6" "libxext6:armhf" "libxinerama-dev" "libxinerama-dev:armhf" "libxxf86vm1" "libxxf86vm1:armhf" "libxrender1" "libxrender1:armhf" "libxcomposite1" "libxcomposite1:armhf" "libxrandr2" "libxrandr2:armhf" "libxi6" "libxi6:armhf" "libxcursor1" "libxcursor1:armhf" "libvulkan-dev" "libvulkan-dev:armhf" "zenity")
  tips "正在更新系统软件索引中..."
  apt update || err "这一步失败了！"
  tips "正在安装额外的依赖软件包..."
  for pkgname in ${DEPLIST[@]};do
    apt install -y $pkgname || err "安装软件包 $pkgname 失败！"
  done
}

function parse_argument() {
	POS_ARGS=$(getopt -n "${0}" -l "wine:,help::" -o "wv:,h::" -- "$@")
	eval set -- "$POS_ARGS"
	while true; do
		case "$1" in
			--wine|-wv)
				if ! [ -z $2 ];then
					WINEVER="$2"
				else
					err "你必须指定一个版本！"
				fi
				shift 2
				break
				;;
			--help|-h) 
				tips "Usage: $0 [options] ..."
				tips "可用选项如下："
				tips "\t-h/--help 显示帮助信息"
				tips "\t-wv/--wine 指定要安装的wine版本"
				exit 1
				;;
			""|--) 
				WINEVER="9.9"
				tips "默认安装wine9.9，是否继续？[y/n]"
				read -n1 opt
				case "$opt" in
					[yY]) ;;
					[nN])
						$0 --help
						exit 1
						;;
					*)
						$0 --help
						exit 1
						;;
				esac
				;;
			*)
				err "未知参数"
				$0 --help
				;;
		esac
	done
	return
}
function install_wine() {
    tips "正在安装传统wine $WINEVER staging（需要cpu支持32位指令集）..."
    {
        cd /tmp/
        wget https://github.com/Kron4ek/Wine-Builds/releases/download/$WINEVER/wine-$WINEVER-staging-amd64.tar.xz
        tar -Jpxf wine-$WINEVER-staging-amd64.tar.xz -C /opt/
        tips "正在设置环境变量..."
      cat >> /etc/profile <<EOF
export BOX86_PATH=/opt/wine-$WINEVER-staging-amd64/bin
export BOX86_LD_LIBRARY_PATH=/opt/wine-$WINEVER-staging-amd64/lib/wine/i386-unix
export BOX64_PATH=/opt/wine-$WINEVER-staging-amd64/bin
export BOX64_LD_LIBRARY_PATH=/opt/wine-$WINEVER-staging-amd64/lib/wine/x86_64-unix
EOF
        source /etc/profile
    } || err "无法安装wine！"
}

function show_versions() {
    tips "--box86和box64的版本信息--"
    box86 --version
    box64 --version
    tips "-------------------------------"
    tips ""
    tips "--wine版本信息--"
    box64 wine64 --version
    tips "--------------------"
}
function boot_wine() {
    tips "正在创建wine容器，这需要一点时间..."
    WINEDLLOVERRIDES="mscoree,mshtml=disabled" box64 wine64 wineboot || { err "无法创建wine容器" ; rm -rf ~/.wine ;}
}

function guide_to_start() {
    tips "注意：以下所有操作都需要在桌面上运行！"
    tips "box64 wine64 taskmgr 启动任务管理器"
    tips "box64 wine64 explorer 启动资源管理器"
    tips "box64 wine64 uninstaller 启动软件管理器"
    tips "box64 wine64 <cmdline> 运行指定的命令行"
}
function final_words() {
  tips "尽情享受boxwine吧!"
  tips "感谢使用此脚本，祝你生活愉快!"
}

function main() {
    detect_chroot_01
    parse_argument "$@"
    is_root_and_check_distro
    check_dependences
    check_additional_dependences  # 调用新的函数
    install_box_from_android
    install_wine
    show_versions
    boot_wine
    guide_to_start
    final_words
    exit 0
}
main "$@"
