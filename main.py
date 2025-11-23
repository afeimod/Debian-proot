import sys
import subprocess
import os
import glob
import configparser
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenu, QAction, 
                            QFileDialog, QSlider, QLabel, QVBoxLayout, 
                            QHBoxLayout, QWidget, QGridLayout, QMessageBox,
                            QSizePolicy, QDialog, QPushButton)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QDesktopServices, QFont, QPainter, QPen

class DesktopIconWidget(QWidget):
    """桌面快捷方式图标 - 使用事件穿透实现完全透明"""
    def __init__(self, desktop_file, parent=None):
        super().__init__(parent)
        self.desktop_file = desktop_file
        self.name = ""
        self.icon_path = ""
        self.exec_cmd = ""
        self.working_dir = ""
        
        # 双击检测
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.single_click_timeout)
        self.click_count = 0
        
        self.parse_desktop_file()
        self.setup_ui()
        
    def parse_desktop_file(self):
        """解析.desktop文件"""
        try:
            config = configparser.ConfigParser(strict=False)
            config.read(self.desktop_file, encoding='utf-8')
            
            if 'Desktop Entry' in config:
                desktop_entry = config['Desktop Entry']
                self.name = desktop_entry.get('Name', '')
                self.icon_path = desktop_entry.get('Icon', '')
                self.exec_cmd = desktop_entry.get('Exec', '')
                self.working_dir = desktop_entry.get('Path', '')
                    
        except Exception as e:
            print(f"解析桌面文件错误: {e}")
            
    def setup_ui(self):
        """设置图标UI - 使用事件穿透实现完全透明"""
        self.setFixedSize(80, 100)
        
        # 关键修复：设置完全透明和事件穿透属性
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # 确保接收鼠标事件
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background: transparent; border: none;")
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)
        
        # 图标
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 图标标签不拦截事件
        
        # 设置图标
        pixmap = self.load_icon()
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            self.icon_label.setText("📄")
            self.icon_label.setStyleSheet("font-size: 24px; color: white; background: transparent; border: none;")
        
        # 应用名称
        self.name_label = QLabel(self.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumWidth(75)
        self.name_label.setStyleSheet("color: white; font-weight: bold; text-shadow: 1px 1px 3px black; background: transparent; border: none; padding: 0px;")
        self.name_label.setMaximumHeight(30)
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 名称标签不拦截事件
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        
        self.setToolTip(self.name)
        
        # 关键修复：添加快捷方式右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def load_icon(self):
        """加载图标"""
        if not self.icon_path:
            return None
            
        if os.path.exists(self.icon_path):
            return QPixmap(self.icon_path)
        
        icon_dirs = [
            "/usr/share/pixmaps",
            "/usr/share/icons/hicolor/48x48/apps",
            "/usr/share/icons/hicolor/64x64/apps",
            "/usr/share/icons/hicolor/128x128/apps",
            "/usr/share/icons/gnome/48x48/apps",
            "/usr/share/icons/gnome/64x64/apps",
            "/usr/share/icons/breeze/apps/48",
            "/usr/share/icons/breeze/apps/64",
            os.path.expanduser("~/.local/share/icons"),
            "/usr/share/app-install/icons",
        ]
        
        for icon_dir in icon_dirs:
            if os.path.exists(icon_dir):
                for ext in ["png", "svg", "xpm", "jpg", "jpeg"]:
                    icon_pattern = os.path.join(icon_dir, f"{self.icon_path}.{ext}")
                    matches = glob.glob(icon_pattern)
                    if matches:
                        pixmap = QPixmap(matches[0])
                        if not pixmap.isNull():
                            return pixmap
        
        try:
            theme_icon = QIcon.fromTheme(self.icon_path)
            if not theme_icon.isNull():
                pixmap = theme_icon.pixmap(64, 64)
                if not pixmap.isNull():
                    return pixmap
        except:
            pass
            
        return None
        
    def mousePressEvent(self, event):
        """鼠标点击事件 - 支持双击检测"""
        if event.button() == Qt.LeftButton:
            self.click_count += 1
            
            if self.click_count == 1:
                self.click_timer.start(250)
            elif self.click_count == 2:
                self.click_timer.stop()
                self.click_count = 0
                self.launch_application()
        
    def single_click_timeout(self):
        """单击超时处理"""
        self.click_count = 0
        
    def launch_application(self):
        """启动应用程序"""
        if self.exec_cmd:
            try:
                cmd = self.exec_cmd.split('%')[0].strip()
                cmd = cmd.replace('%u', '').replace('%U', '').replace('%f', '').replace('%F', '')
                cmd = cmd.strip()
                
                env = os.environ.copy()
                if self.working_dir and os.path.exists(self.working_dir):
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL, cwd=self.working_dir, env=env)
                else:
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL, env=env)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法启动程序: {e}")
    
    def show_context_menu(self, position):
        """显示快捷方式右键菜单"""
        menu = QMenu(self)
        
        # 打开应用程序
        open_action = menu.addAction("打开")
        open_action.triggered.connect(self.launch_application)
        
        # 打开文件位置
        location_action = menu.addAction("打开文件位置")
        location_action.triggered.connect(self.open_file_location)
        
        menu.addSeparator()
        
        # 属性
        properties_action = menu.addAction("属性")
        properties_action.triggered.connect(self.show_properties)
        
        menu.exec_(self.mapToGlobal(position))
        
    def open_file_location(self):
        """打开.desktop文件所在目录"""
        try:
            desktop_dir = os.path.dirname(self.desktop_file)
            subprocess.Popen(['xdg-open', desktop_dir])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件位置: {e}")
            
    def show_properties(self):
        """显示属性对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{self.name} - 属性")
            dialog.setFixedSize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            name_layout = QHBoxLayout()
            name_label = QLabel("名称:")
            name_value = QLabel(self.name)
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_value)
            
            path_layout = QHBoxLayout()
            path_label = QLabel("路径:")
            path_value = QLabel(self.desktop_file)
            path_layout.addWidget(path_label)
            path_layout.addWidget(path_value)
            
            cmd_layout = QHBoxLayout()
            cmd_label = QLabel("命令:")
            cmd_value = QLabel(self.exec_cmd)
            cmd_value.setWordWrap(True)
            cmd_layout.addWidget(cmd_label)
            cmd_layout.addWidget(cmd_value)
            
            dir_layout = QHBoxLayout()
            dir_label = QLabel("工作目录:")
            dir_value = QLabel(self.working_dir if self.working_dir else "未设置")
            dir_value.setWordWrap(True)
            dir_layout.addWidget(dir_label)
            dir_layout.addWidget(dir_value)
            
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            
            layout.addLayout(name_layout)
            layout.addLayout(path_layout)
            layout.addLayout(cmd_layout)
            layout.addLayout(dir_layout)
            layout.addWidget(close_button)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法显示属性: {e}")

    def set_icon_size(self, icon_size, text_size):
        """设置图标大小"""
        self.setFixedSize(icon_size + 20, icon_size + 40)
        self.icon_label.setFixedSize(icon_size, icon_size)
        
        pixmap = self.load_icon()
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(icon_size - 4, icon_size - 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(scaled_pixmap)
        
        self.name_label.setStyleSheet(f"color: white; font-weight: bold; font-size: {text_size}px; text-shadow: 1px 1px 3px black; background: transparent; border: none; padding: 0px;")
        self.name_label.setMaximumWidth(icon_size + 15)

class IconSizeDialog(QDialog):
    """图标大小设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("设置图标大小")
        self.setFixedSize(300, 200)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        icon_layout = QHBoxLayout()
        icon_label = QLabel("图标大小:")
        self.icon_slider = QSlider(Qt.Horizontal)
        self.icon_slider.setRange(32, 128)
        self.icon_slider.setValue(64)
        self.icon_value = QLabel("64px")
        
        icon_layout.addWidget(icon_label)
        icon_layout.addWidget(self.icon_slider)
        icon_layout.addWidget(self.icon_value)
        
        text_layout = QHBoxLayout()
        text_label = QLabel("文本大小:")
        self.text_slider = QSlider(Qt.Horizontal)
        self.text_slider.setRange(8, 16)
        self.text_slider.setValue(10)
        self.text_value = QLabel("10px")
        
        text_layout.addWidget(text_label)
        text_layout.addWidget(self.text_slider)
        text_layout.addWidget(self.text_value)
        
        button_layout = QHBoxLayout()
        apply_button = QPushButton("应用")
        cancel_button = QPushButton("取消")
        
        apply_button.clicked.connect(self.apply_changes)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        
        self.icon_slider.valueChanged.connect(lambda v: self.icon_value.setText(f"{v}px"))
        self.text_slider.valueChanged.connect(lambda v: self.text_value.setText(f"{v}px"))
        
        layout.addLayout(icon_layout)
        layout.addLayout(text_layout)
        layout.addLayout(button_layout)
        
    def apply_changes(self):
        """应用大小更改"""
        icon_size = self.icon_slider.value()
        text_size = self.text_slider.value()
        
        if self.parent:
            self.parent.set_icon_sizes(icon_size, text_size)
        
        self.accept()

