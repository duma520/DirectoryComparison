import sys
import os
import json
import hashlib
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem, QLabel,
    QFileDialog, QMessageBox, QProgressBar, QComboBox, QCheckBox,
    QGroupBox, QSplitter, QMenu, QHeaderView, QStatusBar,
    QToolBar, QTabWidget, QTextEdit, QDialog, QDialogButtonBox,
    QListWidget, QAbstractItemView, QGridLayout, QFrame, QTextBrowser,
    QListWidgetItem
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QSize, QSettings, QDir, QMutex,
    QWaitCondition, QTimer, QCoreApplication
)
from PySide6.QtGui import (
    QIcon, QAction, QColor, QBrush, QFont, QPalette,
    QClipboard, QKeySequence, QPixmap, QDragEnterEvent, QDropEvent
)

# 颜色定义
COLOR_EXIST = QColor('#B5EAD7')   # 薄荷绿 - 都存在的文件
COLOR_MISSING = QColor('#FFDAC1') # 蜜桃橙 - 缺少的文件
COLOR_EXTRA = QColor('#FFB7CE')    # 樱花粉 - 多出的文件

class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    VERSION = "5.1.8"
    BUILD_DATE = "2026-03-09"
    AUTHOR = "杜玛"
    LICENSE = "GNU Affero General Public License v3.0"
    COPYRIGHT = "© 2026 杜玛。永久保留所有权利。"
    URL = "https://github.com/duma520"
    MAINTAINER_EMAIL = "duma520@example.com"  # 示例邮箱，请替换为实际邮箱
    NAME = "多目录文件比对工具"
    DESCRIPTION = """多目录文件比对工具 - 高效、精准的目录比较解决方案

主要功能：
• 快速扫描和比较两个目录的内容差异
• 支持子目录递归比较
• 多种显示模式：分组显示、平铺显示、列表显示
• 灵活的过滤选项：共同存在、差异、多出、缺少
• 文件大小和修改时间对比
• 历史记录功能，快速访问常用目录
• 支持拖拽目录到输入框
• 右键菜单快速操作文件
• 多线程扫描，界面不卡顿
• 支持取消操作
"""

    VERSION_HISTORY = {
        "1.0.0": "初始版本 - 基础目录比较功能",
        "2.0.0": "添加多线程扫描，提升性能",
        "3.0.0": "增加过滤和显示模式选项",
        "4.0.0": "添加历史记录和设置保存功能",
        "5.0.0": "优化界面，增加右键菜单",
        "5.1.0": "增加共同存在过滤选项",
        "5.1.1": "优化性能和修复已知问题"
    }
    
    HELP_TEXT = """<h2>多目录文件比对工具 - 使用指南</h2>

<h3>基本操作步骤：</h3>
<ol>
    <li><b>选择目录</b>：点击"浏览"按钮或直接粘贴路径到输入框</li>
    <li><b>开始比较</b>：点击工具栏的"开始比较"按钮或按F5键</li>
    <li><b>查看结果</b>：比较完成后，结果会以彩色方式显示</li>
    <li><b>过滤结果</b>：使用"比较模式"下拉框筛选显示内容</li>
</ol>

<h3>颜色标识：</h3>
<ul>
    <li><span style='background-color: #B5EAD7'>薄荷绿</span> - 两个目录都存在的文件</li>
    <li><span style='background-color: #FFDAC1'>蜜桃橙</span> - 目录2中缺少的文件</li>
    <li><span style='background-color: #FFB7CE'>樱花粉</span> - 目录1中多出的文件</li>
</ul>

<h3>比较模式说明：</h3>
<ul>
    <li><b>全部文件</b> - 显示所有文件和目录</li>
    <li><b>只显示共同存在</b> - 仅显示两个目录都有的项目</li>
    <li><b>只显示差异</b> - 仅显示存在差异的项目</li>
    <li><b>只显示多出的文件</b> - 仅显示目录1有而目录2没有的项目</li>
    <li><b>只显示缺少的文件</b> - 仅显示目录2有而目录1没有的项目</li>
</ul>

<h3>显示模式：</h3>
<ul>
    <li><b>分组显示</b> - 按状态分组显示（推荐）</li>
    <li><b>平铺显示</b> - 所有项目平铺显示</li>
    <li><b>列表显示</b> - 简洁列表形式</li>
</ul>

<h3>右键菜单功能：</h3>
<ul>
    <li><b>打开文件位置</b> - 在资源管理器中打开文件所在目录</li>
    <li><b>复制路径</b> - 复制文件的相对路径到剪贴板</li>
    <li><b>复制文件名</b> - 复制文件名到剪贴板</li>
    <li><b>比较内容</b> - 对文件进行内容比较（需额外配置）</li>
    <li><b>刷新</b> - 重新比较当前选中的项目</li>
</ul>

<h3>快捷键：</h3>
<ul>
    <li><b>F5</b> - 开始比较</li>
    <li><b>Ctrl+Q</b> - 退出程序</li>
    <li><b>F1</b> - 打开帮助</li>
    <li><b>Ctrl+C</b> - 复制选中项的信息</li>
</ul>

<h3>使用技巧：</h3>
<ul>
    <li>可以直接从文件夹拖拽目录到输入框</li>
    <li>双击目录输入框可以快速打开目录选择对话框</li>
    <li>使用"交换目录"按钮快速切换两个目录的位置</li>
    <li>历史记录会自动保存最近使用的20个目录</li>
    <li>程序会自动保存窗口位置和显示设置</li>
</ul>

<h3>注意事项：</h3>
<ul>
    <li>比较大量文件时请耐心等待，可使用"停止"按钮取消操作</li>
    <li>目录权限不足可能导致某些文件无法访问</li>
    <li>符号链接会被当作普通文件处理</li>
    <li>建议在使用前关闭不必要的程序以释放系统资源</li>
</ul>

<p><i>如有问题或建议，请联系：duma520@example.com</i></p>
"""

    @classmethod
    def get_metadata(cls) -> dict:
        """获取主要元数据字典"""
        return {
            'version': cls.VERSION,
            'author': cls.AUTHOR,
            'license': cls.LICENSE,
            'url': cls.URL,
            'email': cls.MAINTAINER_EMAIL
        }

    @classmethod
    def get_header(cls) -> str:
        """生成标准化的项目头信息"""
        return f"{cls.NAME} v{cls.VERSION} | {cls.LICENSE} License | {cls.URL}"

    @classmethod
    def get_about_info(cls) -> dict:
        """获取ABOUT信息字典"""
        return {
            "name": cls.NAME,
            "version": cls.VERSION,
            "build_date": cls.BUILD_DATE,
            "author": cls.AUTHOR,
            "license": cls.LICENSE,
            "copyright": cls.COPYRIGHT,
            "url": cls.URL,
            "email": cls.MAINTAINER_EMAIL,
            "description": cls.DESCRIPTION.strip(),
            "features": [
                "快速扫描和比较两个目录",
                "递归子目录比较",
                "多种显示和过滤模式",
                "文件大小和修改时间对比",
                "彩色标识文件状态",
                "历史记录功能",
                "拖拽支持",
                "右键菜单快速操作",
                "多线程扫描不卡顿",
                "设置自动保存"
            ]
        }

    @classmethod
    def get_version_history(cls) -> str:
        """获取格式化的版本历史"""
        history = "<h3>版本历史：</h3><ul>"
        for version, desc in sorted(cls.VERSION_HISTORY.items(), reverse=True):
            history += f"<li><b>{version}</b>: {desc}</li>"
        history += "</ul>"
        return history


