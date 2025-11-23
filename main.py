import sys
import subprocess
import os
import glob
import configparser
import random
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenu, QAction, 
                            QFileDialog, QSlider, QLabel, QVBoxLayout, 
                            QHBoxLayout, QWidget, QGridLayout, QMessageBox,
                            QSizePolicy, QDialog, QPushButton, QInputDialog,
                            QLineEdit, QSystemTrayIcon)
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize, QPoint, QRect, pyqtSignal, QSettings
from PyQt5.QtGui import QPixmap, QIcon, QDesktopServices, QFont, QPainter, QPen, QImage

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
        self.setFixedSize(100, 280)
        
        # 关键修复：设置正确的窗口属性
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QWidget {
                background: transparent; 
                border: none;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignCenter)
        
        # 图标
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(75, 75)
        self.icon_label.setStyleSheet("""
            QLabel {
                background: transparent; 
                border: none;
                border-radius: 8px;
            }
            QLabel:hover {
                background: rgba(255, 255, 255, 30);
            }
        """)
        
        # 设置图标
        pixmap = self.load_icon()
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            self.icon_label.setText("📄")
            self.icon_label.setStyleSheet("""
                QLabel {
                    font-size: 24px; 
                    color: white; 
                    background: transparent; 
                    border: none;
                    border-radius: 15px;
                }
                QLabel:hover {
                    background: rgba(255, 255, 255, 30);
                }
            """)
        
        # 应用名称
        self.name_label = QLabel(self.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumWidth(80)
        self.name_label.setStyleSheet("""
            QLabel {
                color: white; 
                font-weight: bold; 
                font-size: 12px;
                text-shadow: 1px 1px 3px black; 
                background: transparent; 
                border: none; 
                padding: 2px;
                border-radius: 4px;
            }
            QLabel:hover {
                background: rgba(0, 0, 0, 80);
            }
        """)
        self.name_label.setMaximumHeight(55)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        
        self.setToolTip(f"<b>{self.name}</b><br/>双击打开应用程序")
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def load_icon(self):
        """加载图标 - 优化性能"""
        if not self.icon_path:
            return None
            
        # 直接路径检查
        if os.path.exists(self.icon_path):
            return QPixmap(self.icon_path)
        
        # 优化的图标目录搜索
        icon_dirs = [
            "/usr/share/pixmaps",
            "/usr/share/icons/hicolor/48x48/apps",
            "/usr/share/icons/hicolor/scalable/apps",  # 添加 scalable 目录
            "/usr/share/icons/gnome/scalable/apps",
            os.path.expanduser("~/.local/share/icons"),
        ]
        
        # 先尝试主题图标（最快）
        try:
            theme_icon = QIcon.fromTheme(self.icon_path)
            if not theme_icon.isNull():
                pixmap = theme_icon.pixmap(64, 64)
                if not pixmap.isNull():
                    return pixmap
        except:
            pass
            
        # 然后搜索文件系统
        icon_extensions = ["png", "svg", "xpm"]
        for icon_dir in icon_dirs:
            if not os.path.exists(icon_dir):
                continue
                
            for ext in icon_extensions:
                icon_pattern = os.path.join(icon_dir, f"{self.icon_path}.{ext}")
                if os.path.exists(icon_pattern):
                    pixmap = QPixmap(icon_pattern)
                    if not pixmap.isNull():
                        return pixmap
        
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
        
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(40, 40, 40, 220);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                color: white;
                padding: 8px 20px 8px 20px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 50);
            }
            QMenu::item:pressed {
                background-color: rgba(255, 255, 255, 80);
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 50);
                margin: 5px 10px 5px 10px;
            }
        """)
        
        open_action = menu.addAction("📂 打开")
        open_action.triggered.connect(self.launch_application)
        
        location_action = menu.addAction("📁 打开文件位置")
        location_action.triggered.connect(self.open_file_location)
        
        menu.addSeparator()
        
        rename_action = menu.addAction("📝 重命名")
        rename_action.triggered.connect(self.rename_shortcut)
        
        copy_action = menu.addAction("📋 复制")
        copy_action.triggered.connect(self.copy_shortcut)
        
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(self.delete_shortcut)
        
        menu.addSeparator()
        
        properties_action = menu.addAction("⚙️ 属性")
        properties_action.triggered.connect(self.show_properties)
        
        menu.exec_(self.mapToGlobal(position))
        
    def open_file_location(self):
        """打开.desktop文件所在目录"""
        try:
            desktop_dir = os.path.dirname(self.desktop_file)
            subprocess.Popen(['xdg-open', desktop_dir])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件位置: {e}")
            
    def rename_shortcut(self):
        """重命名快捷方式"""
        try:
            # 创建自定义输入对话框，确保文本颜色可见
            dialog = QInputDialog(self)
            dialog.setWindowTitle("重命名")
            dialog.setLabelText("输入新的名称:")
            dialog.setTextValue(self.name)
            dialog.setStyleSheet("""
                QInputDialog {
                    background-color: rgba(50, 50, 50, 240);
                    border: 2px solid rgba(255, 255, 255, 80);
                    border-radius: 12px;
                    color: white;
                }
                QLabel {
                    color: white;
                    background: transparent;
                }
                QLineEdit {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 220);
                }
                QPushButton:pressed {
                    background-color: rgba(110, 110, 110, 240);
                }
            """)
            
            if dialog.exec_() == QDialog.Accepted:
                new_name = dialog.textValue()
                if new_name and new_name != self.name:
                    # 读取并修改.desktop文件
                    config = configparser.ConfigParser(strict=False)
                    config.read(self.desktop_file, encoding='utf-8')
                    
                    if 'Desktop Entry' in config:
                        config['Desktop Entry']['Name'] = new_name
                        
                        with open(self.desktop_file, 'w', encoding='utf-8') as f:
                            config.write(f)
                        
                        self.name = new_name
                        self.name_label.setText(new_name)
                        self.setToolTip(f"<b>{self.name}</b><br/>双击打开应用程序")
                    
        except Exception as e:
            QMessageBox.warning(self, "错误", f"重命名失败: {e}")
            
    def copy_shortcut(self):
        """复制快捷方式"""
        try:
            desktop_dir = os.path.dirname(self.desktop_file)
            base_name = os.path.basename(self.desktop_file)
            name, ext = os.path.splitext(base_name)
            
            # 生成新文件名
            counter = 1
            new_name = f"{name} - 副本{ext}"
            new_path = os.path.join(desktop_dir, new_name)
            
            while os.path.exists(new_path):
                counter += 1
                new_name = f"{name} - 副本{counter}{ext}"
                new_path = os.path.join(desktop_dir, new_name)
            
            # 复制文件
            import shutil
            shutil.copy2(self.desktop_file, new_path)
            
            # 刷新父窗口的图标
            if self.parent():
                self.parent().refresh_desktop_icons()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"复制失败: {e}")
            
    def delete_shortcut(self):
        """删除快捷方式"""
        try:
            reply = QMessageBox.question(self, "确认删除", 
                                       f"确定要删除 '{self.name}' 吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                os.remove(self.desktop_file)
                # 从父窗口移除并删除自己
                if self.parent():
                    self.parent().remove_icon(self)
                self.deleteLater()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除失败: {e}")
            
    def show_properties(self):
        """显示属性对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{self.name} - 属性")
            dialog.setFixedSize(450, 350)
            
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgba(50, 50, 50, 240);
                    border: 2px solid rgba(255, 255, 255, 80);
                    border-radius: 12px;
                    color: white;
                }
                QLabel {
                    color: white;
                    background: transparent;
                    padding: 5px;
                }
                QPushButton {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 220);
                }
                QPushButton:pressed {
                    background-color: rgba(110, 110, 110, 240);
                }
            """)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(0)
            layout.setContentsMargins(10, 10, 10, 10)
            
            title_label = QLabel(f"<h2>{self.name}</h2>")
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)
            
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setSpacing(8)
            
            name_layout = QHBoxLayout()
            name_label = QLabel("<b>名称:</b>")
            name_value = QLabel(self.name)
            name_value.setStyleSheet("color: #a0d2ff;")
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_value)
            name_layout.addStretch()
            
            path_layout = QHBoxLayout()
            path_label = QLabel("<b>路径:</b>")
            path_value = QLabel(self.desktop_file)
            path_value.setWordWrap(True)
            path_value.setStyleSheet("color: #a0d2ff; font-size: 9px;")
            path_layout.addWidget(path_label)
            path_layout.addWidget(path_value)
            path_layout.addStretch()
            
            cmd_layout = QHBoxLayout()
            cmd_label = QLabel("<b>命令:</b>")
            cmd_value = QLabel(self.exec_cmd)
            cmd_value.setWordWrap(True)
            cmd_value.setStyleSheet("color: #a0d2ff; font-family: monospace; font-size: 9px;")
            cmd_layout.addWidget(cmd_label)
            cmd_layout.addWidget(cmd_value)
            cmd_layout.addStretch()
            
            dir_layout = QHBoxLayout()
            dir_label = QLabel("<b>工作目录:</b>")
            dir_value = QLabel(self.working_dir if self.working_dir else "未设置")
            dir_value.setWordWrap(True)
            dir_value.setStyleSheet("color: #a0d2ff; font-size: 9px;")
            dir_layout.addWidget(dir_label)
            dir_layout.addWidget(dir_value)
            dir_layout.addStretch()
            
            info_layout.addLayout(name_layout)
            info_layout.addLayout(path_layout)
            info_layout.addLayout(cmd_layout)
            info_layout.addLayout(dir_layout)
            
            layout.addWidget(info_widget)
            layout.addStretch()
            
            button_layout = QHBoxLayout()
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            close_button.setFixedSize(100, 35)
            
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            button_layout.addStretch()
            
            layout.addLayout(button_layout)
            
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
        
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: white; 
                font-weight: bold; 
                font-size: {text_size}px; 
                text-shadow: 1px 1px 3px black; 
                background: transparent; 
                border: none; 
                padding: 2px;
                border-radius: 4px;
            }}
            QLabel:hover {{
                background: rgba(0, 0, 0, 80);
            }}
        """)
        self.name_label.setMaximumWidth(icon_size + 15)

