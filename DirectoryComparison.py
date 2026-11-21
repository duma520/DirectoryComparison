import sys
import os
import json
import hashlib
import zlib
import shutil
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
COLOR_MD5_MATCH = QColor('#A8E6CF')   # 翠绿 - MD5匹配
COLOR_MD5_MISMATCH = QColor('#FFD3B6') # 杏色 - MD5不匹配


class CompareAlgorithm(Enum):
    """比对算法"""
    BASIC = "基础比对(文件名/大小/时间)"
    MD5 = "MD5指纹比对(更精确)"
    SHA1 = "SHA1指纹比对"
    SHA256 = "SHA256指纹比对"
    CRC32 = "CRC32校验比对"


class CompareMode(Enum):
    """比较模式"""
    ALL = "全部文件"
    COMMON_ONLY = "只显示共同存在"
    DIFF_ONLY = "只显示差异"
    EXTRA_ONLY = "只显示多出的文件"
    MISSING_ONLY = "只显示缺少的文件"
    MD5_DIFF_ONLY = "只显示MD5差异"  # 新增：显示MD5不同的共同文件


class DisplayMode(Enum):
    """显示模式"""
    GROUP = "分组显示"
    FLAT = "平铺显示"
    LIST = "列表显示"


class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    VERSION = "6.1"
    BUILD_DATE = "2026-08-20"
    AUTHOR = "杜玛"
    LICENSE = "GNU Affero General Public License v3.0"
    COPYRIGHT = "© 2026 杜玛。永久保留所有权利。"
    URL = "https://github.com/duma520"
    MAINTAINER_EMAIL = "duma520@example.com"
    NAME = "多目录文件比对工具"
    DESCRIPTION = """多目录文件比对工具 - 高效、精准的目录比较解决方案

主要功能：
• 快速扫描和比较两个目录的内容差异
• 支持子目录递归比较
• 多种显示模式：分组显示、平铺显示、列表显示
• 灵活的过滤选项：共同存在、差异、多出、缺少、MD5差异
• 文件大小和修改时间对比
• 多种哈希校验：MD5 / SHA1 / SHA256 / CRC32
• 一键同步功能（复制缺失/更新差异/删除多余）
• 比较报告导出（HTML / CSV / TXT）
• 文件内容对比查看（文本/十六进制）
• 统计信息面板（各分组数量与大小）
• 设置实时自动保存（下次启动沿用上次设置）
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
        "5.1.1": "优化性能和修复已知问题",
        "5.2.0": "新增MD5指纹比对功能",
        "5.2.1": "新增'只显示MD5差异'过滤选项",
        "6.0.0": "大版本升级：一键同步、报告导出、SHA1/SHA256/CRC32多哈希、文件内容对比、统计面板",
        "6.1.0": "设置实时自动保存（控件变更即自动持久化、窗口最大化状态恢复）；维护约定落地（软件升级迭代记录.md + version 备份）"
    }
    
    HELP_TEXT = """<h2>多目录文件比对工具 - 使用指南</h2>

<h3>基本操作步骤：</h3>
<ol>
    <li><b>选择目录</b>：点击"浏览"按钮或直接粘贴路径到输入框</li>
    <li><b>选择比对算法</b>：基础比对 或 MD5/SHA1/SHA256/CRC32 哈希比对</li>
    <li><b>开始比较</b>：点击工具栏的"开始比较"按钮或按F5键</li>
    <li><b>查看结果</b>：比较完成后，结果会以彩色方式显示</li>
    <li><b>过滤结果</b>：使用"比较模式"下拉框筛选显示内容</li>
</ol>

<h3>比对模式说明：</h3>
<ul>
    <li><b>基础比对</b>：基于文件名、文件大小和修改时间进行比对，速度快</li>
    <li><b>MD5/SHA1/SHA256/CRC32 哈希比对</b>：基于文件内容的哈希值进行比对，更精确但速度较慢。CRC32 速度最快，SHA256 安全性最高</li>
</ul>

<h3>颜色标识：</h3>
<ul>
    <li><span style='background-color: #B5EAD7'>薄荷绿</span> - 两个目录都存在的文件（基础比对）</li>
    <li><span style='background-color: #FFDAC1'>蜜桃橙</span> - 目录2中缺少的文件</li>
    <li><span style='background-color: #FFB7CE'>樱花粉</span> - 目录1中多出的文件</li>
    <li><span style='background-color: #A8E6CF'>翠绿</span> - 哈希匹配的文件</li>
    <li><span style='background-color: #FFD3B6'>杏色</span> - 哈希不匹配的文件</li>
</ul>

<h3>比较模式说明：</h3>
<ul>
    <li><b>全部文件</b> - 显示所有文件和目录</li>
    <li><b>只显示共同存在</b> - 仅显示两个目录都有的项目</li>
    <li><b>只显示差异</b> - 仅显示存在差异的项目（包括一边有另一边没有，以及哈希不匹配的情况）</li>
    <li><b>只显示多出的文件</b> - 仅显示目录1有而目录2没有的项目</li>
    <li><b>只显示缺少的文件</b> - 仅显示目录2有而目录1没有的项目</li>
    <li><b>只显示MD5差异</b> - 仅显示两个目录都存在但哈希值不同的文件（需配合哈希比对模式）</li>
</ul>

<h3>显示模式：</h3>
<ul>
    <li><b>分组显示</b> - 按状态分组显示（推荐）</li>
    <li><b>平铺显示</b> - 所有项目平铺显示</li>
    <li><b>列表显示</b> - 简洁列表形式</li>
</ul>

<h3>一键同步（v6.0 新增）：</h3>
<ul>
    <li>比较完成后，点击工具栏的<b>"同步"</b>按钮打开同步对话框</li>
    <li>选择<b>源目录</b>（目录1→目录2 或 目录2→目录1）</li>
    <li>可勾选：复制缺失文件、覆盖内容不同文件、删除目标目录多余文件（危险操作）</li>
    <li>同步过程实时显示进度，完成后展示操作统计</li>
</ul>

<h3>报告导出（v6.0 新增）：</h3>
<ul>
    <li>点击工具栏的<b>"导出"</b>按钮，可将比较结果导出为 <b>HTML 报告 / CSV / 文本</b></li>
    <li>HTML 报告带彩色标识，适合归档和分享</li>
</ul>

<h3>文件内容对比（v6.0 新增）：</h3>
<ul>
    <li>右键点击共同存在的文件，选择<b>"比较内容"</b>可查看两侧文件差异</li>
    <li>支持 <b>文本视图</b> 与 <b>十六进制视图</b> 两种显示方式</li>
</ul>

