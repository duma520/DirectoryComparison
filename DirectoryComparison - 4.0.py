import sys
import os
import json
from pathlib import Path
from collections import defaultdict

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QListWidget, QListWidgetItem,
                             QLabel, QProgressBar, QFileDialog, QMessageBox,
                             QTabWidget, QSplitter, QScrollArea, QFrame, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QIcon, QFont

class FileComparisonThread(QThread):
    progress_updated = pyqtSignal(int)
    comparison_finished = pyqtSignal(dict)
    directory_processed = pyqtSignal(str, list)
    
    def __init__(self, directories):
        super().__init__()
        self.directories = directories
        
    def run(self):
        total_dirs = len(self.directories)
        all_files = defaultdict(set)
        
        for i, directory in enumerate(self.directories):
            if not os.path.exists(directory):
                continue
                
            file_list = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), directory)
                    file_list.append(rel_path)
                    all_files[rel_path].add(directory)
            
            self.directory_processed.emit(directory, file_list)
            progress = int((i + 1) / total_dirs * 100)
            self.progress_updated.emit(progress)
            
        comparison_result = self.analyze_comparison(all_files)
        self.comparison_finished.emit(comparison_result)
    
    def analyze_comparison(self, all_files):
        result = {
            'unique_files': defaultdict(list),
            'common_files': [],
            'directory_stats': {}
        }
        
        for directory in self.directories:
            result['directory_stats'][directory] = {'total_files': 0, 'unique_files': 0}
        
        for filename, dirs_containing in all_files.items():
            if len(dirs_containing) == 1:
                unique_dir = list(dirs_containing)[0]
                result['unique_files'][unique_dir].append(filename)
                result['directory_stats'][unique_dir]['unique_files'] += 1
            else:
                result['common_files'].append(filename)
        
        for directory in self.directories:
            total_files = len([f for f, dirs in all_files.items() if directory in dirs])
            result['directory_stats'][directory]['total_files'] = total_files
            
        return result

class DirectoryComparisonTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.directories = []
        self.settings = QSettings("FileComparisonTool", "DirectoryComparator")
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("多目录文件比对工具")
        self.setMinimumSize(1200, 800)
        
        # 设置图标
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部控制区域
        self.create_control_area(main_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 目录列表标签页
        self.create_directory_tab()
        
        # 结果展示标签页
        self.create_results_tab()
        
        # 统计信息标签页
        self.create_stats_tab()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def create_control_area(self, parent_layout):
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Box)
        control_frame.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 5px; padding: 10px; }")
        
        control_layout = QHBoxLayout(control_frame)
        
        # 按钮区域
        btn_add_dir = QPushButton("添加目录")
        btn_add_dir.setMinimumHeight(35)
        btn_add_dir.clicked.connect(self.add_directory)
        
        btn_remove_dir = QPushButton("移除选中目录")
        btn_remove_dir.setMinimumHeight(35)
        btn_remove_dir.clicked.connect(self.remove_directory)
        
        btn_clear_all = QPushButton("清空所有目录")
        btn_clear_all.setMinimumHeight(35)
        btn_clear_all.clicked.connect(self.clear_directories)
        
        btn_compare = QPushButton("开始比对")
        btn_compare.setMinimumHeight(35)
        btn_compare.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        btn_compare.clicked.connect(self.start_comparison)
        
        control_layout.addWidget(btn_add_dir)
        control_layout.addWidget(btn_remove_dir)
        control_layout.addWidget(btn_clear_all)
        control_layout.addWidget(btn_compare)
        control_layout.addStretch()
        
        parent_layout.addWidget(control_frame)
    
    def create_directory_tab(self):
        dir_tab = QWidget()
        layout = QVBoxLayout(dir_tab)
        
        # 目录列表
        self.dir_list_widget = QListWidget()
        self.dir_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(QLabel("已添加的目录列表:"))
        layout.addWidget(self.dir_list_widget)
        
        self.tab_widget.addTab(dir_tab, "目录管理")
    
    def create_results_tab(self):
        results_tab = QWidget()
        layout = QVBoxLayout(results_tab)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 唯一文件列表
        unique_files_frame = QFrame()
        unique_files_frame.setFrameStyle(QFrame.Box)
        unique_files_layout = QVBoxLayout(unique_files_frame)
        
        unique_files_layout.addWidget(QLabel("各目录独有文件:"))
        self.unique_files_list = QListWidget()
        unique_files_layout.addWidget(self.unique_files_list)
        
        # 公共文件列表
        common_files_frame = QFrame()
        common_files_frame.setFrameStyle(QFrame.Box)
        common_files_layout = QVBoxLayout(common_files_frame)
        
        common_files_layout.addWidget(QLabel("所有目录共有文件:"))
        self.common_files_list = QListWidget()
        common_files_layout.addWidget(self.common_files_list)
        
        splitter.addWidget(unique_files_frame)
        splitter.addWidget(common_files_frame)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        self.tab_widget.addTab(results_tab, "比对结果")
    
    def create_stats_tab(self):
        stats_tab = QWidget()
        layout = QVBoxLayout(stats_tab)
        
        # 统计信息显示
        self.stats_text = QLabel()
        self.stats_text.setAlignment(Qt.AlignTop)
        self.stats_text.setStyleSheet("QLabel { padding: 10px; background-color: #f5f5f5; border: 1px solid #ddd; }")
        self.stats_text.setMinimumHeight(200)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.stats_text)
        
        layout.addWidget(QLabel("统计信息:"))
        layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(stats_tab, "统计信息")
    
    def add_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择要比对的目录")
        if directory and directory not in self.directories:
            self.directories.append(directory)
            self.update_directory_list()
            self.save_settings()
    
    def remove_directory(self):
        selected_items = self.dir_list_widget.selectedItems()
        for item in selected_items:
            directory = item.text()
            if directory in self.directories:
                self.directories.remove(directory)
        self.update_directory_list()
        self.save_settings()
    
    def clear_directories(self):
        self.directories.clear()
        self.update_directory_list()
        self.save_settings()
    
    def update_directory_list(self):
        self.dir_list_widget.clear()
        for directory in self.directories:
            item = QListWidgetItem(directory)
            self.dir_list_widget.addItem(item)
    
    def start_comparison(self):
        if len(self.directories) < 2:
            QMessageBox.warning(self, "警告", "请至少添加两个目录进行比对")
            return
        
        # 清空之前的结果
        self.unique_files_list.clear()
        self.common_files_list.clear()
        self.stats_text.setText("")
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 禁用界面
        self.setEnabled(False)
        self.statusBar().showMessage("正在比对文件...")
        
        # 启动比对线程
        self.comparison_thread = FileComparisonThread(self.directories)
        self.comparison_thread.progress_updated.connect(self.update_progress)
        self.comparison_thread.comparison_finished.connect(self.on_comparison_finished)
        self.comparison_thread.directory_processed.connect(self.on_directory_processed)
        self.comparison_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def on_directory_processed(self, directory, file_list):
        self.statusBar().showMessage(f"已处理目录: {directory} (找到 {len(file_list)} 个文件)")
    
    def on_comparison_finished(self, result):
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        self.statusBar().showMessage("比对完成")
        
        # 显示结果
        self.display_results(result)
        self.save_settings()
    
    def display_results(self, result):
        # 显示唯一文件
        self.unique_files_list.clear()
        for directory, files in result['unique_files'].items():
            if files:
                dir_item = QListWidgetItem(f"【{os.path.basename(directory)}】的独有文件 ({len(files)}个):")
                dir_item.setBackground(Qt.lightGray)
                dir_item.setFlags(Qt.NoItemFlags)  # 不可选择
                self.unique_files_list.addItem(dir_item)
                
                for file in sorted(files):
                    item = QListWidgetItem(f"  {file}")
                    item.setToolTip(os.path.join(directory, file))
                    self.unique_files_list.addItem(item)
        
        # 显示公共文件
        self.common_files_list.clear()
        common_files_item = QListWidgetItem(f"所有目录共有的文件 ({len(result['common_files'])}个):")
        common_files_item.setBackground(Qt.lightGray)
        common_files_item.setFlags(Qt.NoItemFlags)
        self.common_files_list.addItem(common_files_item)
        
        for file in sorted(result['common_files']):
            item = QListWidgetItem(f"  {file}")
            self.common_files_list.addItem(item)
        
        # 显示统计信息
        stats_text = "<h3>目录比对统计</h3>"
        stats_text += f"<p>比对目录数量: <b>{len(self.directories)}</b></p>"
        stats_text += f"<p>总文件数（去重）: <b>{len(result['common_files']) + sum(len(files) for files in result['unique_files'].values())}</b></p>"
        stats_text += "<hr>"
        
        for directory, stats in result['directory_stats'].items():
            dir_name = os.path.basename(directory)
            stats_text += f"<h4>📁 {dir_name}</h4>"
            stats_text += f"<p>目录路径: {directory}</p>"
            stats_text += f"<p>文件总数: <b>{stats['total_files']}</b></p>"
            stats_text += f"<p>独有文件: <b style='color: #e74c3c;'>{stats['unique_files']}</b></p>"
            stats_text += "<br>"
        
        self.stats_text.setText(stats_text)
        
        # 自动切换到结果标签页
        self.tab_widget.setCurrentIndex(1)
    
    def load_settings(self):
        # 加载保存的目录
        size = self.settings.beginReadArray("directories")
        self.directories = []
        for i in range(size):
            self.settings.setArrayIndex(i)
            directory = self.settings.value("path")
            if directory and os.path.exists(directory):
                self.directories.append(directory)
        self.settings.endArray()
        
        self.update_directory_list()
        
        # 加载窗口大小和位置
        window_geometry = self.settings.value("window_geometry")
        if window_geometry:
            self.restoreGeometry(window_geometry)
    
    def save_settings(self):
        # 保存目录列表
        self.settings.beginWriteArray("directories")
        for i, directory in enumerate(self.directories):
            self.settings.setArrayIndex(i)
            self.settings.setValue("path", directory)
        self.settings.endArray()
        
        # 保存窗口状态
        self.settings.setValue("window_geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        self.save_settings()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("多目录文件比对工具")
    app.setApplicationVersion("1.0")
    
    # 设置中文字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = DirectoryComparisonTool()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()