class AboutDialog(QDialog):
    """关于对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"关于 {ProjectInfo.NAME}")
        self.setFixedSize(500, 650)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题和图标区域
        title_layout = QHBoxLayout()
        
        # 图标（如果有）
        icon_label = QLabel()
        if os.path.exists("icon.ico"):
            pixmap = QPixmap("icon.ico")
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(icon_label)
        
        # 标题文本
        title_text = QVBoxLayout()
        name_label = QLabel(ProjectInfo.NAME)
        name_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #2c3e50;")
        title_text.addWidget(name_label)
        
        version_label = QLabel(f"版本 {ProjectInfo.VERSION} (Build: {ProjectInfo.BUILD_DATE})")
        version_label.setFont(QFont("Microsoft YaHei", 10))
        version_label.setStyleSheet("color: #7f8c8d;")
        title_text.addWidget(version_label)
        
        title_layout.addLayout(title_text)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #bdc3c7;")
        layout.addWidget(line)
        
        # 获取信息
        info = ProjectInfo.get_about_info()
        
        # 作者信息
        author_layout = QGridLayout()
        author_layout.setVerticalSpacing(8)
        
        # 作者
        author_layout.addWidget(QLabel("<b>作者：</b>"), 0, 0)
        author_label = QLabel(info['author'])
        author_label.setTextFormat(Qt.RichText)
        author_layout.addWidget(author_label, 0, 1)
        
        # 邮箱
        author_layout.addWidget(QLabel("<b>邮箱：</b>"), 1, 0)
        email_label = QLabel(f'<a href="mailto:{info["email"]}">{info["email"]}</a>')
        email_label.setOpenExternalLinks(True)
        email_label.setTextFormat(Qt.RichText)
        author_layout.addWidget(email_label, 1, 1)
        
        # 网址
        author_layout.addWidget(QLabel("<b>网址：</b>"), 2, 0)
        url_label = QLabel(f'<a href="{info["url"]}">{info["url"]}</a>')
        url_label.setOpenExternalLinks(True)
        url_label.setTextFormat(Qt.RichText)
        author_layout.addWidget(url_label, 2, 1)
        
        # 许可证
        author_layout.addWidget(QLabel("<b>许可证：</b>"), 3, 0)
        license_label = QLabel(info['license'])
        author_layout.addWidget(license_label, 3, 1)
        
        # 版权
        author_layout.addWidget(QLabel("<b>版权：</b>"), 4, 0)
        copyright_label = QLabel(info['copyright'])
        author_layout.addWidget(copyright_label, 4, 1)
        
        layout.addLayout(author_layout)
        
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        line2.setStyleSheet("background-color: #bdc3c7;")
        layout.addWidget(line2)
        
        # 描述
        desc_label = QLabel(info['description'])
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignLeft)
        desc_label.setStyleSheet("background-color: #f8f9fa; padding: 10px; border-radius: 5px;")
        layout.addWidget(desc_label)
        
        # 功能列表标题
        features_title = QLabel("<b>主要功能：</b>")
        features_title.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(features_title)
        
        # 功能列表
        features_widget = QWidget()
        features_layout = QGridLayout(features_widget)
        features_layout.setVerticalSpacing(5)
        
        for i, feature in enumerate(info['features']):
            row = i // 2
            col = i % 2
            feature_label = QLabel(f"• {feature}")
            feature_label.setStyleSheet("color: #2c3e50;")
            features_layout.addWidget(feature_label, row, col)
        
        layout.addWidget(features_widget)
        
        # 版本历史
        history_label = QLabel(ProjectInfo.get_version_history())
        history_label.setTextFormat(Qt.RichText)
        history_label.setWordWrap(True)
        history_label.setStyleSheet("background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;")
        layout.addWidget(history_label)
        
        layout.addStretch()
        
        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        
        # 自定义确定按钮文本
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText("关闭")
        ok_button.setMinimumWidth(100)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)


class HelpDialog(QDialog):
    """帮助对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{ProjectInfo.NAME} - 帮助")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 使用指南标签页
        guide_widget = QWidget()
        guide_layout = QVBoxLayout(guide_widget)
        
        guide_text = QTextBrowser()
        guide_text.setOpenExternalLinks(True)  # 允许打开外部链接
        guide_text.setHtml(ProjectInfo.HELP_TEXT)
        guide_layout.addWidget(guide_text)
        
        tab_widget.addTab(guide_widget, "使用指南")
        
        # 快捷键标签页
        shortcut_widget = QWidget()
        shortcut_layout = QVBoxLayout(shortcut_widget)
        
        shortcut_text = QTextBrowser()
        shortcut_text.setOpenExternalLinks(True)  # 允许打开外部链接
        shortcut_text.setHtml("""
        <h2>快捷键列表</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th><b>快捷键</b></th>
                <th><b>功能</b></th>
            </tr>
            <tr>
                <td><b>F5</b></td>
                <td>开始比较</td>
            </tr>
            <tr>
                <td><b>Ctrl+Q</b></td>
                <td>退出程序</td>
            </tr>
            <tr>
                <td><b>F1</b></td>
                <td>打开帮助</td>
            </tr>
            <tr>
                <td><b>Ctrl+C</b></td>
                <td>复制选中项信息</td>
            </tr>
            <tr>
                <td><b>Delete</b></td>
                <td>清空当前选择</td>
            </tr>
            <tr>
                <td><b>Ctrl+A</b></td>
                <td>全选</td>
            </tr>
            <tr>
                <td><b>Enter</b></td>
                <td>打开选中文件</td>
            </tr>
        </table>
        
        <h3>鼠标操作：</h3>
        <ul>
            <li><b>单击</b> - 选中项目</li>
            <li><b>双击</b> - 展开/折叠组或打开文件</li>
            <li><b>右键单击</b> - 打开上下文菜单</li>
            <li><b>拖拽</b> - 将目录拖入输入框</li>
        </ul>
        """)
        shortcut_layout.addWidget(shortcut_text)
        
        tab_widget.addTab(shortcut_widget, "快捷键")
        
        # 关于标签页
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)
        
        about_text = QTextBrowser()
        about_text.setOpenExternalLinks(True)  # 允许打开外部链接
        info = ProjectInfo.get_about_info()
        about_html = f"""
        <h2>{info['name']}</h2>
        <p><b>版本：</b> {info['version']}<br>
        <b>构建日期：</b> {info['build_date']}<br>
        <b>作者：</b> {info['author']}<br>
        <b>许可证：</b> {info['license']}<br>
        <b>版权：</b> {info['copyright']}<br>
        <b>网址：</b> <a href="{info['url']}">{info['url']}</a><br>
        <b>邮箱：</b> <a href="mailto:{info['email']}">{info['email']}</a></p>
        
        <h3>描述：</h3>
        <p>{info['description'].replace(chr(10), '<br>')}</p>
        
        <h3>系统要求：</h3>
        <ul>
            <li>Windows 7/8/10/11 或 Linux/MacOS（需Python环境）</li>
            <li>Python 3.7+</li>
            <li>PySide6 6.0+</li>
            <li>至少 100MB 可用内存</li>
        </ul>
        
        <h3>依赖库：</h3>
        <ul>
            <li>PySide6 - GUI框架</li>
            <li>Python标准库 - os, sys, json, hashlib, threading等</li>
        </ul>
        
        <p><i>感谢您使用本工具！</i></p>
        """
        about_text.setHtml(about_html)
        about_layout.addWidget(about_text)
        
        tab_widget.addTab(about_widget, "关于")
        
        layout.addWidget(tab_widget)
        
        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        
        close_button = button_box.button(QDialogButtonBox.Ok)
        close_button.setText("关闭")
        close_button.setMinimumWidth(100)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)