<h3>右键菜单功能：</h3>
<ul>
    <li><b>打开文件位置</b> - 在资源管理器中打开文件所在目录</li>
    <li><b>复制路径</b> - 复制文件的相对路径到剪贴板</li>
    <li><b>复制文件名</b> - 复制文件名到剪贴板</li>
    <li><b>计算哈希值</b> - 计算选中文件的哈希值（哈希模式下可用）</li>
    <li><b>比较内容</b> - 查看两个目录中该文件的内容差异</li>
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
    <li>哈希比对适用于需要精确确认文件内容是否一致的场景</li>
    <li>"只显示MD5差异"模式可以快速找出内容不同但文件名相同的文件</li>
    <li>历史记录会自动保存最近使用的20个目录</li>
</ul>

<h3>注意事项：</h3>
<ul>
    <li>哈希比对会读取所有文件内容，大文件时速度较慢</li>
    <li>比较大量文件时请耐心等待，可使用"停止"按钮取消操作</li>
    <li>目录权限不足可能导致某些文件无法访问</li>
    <li>"只显示MD5差异"模式只在哈希比对模式下有效</li>
    <li>「删除目标目录中多余的文件」为危险操作，同步前请确认备份</li>
</ul>
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
                "MD5指纹比对功能",
                "SHA1/SHA256/CRC32多哈希",
                "只显示MD5差异过滤",
                "一键同步目录",
                "导出HTML/CSV/TXT报告",
                "文件内容对比查看",
                "统计信息面板",
                "设置实时自动保存",
                "彩色标识文件状态",
                "历史记录功能",
                "拖拽支持",
                "右键菜单快速操作",
                "多线程扫描不卡顿"
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
        guide_text.setOpenExternalLinks(True)
        guide_text.setHtml(ProjectInfo.HELP_TEXT)
        guide_layout.addWidget(guide_text)
        
        tab_widget.addTab(guide_widget, "使用指南")
        
        # 快捷键标签页
        shortcut_widget = QWidget()
        shortcut_layout = QVBoxLayout(shortcut_widget)
        
        shortcut_text = QTextBrowser()
        shortcut_text.setOpenExternalLinks(True)
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
        about_text.setOpenExternalLinks(True)
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


class FileInfo:
    """文件信息类"""
    def __init__(self, path: str, rel_path: str, hash_type: str = "MD5"):
        self.path = path
        self.rel_path = rel_path
        self.name = os.path.basename(path)
        self.is_dir = os.path.isdir(path)
        self.size = 0
        self.mod_time = 0
        self.md5 = None  # 哈希值（MD5/SHA1/SHA256/CRC32）
        self.hash_type = hash_type
        self.exists = os.path.exists(path)
        
        if self.exists and not self.is_dir:
            try:
                self.size = os.path.getsize(path)
                self.mod_time = os.path.getmtime(path)
            except:
                pass
    
    def calculate_md5(self, progress_callback=None) -> Optional[str]:
        """计算文件的MD5值（兼容旧调用）"""
        return self.calculate_hash(progress_callback)
    
    def calculate_hash(self, progress_callback=None) -> Optional[str]:
        """计算文件的哈希值（MD5/SHA1/SHA256/CRC32）"""
        if self.is_dir or not self.exists:
            return None
        
        try:
            if self.hash_type == "CRC32":
                crc = 0
                with open(self.path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        crc = zlib.crc32(chunk, crc)
                        if progress_callback:
                            progress_callback()
                self.md5 = format(crc & 0xFFFFFFFF, '08x')
                return self.md5
            
            hash_obj = {
                "MD5": hashlib.md5,
                "SHA1": hashlib.sha1,
                "SHA256": hashlib.sha256,
            }.get(self.hash_type, hashlib.md5)()
            with open(self.path, "rb") as f:
                # 分块读取，避免大文件内存问题
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
                    if progress_callback:
                        progress_callback()
            self.md5 = hash_obj.hexdigest()
            return self.md5
        except Exception as e:
            print(f"计算{self.hash_type}失败 {self.path}: {e}")
            return None


class ScanThread(QThread):
    """扫描线程"""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, dir1: str, dir2: str, use_md5: bool = False, hash_type: str = "MD5"):
        super().__init__()
        self.dir1 = dir1
        self.dir2 = dir2
        self.use_md5 = use_md5
        self.hash_type = hash_type if hash_type else "MD5"
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
            
            if self.is_cancelled:
                return
            
            # 扫描第二个目录
            if self.dir2:
                self.progress.emit(50, f"正在扫描目录2: {self.dir2}")
                files2 = self.scan_directory(self.dir2)
                result['files2'] = files2
            
            # 如果需要MD5比对，计算所有文件的哈希值
            if self.use_md5 and not self.is_cancelled:
                self.progress.emit(60, f"正在计算{self.hash_type}值(目录1)...")
                self.calculate_all_md5(result['files1'], "目录1")
                
                if self.is_cancelled:
                    return
                    
                self.progress.emit(80, f"正在计算{self.hash_type}值(目录2)...")
                self.calculate_all_md5(result['files2'], "目录2")
            
            self.progress.emit(100, "扫描完成")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def calculate_all_md5(self, files_dict: Dict[str, FileInfo], dir_name: str):
        """计算所有文件的哈希值"""
        files = [f for f in files_dict.values() if not f.is_dir]
        total = len(files)
        processed = 0
        
        for file_info in files:
            if self.is_cancelled:
                break
            
            file_info.calculate_hash()
            processed += 1
            
            if processed % 10 == 0:
                progress = 60 + int(processed * 20 / total) if dir_name == "目录1" else 80 + int(processed * 20 / total)
                self.progress.emit(progress, f"正在计算{dir_name}{self.hash_type}: {processed}/{total}")
    
    def scan_directory(self, root_path: str) -> Dict[str, FileInfo]:
        """扫描目录"""
        result = {}
        try:
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
                        result[rel_path] = FileInfo(full_path, rel_path, self.hash_type)
                    except Exception as e:
                        print(f"处理目录出错: {e}")
                        
                # 处理文件
                for file_name in files:
                    try:
                        full_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(full_path, root_path)
                        result[rel_path] = FileInfo(full_path, rel_path, self.hash_type)
                    except Exception as e:
                        print(f"处理文件出错: {e}")
                        
        except Exception as e:
            print(f"扫描目录出错: {e}")
            
        return result