class IconSizeDialog(QDialog):
    """图标大小设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # 保存对主窗口的引用
        self.setWindowTitle("设置图标大小")
        self.setFixedSize(350, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(50, 50, 50, 240);
                border: 2px solid rgba(255, 255, 255, 80);
                border-radius: 12px;
                color: white;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QPushButton {
                background-color: rgba(70, 70, 70, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(90, 90, 90, 220);
            }
            QPushButton:pressed {
                background-color: rgba(110, 110, 110, 240);
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        icon_layout = QHBoxLayout()
        icon_label = QLabel("图标大小:")
        icon_label.setFixedWidth(80)
        self.icon_slider = QSlider(Qt.Horizontal)
        self.icon_slider.setRange(32, 128)
        self.icon_slider.setValue(70)
        self.icon_value = QLabel("70px")
        self.icon_value.setFixedWidth(50)
        
        icon_layout.addWidget(icon_label)
        icon_layout.addWidget(self.icon_slider)
        icon_layout.addWidget(self.icon_value)
        
        text_layout = QHBoxLayout()
        text_label = QLabel("文本大小:")
        text_label.setFixedWidth(80)
        self.text_slider = QSlider(Qt.Horizontal)
        self.text_slider.setRange(8, 25)
        self.text_slider.setValue(14)
        self.text_value = QLabel("14px")
        self.text_value.setFixedWidth(50)
        
        text_layout.addWidget(text_label)
        text_layout.addWidget(self.text_slider)
        text_layout.addWidget(self.text_value)
        
        button_layout = QHBoxLayout()
        apply_button = QPushButton("应用")
        cancel_button = QPushButton("取消")
        
        apply_button.clicked.connect(self.apply_changes)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        
        self.icon_slider.valueChanged.connect(lambda v: self.icon_value.setText(f"{v}px"))
        self.text_slider.valueChanged.connect(lambda v: self.text_value.setText(f"{v}px"))
        
        layout.addLayout(icon_layout)
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def apply_changes(self):
        """应用大小更改"""
        icon_size = self.icon_slider.value()
        text_size = self.text_slider.value()
        
        # 修复：直接调用主窗口的方法
        if self.main_window and hasattr(self.main_window, 'set_icon_sizes'):
            self.main_window.set_icon_sizes(icon_size, text_size)
        else:
            # 备用方法：通过图标容器找到主窗口
            parent = self.parent()
            while parent and not hasattr(parent, 'set_icon_sizes'):
                parent = parent.parent()
            if parent:
                parent.set_icon_sizes(icon_size, text_size)
            else:
                print("错误：无法找到主窗口来设置图标大小")
        
        self.accept()

class PlaybackSpeedDialog(QDialog):
    """播放速度设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("设置播放速度")
        self.setFixedSize(350, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(50, 50, 50, 240);
                border: 2px solid rgba(255, 255, 255, 80);
                border-radius: 12px;
                color: white;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QPushButton {
                background-color: rgba(70, 70, 70, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(90, 90, 90, 220);
            }
            QPushButton:pressed {
                background-color: rgba(110, 110, 110, 240);
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        speed_layout = QHBoxLayout()
        speed_label = QLabel("播放速度:")
        speed_label.setFixedWidth(80)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 300)  # 10% 到 300%
        self.speed_slider.setValue(100)  # 默认100%
        self.speed_value = QLabel("100%")
        self.speed_value.setFixedWidth(50)
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value)
        
        # 预设速度按钮
        preset_layout = QHBoxLayout()
        preset_label = QLabel("预设:")
        preset_label.setFixedWidth(40)
        
        slow_btn = QPushButton("0.5x")
        normal_btn = QPushButton("1x")
        fast_btn = QPushButton("1.5x")
        faster_btn = QPushButton("2x")
        
        slow_btn.setFixedSize(50, 30)
        normal_btn.setFixedSize(50, 30)
        fast_btn.setFixedSize(50, 30)
        faster_btn.setFixedSize(50, 30)
        
        slow_btn.clicked.connect(lambda: self.speed_slider.setValue(50))
        normal_btn.clicked.connect(lambda: self.speed_slider.setValue(100))
        fast_btn.clicked.connect(lambda: self.speed_slider.setValue(150))
        faster_btn.clicked.connect(lambda: self.speed_slider.setValue(200))
        
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(slow_btn)
        preset_layout.addWidget(normal_btn)
        preset_layout.addWidget(fast_btn)
        preset_layout.addWidget(faster_btn)
        preset_layout.addStretch()
        
        button_layout = QHBoxLayout()
        apply_button = QPushButton("应用")
        cancel_button = QPushButton("取消")
        
        apply_button.clicked.connect(self.apply_changes)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        
        self.speed_slider.valueChanged.connect(lambda v: self.speed_value.setText(f"{v}%"))
        
        layout.addLayout(speed_layout)
        layout.addLayout(preset_layout)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def apply_changes(self):
        """应用速度更改"""
        speed_percent = self.speed_slider.value()
        
        if self.parent:
            self.parent.set_playback_speed(speed_percent)
        
        self.accept()

class OptimizedOpenCVVideoPlayer:
    """优化的OpenCV视频播放器 - 降低内存和CPU使用"""
    def __init__(self, video_label, screen_width, screen_height):
        self.video_label = video_label
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.video_path = ""
        self.playing = False
        self.video_mode = "stretch"  # 默认拉伸模式
        
        # 性能优化设置
        self.frame_skip = 0  # 跳帧计数器
        self.frame_skip_threshold = 1  # 每2帧处理1帧 (降低CPU使用)
        self.low_resolution_mode = False  # 低分辨率模式
        self.last_frame_time = 0
        
        # 内存优化
        self.frame_buffer = None
        self.frame_count = 0
        
        # 播放速度控制
        self.playback_speed = 1.0  # 默认正常速度
        self.speed_multiplier = 1.0  # 速度倍数
        
    def load_video(self, video_path):
        """加载视频文件 - 优化内存使用"""
        try:
            self.video_path = video_path
            
            # 释放之前的资源
            if self.cap:
                self.cap.release()
                self.cap = None
            
            self.cap = cv2.VideoCapture(video_path)
            
            if not self.cap.isOpened():
                print(f"无法打开视频文件: {video_path}")
                return False
                
            # 获取视频信息
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            print(f"视频信息: {self.video_width}x{self.video_height} @ {self.video_fps}fps")
            
            # 根据视频分辨率决定是否启用低分辨率模式
            # 如果视频分辨率超过屏幕分辨率的2倍，启用低分辨率模式
            if self.video_width > self.screen_width * 2 or self.video_height > self.screen_height * 2:
                self.low_resolution_mode = True
                print("启用低分辨率模式")
            
            # 根据视频FPS调整帧跳过阈值
            if self.video_fps > 30:
                self.frame_skip_threshold = int(self.video_fps / 30)  # 目标30fps
                print(f"设置帧跳过阈值: {self.frame_skip_threshold}")
            
            return True
            
        except Exception as e:
            print(f"加载视频错误: {e}")
            return False
            
    def play(self):
        """开始播放视频"""
        if self.cap and self.cap.isOpened():
            self.playing = True
            # 根据播放速度调整定时器间隔
            base_interval = 33  # ~30fps的基础间隔
            adjusted_interval = int(base_interval / self.speed_multiplier)
            self.timer.start(max(1, adjusted_interval))  # 确保间隔至少为1ms
            print(f"开始播放视频 (速度: {self.speed_multiplier:.1f}x)")
            
    def stop(self):
        """停止播放"""
        self.playing = False
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
            
    def pause(self):
        """暂停播放"""
        self.playing = False
        self.timer.stop()
        
    def resume(self):
        """恢复播放"""
        if self.cap and self.cap.isOpened():
            self.playing = True
            base_interval = 33  # ~30fps的基础间隔
            adjusted_interval = int(base_interval / self.speed_multiplier)
            self.timer.start(max(1, adjusted_interval))
            
    def set_position(self, position):
        """设置播放位置（百分比）"""
        if self.cap and self.cap.isOpened():
            total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            target_frame = int(total_frames * position / 100)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
    def set_video_mode(self, mode):
        """设置视频显示模式"""
        self.video_mode = mode
        
    def set_playback_speed(self, speed_percent):
        """设置播放速度 (百分比)"""
        self.speed_multiplier = speed_percent / 100.0
        
        # 如果正在播放，重新启动定时器以应用新速度
        if self.playing:
            self.timer.stop()
            base_interval = 33  # ~30fps的基础间隔
            adjusted_interval = int(base_interval / self.speed_multiplier)
            self.timer.start(max(1, adjusted_interval))
            
        print(f"播放速度设置为: {speed_percent}% ({self.speed_multiplier:.1f}x)")
        
    def update_frame(self):
        """更新视频帧 - 优化内存和CPU使用"""
        if not self.cap or not self.cap.isOpened() or not self.playing:
            self.timer.stop()
            return
            
        # 根据速度倍数调整帧读取
        frames_to_advance = max(1, int(self.speed_multiplier))
        
        # 快速前进到目标帧
        for i in range(frames_to_advance - 1):
            ret = self.cap.grab()  # 只抓取不解码，速度快
            if not ret:
                break
        
        ret, frame = self.cap.read()
        if not ret:
            # 视频结束，重新开始
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
            
        # 根据模式处理帧
        processed_frame = self.process_frame_optimized(frame)
        
        # 转换为QImage并显示
        q_image = self.cv2_to_qimage(processed_frame)
        self.video_label.setPixmap(QPixmap.fromImage(q_image))
        
    def process_frame_optimized(self, frame):
        """优化的帧处理 - 降低内存和CPU使用"""
        try:
            # 低分辨率模式：先缩小再处理
            if self.low_resolution_mode:
                # 计算合适的缩小比例
                scale_factor = min(self.screen_width / frame.shape[1], self.screen_height / frame.shape[0])
                if scale_factor < 0.5:  # 如果视频远大于屏幕
                    new_width = int(frame.shape[1] * 0.5)
                    new_height = int(frame.shape[0] * 0.5)
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            if self.video_mode == "stretch":
                # 强制拉伸到屏幕尺寸
                return cv2.resize(frame, (self.screen_width, self.screen_height), 
                                interpolation=cv2.INTER_LINEAR)
                
            elif self.video_mode == "scale":
                # 缩放填充 - 保持宽高比，填充整个区域
                h, w = frame.shape[:2]
                screen_ratio = self.screen_width / self.screen_height
                frame_ratio = w / h
                
                if frame_ratio > screen_ratio:
                    # 视频更宽，按宽度缩放
                    new_w = self.screen_width
                    new_h = int(new_w / frame_ratio)
                    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                    
                    # 创建黑色背景
                    result = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)
                    # 垂直居中
                    y_offset = (self.screen_height - new_h) // 2
                    # 确保不超出边界
                    y_offset = max(0, min(y_offset, self.screen_height - new_h))
                    result[y_offset:y_offset+new_h, :] = resized
                    return result
                    
                else:
                    # 视频更高，按高度缩放
                    new_h = self.screen_height
                    new_w = int(new_h * frame_ratio)
                    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                    
                    # 创建黑色背景
                    result = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)
                    # 水平居中
                    x_offset = (self.screen_width - new_w) // 2
                    # 确保不超出边界
                    x_offset = max(0, min(x_offset, self.screen_width - new_w))
                    result[:, x_offset:x_offset+new_w] = resized
                    return result
                    
            elif self.video_mode == "fit":
                # 适应屏幕 - 保持宽高比，适应屏幕
                h, w = frame.shape[:2]
                screen_ratio = self.screen_width / self.screen_height
                frame_ratio = w / h
                
                if frame_ratio > screen_ratio:
                    # 视频更宽，按高度缩放
                    new_h = self.screen_height
                    new_w = int(new_h * frame_ratio)
                    # 确保新宽度不超过屏幕宽度
                    new_w = min(new_w, self.screen_width)
                    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                    
                    # 创建黑色背景
                    result = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)
                    # 水平居中
                    x_offset = (self.screen_width - new_w) // 2
                    # 确保不超出边界
                    x_offset = max(0, min(x_offset, self.screen_width - new_w))
                    # 确保resized的宽度不超过可用空间
                    actual_width = min(new_w, self.screen_width - x_offset)
                    result[:, x_offset:x_offset+actual_width] = resized[:, :actual_width]
                    return result
                    
                else:
                    # 视频更高，按宽度缩放
                    new_w = self.screen_width
                    new_h = int(new_w / frame_ratio)
                    # 确保新高度不超过屏幕高度
                    new_h = min(new_h, self.screen_height)
                    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                    
                    # 创建黑色背景
                    result = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)
                    # 垂直居中
                    y_offset = (self.screen_height - new_h) // 2
                    # 确保不超出边界
                    y_offset = max(0, min(y_offset, self.screen_height - new_h))
                    # 确保resized的高度不超过可用空间
                    actual_height = min(new_h, self.screen_height - y_offset)
                    result[y_offset:y_offset+actual_height, :] = resized[:actual_height, :]
                    return result
                    
        except Exception as e:
            print(f"处理视频帧时出错: {e}")
            # 出错时回退到简单拉伸
            return cv2.resize(frame, (self.screen_width, self.screen_height), 
                            interpolation=cv2.INTER_LINEAR)
                
    def cv2_to_qimage(self, cv_image):
        """将OpenCV图像转换为QImage - 优化内存使用"""
        try:
            # 转换BGR到RGB
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # 重用QImage对象以减少内存分配
            if self.frame_buffer is None or self.frame_buffer.width() != w or self.frame_buffer.height() != h:
                self.frame_buffer = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            else:
                # 重用现有的QImage对象
                self.frame_buffer = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
            return self.frame_buffer.copy()  # 返回副本以确保数据安全
            
        except Exception as e:
            print(f"转换QImage时出错: {e}")
            # 创建错误图像
            error_image = QImage(self.screen_width, self.screen_height, QImage.Format_RGB888)
            error_image.fill(Qt.black)
            return error_image

