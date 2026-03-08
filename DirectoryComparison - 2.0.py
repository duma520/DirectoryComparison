import sys
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
                             QLabel, QProgressBar, QFileDialog, QMessageBox,
                             QTabWidget, QSplitter, QScrollArea, QSizePolicy,
                             QGridLayout, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QFileInfo, QSize
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor

class CompareWorker(QThread):
    """比对工作线程"""
    progress_updated = pyqtSignal(int, str)
    finished_compare = pyqtSignal(dict)
    
    def __init__(self, directories):
        super().__init__()
        self.directories = directories
    
    def run(self):
        try:
            total_dirs = len(self.directories)
            all_files = {}
            
            # 收集所有目录的文件
            for idx, directory in enumerate(self.directories):
                self.progress_updated.emit(int(idx / total_dirs * 50), 
                                         f"正在扫描目录 {idx+1}/{total_dirs}: {directory}")
                
                if not os.path.exists(directory):
                    continue
                    
                files = set()
                for root, dirs, filenames in os.walk(directory):
                    for filename in filenames:
                        relative_path = os.path.relpath(os.path.join(root, filename), directory)
                        files.add(relative_path)
                
                all_files[directory] = files
                self.progress_updated.emit(int((idx + 1) / total_dirs * 50), 
                                         f"完成扫描目录 {idx+1}/{total_dirs}")
            
            # 分析差异
            self.progress_updated.emit(50, "正在分析文件差异...")
            results = self.analyze_differences(all_files)
            
            self.progress_updated.emit(100, "比对完成")
            self.finished_compare.emit(results)
            
        except Exception as e:
            self.progress_updated.emit(0, f"比对出错: {str(e)}")
    
    def analyze_differences(self, all_files):
        """分析文件差异"""
        results = {}
        all_directories = list(all_files.keys())
        
        # 获取所有唯一文件
        all_unique_files = set()
        for files in all_files.values():
            all_unique_files.update(files)
        
        # 为每个目录找出缺失的文件
        for i, dir_path in enumerate(all_directories):
            dir_files = all_files[dir_path]
            missing_files = []
            
            for filename in all_unique_files:
                # 检查其他目录中是否有此文件
                other_dirs_have = False
                for other_dir in all_directories:
                    if other_dir != dir_path and filename in all_files[other_dir]:
                        other_dirs_have = True
                        break
                
                # 如果其他目录有此文件而当前目录没有，则为缺失文件
                if other_dirs_have and filename not in dir_files:
                    missing_files.append(filename)
            
            # 找出当前目录独有的文件
            extra_files = []
            for filename in dir_files:
                other_dirs_have = False
                for other_dir in all_directories:
                    if other_dir != dir_path and filename in all_files[other_dir]:
                        other_dirs_have = True
                        break
                if not other_dirs_have:
                    extra_files.append(filename)
            
            results[dir_path] = {
                'missing': sorted(missing_files),
                'extra': sorted(extra_files),
                'total_files': len(dir_files)
            }
        
        return results