class CompareThread(QThread):
    """比较线程"""
    progress = Signal(int, str)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, files1: Dict, files2: Dict, use_md5: bool = False, hash_type: str = "MD5"):
        super().__init__()
        self.files1 = files1
        self.files2 = files2
        self.use_md5 = use_md5
        self.hash_type = hash_type if hash_type else "MD5"
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
                
                # 判断文件是否相同
                is_same = self.is_same_file(file1, file2)
                
                item = {
                    'rel_path': rel_path,
                    'name': os.path.basename(rel_path),
                    'in_dir1': file1 is not None,
                    'in_dir2': file2 is not None,
                    'is_dir': file1.is_dir if file1 else (file2.is_dir if file2 else False),
                    'size1': file1.size if file1 else 0,
                    'size2': file2.size if file2 else 0,
                    'time1': file1.mod_time if file1 else 0,
                    'time2': file2.mod_time if file2 else 0,
                    'is_same': is_same,  # 新增：是否相同
                    'md5_1': file1.md5 if file1 and file1.md5 else None,
                    'md5_2': file2.md5 if file2 and file2.md5 else None
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
    
    def is_same_file(self, file1: Optional[FileInfo], file2: Optional[FileInfo]) -> bool:
        """判断两个文件是否相同"""
        if file1 is None or file2 is None:
            return False
        
        # 如果是目录，只比较名称
        if file1.is_dir or file2.is_dir:
            return file1.name == file2.name
        
        # 如果使用MD5比对
        if self.use_md5:
            if file1.md5 is not None and file2.md5 is not None:
                return file1.md5 == file2.md5
            else:
                # 如果MD5计算失败，回退到基础比对
                return file1.size == file2.size and file1.mod_time == file2.mod_time
        
        # 基础比对：大小和修改时间
        return file1.size == file2.size and file1.mod_time == file2.mod_time


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


class SyncThread(QThread):
    """同步线程"""
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, src_dir: str, dst_dir: str, results: list,
                 reverse: bool = False, copy_missing: bool = True,
                 copy_diff: bool = True, delete_extra: bool = False):
        super().__init__()
        self.src_dir = src_dir
        self.dst_dir = dst_dir
        self.results = results
        self.reverse = reverse
        self.copy_missing = copy_missing
        self.copy_diff = copy_diff
        self.delete_extra = delete_extra
        self.is_cancelled = False
        self.mutex = QMutex()

    def cancel(self):
        self.mutex.lock()
        self.is_cancelled = True
        self.mutex.unlock()

    def run(self):
        try:
            summary = {'copied': 0, 'updated': 0, 'deleted': 0, 'failed': 0, 'failed_list': []}
            if self.reverse:
                src_flag, dst_flag = 'in_dir2', 'in_dir1'
            else:
                src_flag, dst_flag = 'in_dir1', 'in_dir2'

            total = len(self.results)
            processed = 0

            for item in self.results:
                self.mutex.lock()
                if self.is_cancelled:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()

                rel = item.get('rel_path', '')
                src_exists = item.get(src_flag, False)
                dst_exists = item.get(dst_flag, False)
                is_same = item.get('is_same', True)
                is_dir = item.get('is_dir', False)

                src_path = os.path.join(self.src_dir, rel)
                dst_path = os.path.join(self.dst_dir, rel)

                try:
                    if src_exists and not dst_exists:
                        if self.copy_missing:
                            self._copy(src_path, dst_path, is_dir)
                            summary['copied'] += 1
                    elif src_exists and dst_exists and not is_same:
                        if self.copy_diff:
                            self._copy(src_path, dst_path, is_dir)
                            summary['updated'] += 1
                    elif not src_exists and dst_exists:
                        if self.delete_extra:
                            self._delete(dst_path, is_dir)
                            summary['deleted'] += 1
                except Exception as e:
                    summary['failed'] += 1
                    summary['failed_list'].append((rel, str(e)))

                processed += 1
                if processed % 20 == 0:
                    self.progress.emit(
                        int(processed * 100 / total) if total else 100,
                        f"正在同步: {processed}/{total}"
                    )

            self.progress.emit(100, "同步完成")
            self.finished.emit(summary)

        except Exception as e:
            self.error.emit(str(e))

    def _copy(self, src_path: str, dst_path: str, is_dir: bool):
        """复制文件或创建目录"""
        if is_dir:
            if not os.path.exists(dst_path):
                os.makedirs(dst_path, exist_ok=True)
            return
        dst_dir = os.path.dirname(dst_path)
        if dst_dir and not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)
        if os.path.exists(src_path) and os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)

    def _delete(self, dst_path: str, is_dir: bool):
        """删除文件或目录"""
        if not os.path.exists(dst_path):
            return
        if is_dir:
            shutil.rmtree(dst_path, ignore_errors=True)
        else:
            os.remove(dst_path)


class SyncDialog(QDialog):
    """一键同步对话框"""
    def __init__(self, parent, dir1: str, dir2: str, results: list):
        super().__init__(parent)
        self.setWindowTitle("一键同步")
        self.setMinimumSize(560, 360)
        self.dir1 = dir1
        self.dir2 = dir2
        self.results = results
        self.sync_thread = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 同步方向
        dir_group = QGroupBox("同步方向")
        gl = QHBoxLayout(dir_group)
        gl.addWidget(QLabel("源目录:"))
        self.src_combo = QComboBox()
        self.src_combo.addItem(f"目录1: {self.dir1}")
        self.src_combo.addItem(f"目录2: {self.dir2}")
        gl.addWidget(self.src_combo, 1)
        layout.addWidget(dir_group)

        # 同步选项
        opt_group = QGroupBox("同步选项")
        ol = QVBoxLayout(opt_group)
        self.copy_missing_check = QCheckBox("复制源目录中有、目标目录中缺失的文件")
        self.copy_missing_check.setChecked(True)
        self.copy_diff_check = QCheckBox("覆盖内容不同的文件（大小/时间/哈希不同）")
        self.copy_diff_check.setChecked(True)
        self.delete_extra_check = QCheckBox("删除目标目录中多余的文件（⚠ 危险操作，请谨慎）")
        self.delete_extra_check.setChecked(False)
        ol.addWidget(self.copy_missing_check)
        ol.addWidget(self.copy_diff_check)
        ol.addWidget(self.delete_extra_check)
        layout.addWidget(opt_group)

        # 进度与状态
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.start_btn = QPushButton("开始同步")
        self.start_btn.setMinimumWidth(120)
        self.start_btn.clicked.connect(self.start_sync)
        self.close_btn = QPushButton("关闭")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def start_sync(self):
        if self.sync_thread and self.sync_thread.isRunning():
            self.sync_thread.cancel()
            self.start_btn.setText("开始同步")
            return

        reverse = self.src_combo.currentIndex() == 1
        if reverse:
            src, dst = self.dir2, self.dir1
        else:
            src, dst = self.dir1, self.dir2

        self.sync_thread = SyncThread(
            src, dst, self.results, reverse=reverse,
            copy_missing=self.copy_missing_check.isChecked(),
            copy_diff=self.copy_diff_check.isChecked(),
            delete_extra=self.delete_extra_check.isChecked(),
        )
        self.sync_thread.progress.connect(self._on_sync_progress)
        self.sync_thread.finished.connect(self._on_sync_finished)
        self.sync_thread.error.connect(self._on_sync_error)
        self.start_btn.setText("取消同步")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在同步...")
        self.sync_thread.start()

    def _on_sync_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def _on_sync_finished(self, summary: dict):
        self.start_btn.setText("开始同步")
        copied = summary.get('copied', 0)
        updated = summary.get('updated', 0)
        deleted = summary.get('deleted', 0)
        failed = summary.get('failed', 0)
        self.status_label.setText(
            f"同步完成: 复制 {copied} 个, 覆盖更新 {updated} 个, 删除 {deleted} 个, 失败 {failed} 个"
        )
        msg = (f"同步完成！\n\n"
               f"复制缺失文件: {copied} 个\n"
               f"覆盖更新文件: {updated} 个\n"
               f"删除多余文件: {deleted} 个\n"
               f"失败: {failed} 个")
        if failed and summary.get('failed_list'):
            msg += "\n\n失败明细:\n" + "\n".join(f"  {r}: {e}" for r, e in summary['failed_list'][:10])
        QMessageBox.information(self, "同步完成", msg)

    def _on_sync_error(self, error_msg: str):
        self.start_btn.setText("开始同步")
        self.status_label.setText("同步失败")
        QMessageBox.critical(self, "同步失败", error_msg)

    def closeEvent(self, event):
        if self.sync_thread and self.sync_thread.isRunning():
            self.sync_thread.cancel()
            self.sync_thread.wait()
        event.accept()