class DynamicWallpaper(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化设置
        self.settings = QSettings("DynamicWallpaper", "WallpaperSettings")
        
        # 禁用 xfdesktop
        self.disable_xfdesktop()
        
        # 获取屏幕尺寸
        self.screen_rect = QApplication.primaryScreen().geometry()
        self.screen_width = self.screen_rect.width()
        self.screen_height = self.screen_rect.height()
        
        print(f"检测到屏幕分辨率: {self.screen_width}x{self.screen_height}")
        
        # 关键修复：设置正确的窗口属性
        # 使用正确的窗口标志组合，确保壁纸在最底层且不拦截事件
        # 添加 Qt.Tool 标志，确保不在任务栏显示
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 关键：壁纸窗口不拦截鼠标事件
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        
        # 从设置加载配置
        self.load_settings()
        
        # 存储桌面图标
        self.desktop_icons = []
        
        # OpenCV视频播放器
        self.opencv_player = None
        
        # 初始化系统托盘
        self.setup_system_tray()
        
        # 初始化UI组件
        self.setup_ui()
        
        # 延迟设置窗口为桌面背景
        QTimer.singleShot(100, self.set_desktop_window)
        
        # 关键修复：创建独立的图标容器窗口
        self.setup_icon_container()

    def setup_system_tray(self):
        """设置系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统托盘不可用")
            return
            
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 尝试设置图标
        icon_theme = QIcon.fromTheme("video-display")
        if not icon_theme.isNull():
            self.tray_icon.setIcon(icon_theme)
        else:
            # 创建简单的图标
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(70, 130, 180))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(8, 8, 48, 48)
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))
        
        self.tray_icon.setToolTip("动态壁纸")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("显示桌面")
        show_action.triggered.connect(self.show_desktop)
        
        settings_action = tray_menu.addAction("设置")
        settings_action.triggered.connect(self.show_settings)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("退出")
        exit_action.triggered.connect(self.close_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        
        print("系统托盘图标已创建")

    def on_tray_activated(self, reason):
        """系统托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_desktop()

    def show_desktop(self):
        """显示桌面 - 确保图标在最前面"""
        self.raise_icons()

    def show_settings(self):
        """显示设置菜单"""
        # 模拟在图标容器上显示右键菜单
        self.show_context_menu(QPoint(100, 100))

    def load_settings(self):
        """从设置文件加载所有配置"""
        # 背景类型
        self.current_background_type = self.settings.value("background_type", "video", type=str)
        
        # 显示模式
        self.video_mode = self.settings.value("video_mode", "stretch", type=str)
        self.image_mode = self.settings.value("image_mode", "scale", type=str)
        
        # 图标排列方式
        self.icon_arrangement = self.settings.value("icon_arrangement", "vertical", type=str)
        
        # 图标大小设置
        self.icon_size = self.settings.value("icon_size", 64, type=int)
        self.text_size = self.settings.value("text_size", 10, type=int)
        
        # 透明度
        self.transparency = self.settings.value("transparency", 100, type=int)
        
        # 文件路径
        self.current_video_path = self.settings.value("video_path", os.path.expanduser("~/1.mp4"), type=str)
        self.current_image_path = self.settings.value("image_path", "", type=str)
        
        # 上次使用的目录
        self.last_video_dir = self.settings.value("last_video_dir", os.path.expanduser("~/Videos"), type=str)
        self.last_image_dir = self.settings.value("last_image_dir", os.path.expanduser("~/Pictures"), type=str)
        
        # 播放速度
        self.playback_speed = self.settings.value("playback_speed", 100, type=int)
        
        print("设置加载完成")

    def save_settings(self):
        """保存所有设置到文件"""
        # 背景类型
        self.settings.setValue("background_type", self.current_background_type)
        
        # 显示模式
        self.settings.setValue("video_mode", self.video_mode)
        self.settings.setValue("image_mode", self.image_mode)
        
        # 图标排列方式
        self.settings.setValue("icon_arrangement", self.icon_arrangement)
        
        # 图标大小设置
        self.settings.setValue("icon_size", self.icon_size)
        self.settings.setValue("text_size", self.text_size)
        
        # 透明度
        self.settings.setValue("transparency", self.transparency)
        
        # 文件路径
        self.settings.setValue("video_path", self.current_video_path)
        self.settings.setValue("image_path", self.current_image_path)
        
        # 上次使用的目录
        self.settings.setValue("last_video_dir", self.last_video_dir)
        self.settings.setValue("last_image_dir", self.last_image_dir)
        
        # 播放速度
        self.settings.setValue("playback_speed", self.playback_speed)
        
        self.settings.sync()
        print("设置已保存")

    def setup_icon_container(self):
        """创建独立的图标容器窗口 - 修复鼠标事件问题"""
        self.icon_container = QWidget()
        # 关键修复：移除 Qt.WindowStaysOnTopHint，避免覆盖 XFCE4 面板
        # 只保留 Qt.FramelessWindowHint 和 Qt.Tool
        self.icon_container.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.icon_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.icon_container.setGeometry(0, 0, self.screen_width, self.screen_height)
        self.icon_container.setStyleSheet("background: transparent;")
        
        # 关键修复：图标容器正常处理鼠标事件
        self.icon_container.setContextMenuPolicy(Qt.CustomContextMenu)
        self.icon_container.customContextMenuRequested.connect(self.show_context_menu)
        
        self.icon_container.show()

    def remove_icon(self, icon_widget):
        """从图标列表中移除图标"""
        if icon_widget in self.desktop_icons:
            self.desktop_icons.remove(icon_widget)

    def setup_ui(self):
        """设置UI组件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 视频显示组件 (使用QLabel显示OpenCV视频)
        self.setup_video_display()
        
        # 图片显示组件
        self.setup_image_display()
        
        # 初始化右键菜单
        self.setup_context_menu()
        
        # 加载桌面图标
        self.load_desktop_icons()
        
        # 应用透明度设置
        self.apply_transparency()

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
    
    def setup_video_display(self):
        """设置OpenCV视频显示"""
        # 创建视频显示标签
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background: black;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(self.screen_width, self.screen_height)
        # 关键修复：视频标签不拦截鼠标事件
        self.video_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        self.main_layout.addWidget(self.video_label)
        
        # 初始化优化的OpenCV视频播放器
        self.opencv_player = OptimizedOpenCVVideoPlayer(
            self.video_label, 
            self.screen_width, 
            self.screen_height
        )
        
        # 根据设置加载视频或图片
        if self.current_background_type == "video" and os.path.exists(self.current_video_path):
            self.load_video_file(self.current_video_path)
        elif self.current_background_type == "image" and os.path.exists(self.current_image_path):
            self.set_image_background(self.current_image_path)
        else:
            # 默认视频文件路径
            video_path = os.path.expanduser("~/1.mp4")
            if os.path.exists(video_path):
                self.current_video_path = video_path
                self.load_video_file(video_path)
            else:
                print(f"警告: 默认视频文件未找到在 {video_path}")
            
        # 应用视频显示模式
        self.apply_video_mode()
        
        # 应用播放速度设置
        self.set_playback_speed(self.playback_speed)

    def load_video_file(self, video_path):
        """加载视频文件 - 使用优化的OpenCV"""
        try:
            print(f"加载视频文件: {video_path}")
            
            if self.opencv_player:
                # 停止当前播放
                self.opencv_player.stop()
                
                # 加载新视频
                if self.opencv_player.load_video(video_path):
                    # 设置视频模式
                    self.opencv_player.set_video_mode(self.video_mode)
                    # 设置播放速度
                    self.opencv_player.set_playback_speed(self.playback_speed)
                    # 开始播放
                    QTimer.singleShot(100, self.opencv_player.play)
                    print("优化版OpenCV视频加载成功")
                    
                    # 更新背景类型
                    self.current_background_type = "video"
                    self.current_video_path = video_path
                    
                    # 显示视频，隐藏图片
                    self.image_label.hide()
                    self.video_label.show()
                    
                    # 保存设置
                    self.save_settings()
                else:
                    print("OpenCV视频加载失败")
                    self.show_video_error("无法加载视频文件")
                    
        except Exception as e:
            print(f"加载视频文件错误: {e}")
            self.show_video_error(f"加载视频错误: {e}")

    def show_video_error(self, message):
        """显示视频错误信息"""
        error_pixmap = QPixmap(self.screen_width, self.screen_height)
        error_pixmap.fill(Qt.black)
        
        painter = QPainter(error_pixmap)
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 20))
        painter.drawText(error_pixmap.rect(), Qt.AlignCenter, message)
        painter.end()
        
        self.video_label.setPixmap(error_pixmap)

    def setup_image_display(self):
        """设置图片显示"""
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(self.screen_width, self.screen_height)
        # 关键修复：图片标签不拦截鼠标事件
        self.image_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        self.main_layout.addWidget(self.image_label)
        self.image_label.hide()

    def setup_context_menu(self):
        """设置右键菜单 - 现在只用于图标容器"""
        # 壁纸主窗口不设置右键菜单，由图标容器处理
        pass

    def show_context_menu(self, position):
        """显示桌面右键菜单 - 由图标容器调用"""
        menu = QMenu(self.icon_container)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(40, 40, 40, 220);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                color: white;
                padding: 8px 25px 8px 25px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 50);
            }
            QMenu::item:pressed {
                background-color: rgba(255, 255, 255, 80);
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 50);
                margin: 5px 10px 5px 10px;
            }
        """)
        
        bg_menu = QMenu("🖼️ 设置背景", menu)
        bg_menu.setStyleSheet(menu.styleSheet())
        
        video_action = bg_menu.addAction("🎬 选择视频")
        video_action.triggered.connect(self.select_video)
        
        image_action = bg_menu.addAction("🖼️ 选择图片")
        image_action.triggered.connect(self.select_image)
        
        menu.addMenu(bg_menu)
        
        menu.addSeparator()
        
        video_mode_menu = QMenu("📺 视频显示模式", menu)
        video_mode_menu.setStyleSheet(menu.styleSheet())
        
        video_scale_action = video_mode_menu.addAction("🔍 缩放填充")
        video_scale_action.triggered.connect(lambda: self.set_video_mode("scale"))
        
        video_stretch_action = video_mode_menu.addAction("🔄 全屏拉伸")
        video_stretch_action.triggered.connect(lambda: self.set_video_mode("stretch"))
        
        video_fit_action = video_mode_menu.addAction("📐 适应屏幕")
        video_fit_action.triggered.connect(lambda: self.set_video_mode("fit"))
        
        menu.addMenu(video_mode_menu)
        
        image_mode_menu = QMenu("🖼️ 图片显示模式", menu)
        image_mode_menu.setStyleSheet(menu.styleSheet())
        
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
        
        menu.addMenu(image_mode_menu)
        
        menu.addSeparator()
        
        # 添加播放速度控制菜单
        speed_menu = QMenu("⏩ 播放速度", menu)
        speed_menu.setStyleSheet(menu.styleSheet())
        
        speed_slow_action = speed_menu.addAction("🐢 慢速 (0.5x)")
        speed_slow_action.triggered.connect(lambda: self.set_playback_speed(50))
        
        speed_normal_action = speed_menu.addAction("🚶 正常 (1x)")
        speed_normal_action.triggered.connect(lambda: self.set_playback_speed(100))
        
        speed_fast_action = speed_menu.addAction("🏃 快速 (1.5x)")
        speed_fast_action.triggered.connect(lambda: self.set_playback_speed(150))
        
        speed_faster_action = speed_menu.addAction("🚀 极速 (2x)")
        speed_faster_action.triggered.connect(lambda: self.set_playback_speed(200))
        
        speed_custom_action = speed_menu.addAction("⚙️ 自定义速度")
        speed_custom_action.triggered.connect(self.set_custom_speed)
        
        menu.addMenu(speed_menu)
        
        menu.addSeparator()
        
        arrange_menu = QMenu("📑 图标排列方式", menu)
        arrange_menu.setStyleSheet(menu.styleSheet())
        
        grid_action = arrange_menu.addAction("🔲 网格排列")
        grid_action.triggered.connect(lambda: self.set_icon_arrangement("grid"))
        
        horizontal_action = arrange_menu.addAction("↔️ 水平排列")
        horizontal_action.triggered.connect(lambda: self.set_icon_arrangement("horizontal"))
        
        vertical_action = arrange_menu.addAction("↕️ 垂直排列")
        vertical_action.triggered.connect(lambda: self.set_icon_arrangement("vertical"))
        
        free_action = arrange_menu.addAction("🎯 自由排列")
        free_action.triggered.connect(lambda: self.set_icon_arrangement("free"))
        
        menu.addMenu(arrange_menu)
        
        menu.addSeparator()
        
        icon_size_action = menu.addAction("📏 设置图标大小")
        icon_size_action.triggered.connect(self.set_icon_size)
        
        menu.addSeparator()
        
        transparency_action = menu.addAction("🌫️ 设置透明度")
        transparency_action.triggered.connect(self.set_transparency)
        
        menu.addSeparator()
        
        refresh_action = menu.addAction("🔄 刷新桌面图标")
        refresh_action.triggered.connect(self.refresh_desktop_icons)
        
        new_shortcut_action = menu.addAction("➕ 新建快捷方式")
        new_shortcut_action.triggered.connect(self.create_new_shortcut)
        
        menu.addSeparator()
        
        exit_action = menu.addAction("❌ 退出")
        exit_action.triggered.connect(self.close_application)
        
        menu.exec_(self.icon_container.mapToGlobal(position))

    def set_custom_speed(self):
        """打开自定义速度设置对话框"""
        dialog = PlaybackSpeedDialog(self.icon_container)
        dialog.exec_()

    def set_playback_speed(self, speed_percent):
        """设置播放速度"""
        self.playback_speed = speed_percent
        
        if self.opencv_player:
            self.opencv_player.set_playback_speed(speed_percent)
            
        # 保存设置
        self.save_settings()

    def create_new_shortcut(self):
        """创建新的快捷方式 - 修复文本颜色问题"""
        try:
            # 创建自定义输入对话框，确保文本颜色可见
            dialog = QInputDialog(self.icon_container)
            dialog.setWindowTitle("新建快捷方式")
            dialog.setLabelText("输入应用程序名称:")
            dialog.setStyleSheet("""
                QInputDialog {
                    background-color: rgba(50, 50, 50, 240);
                    border: 2px solid rgba(255, 255, 255, 80);
                    border-radius: 12px;
                    color: white;
                }
                QLabel {
                    color: white;
                    background: transparent;
                }
                QLineEdit {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 220);
                }
                QPushButton:pressed {
                    background-color: rgba(110, 110, 110, 240);
                }
            """)
            
            if dialog.exec_() != QDialog.Accepted:
                return
                
            app_name = dialog.textValue()
            if not app_name:
                return
                
            # 暂停视频播放以释放资源
            if self.opencv_player:
                self.opencv_player.pause()
                
            # 创建自定义文件对话框，确保文本颜色可见
            file_dialog = QFileDialog(self.icon_container)
            file_dialog.setWindowTitle("选择应用程序")
            file_dialog.setDirectory("/usr/bin")
            file_dialog.setNameFilter("可执行文件 (*)")
            file_dialog.setStyleSheet("""
                QFileDialog {
                    background-color: rgba(50, 50, 50, 240);
                    border: 2px solid rgba(255, 255, 255, 80);
                    border-radius: 12px;
                    color: white;
                }
                QLabel {
                    color: white;
                    background: transparent;
                }
                QLineEdit {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px;
                }
                QPushButton {
                    background-color: rgba(70, 70, 70, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 60);
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 220);
                }
                QPushButton:pressed {
                    background-color: rgba(110, 110, 110, 240);
                }
                QTreeView, QListView {
                    background-color: rgba(60, 60, 60, 200);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 40);
                    border-radius: 6px;
                }
                QHeaderView::section {
                    background-color: rgba(80, 80, 80, 200);
                    color: white;
                    padding: 5px;
                    border: 1px solid rgba(255, 255, 255, 40);
                }
            """)
            
            # 临时禁用图标容器的鼠标事件穿透
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            if file_dialog.exec_() != QFileDialog.Accepted:
                # 恢复视频播放
                if self.opencv_player:
                    self.opencv_player.resume()
                # 恢复图标容器的鼠标事件处理
                self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                return
                
            selected_files = file_dialog.selectedFiles()
            if not selected_files:
                # 恢复视频播放
                if self.opencv_player:
                    self.opencv_player.resume()
                # 恢复图标容器的鼠标事件处理
                self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                return
                
            app_path = selected_files[0]
            
            # 恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                
            # 创建.desktop文件
            desktop_dir = os.path.expanduser("~/Desktop")
            if not os.path.exists(desktop_dir):
                desktop_dir = os.path.expanduser("~/桌面")
                
            desktop_file = os.path.join(desktop_dir, f"{app_name}.desktop")
            
            with open(desktop_file, 'w', encoding='utf-8') as f:
                f.write("[Desktop Entry]\n")
                f.write("Version=1.0\n")
                f.write(f"Name={app_name}\n")
                f.write(f"Exec={app_path}\n")
                f.write("Icon=application-x-executable\n")
                f.write("Terminal=false\n")
                f.write("Type=Application\n")
                f.write("StartupNotify=true\n")
            
            # 设置可执行权限
            os.chmod(desktop_file, 0o755)
            
            # 刷新图标
            self.refresh_desktop_icons()
            
            QMessageBox.information(self.icon_container, "成功", f"已创建快捷方式: {app_name}")
            
        except Exception as e:
            QMessageBox.warning(self.icon_container, "错误", f"创建快捷方式失败: {e}")
            # 确保恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 确保恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def select_video(self):
        """选择视频文件 - 优化文件对话框性能"""
        try:
            # 暂停视频播放以释放资源
            if self.opencv_player:
                self.opencv_player.pause()
                
            # 使用优化的文件对话框
            file_dialog = QFileDialog(self.icon_container)
            file_dialog.setWindowTitle("选择视频文件")
            
            # 设置默认目录为上次使用的视频目录
            if os.path.exists(self.last_video_dir):
                file_dialog.setDirectory(self.last_video_dir)
            else:
                file_dialog.setDirectory(os.path.expanduser("~/Videos"))
            
            # 优化文件过滤器 - 只显示常见视频格式
            file_dialog.setNameFilter("视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v)")
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            
            # 设置选项优化性能
            file_dialog.setOption(QFileDialog.DontUseNativeDialog, False)  # 使用原生对话框
            file_dialog.setOption(QFileDialog.DontResolveSymlinks, True)   # 不解析符号链接
            
            # 禁用预览等功能以提高性能
            file_dialog.setOption(QFileDialog.HideNameFilterDetails, True)
            
            # 设置视图模式为列表（通常更快）
            file_dialog.setViewMode(QFileDialog.List)
            
            # 临时禁用图标容器的鼠标事件穿透
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            if file_dialog.exec_() == QFileDialog.Accepted:
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    file_path = selected_files[0]
                    # 更新上次使用的目录
                    self.last_video_dir = os.path.dirname(file_path)
                    self.save_settings()
                    self.set_video_background(file_path)
            
            # 恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
        except Exception as e:
            print(f"选择视频文件时出错: {e}")
            # 确保恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 确保恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            # 出错时回退到简单方法
            self.select_video_fallback()

    def select_video_fallback(self):
        """选择视频文件 - 回退方法"""
        try:
            # 暂停视频播放以释放资源
            if self.opencv_player:
                self.opencv_player.pause()
                
            # 临时禁用图标容器的鼠标事件穿透
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            file_path, _ = QFileDialog.getOpenFileName(
                self.icon_container, 
                "选择视频文件", 
                self.last_video_dir if os.path.exists(self.last_video_dir) else os.path.expanduser("~/Videos"),
                "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;所有文件 (*)"
            )
            
            # 恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
            if file_path:
                # 更新上次使用的目录
                self.last_video_dir = os.path.dirname(file_path)
                self.save_settings()
                self.set_video_background(file_path)
                
        except Exception as e:
            print(f"回退方法选择视频文件时出错: {e}")
            # 确保恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 确保恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def select_image(self):
        """选择图片文件 - 优化文件对话框性能"""
        try:
            # 暂停视频播放以释放资源
            if self.opencv_player:
                self.opencv_player.pause()
                
            # 使用优化的文件对话框
            file_dialog = QFileDialog(self.icon_container)
            file_dialog.setWindowTitle("选择图片文件")
            
            # 设置默认目录为上次使用的图片目录
            if os.path.exists(self.last_image_dir):
                file_dialog.setDirectory(self.last_image_dir)
            else:
                file_dialog.setDirectory(os.path.expanduser("~/Pictures"))
            
            # 优化文件过滤器 - 只显示常见图片格式
            file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            
            # 设置选项优化性能
            file_dialog.setOption(QFileDialog.DontUseNativeDialog, False)  # 使用原生对话框
            file_dialog.setOption(QFileDialog.DontResolveSymlinks, True)   # 不解析符号链接
            
            # 禁用预览等功能以提高性能
            file_dialog.setOption(QFileDialog.HideNameFilterDetails, True)
            
            # 设置视图模式为列表（通常更快）
            file_dialog.setViewMode(QFileDialog.List)
            
            # 临时禁用图标容器的鼠标事件穿透
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            if file_dialog.exec_() == QFileDialog.Accepted:
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    file_path = selected_files[0]
                    # 更新上次使用的目录
                    self.last_image_dir = os.path.dirname(file_path)
                    self.save_settings()
                    self.set_image_background(file_path)
            
            # 恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
        except Exception as e:
            print(f"选择图片文件时出错: {e}")
            # 确保恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 确保恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            # 出错时回退到简单方法
            self.select_image_fallback()

    def select_image_fallback(self):
        """选择图片文件 - 回退方法"""
        try:
            # 暂停视频播放以释放资源
            if self.opencv_player:
                self.opencv_player.pause()
                
            # 临时禁用图标容器的鼠标事件穿透
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            file_path, _ = QFileDialog.getOpenFileName(
                self.icon_container, 
                "选择图片文件", 
                self.last_image_dir if os.path.exists(self.last_image_dir) else os.path.expanduser("~/Pictures"),
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;所有文件 (*)"
            )
            
            # 恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
            if file_path:
                # 更新上次使用的目录
                self.last_image_dir = os.path.dirname(file_path)
                self.save_settings()
                self.set_image_background(file_path)
                
        except Exception as e:
            print(f"回退方法选择图片文件时出错: {e}")
            # 确保恢复视频播放
            if self.opencv_player:
                self.opencv_player.resume()
            # 确保恢复图标容器的鼠标事件处理
            self.icon_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def set_video_background(self, video_path):
        """设置视频背景"""
        try:
            self.current_background_type = "video"
            self.current_video_path = video_path
            
            # 显示视频，隐藏图片
            self.image_label.hide()
            self.video_label.show()
            
            # 加载并播放视频
            self.load_video_file(video_path)
            
            self.hide_original_desktop()
            self.raise_icons()
            
            # 保存设置
            self.save_settings()
            
        except Exception as e:
            print(f"设置视频背景错误: {e}")
            QMessageBox.warning(self.icon_container, "错误", f"无法设置视频背景: {e}")

    def set_image_background(self, image_path):
        """设置图片背景"""
        self.current_background_type = "image"
        
        # 暂停视频播放
        if self.opencv_player:
            self.opencv_player.stop()
        
        self.current_image_path = image_path
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap)
            self.video_label.hide()
            self.image_label.show()
            
            self.apply_image_mode()
            self.hide_original_desktop()
            self.raise_icons()
            
            # 保存设置
            self.save_settings()

    def set_video_mode(self, mode):
        """设置视频显示模式"""
        self.video_mode = mode
        
        if self.current_background_type == "video" and self.opencv_player:
            self.opencv_player.set_video_mode(mode)
            
        self.refresh_desktop_icons()
        
        # 保存设置
        self.save_settings()

    def set_image_mode(self, mode):
        """设置图片显示模式"""
        self.image_mode = mode
        
        if self.current_background_type == "image":
            self.apply_image_mode()
            
        self.refresh_desktop_icons()
        
        # 保存设置
        self.save_settings()

    def apply_video_mode(self):
        """应用视频显示模式 - OpenCV会自动处理"""
        if self.opencv_player:
            self.opencv_player.set_video_mode(self.video_mode)
        print(f"视频模式已设置为: {self.video_mode}")

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
        
        # 保存设置
        self.save_settings()

    def arrange_desktop_icons(self):
        """排列桌面图标 - 避开底部面板区域"""
        if not self.desktop_icons:
            return
            
        # 关键修复：避开 XFCE4 面板区域
        # 估计面板高度，通常为40-60像素，为安全起见留更多空间
        panel_height = 80
        available_height = self.screen_height - panel_height
        
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
                # 确保图标不会超出可用高度
                if y + icon_height > available_height - margin:
                    # 如果超出，重新从左上角开始
                    x = margin
                    y = margin
                icon.move(x, y)
                
        elif self.icon_arrangement == "horizontal":
            for i, icon in enumerate(self.desktop_icons):
                x = margin + i * icon_width
                y = margin
                if x + icon_width > self.screen_width - margin:
                    x = margin
                    y += icon_height
                # 确保图标不会超出可用高度
                if y + icon_height > available_height - margin:
                    y = margin
                icon.move(x, y)
                
        elif self.icon_arrangement == "vertical":
            for i, icon in enumerate(self.desktop_icons):
                x = margin
                y = margin + i * icon_height
                # 确保图标不会超出可用高度
                if y + icon_height > available_height - margin:
                    x += icon_width
                    y = margin
                icon.move(x, y)
                
        elif self.icon_arrangement == "free":
            for icon in self.desktop_icons:
                max_x = self.screen_width - icon_width - margin
                max_y = available_height - icon_height - margin
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
        dialog = QDialog(self.icon_container)
        dialog.setWindowTitle("设置透明度")
        dialog.setFixedSize(350, 120)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgba(50, 50, 50, 240);
                border: 2px solid rgba(255, 255, 255, 80);
                border-radius: 12px;
                color: white;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        slider_layout = QHBoxLayout()
        slider_label = QLabel("透明度:")
        slider_label.setFixedWidth(60)
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setRange(10, 100)
        self.transparency_slider.setValue(self.transparency)
        self.transparency_slider.valueChanged.connect(self.update_transparency)
        
        self.transparency_value = QLabel(f"{self.transparency_slider.value()}%")
        self.transparency_value.setFixedWidth(40)
        
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.transparency_slider)
        slider_layout.addWidget(self.transparency_value)
        
        layout.addLayout(slider_layout)
        
        dialog.move(self.icon_container.geometry().center() - dialog.rect().center())
        dialog.exec_()

    def update_transparency(self, value):
        """更新透明度"""
        self.transparency = value
        self.apply_transparency()
        self.transparency_value.setText(f"{value}%")
        
        # 保存设置
        self.save_settings()

    def apply_transparency(self):
        """应用透明度设置到壁纸窗口"""
        opacity = self.transparency / 100.0
        self.setWindowOpacity(opacity)
        # 注意：图标容器窗口保持不透明，只有壁纸背景有透明度

    def set_icon_size(self):
        """设置图标大小"""
        try:
            # 确保传递正确的主窗口引用
            dialog = IconSizeDialog(self)  # 传递 self 而不是 self.icon_container
            dialog.exec_()
        except Exception as e:
            print(f"设置图标大小时出错: {e}")
            QMessageBox.warning(self.icon_container, "错误", f"设置图标大小失败: {e}")
            

    def set_icon_sizes(self, icon_size, text_size):
        """应用图标大小设置"""
        self.icon_size = icon_size
        self.text_size = text_size
        
        for icon in self.desktop_icons:
            icon.set_icon_size(icon_size, text_size)
        
        self.arrange_desktop_icons()
        self.refresh_desktop_icons()
        
        # 保存设置
        self.save_settings()

    def load_desktop_icons(self):
        """加载桌面图标 - 优化性能"""
        for icon in self.desktop_icons:
            icon.setParent(None)
            icon.deleteLater()
        self.desktop_icons.clear()
        
        # 优化的桌面目录搜索
        desktop_dirs = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/桌面"),
        ]
        
        desktop_dir = None
        for dir_path in desktop_dirs:
            if os.path.exists(dir_path):
                desktop_dir = dir_path
                break
        
        if not desktop_dir:
            print("未找到桌面目录")
            return
        
        # 使用更快的文件搜索
        try:
            desktop_files = [f for f in os.listdir(desktop_dir) 
                           if f.endswith('.desktop') and os.path.isfile(os.path.join(desktop_dir, f))]
            desktop_files = [os.path.join(desktop_dir, f) for f in desktop_files]
        except Exception as e:
            print(f"读取桌面目录错误: {e}")
            return
        
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
        """开始播放视频"""
        try:
            if self.current_background_type == "video" and self.opencv_player:
                self.apply_video_mode()
                QTimer.singleShot(200, self.opencv_player.play)
                print("开始播放视频")
        except Exception as e:
            print(f"播放视频错误: {e}")
            QTimer.singleShot(1000, self.recover_from_error)

    def close_application(self):
        """关闭应用程序"""
        try:
            if hasattr(self, 'opencv_player') and self.opencv_player:
                self.opencv_player.stop()
            
            for icon in self.desktop_icons:
                icon.setParent(None)
                icon.deleteLater()
            self.desktop_icons.clear()
            
            self.enable_xfdesktop()
            
            # 保存设置
            self.save_settings()
            
        except Exception as e:
            print(f"关闭应用程序时出错: {e}")
        finally:
            QApplication.quit()

    def recover_from_error(self):
        """从错误中恢复"""
        print("尝试从错误中恢复...")
        
        # 尝试重新加载当前视频
        if hasattr(self, 'current_video_path') and self.current_video_path:
            QTimer.singleShot(1000, lambda: self.load_video_file(self.current_video_path))
        else:
            # 尝试加载默认视频
            video_path = os.path.expanduser("~/1.mp4")
            if os.path.exists(video_path):
                QTimer.singleShot(1000, lambda: self.load_video_file(video_path))

