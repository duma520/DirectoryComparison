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
    QListWidget, QAbstractItemView, QGridLayout, QFrame
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


class CompareMode(Enum):
    """比较模式"""
    ALL = "全部文件"
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
        self.init_ui()
        self.load_settings()
        self.setup_connections()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("目录比较工具")
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
        
        # 创建过滤和显示选项
        self.create_filter_options(main_layout)
        
        # 创建结果显示区域
        self.create_result_display(main_layout)
        
        # 创建进度条和状态栏
        self.create_progress_and_status(main_layout)
        
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
        
        # 历史记录
        history_action = QAction("历史记录", self)
        toolbar.addAction(history_action)
        
        # 清空
        clear_action = QAction("清空", self)
        toolbar.addAction(clear_action)
        
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
        
        # 交换按钮
        swap_btn = QPushButton("交换目录")
        layout.addWidget(swap_btn, 2, 1, Qt.AlignCenter)
        
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
        
    def setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        self.browse1_btn.clicked.connect(lambda: self.browse_directory(self.dir1_edit))
        self.browse2_btn.clicked.connect(lambda: self.browse_directory(self.dir2_edit))
        self.paste1_btn.clicked.connect(lambda: self.paste_directory(self.dir1_edit))
        self.paste2_btn.clicked.connect(lambda: self.paste_directory(self.dir2_edit))
        
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
        else:
            self.display_flat()
            
    def display_grouped(self):
        """分组显示"""
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
                self.add_tree_item(group_item, item)
                
    def display_flat(self):
        """平铺显示"""
        for item in self.filtered_results:
            self.add_tree_item(self.result_tree, item)
            
    def add_tree_item(self, parent, item):
        """添加树项目"""
        tree_item = QTreeWidgetItem([
            item['name'],
            item['rel_path'],
            self.get_status_text(item),
            self.format_size(item['size1']),
            self.format_size(item['size2']),
            self.format_time(item['time1']),
            self.format_time(item['time2'])
        ])
        
        # 设置颜色
        if item['in_dir1'] and item['in_dir2']:
            for i in range(7):
                tree_item.setBackground(i, COLOR_EXIST)
        elif item['in_dir1'] and not item['in_dir2']:
            for i in range(7):
                tree_item.setBackground(i, COLOR_EXTRA)
        elif not item['in_dir1'] and item['in_dir2']:
            for i in range(7):
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