class DynamicWallpaper(QMainWindow):
    def __init__(self):
        super().__init__()
        # 禁用 xfdesktop
        self.disable_xfdesktop()
        
        # 获取屏幕尺寸
        self.screen_rect = QApplication.primaryScreen().geometry()
        self.screen_width = self.screen_rect.width()
        self.screen_height = self.screen_rect.height()
        
        # 关键修复：设置正确的窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 关键修复：主窗口不拦截鼠标事件
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        
        # 当前背景类型
        self.current_background_type = "video"
        
        # 显示模式
        self.video_mode = "stretch"
        self.image_mode = "scale"
        
        # 图标排列方式
        self.icon_arrangement = "vertical"
        
        # 图标大小设置
        self.icon_size = 64
        self.text_size = 10
        
        # 静音状态
        self.muted = False
        
        # 存储桌面图标
        self.desktop_icons = []
        
        # 初始化UI组件
        self.setup_ui()
        
        # 延迟设置窗口为桌面背景
        QTimer.singleShot(100, self.set_desktop_window)
        
        # 关键修复：创建独立的图标容器窗口
        self.setup_icon_container()

    def setup_icon_container(self):
        """创建独立的图标容器窗口"""
        self.icon_container = QWidget()
        # 关键修复：移除WindowStaysOnTopHint，确保鼠标事件正常传递
        self.icon_container.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.icon_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # 确保接收鼠标事件
        self.icon_container.setGeometry(0, 0, self.screen_width, self.screen_height)
        self.icon_container.setStyleSheet("background: transparent;")
        
        # 关键修复：为图标容器添加右键菜单
        self.icon_container.setContextMenuPolicy(Qt.CustomContextMenu)
        self.icon_container.customContextMenuRequested.connect(self.show_context_menu)
        
        self.icon_container.show()

    def setup_ui(self):
        """设置UI组件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 视频播放组件
        self.setup_video_player()
        
        # 图片显示组件
        self.setup_image_display()
        
        # 初始化右键菜单
        self.setup_context_menu()
        
        # 加载桌面图标
        self.load_desktop_icons()

    def disable_xfdesktop(self):
        """临时禁用 xfdesktop"""
        try:
            subprocess.run(['pkill', 'xfdesktop'], timeout=5)
            print("已禁用 xfdesktop")
        except Exception as e:
            print(f"禁用 xfdesktop 时出错: {e}")

    def enable_xfdesktop(self):
        """重新启用 xfdesktop"""
        try:
            subprocess.Popen(['xfdesktop', '--reload'])
            print("已重新启用 xfdesktop")
        except Exception as e:
            print(f"启用 xfdesktop 时出错: {e}")
    
    def setup_video_player(self):
        """设置视频播放器 - 修复视频播放问题"""
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background: transparent;")
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 关键修复：确保视频控件填满屏幕
        self.video_widget.setMinimumSize(self.screen_width, self.screen_height)
        self.video_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 视频控件不拦截事件
        
        self.main_layout.addWidget(self.video_widget)
        
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        
        # 关键修复：添加错误处理和状态监控
        self.media_player.error.connect(self.handle_media_error)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)
        self.media_player.stateChanged.connect(self.handle_player_state)
        
        # 设置默认视频文件路径
        video_path = os.path.expanduser("~/1.mp4")
        if os.path.exists(video_path):
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.media_player.mediaStatusChanged.connect(self.loop_video)
        else:
            print(f"警告: 默认视频文件未找到在 {video_path}。")
            
        # 应用视频显示模式
        self.apply_video_mode()

    def handle_media_error(self, error):
        """处理媒体错误"""
        error_msg = self.media_player.errorString()
        print(f"媒体播放错误: {error} - {error_msg}")
        # 尝试重新加载媒体
        QTimer.singleShot(1000, self.recover_from_error)

    def handle_media_status(self, status):
        """处理媒体状态变化"""
        status_names = {
            QMediaPlayer.UnknownMediaStatus: "Unknown",
            QMediaPlayer.NoMedia: "NoMedia",
            QMediaPlayer.LoadingMedia: "Loading",
            QMediaPlayer.LoadedMedia: "Loaded",
            QMediaPlayer.StalledMedia: "Stalled",
            QMediaPlayer.BufferingMedia: "Buffering",
            QMediaPlayer.BufferedMedia: "Buffered",
            QMediaPlayer.EndOfMedia: "EndOfMedia",
            QMediaPlayer.InvalidMedia: "InvalidMedia"
        }
        print(f"媒体状态: {status_names.get(status, 'Unknown')}")

    def handle_player_state(self, state):
        """处理播放器状态变化"""
        state_names = {
            QMediaPlayer.StoppedState: "Stopped",
            QMediaPlayer.PlayingState: "Playing",
            QMediaPlayer.PausedState: "Paused"
        }
        print(f"播放器状态: {state_names.get(state, 'Unknown')}")

    def recover_from_error(self):
        """从错误中恢复"""
        print("尝试从媒体错误中恢复...")
        if hasattr(self, 'current_video_path') and self.current_video_path:
            self.set_video_background(self.current_video_path)
        else:
            video_path = os.path.expanduser("~/1.mp4")
            if os.path.exists(video_path):
                self.set_video_background(video_path)

    def setup_image_display(self):
        """设置图片显示"""
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(self.screen_width, self.screen_height)
        self.image_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 图片控件不拦截事件
        
        self.main_layout.addWidget(self.image_label)
        self.image_label.hide()

    def setup_context_menu(self):
        """设置右键菜单"""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        """显示桌面右键菜单"""
        menu = QMenu(self)
        
        # 背景选择菜单
        bg_menu = menu.addMenu("🖼️ 设置背景")
        
        video_action = bg_menu.addAction("🎬 选择视频")
        video_action.triggered.connect(self.select_video)
        
        image_action = bg_menu.addAction("🖼️ 选择图片")
        image_action.triggered.connect(self.select_image)
        
        menu.addSeparator()
        
        # 视频显示模式
        video_mode_menu = menu.addMenu("📺 视频显示模式")
        
        video_scale_action = video_mode_menu.addAction("🔍 缩放填充")
        video_scale_action.triggered.connect(lambda: self.set_video_mode("scale"))
        
        video_stretch_action = video_mode_menu.addAction("🔄 全屏拉伸")
        video_stretch_action.triggered.connect(lambda: self.set_video_mode("stretch"))
        
        video_fit_action = video_mode_menu.addAction("📐 适应屏幕")
        video_fit_action.triggered.connect(lambda: self.set_video_mode("fit"))
        
        # 图片显示模式
        image_mode_menu = menu.addMenu("🖼️ 图片显示模式")
        
        image_scale_action = image_mode_menu.addAction("🔍 缩放填充")
        image_scale_action.triggered.connect(lambda: self.set_image_mode("scale"))
        
        image_stretch_action = image_mode_menu.addAction("🔄 全屏拉伸")
        image_stretch_action.triggered.connect(lambda: self.set_image_mode("stretch"))
        
        image_tile_action = image_mode_menu.addAction("🧱 平铺")
        image_tile_action.triggered.connect(lambda: self.set_image_mode("tile"))
        
        image_center_action = image_mode_menu.addAction("🎯 居中")
        image_center_action.triggered.connect(lambda: self.set_image_mode("center"))
        
        image_fit_action = image_mode_menu.addAction("📐 适应")
        image_fit_action.triggered.connect(lambda: self.set_image_mode("fit"))
        
        menu.addSeparator()
        
        # 图标排列方式
        arrange_menu = menu.addMenu("📑 图标排列方式")
        
        grid_action = arrange_menu.addAction("🔲 网格排列")
        grid_action.triggered.connect(lambda: self.set_icon_arrangement("grid"))
        
        horizontal_action = arrange_menu.addAction("↔️ 水平排列")
        horizontal_action.triggered.connect(lambda: self.set_icon_arrangement("horizontal"))
        
        vertical_action = arrange_menu.addAction("↕️ 垂直排列")
        vertical_action.triggered.connect(lambda: self.set_icon_arrangement("vertical"))
        
        free_action = arrange_menu.addAction("🎯 自由排列")
        free_action.triggered.connect(lambda: self.set_icon_arrangement("free"))
        
        menu.addSeparator()
        
        # 图标大小设置
        icon_size_action = menu.addAction("📏 设置图标大小")
        icon_size_action.triggered.connect(self.set_icon_size)
        
        menu.addSeparator()
        
        # 视频控制
        video_menu = menu.addMenu("🎵 视频控制")
        
        # 静音/取消静音
        mute_text = "🔇 取消静音" if self.muted else "🔊 静音"
        mute_action = video_menu.addAction(mute_text)
        mute_action.triggered.connect(self.toggle_mute)
        
        # 音量控制
        volume_action = video_menu.addAction("🎚️ 设置音量")
        volume_action.triggered.connect(self.set_volume)
        
        # 重新加载视频
        reload_action = video_menu.addAction("🔄 重新加载视频")
        reload_action.triggered.connect(self.reload_video)
        
        menu.addSeparator()
        
        # 透明度设置
        transparency_action = menu.addAction("🌫️ 设置透明度")
        transparency_action.triggered.connect(self.set_transparency)
        
        menu.addSeparator()
        
        # 刷新桌面图标
        refresh_action = menu.addAction("🔄 刷新桌面图标")
        refresh_action.triggered.connect(self.refresh_desktop_icons)
        
        menu.addSeparator()
        
        # 退出
        exit_action = menu.addAction("❌ 退出")
        exit_action.triggered.connect(self.close_application)
        
        menu.exec_(self.mapToGlobal(position))

    def reload_video(self):
        """重新加载当前视频"""
        if hasattr(self, 'current_video_path') and self.current_video_path:
            self.set_video_background(self.current_video_path)

    def toggle_mute(self):
        """切换静音状态"""
        self.muted = not self.muted
        self.media_player.setMuted(self.muted)
        print(f"视频已{'静音' if self.muted else '取消静音'}")

    def set_volume(self):
        """设置音量"""
        dialog = QWidget(self, Qt.Window)
        dialog.setWindowTitle("设置音量")
        dialog.setFixedSize(300, 100)
        dialog.setStyleSheet("background: white; padding: 10px;")
        
        layout = QVBoxLayout(dialog)
        
        slider_layout = QHBoxLayout()
        slider_label = QLabel("音量:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.media_player.volume())
        self.volume_slider.valueChanged.connect(self.update_volume)
        
        self.volume_value = QLabel(f"{self.media_player.volume()}%")
        
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.volume_slider)
        slider_layout.addWidget(self.volume_value)
        
        layout.addLayout(slider_layout)
        
        dialog.move(self.geometry().center() - dialog.rect().center())
        dialog.show()

    def update_volume(self, value):
        """更新音量"""
        self.media_player.setVolume(value)
        self.volume_value.setText(f"{value}%")

    def select_video(self):
        """选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", 
            os.path.expanduser("~"),
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv)"
        )
        
        if file_path:
            self.set_video_background(file_path)

    def select_image(self):
        """选择图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片文件", 
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.set_image_background(file_path)

    def set_video_background(self, video_path):
        """设置视频背景"""
        try:
            self.current_background_type = "video"
            self.current_video_path = video_path  # 保存当前视频路径
            
            # 关键修复：先停止当前播放
            self.media_player.stop()
            
            # 设置新的媒体内容
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.image_label.hide()
            self.video_widget.show()
            
            # 关键修复：重新应用视频模式
            self.apply_video_mode()
            
            self.hide_original_desktop()
            self.raise_icons()
            
            # 延迟播放以确保设置生效
            QTimer.singleShot(100, self.play)
            
        except Exception as e:
            print(f"设置视频背景错误: {e}")
            QMessageBox.warning(self, "错误", f"无法设置视频背景: {e}")

    def set_image_background(self, image_path):
        """设置图片背景"""
        self.current_background_type = "image"
        self.media_player.pause()
        
        self.current_image_path = image_path
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap)
            self.video_widget.hide()
            self.image_label.show()
            
            self.apply_image_mode()
            self.hide_original_desktop()
            self.raise_icons()

    def set_video_mode(self, mode):
        """设置视频显示模式"""
        self.video_mode = mode
        
        if self.current_background_type == "video":
            self.apply_video_mode()
            
        self.refresh_desktop_icons()

    def set_image_mode(self, mode):
        """设置图片显示模式"""
        self.image_mode = mode
        
        if self.current_background_type == "image":
            self.apply_image_mode()
            
        self.refresh_desktop_icons()

    def apply_video_mode(self):
        """应用视频显示模式 - 修复全屏拉伸问题"""
        try:
            # 关键修复：使用正确的视频拉伸方法
            if self.video_mode == "scale":
                self.video_widget.setAspectRatioMode(Qt.KeepAspectRatioByExpanding)
            elif self.video_mode == "stretch":
                self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)
            elif self.video_mode == "fit":
                self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
            
            # 强制重新绘制和调整大小
            self.video_widget.resize(self.screen_width, self.screen_height)
            self.video_widget.update()
            
            print(f"视频模式已设置为: {self.video_mode}")
            
        except Exception as e:
            print(f"应用视频模式错误: {e}")

    def apply_image_mode(self):
        """应用图片显示模式"""
        if self.current_background_type == "image" and hasattr(self, 'current_image_path'):
            pixmap = QPixmap(self.current_image_path)
            if pixmap.isNull():
                return
            
            screen_width = self.screen_width
            screen_height = self.screen_height
            
            if self.image_mode == "scale":
                scaled_pixmap = pixmap.scaled(screen_width, screen_height, 
                                            Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                
            elif self.image_mode == "stretch":
                scaled_pixmap = pixmap.scaled(screen_width, screen_height, 
                                            Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                
            elif self.image_mode == "tile":
                tile_pixmap = QPixmap(screen_width, screen_height)
                tile_pixmap.fill(Qt.transparent)
                
                painter = QPainter(tile_pixmap)
                for x in range(0, screen_width, pixmap.width()):
                    for y in range(0, screen_height, pixmap.height()):
                        painter.drawPixmap(x, y, pixmap)
                painter.end()
                
                self.image_label.setPixmap(tile_pixmap)
                
            elif self.image_mode == "center":
                self.image_label.setAlignment(Qt.AlignCenter)
                self.image_label.setPixmap(pixmap)
                
            elif self.image_mode == "fit":
                scaled_pixmap = pixmap.scaled(screen_width, screen_height, 
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setAlignment(Qt.AlignCenter)

    def set_icon_arrangement(self, arrangement):
        """设置图标排列方式"""
        self.icon_arrangement = arrangement
        self.arrange_desktop_icons()
        self.refresh_desktop_icons()

    def arrange_desktop_icons(self):
        """排列桌面图标"""
        if not self.desktop_icons:
            return
            
        icon_width = self.icon_size + 20
        icon_height = self.icon_size + 40
        margin = 20
        
        if self.icon_arrangement == "grid":
            max_cols = max(1, (self.screen_width - margin * 2) // icon_width)
            for i, icon in enumerate(self.desktop_icons):
                row = i // max_cols
                col = i % max_cols
                x = margin + col * icon_width
                y = margin + row * icon_height
                icon.move(x, y)
                
        elif self.icon_arrangement == "horizontal":
            for i, icon in enumerate(self.desktop_icons):
                x = margin + i * icon_width
                y = margin
                if x + icon_width > self.screen_width - margin:
                    x = margin
                    y += icon_height
                icon.move(x, y)
                
        elif self.icon_arrangement == "vertical":
            for i, icon in enumerate(self.desktop_icons):
                x = margin
                y = margin + i * icon_height
                if y + icon_height > self.screen_height - margin:
                    x += icon_width
                    y = margin
                icon.move(x, y)
                
        elif self.icon_arrangement == "free":
            for icon in self.desktop_icons:
                max_x = self.screen_width - icon_width - margin
                max_y = self.screen_height - icon_height - margin
                x = random.randint(margin, max(margin, max_x))
                y = random.randint(margin, max(margin, max_y))
                icon.move(x, y)

    def hide_original_desktop(self):
        """彻底隐藏原桌面"""
        try:
            subprocess.run([
                'gsettings', 'set', 'org.gnome.desktop.background', 
                'show-desktop-icons', 'false'
            ], timeout=5, capture_output=True)
            
            subprocess.run([
                'gsettings', 'set', 'org.gnome.desktop.background', 
                'picture-uri', '""'
            ], timeout=5, capture_output=True)
            
            result = subprocess.run([
                'xfconf-query', '-c', 'xfce4-desktop', '-p', 
                '/backdrop/screen0/monitor0/image-path'
            ], timeout=5, capture_output=True)
            
            if result.returncode == 0:
                subprocess.run([
                    'xfconf-query', '-c', 'xfce4-desktop', '-p', 
                    '/backdrop/screen0/monitor0/image-path', '-s', '""'
                ], timeout=5, capture_output=True)
            
            subprocess.run([
                'gsettings', 'set', 'org.gnome.desktop.background', 
                'primary-color', '#000000'
            ], timeout=5, capture_output=True)
            
            try:
                subprocess.run([
                    'gsettings', 'set', 'org.gnome.desktop.background', 
                    'draw-background', 'false'
                ], timeout=5, capture_output=True)
            except:
                pass
                
        except Exception as e:
            print(f"隐藏原桌面时出错: {e}")

    def set_transparency(self):
        """设置透明度"""
        dialog = QWidget(self, Qt.Window)
        dialog.setWindowTitle("设置透明度")
        dialog.setFixedSize(300, 100)
        dialog.setStyleSheet("background: white; padding: 10px;")
        
        layout = QVBoxLayout(dialog)
        
        slider_layout = QHBoxLayout()
        slider_label = QLabel("透明度:")
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setRange(10, 100)
        self.transparency_slider.setValue(int(self.windowOpacity() * 100))
        self.transparency_slider.valueChanged.connect(self.update_transparency)
        
        self.transparency_value = QLabel(f"{self.transparency_slider.value()}%")
        
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.transparency_slider)
        slider_layout.addWidget(self.transparency_value)
        
        layout.addLayout(slider_layout)
        
        dialog.move(self.geometry().center() - dialog.rect().center())
        dialog.show()

    def update_transparency(self, value):
        """更新透明度"""
        opacity = value / 100.0
        self.setWindowOpacity(opacity)
        self.transparency_value.setText(f"{value}%")

    def set_icon_size(self):
        """设置图标大小"""
        dialog = IconSizeDialog(self)
        dialog.exec_()

    def set_icon_sizes(self, icon_size, text_size):
        """应用图标大小设置"""
        self.icon_size = icon_size
        self.text_size = text_size
        
        for icon in self.desktop_icons:
            icon.set_icon_size(icon_size, text_size)
        
        self.arrange_desktop_icons()
        self.refresh_desktop_icons()

    def load_desktop_icons(self):
        """加载桌面图标"""
        # 清除现有的图标
        for icon in self.desktop_icons:
            icon.setParent(None)
            icon.deleteLater()
        self.desktop_icons.clear()
        
        desktop_dirs = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/桌面"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "桌面")
        ]
        
        desktop_dir = None
        for dir_path in desktop_dirs:
            if os.path.exists(dir_path):
                desktop_dir = dir_path
                break
        
        if not desktop_dir:
            print("未找到桌面目录")
            return
        
        desktop_files = glob.glob(os.path.join(desktop_dir, "*.desktop"))
        
        # 关键修复：将图标添加到独立的容器窗口
        for desktop_file in desktop_files:
            try:
                icon_widget = DesktopIconWidget(desktop_file, self.icon_container)
                icon_widget.set_icon_size(self.icon_size, self.text_size)
                icon_widget.show()
                
                self.desktop_icons.append(icon_widget)
                    
            except Exception as e:
                print(f"加载桌面图标失败 {desktop_file}: {e}")
        
        self.arrange_desktop_icons()
        self.raise_icons()

    def raise_icons(self):
        """确保图标在最前面"""
        for icon in self.desktop_icons:
            icon.raise_()
            icon.show()

    def refresh_desktop_icons(self):
        """刷新桌面图标"""
        self.load_desktop_icons()

    def loop_video(self, status):
        """视频循环播放 - 修复循环播放问题"""
        if status == QMediaPlayer.EndOfMedia:
            print("视频播放结束，重新播放")
            # 关键修复：使用单次定时器延迟重新播放
            QTimer.singleShot(100, lambda: self.media_player.play())
        elif status == QMediaPlayer.LoadedMedia:
            print("视频加载完成")
            # 确保视频模式正确应用
            self.apply_video_mode()
        elif status == QMediaPlayer.InvalidMedia:
            print("无效的媒体文件")
            self.recover_from_error()

    def set_desktop_window(self):
        """使用多种方法确保窗口位于最底层并替代原桌面"""
        try:
            win_id = self.winId()
            
            result1 = subprocess.run([
                'xprop', '-id', str(int(win_id)),
                '-f', '_NET_WM_WINDOW_TYPE', '32a',
                '-set', '_NET_WM_WINDOW_TYPE', '_NET_WM_WINDOW_TYPE_DESKTOP'
            ], capture_output=True, text=True, timeout=10)
            
            result2 = subprocess.run([
                'xprop', '-id', str(int(win_id)),
                '-f', '_NET_WM_STATE', '32a',
                '-set', '_NET_WM_STATE', '_NET_WM_STATE_BELOW'
            ], capture_output=True, text=True, timeout=10)
            
            try:
                result3 = subprocess.run([
                    'wmctrl', '-i', '-r', str(int(win_id)), '-b', 'add,below'
                ], capture_output=True, text=True, timeout=10)
                print("使用wmctrl设置窗口为底层")
            except:
                print("wmctrl不可用，跳过此方法")
            
            try:
                result4 = subprocess.run([
                    'xdotool', 'windowlower', str(int(win_id))
                ], capture_output=True, text=True, timeout=10)
                print("使用xdotool将窗口置于底层")
            except:
                print("xdotool不可用，跳过此方法")
            
            result5 = subprocess.run([
                'xprop', '-id', str(int(win_id)),
                '-set', '_NET_WM_DESKTOP', '0xFFFFFFFF'
            ], capture_output=True, text=True, timeout=10)
            
            try:
                result6 = subprocess.run([
                    'xprop', '-id', str(int(win_id)),
                    '-set', '_NET_WM_STATE', '_NET_WM_STATE_STICKY'
                ], capture_output=True, text=True, timeout=10)
            except:
                pass
            
            if result1.returncode == 0 or result2.returncode == 0:
                print("成功将窗口设置为桌面背景层。")
            else:
                print(f"xprop 执行出错: {result1.stderr} {result2.stderr}")
                
            QTimer.singleShot(500, self.ensure_lowest_layer)
            
        except subprocess.TimeoutExpired:
            print("错误: 设置桌面窗口属性的命令超时。")
        except Exception as e:
            print(f"设置桌面窗口时发生未知错误: {e}")
    
    def ensure_lowest_layer(self):
        """确保窗口位于最底层"""
        try:
            win_id = self.winId()
            
            try:
                subprocess.run([
                    'xdotool', 'windowlower', str(int(win_id))
                ], capture_output=True, text=True, timeout=10)
            except:
                pass
                
            self.hide_original_desktop()
            QTimer.singleShot(1000, self.final_layer_check)
            
        except Exception as e:
            print(f"确保底层时出错: {e}")
    
    def final_layer_check(self):
        """最终层级检查"""
        try:
            win_id = self.winId()
            
            subprocess.run([
                'xprop', '-id', str(int(win_id)),
                '-f', '_NET_WM_STATE', '32a',
                '-set', '_NET_WM_STATE', '_NET_WM_STATE_BELOW'
            ], capture_output=True, text=True, timeout=10)
            
            print("桌面窗口层级设置完成")
            self.hide_original_desktop()
            self.refresh_desktop_icons()
            
        except Exception as e:
            print(f"最终层级检查时出错: {e}")

    def play(self):
        """开始播放视频 - 修复播放稳定性"""
        try:
            if self.media_player.isAvailable() and self.current_background_type == "video":
                # 关键修复：确保视频模式正确应用后再播放
                self.apply_video_mode()
                QTimer.singleShot(200, lambda: self.media_player.play())
                print("开始播放视频")
        except Exception as e:
            print(f"播放视频错误: {e}")
            # 尝试恢复播放
            QTimer.singleShot(1000, self.recover_from_error)

    def close_application(self):
        """关闭应用程序 - 修复资源释放问题"""
        try:
            # 关键修复：正确停止和释放媒体播放器
            if hasattr(self, 'media_player'):
                self.media_player.stop()
                self.media_player.setMedia(QMediaContent())  # 清空媒体
            
            # 释放图标资源
            for icon in self.desktop_icons:
                icon.setParent(None)
                icon.deleteLater()
            self.desktop_icons.clear()
            
            # 重新启用原桌面
            self.enable_xfdesktop()
            
        except Exception as e:
            print(f"关闭应用程序时出错: {e}")
        finally:
            QApplication.quit()

def main():
    app = QApplication(sys.argv)
    
    player = QMediaPlayer()
    if not player.isAvailable():
        print("警告: 没有可用的多媒体服务。动态壁纸可能无法正常播放。")
        print("请确保已安装 gstreamer1.0-plugins-base、gstreamer1.0-plugins-good 和 gstreamer1.0-plugins-bad。")
    
    wallpaper = DynamicWallpaper()
    wallpaper.show()
    
    # 关键修复：延迟播放确保窗口设置完成
    QTimer.singleShot(1000, wallpaper.play)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()