class CompareMode(Enum):
    """比较模式"""
    ALL = "全部文件"
    COMMON_ONLY = "只显示共同存在"  # 新增
    DIFF_ONLY = "只显示差异"
    EXTRA_ONLY = "只显示多出的文件"
    MISSING_ONLY = "只显示缺少的文件"


class DisplayMode(Enum):
    """显示模式"""
    GROUP = "分组显示"
    FLAT = "平铺显示"
    LIST = "列表显示"


class FileInfo:
    """文件信息类"""
    def __init__(self, path: str, rel_path: str):
        self.path = path
        self.rel_path = rel_path
        self.name = os.path.basename(path)
        self.is_dir = os.path.isdir(path)
        self.size = 0
        self.mod_time = 0
        self.exists = os.path.exists(path)
        
        if self.exists and not self.is_dir:
            try:
                self.size = os.path.getsize(path)
                self.mod_time = os.path.getmtime(path)
            except:
                pass


class ScanThread(QThread):
    """扫描线程"""
    progress = Signal(int, str)  # 进度值，状态信息
    finished = Signal(dict)  # 扫描结果
    error = Signal(str)  # 错误信息
    
    def __init__(self, dir1: str, dir2: str):
        super().__init__()
        self.dir1 = dir1
        self.dir2 = dir2
        self.is_cancelled = False
        self.mutex = QMutex()
        
    def cancel(self):
        self.mutex.lock()
        self.is_cancelled = True
        self.mutex.unlock()
        
    def run(self):
        try:
            result = {
                'files1': {},
                'files2': {},
                'errors': []
            }
            
            # 扫描第一个目录
            if self.dir1:
                self.progress.emit(0, f"正在扫描目录1: {self.dir1}")
                files1 = self.scan_directory(self.dir1)
                result['files1'] = files1
                
            # 检查是否取消
            if self.is_cancelled:
                return
                
            # 扫描第二个目录
            if self.dir2:
                self.progress.emit(50, f"正在扫描目录2: {self.dir2}")
                files2 = self.scan_directory(self.dir2)
                result['files2'] = files2
                
            self.progress.emit(100, "扫描完成")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
            
    def scan_directory(self, root_path: str) -> Dict[str, FileInfo]:
        """扫描目录"""
        result = {}
        try:
            all_files = []
            for root, dirs, files in os.walk(root_path):
                # 检查是否取消
                self.mutex.lock()
                if self.is_cancelled:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()
                
                # 处理目录
                for dir_name in dirs:
                    try:
                        full_path = os.path.join(root, dir_name)
                        rel_path = os.path.relpath(full_path, root_path)
                        if rel_path == '.':
                            continue
                        result[rel_path] = FileInfo(full_path, rel_path)
                    except Exception as e:
                        result['errors'].append(f"处理目录出错: {str(e)}")
                        
                # 处理文件
                for file_name in files:
                    try:
                        full_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(full_path, root_path)
                        result[rel_path] = FileInfo(full_path, rel_path)
                    except Exception as e:
                        result['errors'].append(f"处理文件出错: {str(e)}")
                        
        except Exception as e:
            result['errors'].append(f"扫描目录出错: {str(e)}")
            
        return result