def check_opencv_availability():
    """检查OpenCV是否可用"""
    try:
        import cv2
        print("OpenCV版本:", cv2.__version__)
        return True
    except ImportError:
        print("错误: 未找到OpenCV库")
        print("请安装OpenCV: pip install opencv-python")
        return False

def main():
    """主函数"""
    # 检查OpenCV是否可用
    if not check_opencv_availability():
        print("无法启动: OpenCV不可用")
        return
    
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("动态壁纸")
    app.setApplicationVersion("2.0")
    app.setQuitOnLastWindowClosed(False)
    
    try:
        wallpaper = DynamicWallpaper()
        wallpaper.show()
        
        # 延迟播放视频
        QTimer.singleShot(1000, wallpaper.play)
        
        print("动态壁纸应用程序已启动")
        print("使用说明:")
        print("- 在桌面上右键点击可打开设置菜单")
        print("- 可以选择视频或图片作为背景")
        print("- 支持多种显示模式")
        print("- 可以调整图标大小和排列方式")
        print("- 支持播放速度调节 (0.5x - 3x)")
        print("- 所有设置会自动保存")
        print("- 应用程序图标在系统托盘中")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"启动应用程序时出错: {e}")
        QMessageBox.critical(None, "启动错误", f"无法启动动态壁纸应用程序:\n{e}")

if __name__ == '__main__':
    main()