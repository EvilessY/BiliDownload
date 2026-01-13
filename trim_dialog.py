import os
import subprocess
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTimeEdit, QMessageBox,
                             QGroupBox, QFileDialog)
from PyQt5.QtCore import Qt, QTime
from logger import logger

FFMPEG_PATH = os.environ.get('FFMPEG_PATH', os.path.join('C:', 'ffmpeg', 'ffmpeg-8.0.1-essentials_build', 'bin'))

class TrimDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_ext = os.path.splitext(file_path)[1]
        self.is_video = self.file_ext.lower() in ['.mp4', '.avi', '.flv', '.mkv', '.mov']
        
        self.init_ui()
        self.get_file_duration()
    
    def init_ui(self):
        self.setWindowTitle('裁剪工具')
        self.setFixedSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        info_group = QGroupBox('文件信息')
        info_layout = QVBoxLayout()
        
        self.file_label = QLabel(f'文件: {self.file_name}')
        info_layout.addWidget(self.file_label)
        
        self.duration_label = QLabel('时长: 正在获取...')
        info_layout.addWidget(self.duration_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        trim_group = QGroupBox('裁剪设置')
        trim_layout = QVBoxLayout()
        
        time_layout = QHBoxLayout()
        
        start_layout = QVBoxLayout()
        start_label = QLabel('开始时间:')
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat('HH:mm:ss')
        self.start_time.setTime(QTime(0, 0, 0))
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_time)
        
        end_layout = QVBoxLayout()
        end_label = QLabel('结束时间:')
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat('HH:mm:ss')
        self.end_time.setTime(QTime(0, 0, 0))
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_time)
        
        time_layout.addLayout(start_layout)
        time_layout.addLayout(end_layout)
        trim_layout.addLayout(time_layout)
        
        output_layout = QVBoxLayout()
        output_label = QLabel('输出文件名:')
        self.output_name = QLineEdit()
        default_name = os.path.splitext(self.file_name)[0] + '_cut' + self.file_ext
        self.output_name.setText(default_name)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_name)
        
        trim_layout.addLayout(output_layout)
        
        trim_group.setLayout(trim_layout)
        layout.addWidget(trim_group)
        
        button_layout = QHBoxLayout()
        
        self.trim_button = QPushButton('开始裁剪')
        self.trim_button.clicked.connect(self.trim_file)
        self.trim_button.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;')
        button_layout.addWidget(self.trim_button)
        
        self.cancel_button = QPushButton('取消')
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_file_duration(self):
        try:
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
            
            cmd = [
                ffmpeg_exe,
                '-i', self.file_path,
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore')
            
            for line in result.stderr.split('\n'):
                if 'Duration' in line:
                    duration_str = line.split('Duration: ')[1].split(',')[0].strip()
                    hours, minutes, seconds = map(float, duration_str.split(':'))
                    total_seconds = int(hours * 3600 + minutes * 60 + seconds)
                    
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    self.duration_label.setText(f'时长: {hours:02d}:{minutes:02d}:{seconds:02d}')
                    self.end_time.setTime(QTime(hours, minutes, seconds))
                    break
        except Exception as e:
            logger.error(f'获取文件时长失败: {e}')
            self.duration_label.setText('时长: 获取失败')
    
    def trim_file(self):
        start_time = self.start_time.time()
        end_time = self.end_time.time()
        
        start_seconds = start_time.hour() * 3600 + start_time.minute() * 60 + start_time.second()
        end_seconds = end_time.hour() * 3600 + end_time.minute() * 60 + end_time.second()
        
        if start_seconds >= end_seconds:
            QMessageBox.warning(self, '警告', '结束时间必须大于开始时间！')
            return
        
        duration = end_seconds - start_seconds
        output_file = os.path.join(os.path.dirname(self.file_path), self.output_name.text())
        
        try:
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
            
            cmd = [
                ffmpeg_exe,
                '-i', self.file_path,
                '-ss', str(start_seconds),
                '-t', str(duration),
                '-c', 'copy',
                '-y',
                output_file
            ]
            
            logger.info(f'开始裁剪: {self.file_path} -> {output_file}')
            logger.info(f'时间范围: {start_time.toString("HH:mm:ss")} - {end_time.toString("HH:mm:ss")}')
            
            self.trim_button.setEnabled(False)
            self.trim_button.setText('裁剪中...')
            
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                logger.info(f'裁剪完成: {output_file}')
                QMessageBox.information(self, '成功', f'裁剪完成！\n\n输出文件: {output_file}')
                self.accept()
            else:
                logger.error(f'裁剪失败: {result.stderr}')
                QMessageBox.critical(self, '错误', f'裁剪失败！\n\n{result.stderr}')
            
            self.trim_button.setEnabled(True)
            self.trim_button.setText('开始裁剪')
            
        except Exception as e:
            logger.error(f'裁剪异常: {e}')
            QMessageBox.critical(self, '错误', f'裁剪失败！\n\n{str(e)}')
            self.trim_button.setEnabled(True)
            self.trim_button.setText('开始裁剪')