class CompareThread(QThread):
    """比较线程"""
    progress = Signal(int, str)  # 进度值，状态信息
    finished = Signal(list)  # 比较结果
    error = Signal(str)
    
    def __init__(self, files1: Dict, files2: Dict):
        super().__init__()
        self.files1 = files1
        self.files2 = files2
        self.is_cancelled = False
        self.mutex = QMutex()
        
    def cancel(self):
        self.mutex.lock()
        self.is_cancelled = True
        self.mutex.unlock()
        
    def run(self):
        try:
            result = []
            all_keys = set(self.files1.keys()) | set(self.files2.keys())
            total = len(all_keys)
            processed = 0
            
            for rel_path in sorted(all_keys):
                # 检查是否取消
                self.mutex.lock()
                if self.is_cancelled:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()
                
                file1 = self.files1.get(rel_path)
                file2 = self.files2.get(rel_path)
                
                item = {
                    'rel_path': rel_path,
                    'name': os.path.basename(rel_path),
                    'in_dir1': file1 is not None,
                    'in_dir2': file2 is not None,
                    'is_dir': file1.is_dir if file1 else (file2.is_dir if file2 else False),
                    'size1': file1.size if file1 else 0,
                    'size2': file2.size if file2 else 0,
                    'time1': file1.mod_time if file1 else 0,
                    'time2': file2.mod_time if file2 else 0
                }
                
                result.append(item)
                
                processed += 1
                if processed % 100 == 0:
                    self.progress.emit(
                        int(processed * 100 / total),
                        f"正在比较: {processed}/{total}"
                    )
                    
            self.progress.emit(100, "比较完成")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class HistoryDialog(QDialog):
    """历史记录对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("历史记录")
        self.setMinimumSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 历史记录列表
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.history_list)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def set_history(self, history: list):
        """设置历史记录"""
        self.history_list.clear()
        for item in history:
            self.history_list.addItem(item)
            
    def get_selected(self) -> str:
        """获取选中的记录"""
        item = self.history_list.currentItem()
        return item.text() if item else ""


class DirCompareTool(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.settings = QSettings("DirCompare", "Tool")
        self.scan_thread = None
        self.compare_thread = None
        self.current_results = []
        self.filtered_results = []
        self.compare_mode = CompareMode.ALL
        self.display_mode = DisplayMode.GROUP
        self.history = []
        self.result_list = None 
        self.init_ui()
        self.load_settings()
        self.setup_connections()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"{ProjectInfo.NAME} {ProjectInfo.VERSION} (Build: {ProjectInfo.BUILD_DATE})")
        self.setMinimumSize(900, 600)
        
        # 设置图标
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
    
        # 删除菜单栏创建 - 注释掉或删除这行
        # self.create_menu_bar()
    
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建目录选择区域
        self.create_dir_selection(main_layout)
        
        # 创建过滤和显示选项
        self.create_filter_options(main_layout)
        
        # 创建结果显示区域
        self.create_result_display(main_layout)
        
        # 创建进度条和状态栏
        self.create_progress_and_status(main_layout)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        open_dir1_action = QAction("打开目录1", self)
        open_dir1_action.triggered.connect(lambda: self.browse_directory(self.dir1_edit))
        file_menu.addAction(open_dir1_action)
        
        open_dir2_action = QAction("打开目录2", self)
        open_dir2_action.triggered.connect(lambda: self.browse_directory(self.dir2_edit))
        file_menu.addAction(open_dir2_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 查看菜单 - 完善
        view_menu = menubar.addMenu("查看")
    
        # 显示模式子菜单
        display_mode_menu = view_menu.addMenu("显示模式")
        
        group_action = QAction("分组显示", self, checkable=True)
        group_action.setChecked(True)
        group_action.triggered.connect(lambda: self.change_display_mode(DisplayMode.GROUP))
        display_mode_menu.addAction(group_action)
        
        flat_action = QAction("平铺显示", self, checkable=True)
        flat_action.triggered.connect(lambda: self.change_display_mode(DisplayMode.FLAT))
        display_mode_menu.addAction(flat_action)
        
        list_action = QAction("列表显示", self, checkable=True)
        list_action.triggered.connect(lambda: self.change_display_mode(DisplayMode.LIST))
        display_mode_menu.addAction(list_action)
        
        view_menu.addSeparator()
        
        # 过滤模式子菜单
        filter_mode_menu = view_menu.addMenu("过滤模式")
        
        all_action = QAction("全部文件", self, checkable=True)
        all_action.setChecked(True)
        all_action.triggered.connect(lambda: self.change_filter_mode(CompareMode.ALL))
        filter_mode_menu.addAction(all_action)
        
        common_action = QAction("只显示共同存在", self, checkable=True)
        common_action.triggered.connect(lambda: self.change_filter_mode(CompareMode.COMMON_ONLY))
        filter_mode_menu.addAction(common_action)
        
        diff_action = QAction("只显示差异", self, checkable=True)
        diff_action.triggered.connect(lambda: self.change_filter_mode(CompareMode.DIFF_ONLY))
        filter_mode_menu.addAction(diff_action)
        
        extra_action = QAction("只显示多出的文件", self, checkable=True)
        extra_action.triggered.connect(lambda: self.change_filter_mode(CompareMode.EXTRA_ONLY))
        filter_mode_menu.addAction(extra_action)
        
        missing_action = QAction("只显示缺少的文件", self, checkable=True)
        missing_action.triggered.connect(lambda: self.change_filter_mode(CompareMode.MISSING_ONLY))
        filter_mode_menu.addAction(missing_action)
        
        view_menu.addSeparator()
        
        # 工具栏显示/隐藏
        show_toolbar_action = QAction("显示工具栏", self, checkable=True)
        show_toolbar_action.setChecked(True)
        show_toolbar_action.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(show_toolbar_action)
        
        # 状态栏显示/隐藏
        show_statusbar_action = QAction("显示状态栏", self, checkable=True)
        show_statusbar_action.setChecked(True)
        show_statusbar_action.triggered.connect(self.toggle_statusbar)
        view_menu.addAction(show_statusbar_action)
        
        view_menu.addSeparator()
        
        # 刷新
        refresh_view_action = QAction("刷新", self)
        refresh_view_action.setShortcut(QKeySequence("F5"))
        refresh_view_action.triggered.connect(self.start_comparison)
        view_menu.addAction(refresh_view_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        compare_action = QAction("开始比较", self)
        compare_action.setShortcut(QKeySequence("F5"))
        compare_action.triggered.connect(self.start_comparison)
        tools_menu.addAction(compare_action)
        
        stop_action = QAction("停止比较", self)
        stop_action.triggered.connect(self.stop_comparison)
        tools_menu.addAction(stop_action)
        
        tools_menu.addSeparator()
        
        history_action = QAction("历史记录", self)
        history_action.triggered.connect(self.show_history)
        tools_menu.addAction(history_action)
    
        clear_action = QAction("清空目录", self)
        clear_action.triggered.connect(self.clear_directories)
        tools_menu.addAction(clear_action)
    
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        help_action = QAction("帮助", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        about_qt_action = QAction("关于Qt", self)
        about_qt_action.triggered.connect(QApplication.aboutQt)
        help_menu.addAction(about_qt_action)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 开始比较
        self.start_action = QAction("开始比较", self)
        self.start_action.setShortcut(QKeySequence("F5"))
        toolbar.addAction(self.start_action)
        
        # 停止
        self.stop_action = QAction("停止", self)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)
        
        toolbar.addSeparator()
        
        # 刷新
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        toolbar.addAction(refresh_action)
        # 添加信号连接
        refresh_action.triggered.connect(self.start_comparison)
        
        # 历史记录
        history_action = QAction("历史记录", self)
        toolbar.addAction(history_action)
        # 添加信号连接
        history_action.triggered.connect(self.show_history)
        
        # 清空
        clear_action = QAction("清空", self)
        toolbar.addAction(clear_action)
        # 添加信号连接
        clear_action.triggered.connect(self.clear_directories)
        
        toolbar.addSeparator()
    
        # 添加帮助菜单
        help_action = QAction("帮助", self)
        help_action.setShortcut(QKeySequence("F1"))
        toolbar.addAction(help_action)
        # 添加信号连接
        help_action.triggered.connect(self.show_help)
        
        # 添加关于菜单
        about_action = QAction("关于", self)
        toolbar.addAction(about_action)
        # 添加信号连接
        about_action.triggered.connect(self.show_about)
        
       

    def create_dir_selection(self, parent_layout):
        """创建目录选择区域"""
        group = QGroupBox("目录选择")
        layout = QGridLayout(group)
        layout.setContentsMargins(5, 10, 5, 5)
        layout.setSpacing(5)
        
        # 目录1
        layout.addWidget(QLabel("目录1:"), 0, 0)
        self.dir1_edit = QLineEdit()
        self.dir1_edit.setPlaceholderText("请选择或粘贴目录路径")
        layout.addWidget(self.dir1_edit, 0, 1)
        
        btn1_layout = QHBoxLayout()
        self.browse1_btn = QPushButton("浏览...")
        self.paste1_btn = QPushButton("粘贴")
        btn1_layout.addWidget(self.browse1_btn)
        btn1_layout.addWidget(self.paste1_btn)
        layout.addLayout(btn1_layout, 0, 2)
        
        # 目录2
        layout.addWidget(QLabel("目录2:"), 1, 0)
        self.dir2_edit = QLineEdit()
        self.dir2_edit.setPlaceholderText("请选择或粘贴目录路径")
        layout.addWidget(self.dir2_edit, 1, 1)
        
        btn2_layout = QHBoxLayout()
        self.browse2_btn = QPushButton("浏览...")
        self.paste2_btn = QPushButton("粘贴")
        btn2_layout.addWidget(self.browse2_btn)
        btn2_layout.addWidget(self.paste2_btn)
        layout.addLayout(btn2_layout, 1, 2)
        
        # 交换按钮 - 保存为实例变量
        self.swap_btn = QPushButton("交换目录")
        layout.addWidget(self.swap_btn, 2, 1, Qt.AlignCenter)
        
        parent_layout.addWidget(group)
        
    def create_filter_options(self, parent_layout):
        """创建过滤选项"""
        group = QGroupBox("显示选项")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 比较模式
        layout.addWidget(QLabel("比较模式:"))
        self.mode_combo = QComboBox()
        for mode in CompareMode:
            self.mode_combo.addItem(mode.value)
        layout.addWidget(self.mode_combo)
        
        # 显示模式
        layout.addWidget(QLabel("显示模式:"))
        self.display_combo = QComboBox()
        for mode in DisplayMode:
            self.display_combo.addItem(mode.value)
        layout.addWidget(self.display_combo)
        
        layout.addStretch()
        
        # 包含子目录
        self.subdir_check = QCheckBox("包含子目录")
        self.subdir_check.setChecked(True)
        layout.addWidget(self.subdir_check)
        
        parent_layout.addWidget(group)
        
    def create_result_display(self, parent_layout):
        """创建结果显示区域"""
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels([
            "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
            "修改时间(目录1)", "修改时间(目录2)"
        ])
        
        # 设置列宽
        header = self.result_tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        # 启用右键菜单
        self.result_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.result_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        parent_layout.addWidget(self.result_tree)
        
    def create_progress_and_status(self, parent_layout):
        """创建进度条和状态栏"""
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        parent_layout.addWidget(self.progress_bar)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
        # 在状态栏右侧显示版本信息
        self.version_label = QLabel(ProjectInfo.get_header())
        self.version_label.setStyleSheet("color: gray;")
        self.status_bar.addPermanentWidget(self.version_label)

    def setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        self.browse1_btn.clicked.connect(lambda: self.browse_directory(self.dir1_edit))
        self.browse2_btn.clicked.connect(lambda: self.browse_directory(self.dir2_edit))
        self.paste1_btn.clicked.connect(lambda: self.paste_directory(self.dir1_edit))
        self.paste2_btn.clicked.connect(lambda: self.paste_directory(self.dir2_edit))
    
        # 交换按钮连接
        self.swap_btn.clicked.connect(self.swap_directories)
    
        # 工具栏动作
        self.start_action.triggered.connect(self.start_comparison)
        self.stop_action.triggered.connect(self.stop_comparison)
        
        # 过滤选项
        self.mode_combo.currentTextChanged.connect(self.filter_results)
        self.display_combo.currentTextChanged.connect(self.filter_results)
        
    def browse_directory(self, line_edit):
        """浏览目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", line_edit.text()
        )
        if directory:
            line_edit.setText(directory)
            self.add_to_history(directory)
            
    def paste_directory(self, line_edit):
        """粘贴目录"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text and os.path.isdir(text):
            line_edit.setText(text)
            self.add_to_history(text)
        else:
            QMessageBox.warning(self, "警告", "剪贴板内容不是有效的目录路径")
            
    def add_to_history(self, path):
        """添加到历史记录"""
        if path not in self.history:
            self.history.insert(0, path)
            if len(self.history) > 20:
                self.history.pop()
            self.save_settings()
            
    def start_comparison(self):
        """开始比较"""
        dir1 = self.dir1_edit.text().strip()
        dir2 = self.dir2_edit.text().strip()
        
        if not dir1 or not dir2:
            QMessageBox.warning(self, "警告", "请选择两个目录")
            return
            
        if not os.path.isdir(dir1) or not os.path.isdir(dir2):
            QMessageBox.warning(self, "警告", "目录路径无效")
            return
            
        # 更新UI状态
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_tree.clear()
        
        # 启动扫描线程
        self.scan_thread = ScanThread(dir1, dir2)
        self.scan_thread.progress.connect(self.update_progress)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.error.connect(self.on_error)
        self.scan_thread.start()
        
    def stop_comparison(self):
        """停止比较"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.cancel()
            self.scan_thread.wait()
            
        if self.compare_thread and self.compare_thread.isRunning():
            self.compare_thread.cancel()
            self.compare_thread.wait()
            
        self.reset_ui_state()
        self.status_label.setText("已停止")
        
    def on_scan_finished(self, result):
        """扫描完成"""
        self.scan_thread = None
        
        # 检查是否有错误
        errors = result.get('errors', [])
        if errors:
            QMessageBox.warning(self, "扫描警告", "\n".join(errors[:5]))
            
        # 启动比较线程
        self.compare_thread = CompareThread(
            result.get('files1', {}),
            result.get('files2', {})
        )
        self.compare_thread.progress.connect(self.update_progress)
        self.compare_thread.finished.connect(self.on_compare_finished)
        self.compare_thread.error.connect(self.on_error)
        self.compare_thread.start()
        
    def on_compare_finished(self, results):
        """比较完成"""
        self.compare_thread = None
        self.current_results = results
        self.filter_results()
        self.reset_ui_state()
        self.status_label.setText(f"比较完成，共 {len(results)} 个项目")
        
    def filter_results(self):
        """过滤结果"""
        if not self.current_results:
            return
            
        mode = list(CompareMode)[self.mode_combo.currentIndex()]
        self.filtered_results = []
        
        for item in self.current_results:
            if mode == CompareMode.ALL:
                self.filtered_results.append(item)
            elif mode == CompareMode.COMMON_ONLY:  # 新增条件
                if item['in_dir1'] and item['in_dir2']:
                    self.filtered_results.append(item)
            elif mode == CompareMode.DIFF_ONLY:
                if item['in_dir1'] != item['in_dir2']:
                    self.filtered_results.append(item)
            elif mode == CompareMode.EXTRA_ONLY:
                if item['in_dir1'] and not item['in_dir2']:
                    self.filtered_results.append(item)
            elif mode == CompareMode.MISSING_ONLY:
                if not item['in_dir1'] and item['in_dir2']:
                    self.filtered_results.append(item)
                    
        self.display_results()
        
    def display_results(self):
        """显示结果"""
        self.result_tree.clear()
        
        if not self.filtered_results:
            item = QTreeWidgetItem(["没有找到匹配的项目"])
            self.result_tree.addTopLevelItem(item)
            return
            
        # 根据显示模式显示
        display_mode = list(DisplayMode)[self.display_combo.currentIndex()]
        
        if display_mode == DisplayMode.GROUP:
            self.display_grouped()
        elif display_mode == DisplayMode.FLAT:
            self.display_flat()
        elif display_mode == DisplayMode.LIST:
            self.display_list() 
            
            
    def display_grouped(self):
        """分组显示"""
        # 显示树形控件
        self.result_tree.setVisible(True)
        
        # 如果列表控件存在，则隐藏它
        if hasattr(self, 'result_list') and self.result_list is not None:
            self.result_list.setVisible(False)
    
        # 恢复所有列的显示
        self.result_tree.setHeaderLabels([
            "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
            "修改时间(目录1)", "修改时间(目录2)"
        ])
        for i in range(7):
            self.result_tree.setColumnHidden(i, False)
        
        groups = {
            "共同文件": [],
            "仅在目录1中": [],
            "仅在目录2中": []
        }
        
        for item in self.filtered_results:
            if item['in_dir1'] and item['in_dir2']:
                groups["共同文件"].append(item)
            elif item['in_dir1'] and not item['in_dir2']:
                groups["仅在目录1中"].append(item)
            elif not item['in_dir1'] and item['in_dir2']:
                groups["仅在目录2中"].append(item)
                
        for group_name, items in groups.items():
            if not items:
                continue
                
            group_item = QTreeWidgetItem([group_name, f"({len(items)}个项目)"])
            group_item.setExpanded(True)
            
            # 设置组标题颜色
            if group_name == "共同文件":
                group_item.setBackground(0, COLOR_EXIST)
            elif group_name == "仅在目录1中":
                group_item.setBackground(0, COLOR_EXTRA)
            elif group_name == "仅在目录2中":
                group_item.setBackground(0, COLOR_MISSING)
                
            self.result_tree.addTopLevelItem(group_item)
            
            for item in items:
                self.add_tree_item(group_item, item, DisplayMode.FLAT)
                
    def display_flat(self):
        """平铺显示 - 显示所有详细信息"""
        # 显示树形控件
        self.result_tree.setVisible(True)
        
        # 如果列表控件存在，则隐藏它
        if hasattr(self, 'result_list') and self.result_list is not None:
            self.result_list.setVisible(False)

        # 恢复所有列的显示
        self.result_tree.setHeaderLabels([
            "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
            "修改时间(目录1)", "修改时间(目录2)"
        ])
        for i in range(7):
            self.result_tree.setColumnHidden(i, False)
        
        for item in self.filtered_results:
            tree_item = QTreeWidgetItem([
                item['name'],
                item['rel_path'],
                self.get_status_text(item),
                self.format_size(item['size1']),
                self.format_size(item['size2']),
                self.format_time(item['time1']),
                self.format_time(item['time2'])
            ])
            
            # 设置颜色 - 所有列都上色
            if item['in_dir1'] and item['in_dir2']:
                for i in range(7):
                    tree_item.setBackground(i, COLOR_EXIST)
            elif item['in_dir1'] and not item['in_dir2']:
                for i in range(7):
                    tree_item.setBackground(i, COLOR_EXTRA)
            elif not item['in_dir1'] and item['in_dir2']:
                for i in range(7):
                    tree_item.setBackground(i, COLOR_MISSING)
            
            self.result_tree.addTopLevelItem(tree_item)
            
    def add_tree_item(self, parent, item, mode=DisplayMode.FLAT):
        """添加树项目，支持不同的显示模式"""
        if mode == DisplayMode.LIST:
            # 列表模式只显示基本列
            tree_item = QTreeWidgetItem([
                item['name'],
                item['rel_path'],
                self.get_status_text(item)
            ])
            col_count = 3
        else:
            # 平铺模式显示所有列
            tree_item = QTreeWidgetItem([
                item['name'],
                item['rel_path'],
                self.get_status_text(item),
                self.format_size(item['size1']),
                self.format_size(item['size2']),
                self.format_time(item['time1']),
                self.format_time(item['time2'])
            ])
            col_count = 7
        
        # 设置颜色
        if item['in_dir1'] and item['in_dir2']:
            for i in range(col_count):
                tree_item.setBackground(i, COLOR_EXIST)
        elif item['in_dir1'] and not item['in_dir2']:
            for i in range(col_count):
                tree_item.setBackground(i, COLOR_EXTRA)
        elif not item['in_dir1'] and item['in_dir2']:
            for i in range(col_count):
                tree_item.setBackground(i, COLOR_MISSING)
        
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(tree_item)
        else:
            parent.addChild(tree_item)
            
    def get_status_text(self, item) -> str:
        """获取状态文本"""
        if item['in_dir1'] and item['in_dir2']:
            return "共同存在"
        elif item['in_dir1'] and not item['in_dir2']:
            return "仅在目录1"
        elif not item['in_dir1'] and item['in_dir2']:
            return "仅在目录2"
        return "未知"
        
    def format_size(self, size: int) -> str:
        """格式化大小"""
        if size == 0:
            return "-"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def format_time(self, timestamp: float) -> str:
        """格式化时间"""
        if timestamp == 0:
            return "-"
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "-"
            
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        
        # 获取当前选中项
        item = self.result_tree.currentItem()
        if not item:
            return
            
        # 添加菜单项
        open_action = menu.addAction("打开文件位置")
        copy_path_action = menu.addAction("复制路径")
        copy_name_action = menu.addAction("复制文件名")
        menu.addSeparator()
        compare_action = menu.addAction("比较内容")
        menu.addSeparator()
        refresh_action = menu.addAction("刷新")
        
        # 显示菜单
        action = menu.exec_(self.result_tree.viewport().mapToGlobal(position))
        
        if action == open_action:
            self.open_file_location(item)
        elif action == copy_path_action:
            self.copy_path(item)
        elif action == copy_name_action:
            self.copy_name(item)
            
    def open_file_location(self, item):
        """打开文件位置"""
        path = item.text(1)  # 路径列
        if path and path != "路径":
            dir1 = self.dir1_edit.text()
            dir2 = self.dir2_edit.text()
            full_path = os.path.join(dir1, path) if os.path.exists(os.path.join(dir1, path)) else os.path.join(dir2, path)
            if os.path.exists(full_path):
                os.startfile(os.path.dirname(full_path))
                
    def copy_path(self, item):
        """复制路径"""
        path = item.text(1)
        if path and path != "路径":
            clipboard = QApplication.clipboard()
            clipboard.setText(path)
            
    def copy_name(self, item):
        """复制文件名"""
        name = item.text(0)
        if name and name != "文件名":
            clipboard = QApplication.clipboard()
            clipboard.setText(name)
            
    def update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        
    def on_error(self, error_msg: str):
        """错误处理"""
        QMessageBox.critical(self, "错误", error_msg)
        self.reset_ui_state()
        
    def reset_ui_state(self):
        """重置UI状态"""
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.progress_bar.setVisible(False)
        
    def load_settings(self):
        """加载设置"""
        # 加载历史记录
        self.history = self.settings.value("history", [])
        if not isinstance(self.history, list):
            self.history = []
            
        # 加载上次的目录
        self.dir1_edit.setText(self.settings.value("last_dir1", ""))
        self.dir2_edit.setText(self.settings.value("last_dir2", ""))
        
        # 加载显示选项
        mode_index = self.settings.value("mode_index", 0, type=int)
        self.mode_combo.setCurrentIndex(mode_index)
        
        display_index = self.settings.value("display_index", 0, type=int)
        self.display_combo.setCurrentIndex(display_index)
        
        # 加载窗口位置
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
    def save_settings(self):
        """保存设置"""
        self.settings.setValue("history", self.history)
        self.settings.setValue("last_dir1", self.dir1_edit.text())
        self.settings.setValue("last_dir2", self.dir2_edit.text())
        self.settings.setValue("mode_index", self.mode_combo.currentIndex())
        self.settings.setValue("display_index", self.display_combo.currentIndex())
        self.settings.setValue("geometry", self.saveGeometry())
        
    def closeEvent(self, event):
        """关闭事件"""
        self.save_settings()
        self.stop_comparison()
        event.accept()

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()

    def show_help(self):
        """显示帮助对话框"""
        dialog = HelpDialog(self)
        dialog.exec()

    def show_history(self):
        """显示历史记录对话框"""
        if not self.history:
            QMessageBox.information(self, "提示", "暂无历史记录")
            return
            
        dialog = HistoryDialog(self)
        dialog.set_history(self.history)
        
        if dialog.exec() == QDialog.Accepted:
            selected = dialog.get_selected()
            if selected:
                # 可以选择将选中的历史记录填充到目录输入框
                reply = QMessageBox.question(
                    self, 
                    "选择目录",
                    f"要将历史记录应用到哪个目录？",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.dir1_edit.setText(selected)
                elif reply == QMessageBox.No:
                    self.dir2_edit.setText(selected)

    def clear_directories(self):
        """清空目录输入框"""
        reply = QMessageBox.question(
            self, 
            "确认清空",
            "确定要清空两个目录的输入框吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.dir1_edit.clear()
            self.dir2_edit.clear()
            self.result_tree.clear()
            if hasattr(self, 'result_list') and self.result_list:
                self.result_list.clear()
            self.current_results = []
            self.filtered_results = []
            self.status_label.setText("已清空")

    def swap_directories(self):
        """交换两个目录"""
        dir1 = self.dir1_edit.text()
        dir2 = self.dir2_edit.text()
        self.dir1_edit.setText(dir2)
        self.dir2_edit.setText(dir1)
        
        # 如果当前有结果显示，可以选择重新比较
        if self.current_results and dir1 and dir2:
            reply = QMessageBox.question(
                self,
                "重新比较",
                "目录已交换，是否重新比较？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.start_comparison()

    def change_display_mode(self, mode):
        """更改显示模式"""
        self.display_combo.setCurrentText(mode.value)
        
    def change_filter_mode(self, mode):
        """更改过滤模式"""
        self.mode_combo.setCurrentText(mode.value)
        
    def toggle_toolbar(self, checked):
        """切换工具栏显示"""
        for child in self.findChildren(QToolBar):
            child.setVisible(checked)
            
    def toggle_statusbar(self, checked):
        """切换状态栏显示"""
        self.status_bar.setVisible(checked)

    def display_list(self):
        """列表显示 - 类似资源管理器，根据窗口宽度自动调整列数"""
        # 隐藏树形控件，显示列表控件
        self.result_tree.setVisible(False)
        
        # 如果列表控件不存在，创建它
        if not hasattr(self, 'result_list') or self.result_list is None:
            self.result_list = QListWidget()
            self.result_list.setViewMode(QListWidget.IconMode)  # 图标模式允许自动换行
            self.result_list.setFlow(QListWidget.LeftToRight)   # 从左到右排列
            self.result_list.setWrapping(True)                  # 自动换行
            self.result_list.setResizeMode(QListWidget.Adjust)  # 调整大小时自动重新排列
            self.result_list.setSpacing(5)                       # 设置间距
            
            # 设置统一的项目大小
            self.result_list.setGridSize(QSize(150, 30))         # 设置网格大小
            
            # 设置选择模式
            self.result_list.setSelectionMode(QListWidget.ExtendedSelection)
            
            # 启用右键菜单
            self.result_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.result_list.customContextMenuRequested.connect(self.show_list_context_menu)
            
            # 将列表控件添加到布局中（放在树形控件的位置）
            layout = self.centralWidget().layout()
            index = layout.indexOf(self.result_tree)
            layout.insertWidget(index, self.result_list)
        
        # 清空列表
        self.result_list.clear()
        
        for item in self.filtered_results:
            list_item = QListWidgetItem(item['name'])
            
            # 设置背景色
            if item['in_dir1'] and item['in_dir2']:
                list_item.setBackground(COLOR_EXIST)
            elif item['in_dir1'] and not item['in_dir2']:
                list_item.setBackground(COLOR_EXTRA)
            elif not item['in_dir1'] and item['in_dir2']:
                list_item.setBackground(COLOR_MISSING)
            
            # 存储完整数据供右键菜单使用
            list_item.setData(Qt.UserRole, item)
            
            # 设置文本对齐方式
            list_item.setTextAlignment(Qt.AlignCenter)
            
            self.result_list.addItem(list_item)
        
        # 显示列表控件，隐藏树形控件
        self.result_list.setVisible(True)
        self.result_tree.setVisible(False)

    def get_current_display_mode(self) -> DisplayMode:
        """获取当前显示模式"""
        return list(DisplayMode)[self.display_combo.currentIndex()]
    
    def show_list_context_menu(self, position):
        """显示列表控件的右键菜单"""
        menu = QMenu()
        
        # 获取当前选中项
        item = self.result_list.currentItem()
        if not item:
            return
        
        # 获取存储的完整数据
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        # 添加菜单项
        open_action = menu.addAction("打开文件位置")
        copy_path_action = menu.addAction("复制路径")
        copy_name_action = menu.addAction("复制文件名")
        menu.addSeparator()
        compare_action = menu.addAction("比较内容")
        menu.addSeparator()
        refresh_action = menu.addAction("刷新")
        
        # 显示菜单
        action = menu.exec_(self.result_list.viewport().mapToGlobal(position))
        
        if action == open_action:
            self.open_list_file_location(data)
        elif action == copy_path_action:
            self.copy_list_path(data)
        elif action == copy_name_action:
            self.copy_list_name(data)

    def open_list_file_location(self, data):
        """打开列表项的文件位置"""
        if data and 'rel_path' in data:
            dir1 = self.dir1_edit.text()
            dir2 = self.dir2_edit.text()
            full_path = os.path.join(dir1, data['rel_path']) if os.path.exists(os.path.join(dir1, data['rel_path'])) else os.path.join(dir2, data['rel_path'])
            if os.path.exists(full_path):
                os.startfile(os.path.dirname(full_path))

    def copy_list_path(self, data):
        """复制列表项的路径"""
        if data and 'rel_path' in data:
            clipboard = QApplication.clipboard()
            clipboard.setText(data['rel_path'])

    def copy_list_name(self, data):
        """复制列表项的文件名"""
        if data and 'name' in data:
            clipboard = QApplication.clipboard()
            clipboard.setText(data['name'])





def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置中文字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = DirCompareTool()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()