class DirectoryComparator(QMainWindow):
    """目录比对器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.directories = []
        self.settings = QSettings("DirectoryComparator", "DirCompare")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置高DPI缩放 :cite[3]:cite[8]
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        self.setWindowTitle("目录比对工具")
        self.setMinimumSize(1200, 800)
        
        # 设置图标 :cite[7]
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建控制区域
        self.create_control_area(main_layout)
        
        # 创建目录列表区域
        self.create_directory_list(main_layout)
        
        # 创建进度条 :cite[1]:cite[6]
        self.create_progress_bar(main_layout)
        
        # 创建结果显示区域
        self.create_results_area(main_layout)
    
    def create_control_area(self, parent_layout):
        """创建控制按钮区域"""
        control_layout = QHBoxLayout()
        
        # 添加目录按钮
        self.add_dir_btn = QPushButton("添加目录")
        self.add_dir_btn.setMinimumHeight(35)
        self.add_dir_btn.clicked.connect(self.add_directory)
        control_layout.addWidget(self.add_dir_btn)
        
        # 移除目录按钮
        self.remove_dir_btn = QPushButton("移除选中目录")
        self.remove_dir_btn.setMinimumHeight(35)
        self.remove_dir_btn.clicked.connect(self.remove_directory)
        control_layout.addWidget(self.remove_dir_btn)
        
        # 开始比对按钮
        self.compare_btn = QPushButton("开始比对")
        self.compare_btn.setMinimumHeight(35)
        self.compare_btn.clicked.connect(self.start_comparison)
        control_layout.addWidget(self.compare_btn)
        
        # 清空结果按钮
        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.setMinimumHeight(35)
        self.clear_btn.clicked.connect(self.clear_results)
        control_layout.addWidget(self.clear_btn)
        
        parent_layout.addLayout(control_layout)
    
    def create_directory_list(self, parent_layout):
        """创建目录列表"""
        dir_layout = QVBoxLayout()
        
        # 目录列表标签
        dir_label = QLabel("比对目录列表:")
        dir_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        dir_layout.addWidget(dir_label)
        
        # 目录列表
        self.dir_listwidget = QListWidget()
        self.dir_listwidget.setMinimumHeight(120)
        self.dir_listwidget.setSelectionMode(QListWidget.ExtendedSelection)
        dir_layout.addWidget(self.dir_listwidget)
        
        parent_layout.addLayout(dir_layout)
    
    def create_progress_bar(self, parent_layout):
        """创建进度条 :cite[1]:cite[6]"""
        progress_layout = QVBoxLayout()
        
        # 进度标签
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setFont(QFont("Microsoft YaHei", 9))
        progress_layout.addWidget(self.progress_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        # 设置进度条样式 :cite[1]
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                background-color: #FFFFFF;
                text-align: center;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
        """)
        
        progress_layout.addWidget(self.progress_bar)
        parent_layout.addLayout(progress_layout)
    
    def create_results_area(self, parent_layout):
        """创建结果显示区域"""
        # 创建标签页显示结果
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        
        # 初始结果标签
        self.initial_tab = QWidget()
        self.initial_layout = QVBoxLayout(self.initial_tab)
        
        initial_label = QLabel("比对结果将显示在此处")
        initial_label.setAlignment(Qt.AlignCenter)
        initial_label.setStyleSheet("color: #666; font-size: 14px;")
        self.initial_layout.addWidget(initial_label)
        
        self.results_tabs.addTab(self.initial_tab, "等待比对")
        
        parent_layout.addWidget(self.results_tabs)
    
    def add_directory(self):
        """添加目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择要比对的目录")
        if directory and directory not in self.directories:
            self.directories.append(directory)
            self.dir_listwidget.addItem(directory)
            self.save_settings()
    
    def remove_directory(self):
        """移除选中目录"""
        selected_items = self.dir_listwidget.selectedItems()
        for item in selected_items:
            directory = item.text()
            if directory in self.directories:
                self.directories.remove(directory)
            self.dir_listwidget.takeItem(self.dir_listwidget.row(item))
        self.save_settings()
    
    def start_comparison(self):
        """开始比对"""
        if len(self.directories) < 2:
            QMessageBox.warning(self, "警告", "请至少添加两个目录进行比对")
            return
        
        # 禁用按钮防止重复操作
        self.compare_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("开始比对...")
        
        # 创建工作线程
        self.worker = CompareWorker(self.directories)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.finished_compare.connect(self.on_comparison_finished)
        self.worker.start()
    
    def update_progress(self, value, message):
        """更新进度条 :cite[1]:cite[6]"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        QApplication.processEvents()  # 确保UI更新
    
    def on_comparison_finished(self, results):
        """比对完成处理"""
        self.compare_btn.setEnabled(True)
        self.display_results(results)
        self.save_settings()
    
    def display_results(self, results):
        """显示比对结果"""
        # 清除之前的结果标签页
        while self.results_tabs.count() > 0:
            self.results_tabs.removeTab(0)
        
        # 为每个目录创建结果标签页
        for directory, data in results.items():
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            
            # 显示统计信息
            stats_text = f"目录: {directory}\n总文件数: {data['total_files']}\n缺失文件: {len(data['missing'])}\n独有文件: {len(data['extra'])}"
            stats_label = QLabel(stats_text)
            stats_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            stats_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
            scroll_layout.addWidget(stats_label)
            
            # 显示缺失文件
            if data['missing']:
                missing_label = QLabel("缺失文件 (在其他目录中存在但本目录缺少):")
                missing_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
                missing_label.setStyleSheet("color: #d32f2f; margin-top: 10px;")
                scroll_layout.addWidget(missing_label)
                
                for file in data['missing']:
                    file_label = QLabel(f"  • {file}")
                    file_label.setFont(QFont("Consolas", 9))
                    file_label.setStyleSheet("color: #d32f2f; margin-left: 10px;")
                    scroll_layout.addWidget(file_label)
            
            # 显示独有文件
            if data['extra']:
                extra_label = QLabel("独有文件 (仅在本目录中存在):")
                extra_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
                extra_label.setStyleSheet("color: #388e3c; margin-top: 10px;")
                scroll_layout.addWidget(extra_label)
                
                for file in data['extra']:
                    file_label = QLabel(f"  • {file}")
                    file_label.setFont(QFont("Consolas", 9))
                    file_label.setStyleSheet("color: #388e3c; margin-left: 10px;")
                    scroll_layout.addWidget(file_label)
            
            # 如果没有差异
            if not data['missing'] and not data['extra']:
                no_diff_label = QLabel("该目录与其他目录相比没有文件差异")
                no_diff_label.setStyleSheet("color: #666; font-style: italic; margin-top: 20px;")
                no_diff_label.setAlignment(Qt.AlignCenter)
                scroll_layout.addWidget(no_diff_label)
            
            scroll_layout.addStretch()
            scroll.setWidget(scroll_content)
            layout.addWidget(scroll)
            
            # 使用目录名作为标签页标题
            tab_name = os.path.basename(directory) or directory
            if len(tab_name) > 15:
                tab_name = tab_name[:12] + "..."
            self.results_tabs.addTab(tab, tab_name)
    
    def clear_results(self):
        """清空结果"""
        self.progress_bar.setValue(0)
        self.progress_label.setText("准备就绪")
        
        # 重置结果标签页
        while self.results_tabs.count() > 0:
            self.results_tabs.removeTab(0)
        
        self.initial_tab = QWidget()
        self.initial_layout = QVBoxLayout(self.initial_tab)
        
        initial_label = QLabel("比对结果将显示在此处")
        initial_label.setAlignment(Qt.AlignCenter)
        initial_label.setStyleSheet("color: #666; font-size: 14px;")
        self.initial_layout.addWidget(initial_label)
        
        self.results_tabs.addTab(self.initial_tab, "等待比对")
    
    def load_settings(self):
        """加载保存的设置"""
        # 加载目录列表
        saved_dirs = self.settings.value("directories", [])
        if saved_dirs:
            self.directories = saved_dirs
            for directory in saved_dirs:
                self.dir_listwidget.addItem(directory)
        
        # 加载窗口几何信息
        geometry = self.settings.value("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def save_settings(self):
        """保存设置"""
        # 保存目录列表
        self.settings.setValue("directories", self.directories)
        
        # 保存窗口几何信息
        self.settings.setValue("window_geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.save_settings()
        event.accept()

def main():
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("目录比对工具")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("DirectoryComparator")
    
    # 设置高DPI缩放 :cite[3]:cite[8]
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建并显示主窗口
    window = DirectoryComparator()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()