class FileCompareDialog(QDialog):
    """文件内容对比对话框"""
    def __init__(self, path1: str, path2: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件内容对比")
        self.resize(900, 600)
        self.path1 = path1
        self.path2 = path2
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # 文件信息
        info1 = QLabel(f"左侧: {os.path.basename(self.path1)}\n{self.path1}")
        info1.setStyleSheet("color: #2c3e50; padding: 4px; background: #f8f9fa; border-radius: 4px;")
        info2 = QLabel(f"右侧: {os.path.basename(self.path2)}\n{self.path2}")
        info2.setStyleSheet("color: #2c3e50; padding: 4px; background: #f8f9fa; border-radius: 4px;")

        top = QHBoxLayout()
        top.addWidget(info1)
        top.addWidget(info2)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        self.edit1 = QTextEdit()
        self.edit2 = QTextEdit()
        self.edit1.setReadOnly(True)
        self.edit2.setReadOnly(True)
        self.edit1.setLineWrapMode(QTextEdit.NoWrap)
        self.edit2.setLineWrapMode(QTextEdit.NoWrap)
        self.edit1.setFont(QFont("Consolas", 10))
        self.edit2.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.edit1)
        splitter.addWidget(self.edit2)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter, 1)

        # 视图切换
        view_layout = QHBoxLayout()
        view_layout.addStretch()
        self.view_combo = QComboBox()
        self.view_combo.addItem("文本视图")
        self.view_combo.addItem("十六进制视图")
        self.view_combo.currentIndexChanged.connect(self.load_content)
        view_layout.addWidget(QLabel("显示方式:"))
        view_layout.addWidget(self.view_combo)
        layout.addLayout(view_layout)

        self.load_content()

    def load_content(self):
        hex_mode = self.view_combo.currentIndex() == 1
        for edit, path in [(self.edit1, self.path1), (self.edit2, self.path2)]:
            try:
                with open(path, 'rb') as f:
                    raw = f.read()
                if hex_mode:
                    edit.setPlainText(self._to_hexdump(raw))
                else:
                    try:
                        text = raw.decode('utf-8')
                    except UnicodeDecodeError:
                        text = raw.decode('gbk', errors='replace')
                    if b'\x00' in raw[:8192]:
                        text = f"[检测到二进制内容，建议使用十六进制视图查看]\n\n{text}"
                    edit.setPlainText(text)
            except Exception as e:
                edit.setPlainText(f"无法读取文件: {e}")

    @staticmethod
    def _to_hexdump(data: bytes, width: int = 16) -> str:
        """将字节数据转换为十六进制视图"""
        lines = []
        for i in range(0, len(data), width):
            chunk = data[i:i + width]
            hex_part = ' '.join(f"{b:02X}" for b in chunk)
            hex_part = hex_part.ljust(width * 3 - 1)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{i:08X}  {hex_part}  {ascii_part}")
        return '\n'.join(lines)


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
        self.compare_algorithm = CompareAlgorithm.BASIC
        self.history = []
        self.result_list = None 
        self._start_maximized = False
        # 设置实时自动保存（★ v6.1）：500ms 防抖单次定时器，控件变更后防抖写盘
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(500)
        self._settings_save_timer.timeout.connect(self.save_settings)
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
        
        # 创建比对模式选择区域
        self.create_algorithm_selection(main_layout)
        
        # 创建过滤和显示选项
        self.create_filter_options(main_layout)
        
        # 创建结果显示区域
        self.create_result_display(main_layout)
        
        # 创建进度条和状态栏
        self.create_progress_and_status(main_layout)

    def create_algorithm_selection(self, parent_layout):
        """创建比对模式选择区域"""
        group = QGroupBox("比对模式")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(10, 5, 10, 5)
        
        layout.addWidget(QLabel("比对算法:"))
        self.algorithm_combo = QComboBox()
        for algo in CompareAlgorithm:
            self.algorithm_combo.addItem(algo.value, algo)
        self.algorithm_combo.setCurrentIndex(0)
        layout.addWidget(self.algorithm_combo)
        
        layout.addStretch()
        
        # 添加提示标签
        hint_label = QLabel("💡 哈希比对会读取文件内容，大文件时速度较慢")
        hint_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(hint_label)
        
        parent_layout.addWidget(group)

    def get_algorithm(self) -> CompareAlgorithm:
        """获取当前选中的比对算法"""
        data = self.algorithm_combo.currentData()
        return data if data else CompareAlgorithm.BASIC

    def get_hash_type(self) -> Optional[str]:
        """获取当前哈希算法名称，基础比对返回 None"""
        algo = self.get_algorithm()
        if algo == CompareAlgorithm.BASIC:
            return None
        return algo.name  # MD5 / SHA1 / SHA256 / CRC32

    def use_hash(self) -> bool:
        """是否使用哈希比对"""
        return self.get_hash_type() is not None

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
        refresh_action.triggered.connect(self.start_comparison)
        
        # 历史记录
        history_action = QAction("历史记录", self)
        toolbar.addAction(history_action)
        history_action.triggered.connect(self.show_history)
        
        # 清空
        clear_action = QAction("清空", self)
        toolbar.addAction(clear_action)
        clear_action.triggered.connect(self.clear_directories)
        
        toolbar.addSeparator()
    
        # 添加帮助菜单
        help_action = QAction("帮助", self)
        help_action.setShortcut(QKeySequence("F1"))
        toolbar.addAction(help_action)
        help_action.triggered.connect(self.show_help)
        
        # 添加关于菜单
        about_action = QAction("关于", self)
        toolbar.addAction(about_action)
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
        # 统计信息面板
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(
            "color: #2c3e50; background: #ecf0f1; padding: 4px 8px; border-radius: 4px;"
        )
        parent_layout.addWidget(self.stats_label)
        
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels([
            "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
            "修改时间(目录1)", "修改时间(目录2)", "MD5(目录1)", "MD5(目录2)"
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
        
        # 比对算法切换时的提示
        self.algorithm_combo.currentIndexChanged.connect(self.on_algorithm_changed)
        
        # 设置实时自动保存（★ v6.1）：控件变更 → 防抖定时器 → save_settings
        self.dir1_edit.textChanged.connect(self._autosave_settings)
        self.dir2_edit.textChanged.connect(self._autosave_settings)
        self.mode_combo.currentIndexChanged.connect(self._autosave_settings)
        self.display_combo.currentIndexChanged.connect(self._autosave_settings)
        self.algorithm_combo.currentIndexChanged.connect(self._autosave_settings)
        
    def _autosave_settings(self):
        """触发防抖自动保存（★ v6.1）：500ms 内无操作才写盘"""
        self._settings_save_timer.start()
        
    def on_algorithm_changed(self, index):
        """比对算法改变时的处理"""
        algo = self.get_algorithm()
        is_hash = algo != CompareAlgorithm.BASIC
        
        if is_hash:
            # 检查当前过滤模式
            current_mode = list(CompareMode)[self.mode_combo.currentIndex()]
            if current_mode == CompareMode.MD5_DIFF_ONLY:
                QMessageBox.information(
                    self, 
                    "哈希比对模式",
                    f"{algo.value}会读取所有文件内容计算哈希值，\n"
                    "对于大文件或大量文件时可能会比较慢。\n"
                    "建议在需要精确比对文件内容时使用。\n\n"
                    "当前已选择'只显示MD5差异'过滤模式，切换后将显示哈希不同的文件。"
                )
            else:
                QMessageBox.information(
                    self, 
                    "哈希比对模式",
                    f"{algo.value}会读取所有文件内容计算哈希值，\n"
                    "对于大文件或大量文件时可能会比较慢。\n"
                    "建议在需要精确比对文件内容时使用。"
                )
        else:
            # 切换到基础比对
            current_mode = list(CompareMode)[self.mode_combo.currentIndex()]
            if current_mode == CompareMode.MD5_DIFF_ONLY:
                QMessageBox.information(
                    self,
                    "模式提示",
                    "您切换到了基础比对模式，但当前过滤模式为'只显示MD5差异'。\n"
                    "基础比对模式下，MD5差异过滤将不会显示任何结果。\n"
                    "如需查看MD5差异，请切换回哈希比对模式。"
                )
                self.filter_results()
        
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
            self._autosave_settings()
            
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
        
        # 获取比对算法
        use_md5 = self.use_hash()
        hash_type = self.get_hash_type() or "MD5"
            
        # 更新UI状态
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_tree.clear()
        if hasattr(self, 'result_list') and self.result_list:
            self.result_list.clear()
        
        # 启动扫描线程
        self.scan_thread = ScanThread(dir1, dir2, use_md5, hash_type)
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
        
        # 获取比对算法
        use_md5 = self.use_hash()
        hash_type = self.get_hash_type() or "MD5"
        
        # 启动比较线程
        self.compare_thread = CompareThread(
            result.get('files1', {}),
            result.get('files2', {}),
            use_md5,
            hash_type
        )
        self.compare_thread.progress.connect(self.update_progress)
        self.compare_thread.finished.connect(self.on_compare_finished)
        self.compare_thread.error.connect(self.on_error)
        self.compare_thread.start()
        
    def on_compare_finished(self, results):
        """比较完成"""
        self.compare_thread = None
        self.current_results = results
        hash_type = self.get_hash_type()
        
        # 统计哈希比对结果
        if hash_type:
            same_count = sum(1 for r in results if r.get('is_same', False))
            diff_count = sum(1 for r in results if r.get('in_dir1') and r.get('in_dir2') and not r.get('is_same', False))
            total_common = sum(1 for r in results if r.get('in_dir1') and r.get('in_dir2'))
            
            # 如果当前选中的是MD5差异模式，但用户使用的是基础比对，给出提示
            current_mode = list(CompareMode)[self.mode_combo.currentIndex()]
            if current_mode == CompareMode.MD5_DIFF_ONLY and not hash_type:
                self.status_label.setText(f"提示: '只显示MD5差异'模式需要配合哈希比对使用，当前为基础比对模式。共同文件: {total_common} 个")
            else:
                self.status_label.setText(f"{hash_type}比对完成: 相同 {same_count} 个, 不同 {diff_count} 个, 总计共同文件 {total_common} 个")
        else:
            self.filter_results()
            self.status_label.setText(f"比较完成，共 {len(results)} 个项目")
        
        # 检查模式兼容性
        current_mode = list(CompareMode)[self.mode_combo.currentIndex()]
        if current_mode == CompareMode.MD5_DIFF_ONLY and not hash_type:
            QMessageBox.information(
                self,
                "模式提示",
                "您当前选择了'只显示MD5差异'过滤模式，但使用的是基础比对。\n"
                "基础比对模式下，MD5差异过滤将不会显示任何结果。\n"
                "如需查看MD5差异，请切换到哈希指纹比对模式后重新比较。"
            )
        
        self.filter_results()
        self.update_stats()
        self.reset_ui_state()
        
    def filter_results(self):
        """过滤结果"""
        if not self.current_results:
            return
            
        mode = list(CompareMode)[self.mode_combo.currentIndex()]
        self.filtered_results = []
        
        for item in self.current_results:
            if mode == CompareMode.ALL:
                self.filtered_results.append(item)
            elif mode == CompareMode.COMMON_ONLY:
                if item['in_dir1'] and item['in_dir2']:
                    self.filtered_results.append(item)
            elif mode == CompareMode.DIFF_ONLY:
                # 差异：一边有另一边没有，或者两边都有但不相同（基础比对模式）
                if (item['in_dir1'] != item['in_dir2']) or \
                   (item['in_dir1'] and item['in_dir2'] and not item.get('is_same', True)):
                    self.filtered_results.append(item)
            elif mode == CompareMode.EXTRA_ONLY:
                if item['in_dir1'] and not item['in_dir2']:
                    self.filtered_results.append(item)
            elif mode == CompareMode.MISSING_ONLY:
                if not item['in_dir1'] and item['in_dir2']:
                    self.filtered_results.append(item)
            elif mode == CompareMode.MD5_DIFF_ONLY:
                # MD5差异：两个目录都存在，但MD5值不同（只有在MD5模式下才有意义）
                if item['in_dir1'] and item['in_dir2'] and not item.get('is_same', True):
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
    
    def get_hash_display(self) -> str:
        """获取哈希显示名称（用于表头等）"""
        return self.get_hash_type() or "MD5"

    def display_grouped(self):
        """分组显示"""
        self.result_tree.setVisible(True)
        
        if hasattr(self, 'result_list') and self.result_list is not None:
            self.result_list.setVisible(False)
    
        # 恢复所有列的显示
        use_md5 = self.use_hash()
        ht = self.get_hash_display()
        
        if use_md5:
            self.result_tree.setHeaderLabels([
                "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
                "修改时间(目录1)", "修改时间(目录2)", f"{ht}(目录1)", f"{ht}(目录2)"
            ])
            for i in range(9):
                self.result_tree.setColumnHidden(i, False)
        else:
            self.result_tree.setHeaderLabels([
                "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
                "修改时间(目录1)", "修改时间(目录2)"
            ])
            for i in range(7):
                self.result_tree.setColumnHidden(i, False)
        
        groups = {
            "共同文件(内容相同)": [],
            "共同文件(内容不同)": [],
            "仅在目录1中": [],
            "仅在目录2中": []
        }
        
        for item in self.filtered_results:
            if item['in_dir1'] and item['in_dir2']:
                if item.get('is_same', True):
                    groups["共同文件(内容相同)"].append(item)
                else:
                    groups["共同文件(内容不同)"].append(item)
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
            if group_name == "共同文件(内容相同)":
                group_item.setBackground(0, COLOR_MD5_MATCH)
            elif group_name == "共同文件(内容不同)":
                group_item.setBackground(0, COLOR_MD5_MISMATCH)
            elif group_name == "仅在目录1中":
                group_item.setBackground(0, COLOR_EXTRA)
            elif group_name == "仅在目录2中":
                group_item.setBackground(0, COLOR_MISSING)
                
            self.result_tree.addTopLevelItem(group_item)
            
            for item in items:
                self.add_tree_item(group_item, item)
                
    def display_flat(self):
        """平铺显示"""
        self.result_tree.setVisible(True)
        
        if hasattr(self, 'result_list') and self.result_list is not None:
            self.result_list.setVisible(False)

        use_md5 = self.use_hash()
        ht = self.get_hash_display()
        
        if use_md5:
            self.result_tree.setHeaderLabels([
                "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
                "修改时间(目录1)", "修改时间(目录2)", f"{ht}(目录1)", f"{ht}(目录2)"
            ])
        else:
            self.result_tree.setHeaderLabels([
                "文件名", "路径", "状态", "大小(目录1)", "大小(目录2)", 
                "修改时间(目录1)", "修改时间(目录2)"
            ])
        
        for item in self.filtered_results:
            if use_md5:
                tree_item = QTreeWidgetItem([
                    item['name'],
                    item['rel_path'],
                    self.get_status_text(item),
                    self.format_size(item['size1']),
                    self.format_size(item['size2']),
                    self.format_time(item['time1']),
                    self.format_time(item['time2']),
                    item.get('md5_1', '-')[:8] + "..." if item.get('md5_1') else "-",
                    item.get('md5_2', '-')[:8] + "..." if item.get('md5_2') else "-"
                ])
                col_count = 9
            else:
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
                if self.use_hash():
                    if item.get('is_same', True):
                        for i in range(col_count):
                            tree_item.setBackground(i, COLOR_MD5_MATCH)
                    else:
                        for i in range(col_count):
                            tree_item.setBackground(i, COLOR_MD5_MISMATCH)
                else:
                    for i in range(col_count):
                        tree_item.setBackground(i, COLOR_EXIST)
            elif item['in_dir1'] and not item['in_dir2']:
                for i in range(col_count):
                    tree_item.setBackground(i, COLOR_EXTRA)
            elif not item['in_dir1'] and item['in_dir2']:
                for i in range(col_count):
                    tree_item.setBackground(i, COLOR_MISSING)
            
            self.result_tree.addTopLevelItem(tree_item)
            
    def add_tree_item(self, parent, item):
        """添加树项目"""
        use_md5 = self.use_hash()
        ht = self.get_hash_display()
        
        if use_md5:
            tree_item = QTreeWidgetItem([
                item['name'],
                item['rel_path'],
                self.get_status_text(item),
                self.format_size(item['size1']),
                self.format_size(item['size2']),
                self.format_time(item['time1']),
                self.format_time(item['time2']),
                item.get('md5_1', '-')[:8] + "..." if item.get('md5_1') else "-",
                item.get('md5_2', '-')[:8] + "..." if item.get('md5_2') else "-"
            ])
            col_count = 9
        else:
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
            if self.use_hash():
                if item.get('is_same', True):
                    for i in range(col_count):
                        tree_item.setBackground(i, COLOR_MD5_MATCH)
                else:
                    for i in range(col_count):
                        tree_item.setBackground(i, COLOR_MD5_MISMATCH)
            else:
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
            if self.use_hash():
                ht = self.get_hash_display()
                if item.get('is_same', True):
                    return f"共同存在({ht}相同)"
                else:
                    return f"共同存在({ht}不同)"
            else:
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
        
        if self.use_hash():
            ht = self.get_hash_display()
            calc_md5_action = menu.addAction(f"计算{ht}值")
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
        elif self.use_hash() and action == calc_md5_action:
            self.calculate_selected_md5(item)
        elif action == compare_action:
            self.compare_file_content(item)
            
    def calculate_selected_md5(self, item):
        """计算选中文件的MD5值"""
        # 获取文件路径
        path = item.text(1)  # 路径列
        if path and path != "路径":
            dir1 = self.dir1_edit.text()
            dir2 = self.dir2_edit.text()
            full_path = os.path.join(dir1, path) if os.path.exists(os.path.join(dir1, path)) else os.path.join(dir2, path)
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                # 计算MD5
                try:
                    hash_md5 = hashlib.md5()
                    with open(full_path, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            hash_md5.update(chunk)
                    md5_value = hash_md5.hexdigest()
                    
                    QMessageBox.information(
                        self, 
                        "MD5计算结果",
                        f"文件: {os.path.basename(full_path)}\nMD5: {md5_value}"
                    )
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"计算MD5失败: {str(e)}")
            else:
                QMessageBox.warning(self, "警告", "无法计算目录的MD5值")
        
    def open_file_location(self, item):
        """打开文件位置"""
        path = item.text(1)
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
        
    def update_stats(self):
        """更新统计信息面板"""
        if not self.current_results:
            self.stats_label.setText("")
            return
            
        same = sum(1 for r in self.current_results if r.get('in_dir1') and r.get('in_dir2') and r.get('is_same', True))
        diff = sum(1 for r in self.current_results if r.get('in_dir1') and r.get('in_dir2') and not r.get('is_same', True))
        only1 = sum(1 for r in self.current_results if r.get('in_dir1') and not r.get('in_dir2'))
        only2 = sum(1 for r in self.current_results if not r.get('in_dir1') and r.get('in_dir2'))
        
        # 文件总大小统计（不含目录）
        def file_size(r, key):
            if r.get('is_dir'):
                return 0
            return r.get(key, 0) or 0
        
        size1 = sum(file_size(r, 'size1') for r in self.current_results if r.get('in_dir1'))
        size2 = sum(file_size(r, 'size2') for r in self.current_results if r.get('in_dir2'))
        
        text = (f"📊 统计: 相同 {same} | 不同 {diff} | 仅目录1 {only1} | 仅目录2 {only2} | "
                f"合计 {len(self.current_results)} 项 | "
                f"目录1体积 {self.format_size(size1)} | 目录2体积 {self.format_size(size2)}")
        self.stats_label.setText(text)
        
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
        
        # 加载比对算法设置（兼容旧版 use_md5）
        algo_index = self.settings.value("algorithm_index", 0, type=int)
        if not 0 <= algo_index < len(CompareAlgorithm):
            algo_index = 0
        use_md5 = self.settings.value("use_md5", False, type=bool)
        if use_md5 and algo_index == 0:
            algo_index = 1  # 旧版保存的是MD5
        self.algorithm_combo.setCurrentIndex(algo_index)
        
        # 加载窗口位置与最大化状态
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self._start_maximized = self.settings.value("window_maximized", False, type=bool)
            
    def save_settings(self):
        """保存设置（立即写盘，供防抖定时器与退出时调用）"""
        self.settings.setValue("history", self.history)
        self.settings.setValue("last_dir1", self.dir1_edit.text())
        self.settings.setValue("last_dir2", self.dir2_edit.text())
        self.settings.setValue("mode_index", self.mode_combo.currentIndex())
        self.settings.setValue("display_index", self.display_combo.currentIndex())
        self.settings.setValue("algorithm_index", self.algorithm_combo.currentIndex())
        self.settings.setValue("use_md5", self.use_hash())
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("window_maximized", self.isMaximized())
        
    def show_window(self):
        """按保存的状态显示窗口（最大化/普通，★ v6.1）"""
        if self._start_maximized:
            self.showMaximized()
        else:
            self.show()
        
    def closeEvent(self, event):
        """关闭事件"""
        self._settings_save_timer.stop()  # 停止防抖，避免退出后触发写盘
        self.save_settings()              # 退出强制立即保存
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

    def show_sync_dialog(self):
        """打开一键同步对话框"""
        dir1 = self.dir1_edit.text().strip()
        dir2 = self.dir2_edit.text().strip()
        
        if not dir1 or not dir2:
            QMessageBox.warning(self, "警告", "请先选择两个目录")
            return
        if not os.path.isdir(dir1) or not os.path.isdir(dir2):
            QMessageBox.warning(self, "警告", "目录路径无效")
            return
        if not self.current_results:
            QMessageBox.information(self, "提示", "请先进行目录比较，再进行同步")
            return
        
        dialog = SyncDialog(self, dir1, dir2, self.current_results)
        dialog.exec()

    def show_export(self):
        """导出比较结果"""
        if not self.current_results:
            QMessageBox.information(self, "提示", "没有可导出的结果，请先进行目录比较")
            return
        
        default_name = f"目录比较报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "导出比较结果", default_name,
            "HTML 报告 (*.html);;CSV 文件 (*.csv);;文本文件 (*.txt)"
        )
        if not path:
            return
        
        try:
            if 'HTML' in selected_filter or path.lower().endswith('.html'):
                self.export_html(path)
            elif 'CSV' in selected_filter or path.lower().endswith('.csv'):
                self.export_csv(path)
            else:
                self.export_txt(path)
            QMessageBox.information(self, "导出成功", f"报告已导出到:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出时发生错误: {str(e)}")

    def export_html(self, path: str):
        """导出为HTML报告"""
        ht = self.get_hash_display()
        rows = []
        for item in self.current_results:
            status = self.get_status_text(item)
            if item['in_dir1'] and item['in_dir2']:
                color = '#A8E6CF' if item.get('is_same', True) else '#FFD3B6'
            elif item['in_dir1']:
                color = '#FFB7CE'
            else:
                color = '#FFDAC1'
            md5_1 = item.get('md5_1') or '-'
            md5_2 = item.get('md5_2') or '-'
            rows.append(
                f"<tr style='background-color: {color}'>"
                f"<td>{self._esc(item['name'])}</td>"
                f"<td>{self._esc(item['rel_path'])}</td>"
                f"<td>{status}</td>"
                f"<td>{self.format_size(item['size1'])}</td>"
                f"<td>{self.format_size(item['size2'])}</td>"
                f"<td>{self.format_time(item['time1'])}</td>"
                f"<td>{self.format_time(item['time2'])}</td>"
                f"<td>{self._esc(md5_1)}</td>"
                f"<td>{self._esc(md5_2)}</td>"
                f"</tr>"
            )
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>目录比较报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; }}
h1 {{ color: #2c3e50; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
th {{ background-color: #f2f2f2; }}
</style>
</head>
<body>
<h1>{self._esc(ProjectInfo.NAME)} - 目录比较报告</h1>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>目录1: {self._esc(self.dir1_edit.text())}<br>目录2: {self._esc(self.dir2_edit.text())}</p>
<p>比对算法: {self.get_algorithm().value} | 共 {len(self.current_results)} 个项目</p>
<table>
<tr><th>文件名</th><th>路径</th><th>状态</th><th>大小(目录1)</th><th>大小(目录2)</th><th>修改时间(目录1)</th><th>修改时间(目录2)</th><th>{ht}(目录1)</th><th>{ht}(目录2)</th></tr>
{''.join(rows)}
</table>
</body>
</html>"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

    def export_csv(self, path: str):
        """导出为CSV文件"""
        import csv
        ht = self.get_hash_display()
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["文件名", "路径", "状态", "大小(目录1)", "大小(目录2)",
                             "修改时间(目录1)", "修改时间(目录2)", f"{ht}(目录1)", f"{ht}(目录2)"])
            for item in self.current_results:
                writer.writerow([
                    item['name'], item['rel_path'], self.get_status_text(item),
                    self.format_size(item['size1']), self.format_size(item['size2']),
                    self.format_time(item['time1']), self.format_time(item['time2']),
                    item.get('md5_1') or '-', item.get('md5_2') or '-'
                ])

    def export_txt(self, path: str):
        """导出为文本文件"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"{ProjectInfo.NAME} - 目录比较报告")
        lines.append("=" * 70)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"目录1: {self.dir1_edit.text()}")
        lines.append(f"目录2: {self.dir2_edit.text()}")
        lines.append(f"比对算法: {self.get_algorithm().value}")
        lines.append(f"共 {len(self.current_results)} 个项目")
        lines.append("=" * 70)
        lines.append("")
        
        groups = {}
        for item in self.current_results:
            status = self.get_status_text(item)
            groups.setdefault(status, []).append(item)
        
        for status, items in groups.items():
            lines.append(f"【{status}】({len(items)}个)")
            lines.append("-" * 70)
            for item in items:
                md5_info = ""
                if item.get('md5_1') or item.get('md5_2'):
                    md5_info = f"  哈希1: {item.get('md5_1') or '-'}  哈希2: {item.get('md5_2') or '-'}"
                lines.append(
                    f"  {item['name']} | {item['rel_path']} | "
                    f"大小1:{self.format_size(item['size1'])} 大小2:{self.format_size(item['size2'])}"
                    f"{md5_info}"
                )
            lines.append("")
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    @staticmethod
    def _esc(text) -> str:
        """HTML转义"""
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def compare_file_content(self, item):
        """比较树控件中选中文件的内容"""
        path = item.text(1)
        if not path or path == "路径":
            QMessageBox.warning(self, "警告", "请选择有效的文件")
            return
        self._open_compare_dialog(path)

    def compare_list_file_content(self, data):
        """比较列表控件中选中文件的内容"""
        if data and 'rel_path' in data:
            self._open_compare_dialog(data['rel_path'])

    def _open_compare_dialog(self, rel_path: str):
        """打开文件内容对比对话框"""
        dir1 = self.dir1_edit.text().strip()
        dir2 = self.dir2_edit.text().strip()
        p1 = os.path.join(dir1, rel_path)
        p2 = os.path.join(dir2, rel_path)
        if not (os.path.exists(p1) and os.path.exists(p2) and os.path.isfile(p1) and os.path.isfile(p2)):
            QMessageBox.warning(self, "警告", "两个目录中均需存在该文件才能比较内容")
            return
        dialog = FileCompareDialog(p1, p2, self)
        dialog.exec()

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
        """列表显示"""
        self.result_tree.setVisible(False)
        
        if not hasattr(self, 'result_list') or self.result_list is None:
            self.result_list = QListWidget()
            self.result_list.setViewMode(QListWidget.IconMode)
            self.result_list.setFlow(QListWidget.LeftToRight)
            self.result_list.setWrapping(True)
            self.result_list.setResizeMode(QListWidget.Adjust)
            self.result_list.setSpacing(5)
            self.result_list.setGridSize(QSize(150, 30))
            self.result_list.setSelectionMode(QListWidget.ExtendedSelection)
            self.result_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.result_list.customContextMenuRequested.connect(self.show_list_context_menu)
            
            layout = self.centralWidget().layout()
            index = layout.indexOf(self.result_tree)
            layout.insertWidget(index, self.result_list)
        
        self.result_list.clear()
        
        for item in self.filtered_results:
            list_item = QListWidgetItem(item['name'])
            
            # 设置背景色
            if item['in_dir1'] and item['in_dir2']:
                if self.use_hash():
                    if item.get('is_same', True):
                        list_item.setBackground(COLOR_MD5_MATCH)
                    else:
                        list_item.setBackground(COLOR_MD5_MISMATCH)
                else:
                    list_item.setBackground(COLOR_EXIST)
            elif item['in_dir1'] and not item['in_dir2']:
                list_item.setBackground(COLOR_EXTRA)
            elif not item['in_dir1'] and item['in_dir2']:
                list_item.setBackground(COLOR_MISSING)
            
            list_item.setData(Qt.UserRole, item)
            list_item.setTextAlignment(Qt.AlignCenter)
            self.result_list.addItem(list_item)
        
        self.result_list.setVisible(True)
        self.result_tree.setVisible(False)

    def get_current_display_mode(self) -> DisplayMode:
        """获取当前显示模式"""
        return list(DisplayMode)[self.display_combo.currentIndex()]
    
    def show_list_context_menu(self, position):
        """显示列表控件的右键菜单"""
        menu = QMenu()
        
        item = self.result_list.currentItem()
        if not item:
            return
        
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        open_action = menu.addAction("打开文件位置")
        copy_path_action = menu.addAction("复制路径")
        copy_name_action = menu.addAction("复制文件名")
        menu.addSeparator()
        
        if self.use_hash():
            ht = self.get_hash_display()
            calc_md5_action = menu.addAction(f"计算{ht}值")
            menu.addSeparator()
        
        compare_action = menu.addAction("比较内容")
        menu.addSeparator()
        refresh_action = menu.addAction("刷新")
        
        action = menu.exec_(self.result_list.viewport().mapToGlobal(position))
        
        if action == open_action:
            self.open_list_file_location(data)
        elif action == copy_path_action:
            self.copy_list_path(data)
        elif action == copy_name_action:
            self.copy_list_name(data)
        elif self.use_hash() and action == calc_md5_action:
            self.calculate_list_md5(data)
        elif action == compare_action:
            self.compare_list_file_content(data)

    def calculate_list_md5(self, data):
        """计算列表项的MD5值"""
        if data and 'rel_path' in data:
            dir1 = self.dir1_edit.text()
            dir2 = self.dir2_edit.text()
            full_path = os.path.join(dir1, data['rel_path']) if os.path.exists(os.path.join(dir1, data['rel_path'])) else os.path.join(dir2, data['rel_path'])
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    hash_md5 = hashlib.md5()
                    with open(full_path, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            hash_md5.update(chunk)
                    md5_value = hash_md5.hexdigest()
                    
                    QMessageBox.information(
                        self, 
                        "MD5计算结果",
                        f"文件: {os.path.basename(full_path)}\nMD5: {md5_value}"
                    )
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"计算MD5失败: {str(e)}")

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
    
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = DirCompareTool()
    window.show_window()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()