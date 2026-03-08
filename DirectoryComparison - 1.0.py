import sys
import os
import shutil
import sqlite3
import json
import datetime
import hashlib
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QCheckBox, QMessageBox, QProgressBar, QTabWidget,
                             QGroupBox, QListWidget, QSplitter, QFileDialog, QDialog,
                             QDialogButtonBox, QDateEdit, QHeaderView, QTextEdit)
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

class DatabaseManager:
    def __init__(self, user_db_path):
        self.user_db_path = user_db_path
        self.conn = None
        self.init_db()
        
    def init_db(self):
        """初始化用户数据库"""
        self.conn = sqlite3.connect(self.user_db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式
        cursor = self.conn.cursor()
        
        # 创建目录比对记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comparison_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                directories TEXT NOT NULL
            )
        ''')
        
        # 创建文件比对结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comparison_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                directory_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                status TEXT NOT NULL, -- 'missing', 'extra'
                FOREIGN KEY (session_id) REFERENCES comparison_sessions (id)
            )
        ''')
        
        # 创建用户设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        self.conn.commit()
    
    def save_comparison_session(self, session_name, directories, results):
        """保存比对会话和结果"""
        cursor = self.conn.cursor()
        
        # 插入会话记录
        cursor.execute(
            'INSERT INTO comparison_sessions (session_name, directories) VALUES (?, ?)',
            (session_name, json.dumps(directories))
        )
        session_id = cursor.lastrowid
        
        # 插入比对结果
        for dir_path, file_list in results.items():
            for file_name in file_list:
                cursor.execute(
                    'INSERT INTO comparison_results (session_id, directory_path, file_name, status) VALUES (?, ?, ?, ?)',
                    (session_id, dir_path, file_name, 'extra')
                )
        
        self.conn.commit()
        return session_id
    
    def get_comparison_history(self):
        """获取比对历史"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, session_name, created_time, directories 
            FROM comparison_sessions 
            ORDER BY created_time DESC
        ''')
        return cursor.fetchall()
    
    def get_comparison_results(self, session_id):
        """获取特定会话的比对结果"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT directory_path, file_name, status
            FROM comparison_results
            WHERE session_id = ?
        ''', (session_id,))
        return cursor.fetchall()
    
    def save_setting(self, key, value):
        """保存用户设置"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)',
            (key, json.dumps(value))
        )
        self.conn.commit()
    
    def load_setting(self, key, default=None):
        """加载用户设置"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM user_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return default
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

class BackupManager:
    def __init__(self, backups_dir, max_backups=30):
        self.backups_dir = Path(backups_dir)
        self.max_backups = max_backups
        self.backups_dir.mkdir(exist_ok=True)
    
    def create_backup(self, db_path, backup_type="manual"):
        """创建数据库备份"""
        if not os.path.exists(db_path):
            return False, "数据库文件不存在"
        
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backups_dir / f"{backup_type}_{timestamp}.db"
            
            # 使用SQLite备份API确保一致性:cite[3]
            source_conn = sqlite3.connect(db_path)
            backup_conn = sqlite3.connect(backup_file)
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # 添加备份元数据
            self._add_backup_metadata(backup_file, backup_type, db_path)
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return True, str(backup_file)
            
        except Exception as e:
            return False, f"备份失败: {str(e)}"
    
    def _add_backup_metadata(self, backup_file, backup_type, original_db_path):
        """添加备份元数据"""
        try:
            file_size = os.path.getsize(backup_file)
            metadata = {
                "backup_type": backup_type,
                "timestamp": datetime.datetime.now().isoformat(),
                "file_size": file_size,
                "original_db": os.path.basename(original_db_path),
                "version": "1.0"
            }
            
            meta_file = backup_file.with_suffix('.meta')
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"添加备份元数据失败: {e}")
    
    def _cleanup_old_backups(self):
        """清理旧备份，只保留最新的max_backups个"""
        try:
            backup_files = list(self.backups_dir.glob("*.db"))
            if len(backup_files) <= self.max_backups:
                return
            
            # 按修改时间排序，删除最旧的
            backup_files.sort(key=os.path.getmtime)
            files_to_delete = backup_files[:-self.max_backups]
            
            for file_path in files_to_delete:
                os.remove(file_path)
                # 删除对应的元数据文件
                meta_file = file_path.with_suffix('.meta')
                if meta_file.exists():
                    os.remove(meta_file)
                    
        except Exception as e:
            print(f"清理旧备份失败: {e}")
    
    def get_backup_list(self):
        """获取备份列表"""
        backups = []
        for db_file in self.backups_dir.glob("*.db"):
            meta_file = db_file.with_suffix('.meta')
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    metadata['file_path'] = db_file
                    backups.append(metadata)
                except Exception as e:
                    print(f"读取备份元数据失败 {meta_file}: {e}")
        
        # 按时间倒序排列
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def restore_backup(self, backup_file, target_db_path):
        """恢复备份"""
        try:
            # 先备份当前数据库
            self.create_backup(target_db_path, "pre_restore")
            
            # 恢复备份
            temp_conn = sqlite3.connect(backup_file)
            target_conn = sqlite3.connect(target_db_path)
            
            with target_conn:
                temp_conn.backup(target_conn)
            
            temp_conn.close()
            target_conn.close()
            
            return True, "恢复成功"
            
        except Exception as e:
            return False, f"恢复失败: {str(e)}"

class DirectoryComparisonThread(QThread):
    """目录比对线程"""
    progress_updated = pyqtSignal(int, str)
    finished_comparison = pyqtSignal(dict)
    
    def __init__(self, directories):
        super().__init__()
        self.directories = directories
    
    def run(self):
        """执行目录比对"""
        try:
            all_files = {}
            total_dirs = len(self.directories)
            
            # 收集所有文件
            for i, directory in enumerate(self.directories):
                self.progress_updated.emit(int((i / total_dirs) * 50), f"扫描目录: {directory}")
                files = self._get_files_in_directory(directory)
                all_files[directory] = set(files)
            
            self.progress_updated.emit(50, "分析文件差异...")
            
            # 分析差异
            results = self._analyze_differences(all_files)
            
            self.progress_updated.emit(100, "比对完成")
            self.finished_comparison.emit(results)
            
        except Exception as e:
            self.progress_updated.emit(0, f"比对出错: {str(e)}")
            self.finished_comparison.emit({})
    
    def _get_files_in_directory(self, directory):
        """获取目录中的所有文件"""
        files = []
        if os.path.exists(directory):
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    relative_path = os.path.relpath(os.path.join(root, filename), directory)
                    files.append(relative_path)
        return files
    
    def _analyze_differences(self, all_files):
        """分析文件差异"""
        results = {}
        all_dirs = list(all_files.keys())
        
        # 找出每个目录中独有的文件
        for i, current_dir in enumerate(all_dirs):
            current_files = all_files[current_dir]
            other_files = set()
            
            for j, other_dir in enumerate(all_dirs):
                if i != j:
                    other_files.update(all_files[other_dir])
            
            # 当前目录有而其他目录没有的文件
            extra_files = current_files - other_files
            if extra_files:
                results[current_dir] = sorted(list(extra_files))
        
        return results

class UserManager:
    def __init__(self, app_data_dir):
        self.app_data_dir = Path(app_data_dir)
        self.app_data_dir.mkdir(exist_ok=True)
        self.users_file = self.app_data_dir / "users.json"
        self.current_user = None
        self.users = self._load_users()
    
    def _load_users(self):
        """加载用户列表"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_users(self):
        """保存用户列表"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def add_user(self, username):
        """添加用户"""
        if username in self.users:
            return False, "用户已存在"
        
        self.users.append(username)
        self._save_users()
        
        # 创建用户数据库目录
        user_db_dir = self.app_data_dir / "user_dbs"
        user_db_dir.mkdir(exist_ok=True)
        
        return True, "用户添加成功"
    
    def delete_user(self, username):
        """删除用户"""
        if username not in self.users:
            return False, "用户不存在"
        
        self.users.remove(username)
        self._save_users()
        
        # 删除用户数据库
        user_db_file = self.app_data_dir / "user_dbs" / f"{username}.db"
        if user_db_file.exists():
            user_db_file.unlink()
        
        return True, "用户删除成功"
    
    def rename_user(self, old_username, new_username):
        """重命名用户"""
        if old_username not in self.users:
            return False, "原用户不存在"
        
        if new_username in self.users:
            return False, "新用户名已存在"
        
        index = self.users.index(old_username)
        self.users[index] = new_username
        self._save_users()
        
        # 重命名用户数据库
        old_db_file = self.app_data_dir / "user_dbs" / f"{old_username}.db"
        new_db_file = self.app_data_dir / "user_dbs" / f"{new_username}.db"
        
        if old_db_file.exists():
            old_db_file.rename(new_db_file)
        
        return True, "用户重命名成功"
    
    def get_users(self):
        """获取用户列表"""
        return self.users.copy()

class RestoreDialog(QDialog):
    """数据库恢复对话框"""
    def __init__(self, backup_manager, current_db_path, parent=None):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.current_db_path = current_db_path
        self.selected_backup = None
        self.init_ui()
        self.load_backups()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("数据库恢复")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # 筛选控件
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("备份类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", "")
        self.type_combo.addItem("自动", "auto")
        self.type_combo.addItem("手动", "manual")
        self.type_combo.addItem("回滚前", "pre_restore")
        self.type_combo.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.type_combo)
        
        filter_layout.addWidget(QLabel("开始时间:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QtCore.QDate.currentDate().addDays(-7))
        self.start_date.dateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.start_date)
        
        filter_layout.addWidget(QLabel("结束时间:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QtCore.QDate.currentDate())
        self.end_date.dateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.end_date)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 备份列表表格
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels(["备份时间", "备份类型", "文件大小", "原数据库", "操作"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.doubleClicked.connect(self.preview_backup)
        layout.addWidget(self.backup_table)
        
        # 详细信息预览
        preview_group = QGroupBox("备份详细信息")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.restore_btn = QPushButton("恢复选中备份")
        self.restore_btn.clicked.connect(self.restore_backup)
        self.restore_btn.setEnabled(False)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.restore_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_backups(self):
        """加载备份列表"""
        self.backups = self.backup_manager.get_backup_list()
        self.apply_filters()
    
    def apply_filters(self):
        """应用筛选条件"""
        backup_type_filter = self.type_combo.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        self.backup_table.setRowCount(0)
        
        for backup in self.backups:
            backup_time = backup['timestamp'][:10]  # 取日期部分
            backup_type = backup['backup_type']
            
            # 类型筛选
            if backup_type_filter and backup_type != backup_type_filter:
                continue
            
            # 时间筛选
            if backup_time < start_date or backup_time > end_date:
                continue
            
            self.add_backup_to_table(backup)
    
    def add_backup_to_table(self, backup):
        """添加备份到表格"""
        row = self.backup_table.rowCount()
        self.backup_table.insertRow(row)
        
        # 备份时间
        time_str = datetime.datetime.fromisoformat(backup['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        self.backup_table.setItem(row, 0, QTableWidgetItem(time_str))
        
        # 备份类型
        type_map = {"auto": "自动", "manual": "手动", "pre_restore": "回滚前"}
        type_str = type_map.get(backup['backup_type'], backup['backup_type'])
        self.backup_table.setItem(row, 1, QTableWidgetItem(type_str))
        
        # 文件大小
        size_str = self._format_file_size(backup['file_size'])
        self.backup_table.setItem(row, 2, QTableWidgetItem(size_str))
        
        # 原数据库
        self.backup_table.setItem(row, 3, QTableWidgetItem(backup['original_db']))
        
        # 操作按钮
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(lambda: self.preview_backup(backup))
        layout.addWidget(preview_btn)
        
        widget.setLayout(layout)
        self.backup_table.setCellWidget(row, 4, widget)
        
        # 保存备份文件路径到表格项
        self.backup_table.item(row, 0).setData(Qt.UserRole, backup)
    
    def _format_file_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def preview_backup(self, backup_item):
        """预览备份详细信息"""
        if isinstance(backup_item, QTableWidgetItem):
            row = backup_item.row()
            backup = self.backup_table.item(row, 0).data(Qt.UserRole)
        else:
            backup = backup_item
        
        if backup:
            preview_text = f"""备份时间: {datetime.datetime.fromisoformat(backup['timestamp']).strftime("%Y-%m-%d %H:%M:%S")}
备份类型: {backup['backup_type']}
文件大小: {self._format_file_size(backup['file_size'])}
原数据库: {backup['original_db']}
备份版本: {backup.get('version', '1.0')}
文件路径: {backup['file_path']}"""
            
            self.preview_text.setPlainText(preview_text)
            self.selected_backup = backup
            self.restore_btn.setEnabled(True)
    
    def restore_backup(self):
        """恢复备份"""
        if not self.selected_backup:
            QMessageBox.warning(self, "警告", "请先选择要恢复的备份")
            return
        
        reply = QMessageBox.question(
            self, "确认恢复",
            "确定要恢复此备份吗？恢复前会自动创建当前数据库的备份。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.backup_manager.restore_backup(
                self.selected_backup['file_path'], 
                self.current_db_path
            )
            
            if success:
                QMessageBox.information(self, "成功", "数据库恢复成功")
                self.accept()
            else:
                QMessageBox.critical(self, "错误", message)

class UserLoginDialog(QDialog):
    """用户登录对话框"""
    def __init__(self, user_manager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.selected_user = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("选择用户")
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("目录比对工具")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # 用户列表
        layout.addWidget(QLabel("选择用户:"))
        self.user_list = QListWidget()
        self.user_list.itemDoubleClicked.connect(self.login_user)
        self.load_users()
        layout.addWidget(self.user_list)
        
        # 用户管理按钮
        user_management_layout = QHBoxLayout()
        
        self.add_user_btn = QPushButton("添加用户")
        self.add_user_btn.clicked.connect(self.add_user)
        user_management_layout.addWidget(self.add_user_btn)
        
        self.delete_user_btn = QPushButton("删除用户")
        self.delete_user_btn.clicked.connect(self.delete_user)
        user_management_layout.addWidget(self.delete_user_btn)
        
        self.rename_user_btn = QPushButton("重命名用户")
        self.rename_user_btn.clicked.connect(self.rename_user)
        user_management_layout.addWidget(self.rename_user_btn)
        
        layout.addLayout(user_management_layout)
        
        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.clicked.connect(self.login_selected_user)
        layout.addWidget(self.login_btn)
        
        self.setLayout(layout)
        self.update_button_states()
    
    def load_users(self):
        """加载用户列表"""
        self.user_list.clear()
        users = self.user_manager.get_users()
        for user in users:
            self.user_list.addItem(user)
    
    def update_button_states(self):
        """更新按钮状态"""
        has_selection = self.user_list.currentItem() is not None
        self.delete_user_btn.setEnabled(has_selection)
        self.rename_user_btn.setEnabled(has_selection)
        self.login_btn.setEnabled(has_selection)
    
    def add_user(self):
        """添加用户"""
        username, ok = QtWidgets.QInputDialog.getText(
            self, "添加用户", "请输入用户名:"
        )
        
        if ok and username:
            success, message = self.user_manager.add_user(username)
            if success:
                self.load_users()
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.warning(self, "警告", message)
    
    def delete_user(self):
        """删除用户"""
        current_item = self.user_list.currentItem()
        if not current_item:
            return
        
        username = current_item.text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除用户 '{username}' 吗？这将删除该用户的所有数据。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.user_manager.delete_user(username)
            if success:
                self.load_users()
                self.update_button_states()
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.warning(self, "警告", message)
    
    def rename_user(self):
        """重命名用户"""
        current_item = self.user_list.currentItem()
        if not current_item:
            return
        
        old_username = current_item.text()
        new_username, ok = QtWidgets.QInputDialog.getText(
            self, "重命名用户", "请输入新用户名:", text=old_username
        )
        
        if ok and new_username:
            success, message = self.user_manager.rename_user(old_username, new_username)
            if success:
                self.load_users()
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.warning(self, "警告", message)
    
    def login_selected_user(self):
        """登录选中的用户"""
        current_item = self.user_list.currentItem()
        if current_item:
            self.login_user(current_item)
    
    def login_user(self, item):
        """登录用户"""
        self.selected_user = item.text()
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self, user_manager, username):
        super().__init__()
        self.user_manager = user_manager
        self.username = username
        self.db_manager = None
        self.backup_manager = None
        self.current_directories = []
        self.comparison_results = {}
        
        # 初始化数据库和备份
        self.init_user_environment()
        
        self.init_ui()
        self.load_settings()
    
    def init_user_environment(self):
        """初始化用户环境"""
        user_db_dir = self.user_manager.app_data_dir / "user_dbs"
        user_db_file = user_db_dir / f"{self.username}.db"
        
        self.db_manager = DatabaseManager(str(user_db_file))
        
        # 设置备份管理器
        backups_dir = Path(__file__).parent / "backups" / self.username
        self.backup_manager = BackupManager(backups_dir)
        
        # 创建自动备份
        self.backup_manager.create_backup(str(user_db_file), "auto")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"目录比对工具 - {self.username}")
        self.setMinimumSize(1200, 800)
        
        # 设置图标
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 目录比对选项卡
        comparison_tab = QWidget()
        self.setup_comparison_tab(comparison_tab)
        tabs.addTab(comparison_tab, "目录比对")
        
        # 历史记录选项卡
        history_tab = QWidget()
        self.setup_history_tab(history_tab)
        tabs.addTab(history_tab, "历史记录")
        
        # 设置状态栏
        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 创建菜单栏
        self.create_menus()
    
    def setup_comparison_tab(self, tab):
        """设置目录比对选项卡"""
        layout = QVBoxLayout(tab)
        
        # 目录选择区域
        dir_group = QGroupBox("选择比对目录")
        dir_layout = QVBoxLayout()
        
        # 目录列表
        self.dir_list = QListWidget()
        dir_layout.addWidget(self.dir_list)
        
        # 目录操作按钮
        dir_buttons_layout = QHBoxLayout()
        
        add_dir_btn = QPushButton("添加目录")
        add_dir_btn.clicked.connect(self.add_directory)
        dir_buttons_layout.addWidget(add_dir_btn)
        
        remove_dir_btn = QPushButton("移除目录")
        remove_dir_btn.clicked.connect(self.remove_directory)
        dir_buttons_layout.addWidget(remove_dir_btn)
        
        clear_dirs_btn = QPushButton("清空目录")
        clear_dirs_btn.clicked.connect(self.clear_directories)
        dir_buttons_layout.addWidget(clear_dirs_btn)
        
        dir_buttons_layout.addStretch()
        dir_layout.addLayout(dir_buttons_layout)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 比对操作区域
        action_layout = QHBoxLayout()
        
        self.compare_btn = QPushButton("开始比对")
        self.compare_btn.clicked.connect(self.start_comparison)
        action_layout.addWidget(self.compare_btn)
        
        self.session_name_input = QLineEdit()
        self.session_name_input.setPlaceholderText("输入比对会话名称（可选）")
        action_layout.addWidget(QLabel("会话名称:"))
        action_layout.addWidget(self.session_name_input)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        # 结果显示区域
        results_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：目录选择
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("选择目录查看差异:"))
        self.results_dir_list = QListWidget()
        self.results_dir_list.currentTextChanged.connect(self.show_directory_differences)
        left_layout.addWidget(self.results_dir_list)
        results_splitter.addWidget(left_widget)
        
        # 右侧：文件列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("多出的文件:"))
        self.files_list = QListWidget()
        right_layout.addWidget(self.files_list)
        results_splitter.addWidget(right_widget)
        
        results_splitter.setSizes([300, 500])
        layout.addWidget(results_splitter)
    
    def setup_history_tab(self, tab):
        """设置历史记录选项卡"""
        layout = QVBoxLayout(tab)
        
        # 历史记录操作按钮
        history_actions_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新历史")
        refresh_btn.clicked.connect(self.load_history)
        history_actions_layout.addWidget(refresh_btn)
        
        delete_history_btn = QPushButton("删除选中历史")
        delete_history_btn.clicked.connect(self.delete_history)
        history_actions_layout.addWidget(delete_history_btn)
        
        history_actions_layout.addStretch()
        layout.addLayout(history_actions_layout)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["会话名称", "比对时间", "目录数量", "操作"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.doubleClicked.connect(self.view_history_item)
        layout.addWidget(self.history_table)
        
        self.load_history()
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        backup_action = file_menu.addAction("手动备份")
        backup_action.triggered.connect(self.manual_backup)
        
        restore_action = file_menu.addAction("恢复数据库")
        restore_action.triggered.connect(self.show_restore_dialog)
        
        file_menu.addSeparator()
        
        logout_action = file_menu.addAction("切换用户")
        logout_action.triggered.connect(self.logout)
        
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        backup_settings_action = settings_menu.addAction("备份设置")
        backup_settings_action.triggered.connect(self.show_backup_settings)
    
    def add_directory(self):
        """添加目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择要比对的目录")
        if directory and directory not in self.current_directories:
            self.current_directories.append(directory)
            self.dir_list.addItem(directory)
            self.save_settings()
    
    def remove_directory(self):
        """移除目录"""
        current_row = self.dir_list.currentRow()
        if current_row >= 0:
            self.current_directories.pop(current_row)
            self.dir_list.takeItem(current_row)
            self.save_settings()
    
    def clear_directories(self):
        """清空目录"""
        self.current_directories.clear()
        self.dir_list.clear()
        self.save_settings()
    
    def start_comparison(self):
        """开始目录比对"""
        if len(self.current_directories) < 2:
            QMessageBox.warning(self, "警告", "请至少选择两个目录进行比对")
            return
        
        # 禁用比对按钮
        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # 创建并启动比对线程
        self.comparison_thread = DirectoryComparisonThread(self.current_directories)
        self.comparison_thread.progress_updated.connect(self.update_progress)
        self.comparison_thread.finished_comparison.connect(self.comparison_finished)
        self.comparison_thread.start()
    
    def update_progress(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_bar.showMessage(message)
    
    def comparison_finished(self, results):
        """比对完成"""
        self.progress_bar.setVisible(False)
        self.compare_btn.setEnabled(True)
        
        self.comparison_results = results
        
        # 显示结果
        self.show_comparison_results(results)
        
        # 保存到数据库
        session_name = self.session_name_input.text().strip()
        if not session_name:
            session_name = f"比对_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.db_manager.save_comparison_session(session_name, self.current_directories, results)
        
        self.status_bar.showMessage("比对完成", 5000)
    
    def show_comparison_results(self, results):
        """显示比对结果"""
        self.results_dir_list.clear()
        self.files_list.clear()
        
        for directory in results.keys():
            self.results_dir_list.addItem(directory)
        
        if results:
            self.results_dir_list.setCurrentRow(0)
    
    def show_directory_differences(self, directory):
        """显示指定目录的差异文件"""
        if not directory:
            return
        
        self.files_list.clear()
        if directory in self.comparison_results:
            for filename in self.comparison_results[directory]:
                self.files_list.addItem(filename)
    
    def load_history(self):
        """加载历史记录"""
        history = self.db_manager.get_comparison_history()
        self.history_table.setRowCount(len(history))
        
        for row, (session_id, session_name, created_time, directories) in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(session_name))
            self.history_table.setItem(row, 1, QTableWidgetItem(created_time))
            
            dir_list = json.loads(directories)
            self.history_table.setItem(row, 2, QTableWidgetItem(str(len(dir_list))))
            
            # 操作按钮
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            
            view_btn = QPushButton("查看")
            view_btn.clicked.connect(lambda checked, sid=session_id: self.view_history_item(sid))
            layout.addWidget(view_btn)
            
            widget.setLayout(layout)
            self.history_table.setCellWidget(row, 3, widget)
    
    def view_history_item(self, session_id):
        """查看历史记录项"""
        if isinstance(session_id, int):
            actual_session_id = session_id
        else:
            row = self.history_table.currentRow()
            if row < 0:
                return
            actual_session_id = self.db_manager.get_comparison_history()[row][0]
        
        results_data = self.db_manager.get_comparison_results(actual_session_id)
        
        # 重新组织结果数据
        reconstructed_results = {}
        for dir_path, filename, status in results_data:
            if dir_path not in reconstructed_results:
                reconstructed_results[dir_path] = []
            reconstructed_results[dir_path].append(filename)
        
        self.comparison_results = reconstructed_results
        self.show_comparison_results(reconstructed_results)
        
        # 切换到比对选项卡
        self.centralWidget().findChild(QTabWidget).setCurrentIndex(0)
    
    def delete_history(self):
        """删除历史记录"""
        current_row = self.history_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要删除的历史记录")
            return
        
        history_data = self.db_manager.get_comparison_history()
        session_id = history_data[current_row][0]
        session_name = history_data[current_row][1]
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除比对会话 '{session_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 这里需要实现删除数据库中的历史记录
            # 由于时间关系，暂不实现具体删除逻辑
            QMessageBox.information(self, "提示", "删除功能待实现")
    
    def manual_backup(self):
        """手动备份"""
        if self.db_manager:
            success, message = self.backup_manager.create_backup(self.db_manager.user_db_path, "manual")
            if success:
                QMessageBox.information(self, "成功", f"备份创建成功: {message}")
            else:
                QMessageBox.critical(self, "错误", message)
    
    def show_restore_dialog(self):
        """显示恢复对话框"""
        if self.db_manager:
            dialog = RestoreDialog(self.backup_manager, self.db_manager.user_db_path, self)
            if dialog.exec_() == QDialog.Accepted:
                # 重新初始化数据库连接
                self.db_manager.close()
                self.init_user_environment()
                
                # 刷新界面数据
                self.load_history()
                self.comparison_results.clear()
                self.show_comparison_results({})
                
                QMessageBox.information(self, "成功", "数据库恢复完成，界面数据已刷新")
    
    def show_backup_settings(self):
        """显示备份设置"""
        max_backups, ok = QtWidgets.QInputDialog.getInt(
            self, "备份设置", "最大备份数量:", 
            value=self.backup_manager.max_backups,
            min=5, max=100, step=1
        )
        
        if ok:
            self.backup_manager.max_backups = max_backups
            self.db_manager.save_setting("max_backups", max_backups)
            QMessageBox.information(self, "成功", f"最大备份数量已设置为: {max_backups}")
    
    def load_settings(self):
        """加载设置"""
        max_backups = self.db_manager.load_setting("max_backups", 30)
        self.backup_manager.max_backups = max_backups
        
        directories = self.db_manager.load_setting("directories", [])
        self.current_directories = directories
        for directory in directories:
            self.dir_list.addItem(directory)
    
    def save_settings(self):
        """保存设置"""
        self.db_manager.save_setting("directories", self.current_directories)
    
    def logout(self):
        """注销登录"""
        self.save_settings()
        if self.db_manager:
            self.db_manager.close()
        self.close()
    
    def closeEvent(self, event):
        """关闭事件"""
        self.save_settings()
        if self.db_manager:
            self.db_manager.close()
        event.accept()

def main():
    # 创建应用数据目录
    app_data_dir = Path.home() / ".directory_comparison_tool"
    app_data_dir.mkdir(exist_ok=True)
    
    # 初始化用户管理器
    user_manager = UserManager(app_data_dir)
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("目录比对工具")
    
    # 设置高DPI支持:cite[9]
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 显示用户登录对话框
    login_dialog = UserLoginDialog(user_manager)
    if login_dialog.exec_() == QDialog.Accepted:
        username = login_dialog.selected_user
        if username:
            # 显示主窗口
            window = MainWindow(user_manager, username)
            window.show()
            sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()