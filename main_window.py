import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QCheckBox, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QProgressBar, QMessageBox, QTabWidget,
                             QGroupBox, QSplitter, QFrame, QButtonGroup, QRadioButton)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap
from bilibili_api import api
from download_manager import DownloadTask, download_manager
from settings_manager import settings
from logger import logger
from config import VIDEO_FORMATS, AUDIO_FORMATS, QUALITY_OPTIONS

class VideoInfoThread(QThread):
    info_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            video_info = api.get_video_info(self.url)
            if video_info:
                self.info_received.emit(video_info)
            else:
                self.error_occurred.emit('无法获取视频信息，请检查链接是否正确')
        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_video_info = None
        self.current_collection_info = None
        self.download_tasks = []
        self.init_ui()
        api.load_cookies()
        self.update_login_status()
        self.check_ffmpeg()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_download_progress)
        self.timer.start(500)
    
    def check_ffmpeg(self):
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                return
        except:
            pass
        
        QMessageBox.warning(self, '警告', 
            'FFmpeg未安装或未添加到环境变量！\n\n'
            '视频合并和音频提取功能需要FFmpeg支持。\n\n'
            '安装方法：\n'
            '1. 使用conda安装: conda install ffmpeg\n'
            '2. 或手动下载并添加到环境变量\n'
            '   下载地址: https://www.gyan.dev/ffmpeg/builds/')
    
    def init_ui(self):
        self.setWindowTitle('Bilibili视频下载器')
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        tab_widget = QTabWidget()
        
        download_tab = self.create_download_tab()
        trim_tab = self.create_trim_tab()
        convert_tab = self.create_convert_tab()
        rename_tab = self.create_rename_tab()
        
        tab_widget.addTab(download_tab, '下载')
        tab_widget.addTab(trim_tab, '裁剪工具')
        tab_widget.addTab(convert_tab, '转换工具')
        tab_widget.addTab(rename_tab, '批量重命名')
        
        main_layout.addWidget(tab_widget)
        
        status_bar = self.create_status_bar()
        self.setStatusBar(status_bar)
    
    def create_top_bar(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)
        
        title_label = QLabel('Bilibili视频下载器')
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        self.login_button = QPushButton('登录')
        self.login_button.clicked.connect(self.show_login_dialog)
        layout.addWidget(self.login_button)
        
        self.logout_button = QPushButton('退出登录')
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setVisible(False)
        layout.addWidget(self.logout_button)
        
        self.settings_button = QPushButton('设置')
        self.settings_button.clicked.connect(self.show_settings_dialog)
        layout.addWidget(self.settings_button)
        
        return frame
    
    def create_download_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        url_group = QGroupBox('视频链接')
        url_layout = QVBoxLayout()
        
        url_input_layout = QHBoxLayout()
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText('请输入B站视频链接或上传txt文件（每行一个链接）')
        self.url_input.setMaximumHeight(100)
        url_input_layout.addWidget(self.url_input)
        
        self.get_info_button = QPushButton('获取信息')
        self.get_info_button.clicked.connect(self.get_video_info)
        url_input_layout.addWidget(self.get_info_button)
        
        self.upload_button = QPushButton('上传txt文件')
        self.upload_button.clicked.connect(self.upload_txt_file)
        url_input_layout.addWidget(self.upload_button)
        
        url_layout.addLayout(url_input_layout)
        url_group.setLayout(url_layout)
        
        info_group = QGroupBox('视频信息')
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        
        options_group = QGroupBox('下载选项')
        options_layout = QHBoxLayout()
        
        type_layout = QVBoxLayout()
        type_label = QLabel('下载类型:')
        self.type_combo = QComboBox()
        self.type_combo.addItems(['视频', '音频'])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        options_layout.addLayout(type_layout)
        
        quality_layout = QVBoxLayout()
        quality_label = QLabel('清晰度:')
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_OPTIONS)
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        options_layout.addLayout(quality_layout)
        
        format_layout = QVBoxLayout()
        format_label = QLabel('格式:')
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        options_layout.addLayout(format_layout)
        
        path_layout = QVBoxLayout()
        path_label = QLabel('保存路径:')
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(settings.get('default_download_path'))
        path_input_layout.addWidget(self.path_input)
        
        self.browse_button = QPushButton('浏览')
        self.browse_button.clicked.connect(self.browse_path)
        path_input_layout.addWidget(self.browse_button)
        
        path_layout.addWidget(path_label)
        path_layout.addLayout(path_input_layout)
        options_layout.addLayout(path_layout)
        
        options_group.setLayout(options_layout)
        
        filename_layout = QHBoxLayout()
        filename_label = QLabel('文件名（留空使用原标题）:')
        self.filename_input = QLineEdit()
        filename_layout.addWidget(filename_label)
        filename_layout.addWidget(self.filename_input)
        
        self.download_cover_checkbox = QCheckBox('下载封面（仅视频）')
        self.download_cover_checkbox.setChecked(settings.get('download_cover', True))
        
        retry_layout = QHBoxLayout()
        retry_label = QLabel('重试次数:')
        self.download_retry_spinbox = QLineEdit('3')
        self.download_retry_spinbox.setMaximumWidth(100)
        retry_layout.addWidget(retry_label)
        retry_layout.addWidget(self.download_retry_spinbox)
        retry_layout.addStretch()
        
        button_layout = QHBoxLayout()
        
        self.download_button = QPushButton('开始下载')
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;')
        button_layout.addWidget(self.download_button)
        
        self.clear_button = QPushButton('清空')
        self.clear_button.clicked.connect(self.clear_inputs)
        button_layout.addWidget(self.clear_button)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addWidget(url_group)
        top_layout.addWidget(info_group)
        top_layout.addWidget(options_group)
        top_layout.addLayout(filename_layout)
        top_layout.addWidget(self.download_cover_checkbox)
        top_layout.addLayout(retry_layout)
        top_layout.addLayout(button_layout)
        
        progress_group = QGroupBox('下载进度')
        progress_layout = QVBoxLayout()
        
        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(8)
        self.progress_table.setHorizontalHeaderLabels(['标题', '状态', '进度', '已下载', '总大小', '速度', '剩余时间', '操作'])
        self.progress_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Interactive)
        self.progress_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Interactive)
        self.progress_table.verticalHeader().setVisible(False)
        progress_layout.addWidget(self.progress_table)
        
        progress_group.setLayout(progress_layout)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.addWidget(progress_group)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(5)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([400, 300])
        splitter.setStyleSheet('''
            QSplitter::handle {
                background-color: #cccccc;
            }
            QSplitter::handle:hover {
                background-color: #999999;
            }
            QSplitter::handle:pressed {
                background-color: #666666;
            }
        ''')
        
        layout.addWidget(splitter)
        
        return widget
    
    def create_trim_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        file_group = QGroupBox('选择文件')
        file_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        path_label = QLabel('文件路径:')
        self.trim_file_input = QLineEdit()
        self.trim_file_input.setPlaceholderText('选择要裁剪的视频或音频文件')
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.trim_file_input)
        
        browse_button = QPushButton('浏览')
        browse_button.clicked.connect(self.browse_trim_file)
        path_layout.addWidget(browse_button)
        
        file_layout.addLayout(path_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        info_group = QGroupBox('文件信息')
        info_layout = QVBoxLayout()
        
        self.trim_info_label = QLabel('请先选择文件')
        self.trim_info_label.setWordWrap(True)
        info_layout.addWidget(self.trim_info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        button_layout = QHBoxLayout()
        
        self.trim_button = QPushButton('打开裁剪工具')
        self.trim_button.clicked.connect(self.open_trim_dialog)
        self.trim_button.setEnabled(False)
        self.trim_button.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;')
        button_layout.addWidget(self.trim_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget
    
    def create_convert_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        file_group = QGroupBox('选择文件')
        file_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        path_label = QLabel('文件路径:')
        self.convert_file_input = QLineEdit()
        self.convert_file_input.setPlaceholderText('选择要转换为MP3的视频文件')
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.convert_file_input)
        
        browse_button = QPushButton('浏览')
        browse_button.clicked.connect(self.browse_convert_file)
        path_layout.addWidget(browse_button)
        
        file_layout.addLayout(path_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        info_group = QGroupBox('文件信息')
        info_layout = QVBoxLayout()
        
        self.convert_info_label = QLabel('请先选择文件')
        self.convert_info_label.setWordWrap(True)
        info_layout.addWidget(self.convert_info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        button_layout = QHBoxLayout()
        
        self.convert_button = QPushButton('打开转换工具')
        self.convert_button.clicked.connect(self.open_convert_dialog)
        self.convert_button.setEnabled(False)
        self.convert_button.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;')
        button_layout.addWidget(self.convert_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget
    
    def create_rename_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        folder_group = QGroupBox('选择文件夹')
        folder_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        path_label = QLabel('文件夹路径:')
        self.rename_folder_input = QLineEdit()
        self.rename_folder_input.setPlaceholderText('选择包含视频/音频文件的文件夹')
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.rename_folder_input)
        
        browse_button = QPushButton('浏览')
        browse_button.clicked.connect(self.browse_rename_folder)
        path_layout.addWidget(browse_button)
        
        folder_layout.addLayout(path_layout)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        mode_group = QGroupBox('重命名模式')
        mode_layout = QVBoxLayout()
        
        self.rename_mode_radio_group = QButtonGroup(self)
        
        extract_radio = QRadioButton('提取书名号内容')
        extract_radio.setChecked(True)
        extract_radio.toggled.connect(self.on_rename_mode_changed)
        self.rename_mode_radio_group.addButton(extract_radio, 0)
        
        replace_radio = QRadioButton('批量替换文本')
        replace_radio.toggled.connect(self.on_rename_mode_changed)
        self.rename_mode_radio_group.addButton(replace_radio, 1)
        
        mode_layout.addWidget(extract_radio)
        mode_layout.addWidget(replace_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        replace_group = QGroupBox('批量替换设置')
        replace_layout = QVBoxLayout()
        replace_group.setEnabled(False)
        self.replace_group = replace_group
        
        old_text_layout = QHBoxLayout()
        old_text_label = QLabel('查找文本:')
        self.replace_old_text = QLineEdit()
        self.replace_old_text.setPlaceholderText('输入要替换的文本')
        old_text_layout.addWidget(old_text_label)
        old_text_layout.addWidget(self.replace_old_text)
        replace_layout.addLayout(old_text_layout)
        
        new_text_layout = QHBoxLayout()
        new_text_label = QLabel('替换为:')
        self.replace_new_text = QLineEdit()
        self.replace_new_text.setPlaceholderText('输入替换后的文本')
        new_text_layout.addWidget(new_text_label)
        new_text_layout.addWidget(self.replace_new_text)
        replace_layout.addLayout(new_text_layout)
        
        case_sensitive_layout = QHBoxLayout()
        self.case_sensitive_checkbox = QCheckBox('区分大小写')
        self.case_sensitive_checkbox.setChecked(True)
        case_sensitive_layout.addWidget(self.case_sensitive_checkbox)
        case_sensitive_layout.addStretch()
        replace_layout.addLayout(case_sensitive_layout)
        
        replace_group.setLayout(replace_layout)
        layout.addWidget(replace_group)
        
        scan_button = QPushButton('扫描文件')
        scan_button.clicked.connect(self.scan_rename_files)
        scan_button.setStyleSheet('background-color: #2196F3; color: white; font-weight: bold; padding: 10px;')
        layout.addWidget(scan_button)
        
        preview_group = QGroupBox('重命名预览')
        preview_layout = QVBoxLayout()
        
        self.rename_table = QTableWidget()
        self.rename_table.setColumnCount(4)
        self.rename_table.setHorizontalHeaderLabels(['原文件名', '新文件名', '状态', '操作'])
        self.rename_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.rename_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.rename_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.rename_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.rename_table.verticalHeader().setVisible(False)
        self.rename_table.setSelectionBehavior(QTableWidget.SelectRows)
        preview_layout.addWidget(self.rename_table)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        button_layout = QHBoxLayout()
        
        self.execute_rename_button = QPushButton('执行重命名')
        self.execute_rename_button.clicked.connect(self.execute_rename)
        self.execute_rename_button.setEnabled(False)
        self.execute_rename_button.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;')
        button_layout.addWidget(self.execute_rename_button)
        
        self.clear_rename_button = QPushButton('清空')
        self.clear_rename_button.clicked.connect(self.clear_rename)
        button_layout.addWidget(self.clear_rename_button)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_status_bar(self):
        from PyQt5.QtWidgets import QStatusBar
        status_bar = QStatusBar()
        
        self.status_label = QLabel('就绪')
        status_bar.addWidget(self.status_label)
        
        return status_bar
    
    def get_video_info(self):
        urls = self.url_input.toPlainText().strip().split('\n')
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            QMessageBox.warning(self, '警告', '请输入视频链接')
            return
        
        if len(urls) > 1:
            self.info_text.setText(f'检测到 {len(urls)} 个链接，将批量下载\n')
            for url in urls:
                self.info_text.append(f'- {url}')
            return
        
        url = urls[0]
        
        collection_info = api.get_collection_info(url)
        if collection_info:
            self.current_collection_info = collection_info
            self.current_video_info = None
            
            info_text = f"合集名称: {collection_info['title']}\n"
            info_text += f"包含视频数: {len(collection_info['videos'])}\n\n"
            info_text += "视频列表:\n"
            for i, video in enumerate(collection_info['videos'], 1):
                info_text += f"{i}. {video['title']} ({video['duration']})\n"
            
            self.info_text.setText(info_text)
            self.status_label.setText(f'获取到合集信息: {collection_info["title"]}')
        else:
            self.info_thread = VideoInfoThread(url)
            self.info_thread.info_received.connect(self.on_video_info_received)
            self.info_thread.error_occurred.connect(self.on_video_info_error)
            self.info_thread.start()
            
            self.status_label.setText('正在获取视频信息...')
    
    def on_video_info_received(self, video_info):
        self.current_video_info = video_info
        self.current_collection_info = None
        
        info_text = f"标题: {video_info['title']}\n"
        info_text += f"UP主: {video_info['author']}\n"
        info_text += f"时长: {video_info['duration']}\n"
        info_text += f"BVID: {video_info['bvid']}\n"
        info_text += f"简介: {video_info['desc'][:100]}..."
        
        self.info_text.setText(info_text)
        self.status_label.setText(f'获取到视频信息: {video_info["title"]}')
    
    def on_video_info_error(self, error_msg):
        QMessageBox.critical(self, '错误', error_msg)
        self.status_label.setText('获取视频信息失败')
    
    def on_type_changed(self, download_type):
        if download_type == '视频':
            self.format_combo.clear()
            self.format_combo.addItems(VIDEO_FORMATS)
            self.download_cover_checkbox.setEnabled(True)
        else:
            self.format_combo.clear()
            self.format_combo.addItems(AUDIO_FORMATS)
            self.download_cover_checkbox.setEnabled(False)
    
    def upload_txt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择txt文件', 
            '', 
            'Text Files (*.txt);;All Files (*)'
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = f.read()
                    self.url_input.setPlainText(urls)
                    self.status_label.setText(f'已加载文件: {os.path.basename(file_path)}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'读取文件失败: {e}')
    
    def browse_path(self):
        directory = QFileDialog.getExistingDirectory(self, '选择保存目录', self.path_input.text())
        if directory:
            self.path_input.setText(directory)
    
    def start_download(self):
        urls = self.url_input.toPlainText().strip().split('\n')
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            QMessageBox.warning(self, '警告', '请输入视频链接或上传txt文件')
            return
        
        output_path = self.path_input.text()
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法创建目录: {e}')
                return
        
        quality = self.quality_combo.currentText()
        format_type = self.format_combo.currentText()
        download_type = self.type_combo.currentText()
        download_cover = self.download_cover_checkbox.isChecked()
        custom_filename = self.filename_input.text().strip() if self.filename_input.text().strip() else None
        
        try:
            retry_count = int(self.download_retry_spinbox.text())
        except:
            retry_count = 3
        
        api.max_retries = retry_count
        
        self.download_tasks = []
        self.progress_table.setRowCount(0)
        
        import time
        
        for i, url in enumerate(urls, 1):
            self.status_label.setText(f'正在获取视频信息 ({i}/{len(urls)})...')
            QApplication.processEvents()
            
            collection_info = api.get_collection_info(url)
            if collection_info and collection_info.get('is_collection'):
                videos = collection_info.get('videos', [])
                self.status_label.setText(f'合集 "{collection_info.get("title")}" 包含 {len(videos)} 个视频')
                logger.info(f'合集 "{collection_info.get("title")}" 包含 {len(videos)} 个视频')
                QApplication.processEvents()
                
                for video in videos:
                    video_url = f'https://www.bilibili.com/video/{video["bvid"]}'
                    logger.info(f'处理合集视频: {video["title"]} ({video_url})')
                    video_info = api.get_video_info(video_url)
                    if video_info:
                        task = DownloadTask(
                            video_info,
                            output_path,
                            quality,
                            format_type,
                            download_cover and download_type == '视频',
                            custom_filename,
                            retry_count,
                            skip_exists_check=True
                        )
                        self.download_tasks.append(task)
                        
                        row = self.progress_table.rowCount()
                        self.progress_table.insertRow(row)
                        self.progress_table.setItem(row, 0, QTableWidgetItem(task.title))
                        self.progress_table.setItem(row, 1, QTableWidgetItem('等待中'))
                        self.progress_table.setItem(row, 2, QTableWidgetItem('0%'))
                        self.progress_table.setItem(row, 3, QTableWidgetItem('0 MB'))
                        self.progress_table.setItem(row, 4, QTableWidgetItem('0 MB'))
                        self.progress_table.setItem(row, 5, QTableWidgetItem('0'))
                        self.progress_table.setItem(row, 6, QTableWidgetItem(''))
                        
                        task.progress_callback = lambda t, r=row: self.on_task_progress(t, r)
                        task.complete_callback = lambda t, r=row: self.on_task_complete(t, r)
                        task.error_callback = lambda t, r=row: self.on_task_error(t, r)
                        
                        download_manager.add_task(task)
                    else:
                        logger.error(f'无法获取合集视频信息: {video_url}')
            else:
                logger.info(f'获取视频信息: {url}')
                video_info = api.get_video_info(url)
                if video_info:
                    if video_info.get('is_multi_page', False):
                        pages = video_info.get('pages', [])
                        self.status_label.setText(f'视频 "{video_info.get("title")}" 包含 {len(pages)} 个分集')
                        logger.info(f'视频 "{video_info.get("title")}" 包含 {len(pages)} 个分集')
                        QApplication.processEvents()
                        
                        for page in pages:
                            page_info = video_info.copy()
                            page_info['cid'] = page.get('cid')
                            page_info['title'] = f"{video_info.get('title')} - {page.get('part')}"
                            page_info['is_multi_page'] = False
                            
                            task = DownloadTask(
                                page_info,
                                output_path,
                                quality,
                                format_type,
                                download_cover and download_type == '视频',
                                custom_filename,
                                retry_count,
                                skip_exists_check=True
                            )
                            self.download_tasks.append(task)
                            
                            row = self.progress_table.rowCount()
                            self.progress_table.insertRow(row)
                            self.progress_table.setItem(row, 0, QTableWidgetItem(task.title))
                            self.progress_table.setItem(row, 1, QTableWidgetItem('等待中'))
                            self.progress_table.setItem(row, 2, QTableWidgetItem('0%'))
                            self.progress_table.setItem(row, 3, QTableWidgetItem('0 MB'))
                            self.progress_table.setItem(row, 4, QTableWidgetItem('0 MB'))
                            self.progress_table.setItem(row, 5, QTableWidgetItem('0'))
                            self.progress_table.setItem(row, 6, QTableWidgetItem(''))
                            
                            task.progress_callback = lambda t, r=row: self.on_task_progress(t, r)
                            task.complete_callback = lambda t, r=row: self.on_task_complete(t, r)
                            task.error_callback = lambda t, r=row: self.on_task_error(t, r)
                            
                            download_manager.add_task(task)
                    else:
                        task = DownloadTask(
                            video_info,
                            output_path,
                            quality,
                            format_type,
                            download_cover and download_type == '视频',
                            custom_filename,
                            retry_count,
                            skip_exists_check=True
                        )
                        self.download_tasks.append(task)
                        
                        row = self.progress_table.rowCount()
                        self.progress_table.insertRow(row)
                        self.progress_table.setItem(row, 0, QTableWidgetItem(task.title))
                        self.progress_table.setItem(row, 1, QTableWidgetItem('等待中'))
                        self.progress_table.setItem(row, 2, QTableWidgetItem('0%'))
                        self.progress_table.setItem(row, 3, QTableWidgetItem('0 MB'))
                        self.progress_table.setItem(row, 4, QTableWidgetItem('0 MB'))
                        self.progress_table.setItem(row, 5, QTableWidgetItem('0'))
                        
                        task.progress_callback = lambda t, r=row: self.on_task_progress(t, r)
                        task.complete_callback = lambda t, r=row: self.on_task_complete(t, r)
                        task.error_callback = lambda t, r=row: self.on_task_error(t, r)
                        
                        download_manager.add_task(task)
                else:
                    logger.error(f'无法获取视频信息: {url}')
            
            if i < len(urls):
                time.sleep(2)
        
        self.status_label.setText(f'已添加 {len(self.download_tasks)} 个下载任务')
    
    def update_download_progress(self):
        for i, task in enumerate(self.download_tasks):
            if i < self.progress_table.rowCount():
                status_map = {
                    'pending': '等待中',
                    'downloading': '下载中',
                    'paused': '已暂停',
                    'completed': '已完成',
                    'error': '失败',
                    'stopped': '已停止',
                    'skipped': '已跳过'
                }
                
                self.progress_table.setItem(i, 1, QTableWidgetItem(status_map.get(task.status, task.status)))
                self.progress_table.setItem(i, 2, QTableWidgetItem(f'{task.progress:.1f}%'))
                self.progress_table.setItem(i, 3, QTableWidgetItem(self.format_size(task.downloaded_size)))
                self.progress_table.setItem(i, 4, QTableWidgetItem(self.format_size(task.total_size)))
                self.progress_table.setItem(i, 5, QTableWidgetItem(self.format_speed(task.speed)))
                self.progress_table.setItem(i, 6, QTableWidgetItem(self.format_time(task.eta)))
                
                self.update_operation_button(i, task)
    
    def update_operation_button(self, row, task):
        if task.status == 'downloading':
            stop_button = QPushButton('停止')
            stop_button.clicked.connect(lambda _, r=row: self.stop_download_task(r))
            self.progress_table.setCellWidget(row, 7, stop_button)
        elif task.status == 'error':
            retry_button = QPushButton('重新下载')
            retry_button.clicked.connect(lambda _, r=row: self.retry_download_task(r))
            self.progress_table.setCellWidget(row, 7, retry_button)
        else:
            self.progress_table.setCellWidget(row, 7, None)
    
    def stop_download_task(self, row):
        if row < len(self.download_tasks):
            task = self.download_tasks[row]
            if task.status == 'downloading':
                task.stop()
                logger.info(f'停止下载: {task.title}')
    
    def retry_download_task(self, row):
        if row < len(self.download_tasks):
            task = self.download_tasks[row]
            if task.status == 'error':
                task.status = 'pending'
                task.progress = 0
                task.downloaded_size = 0
                task.speed = 0
                task.eta = 0
                task.error = None
                task.skip_exists_check = False
                download_manager.add_task(task)
                logger.info(f'重新下载: {task.title}')
    
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{size:.2f} TB'
    
    def format_speed(self, speed):
        return self.format_size(speed) + '/s'
    
    def format_time(self, seconds):
        if seconds == 0:
            return '--:--'
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        hours = minutes // 60
        minutes = minutes % 60
        if hours > 0:
            return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        else:
            return f'{minutes:02d}:{seconds:02d}'
    
    def on_task_progress(self, task, row):
        if row < self.progress_table.rowCount():
            status_map = {
                'pending': '等待中',
                'downloading': '下载中',
                'paused': '已暂停',
                'completed': '已完成',
                'error': '失败',
                'stopped': '已停止',
                'skipped': '已跳过'
            }
            
            self.progress_table.setItem(row, 1, QTableWidgetItem(status_map.get(task.status, task.status)))
            self.progress_table.setItem(row, 2, QTableWidgetItem(f'{task.progress:.1f}%'))
            self.progress_table.setItem(row, 3, QTableWidgetItem(self.format_size(task.downloaded_size)))
            self.progress_table.setItem(row, 4, QTableWidgetItem(self.format_size(task.total_size)))
            self.progress_table.setItem(row, 5, QTableWidgetItem(self.format_speed(task.speed)))
            self.progress_table.setItem(row, 6, QTableWidgetItem(self.format_time(task.eta)))
    
    def on_task_complete(self, task, row):
        if task in download_manager.active_tasks:
            download_manager.active_tasks.remove(task)
        
        if task.status == 'completed':
            if row < self.progress_table.rowCount():
                self.progress_table.setItem(row, 1, QTableWidgetItem('已完成'))
                self.progress_table.setItem(row, 2, QTableWidgetItem('100%'))
            logger.info(f'下载完成: {task.title}')
        elif task.status == 'skipped':
            if row < self.progress_table.rowCount():
                self.progress_table.setItem(row, 1, QTableWidgetItem('已跳过'))
                self.progress_table.setItem(row, 2, QTableWidgetItem('100%'))
            logger.info(f'下载跳过: {task.title}')
        elif task.status == 'error':
            if row < self.progress_table.rowCount():
                self.progress_table.setItem(row, 1, QTableWidgetItem('失败'))
            logger.error(f'下载失败: {task.title}, 错误: {task.error}')
        
        download_manager._process_queue()
    
    def on_task_error(self, task, row):
        if task in download_manager.active_tasks:
            download_manager.active_tasks.remove(task)
        
        if row < self.progress_table.rowCount():
            self.progress_table.setItem(row, 1, QTableWidgetItem('失败'))
        logger.error(f'下载失败: {task.title}, 错误: {task.error}')
        
        download_manager._process_queue()
    
    def clear_inputs(self):
        self.url_input.clear()
        self.info_text.clear()
        self.filename_input.clear()
        self.current_video_info = None
        self.current_collection_info = None
        self.status_label.setText('已清空输入')
    
    def show_login_dialog(self):
        from login_dialog import LoginDialog
        dialog = LoginDialog(self)
        if dialog.exec_() == LoginDialog.Accepted:
            self.update_login_status()
    
    def show_settings_dialog(self):
        from settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec_() == SettingsDialog.Accepted:
            pass
    
    def browse_trim_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择要裁剪的文件',
            settings.get('default_download_path', os.path.expanduser('~/Downloads')),
            '视频文件 (*.mp4 *.avi *.flv *.mkv *.mov);;音频文件 (*.mp3 *.aac *.flac *.wav);;所有文件 (*.*)'
        )
        
        if file_path:
            self.trim_file_input.setText(file_path)
            self.trim_button.setEnabled(True)
            
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            
            self.trim_info_label.setText(f'文件: {file_name}\n大小: {size_mb:.2f} MB\n\n点击"打开裁剪工具"开始裁剪')
    
    def open_trim_dialog(self):
        file_path = self.trim_file_input.text()
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, '警告', '请先选择有效的文件')
            return
        
        from trim_dialog import TrimDialog
        dialog = TrimDialog(file_path, self)
        dialog.exec_()
    
    def browse_convert_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择要转换的视频文件',
            settings.get('default_download_path', os.path.expanduser('~/Downloads')),
            '视频文件 (*.mp4 *.avi *.flv *.mkv *.mov);;所有文件 (*.*)'
        )
        
        if file_path:
            self.convert_file_input.setText(file_path)
            self.convert_button.setEnabled(True)
            
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            
            self.convert_info_label.setText(f'文件: {file_name}\n大小: {size_mb:.2f} MB\n\n点击"打开转换工具"开始转换')
    
    def open_convert_dialog(self):
        file_path = self.convert_file_input.text()
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, '警告', '请先选择有效的文件')
            return
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in ['.mp4', '.avi', '.flv', '.mkv', '.mov']:
            QMessageBox.warning(self, '警告', '只能转换视频文件为MP3')
            return
        
        from convert_dialog import ConvertDialog
        dialog = ConvertDialog(file_path, self)
        dialog.exec_()
    
    def browse_rename_folder(self):
        directory = QFileDialog.getExistingDirectory(self, '选择文件夹', '')
        if directory:
            self.rename_folder_input.setText(directory)
    
    def scan_rename_files(self):
        folder_path = self.rename_folder_input.text().strip()
        
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, '警告', '请先选择有效的文件夹')
            return
        
        if not os.path.isdir(folder_path):
            QMessageBox.warning(self, '警告', '请选择文件夹而不是文件')
            return
        
        self.rename_table.setRowCount(0)
        self.rename_files = []
        
        video_extensions = ['.mp4', '.avi', '.flv', '.mkv', '.mov', '.wmv', '.mp3', '.flac', '.aac', '.m4a']
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in video_extensions:
                continue
            
            new_name = self.get_new_name(filename)
            
            row = self.rename_table.rowCount()
            self.rename_table.insertRow(row)
            
            self.rename_table.setItem(row, 0, QTableWidgetItem(filename))
            
            if new_name:
                new_filename = new_name + file_ext
                self.rename_table.setItem(row, 1, QTableWidgetItem(new_filename))
                self.rename_table.setItem(row, 2, QTableWidgetItem('待重命名'))
                
                rename_button = QPushButton('跳过')
                rename_button.clicked.connect(lambda _, r=row: self.skip_rename_file(r))
                self.rename_table.setCellWidget(row, 3, rename_button)
                
                self.rename_files.append({
                    'old_path': file_path,
                    'new_name': new_filename,
                    'skip': False
                })
            else:
                mode = self.rename_mode_radio_group.checkedId()
                if mode == 0:
                    self.rename_table.setItem(row, 1, QTableWidgetItem('无书名号'))
                else:
                    self.rename_table.setItem(row, 1, QTableWidgetItem('未匹配'))
                self.rename_table.setItem(row, 2, QTableWidgetItem('跳过'))
                self.rename_table.setItem(row, 3, QTableWidgetItem('-'))
        
        self.execute_rename_button.setEnabled(len(self.rename_files) > 0)
        self.status_label.setText(f'扫描完成，找到 {len(self.rename_files)} 个需要重命名的文件')
    
    def extract_book_title(self, filename):
        import re
        
        pattern_book = r'《([^》]+)》'
        match = re.search(pattern_book, filename)
        
        if match:
            return match.group(1)
        
        pattern_bracket = r'【([^】]+)】'
        match = re.search(pattern_bracket, filename)
        
        if match:
            return match.group(1)
        
        return None
    
    def on_rename_mode_changed(self):
        mode = self.rename_mode_radio_group.checkedId()
        self.replace_group.setEnabled(mode == 1)
    
    def get_new_name(self, filename):
        mode = self.rename_mode_radio_group.checkedId()
        
        if mode == 0:
            return self.extract_book_title(filename)
        else:
            old_text = self.replace_old_text.text().strip()
            new_text = self.replace_new_text.text().strip()
            case_sensitive = self.case_sensitive_checkbox.isChecked()
            
            if not old_text:
                return None
            
            if case_sensitive:
                if old_text not in filename:
                    return None
                new_name = filename.replace(old_text, new_text)
            else:
                if old_text.lower() not in filename.lower():
                    return None
                new_name = filename.replace(old_text, new_text)
            
            return os.path.splitext(new_name)[0]
    
    def skip_rename_file(self, row):
        if row < len(self.rename_files):
            self.rename_files[row]['skip'] = True
            self.rename_table.setItem(row, 2, QTableWidgetItem('已跳过'))
            self.rename_table.setCellWidget(row, 3, None)
    
    def execute_rename(self):
        if not hasattr(self, 'rename_files') or not self.rename_files:
            QMessageBox.warning(self, '警告', '没有需要重命名的文件')
            return
        
        reply = QMessageBox.question(self, '确认', 
            f'确定要重命名 {len(self.rename_files)} 个文件吗？\n\n'
            '此操作不可撤销！',
            QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for i, file_info in enumerate(self.rename_files):
            if file_info['skip']:
                skip_count += 1
                continue
            
            old_path = file_info['old_path']
            new_name = file_info['new_name']
            folder = os.path.dirname(old_path)
            new_path = os.path.join(folder, new_name)
            
            try:
                os.rename(old_path, new_path)
                self.rename_table.setItem(i, 2, QTableWidgetItem('成功'))
                self.rename_table.setCellWidget(i, 3, None)
                success_count += 1
                logger.info(f'重命名成功: {os.path.basename(old_path)} -> {new_name}')
            except Exception as e:
                self.rename_table.setItem(i, 2, QTableWidgetItem(f'失败: {str(e)}'))
                fail_count += 1
                logger.error(f'重命名失败: {os.path.basename(old_path)}, 错误: {e}')
        
        self.execute_rename_button.setEnabled(False)
        self.status_label.setText(f'重命名完成：成功 {success_count} 个，跳过 {skip_count} 个，失败 {fail_count} 个')
        
        QMessageBox.information(self, '完成', 
            f'重命名操作完成！\n\n'
            f'成功: {success_count} 个\n'
            f'跳过: {skip_count} 个\n'
            f'失败: {fail_count} 个')
    
    def clear_rename(self):
        self.rename_table.setRowCount(0)
        self.rename_folder_input.clear()
        if hasattr(self, 'rename_files'):
            self.rename_files = []
        self.execute_rename_button.setEnabled(False)
        self.status_label.setText('已清空重命名列表')
    
    def update_login_status(self):
        if api.is_logged_in:
            user_info = api.get_user_info()
            if user_info:
                self.login_button.setText(f'{user_info.get("name", "已登录")}')
                self.login_button.setVisible(False)
                self.logout_button.setVisible(True)
                self.status_label.setText(f'已登录: {user_info.get("name", "")}')
            else:
                self.login_button.setText('已登录')
                self.login_button.setVisible(False)
                self.logout_button.setVisible(True)
                self.status_label.setText('已登录')
        else:
            self.login_button.setText('登录')
            self.login_button.setVisible(True)
            self.logout_button.setVisible(False)
            self.status_label.setText('未登录')
    
    def logout(self):
        reply = QMessageBox.question(self, '确认', '确定要退出登录吗？',
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            api.clear_cookies()
            self.update_login_status()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())
