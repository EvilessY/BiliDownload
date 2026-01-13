import os
import subprocess
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTimeEdit, QMessageBox,
                             QGroupBox, QCheckBox, QComboBox, QFileDialog)
from PyQt5.QtCore import Qt, QTime
from logger import logger

FFMPEG_PATH = os.environ.get('FFMPEG_PATH', os.path.join('C:', 'ffmpeg', 'ffmpeg-8.0.1-essentials_build', 'bin'))

class ConvertDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_ext = os.path.splitext(file_path)[1]
        self.is_video = self.file_ext.lower() in ['.mp4', '.avi', '.flv', '.mkv', '.mov']
        
        self.init_ui()
        self.get_file_info()
    
    def init_ui(self):
        self.setWindowTitle('视频转MP3')
        self.setFixedSize(500, 450)
        
        layout = QVBoxLayout(self)
        
        info_group = QGroupBox('文件信息')
        info_layout = QVBoxLayout()
        
        self.file_label = QLabel(f'文件: {self.file_name}')
        info_layout.addWidget(self.file_label)
        
        self.duration_label = QLabel('时长: 正在获取...')
        info_layout.addWidget(self.duration_label)
        
        self.quality_label = QLabel('建议质量: 正在分析...')
        info_layout.addWidget(self.quality_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        trim_group = QGroupBox('裁剪选项（可选）')
        trim_layout = QVBoxLayout()
        
        self.trim_checkbox = QCheckBox('启用裁剪')
        self.trim_checkbox.stateChanged.connect(self.on_trim_changed)
        trim_layout.addWidget(self.trim_checkbox)
        
        time_layout = QHBoxLayout()
        
        start_layout = QVBoxLayout()
        start_label = QLabel('开始时间:')
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat('HH:mm:ss')
        self.start_time.setTime(QTime(0, 0, 0))
        self.start_time.setEnabled(False)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_time)
        
        end_layout = QVBoxLayout()
        end_label = QLabel('结束时间:')
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat('HH:mm:ss')
        self.end_time.setTime(QTime(0, 0, 0))
        self.end_time.setEnabled(False)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_time)
        
        time_layout.addLayout(start_layout)
        time_layout.addLayout(end_layout)
        trim_layout.addLayout(time_layout)
        
        trim_group.setLayout(trim_layout)
        layout.addWidget(trim_group)
        
        output_group = QGroupBox('输出设置')
        output_layout = QVBoxLayout()
        
        quality_layout = QHBoxLayout()
        quality_label = QLabel('音频质量:')
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['自动（推荐）', '128 kbps', '192 kbps', '256 kbps', '320 kbps'])
        self.quality_combo.setCurrentIndex(0)
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        
        output_layout.addLayout(quality_layout)
        
        output_name_layout = QVBoxLayout()
        output_name_label = QLabel('输出文件名:')
        self.output_name = QLineEdit()
        default_name = os.path.splitext(self.file_name)[0] + '.mp3'
        self.output_name.setText(default_name)
        output_name_layout.addWidget(output_name_label)
        output_name_layout.addWidget(self.output_name)
        
        output_layout.addLayout(output_name_layout)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        button_layout = QHBoxLayout()
        
        self.convert_button = QPushButton('开始转换')
        self.convert_button.clicked.connect(self.convert_to_mp3)
        self.convert_button.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;')
        button_layout.addWidget(self.convert_button)
        
        self.cancel_button = QPushButton('取消')
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def on_trim_changed(self, state):
        enabled = state == Qt.Checked
        self.start_time.setEnabled(enabled)
        self.end_time.setEnabled(enabled)
    
    def get_file_info(self):
        try:
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
            
            cmd = [
                ffmpeg_exe,
                '-i', self.file_path,
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore')
            
            duration = 0
            video_bitrate = 0
            
            for line in result.stderr.split('\n'):
                if 'Duration' in line:
                    duration_str = line.split('Duration: ')[1].split(',')[0].strip()
                    hours, minutes, seconds = map(float, duration_str.split(':'))
                    duration = int(hours * 3600 + minutes * 60 + seconds)
                    
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60
                    
                    self.duration_label.setText(f'时长: {hours:02d}:{minutes:02d}:{seconds:02d}')
                    self.end_time.setTime(QTime(hours, minutes, seconds))
                    break
                
                if 'bitrate' in line and 'Video' in line:
                    try:
                        bitrate_str = line.split('bitrate: ')[1].split(' ')[0]
                        video_bitrate = int(float(bitrate_str))
                    except:
                        pass
            
            if video_bitrate > 0:
                if video_bitrate >= 5000:
                    recommended_quality = '320 kbps'
                    self.quality_combo.setCurrentIndex(4)
                elif video_bitrate >= 3000:
                    recommended_quality = '256 kbps'
                    self.quality_combo.setCurrentIndex(3)
                elif video_bitrate >= 2000:
                    recommended_quality = '192 kbps'
                    self.quality_combo.setCurrentIndex(2)
                else:
                    recommended_quality = '128 kbps'
                    self.quality_combo.setCurrentIndex(1)
                
                self.quality_label.setText(f'建议质量: {recommended_quality}')
            else:
                self.quality_label.setText('建议质量: 192 kbps（默认）')
                self.quality_combo.setCurrentIndex(2)
                
        except Exception as e:
            logger.error(f'获取文件信息失败: {e}')
            self.duration_label.setText('时长: 获取失败')
            self.quality_label.setText('建议质量: 192 kbps（默认）')
            self.quality_combo.setCurrentIndex(2)
    
    def convert_to_mp3(self):
        start_time = self.start_time.time()
        end_time = self.end_time.time()
        
        use_trim = self.trim_checkbox.isChecked()
        
        if use_trim:
            start_seconds = start_time.hour() * 3600 + start_time.minute() * 60 + start_time.second()
            end_seconds = end_time.hour() * 3600 + end_time.minute() * 60 + end_time.second()
            
            if start_seconds >= end_seconds:
                QMessageBox.warning(self, '警告', '结束时间必须大于开始时间！')
                return
        
        output_file = os.path.join(os.path.dirname(self.file_path), self.output_name.text())
        
        quality_map = {
            '自动（推荐）': '192k',
            '128 kbps': '128k',
            '192 kbps': '192k',
            '256 kbps': '256k',
            '320 kbps': '320k'
        }
        
        quality_text = self.quality_combo.currentText()
        bitrate = quality_map.get(quality_text, '192k')
        
        try:
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
            
            cmd = [ffmpeg_exe]
            
            if use_trim:
                cmd.extend(['-ss', str(start_seconds), '-t', str(end_seconds - start_seconds)])
            
            cmd.extend([
                '-i', self.file_path,
                '-vn',
                '-acodec', 'libmp3lame',
                '-ab', bitrate,
                '-ar', '44100',
                '-y',
                output_file
            ])
            
            logger.info(f'开始转换: {self.file_path} -> {output_file}')
            logger.info(f'音频质量: {quality_text}')
            if use_trim:
                logger.info(f'裁剪范围: {start_time.toString("HH:mm:ss")} - {end_time.toString("HH:mm:ss")}')
            
            self.convert_button.setEnabled(False)
            self.convert_button.setText('转换中...')
            
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                logger.info(f'转换完成: {output_file}')
                QMessageBox.information(self, '成功', f'转换完成！\n\n输出文件: {output_file}')
                self.accept()
            else:
                logger.error(f'转换失败: {result.stderr}')
                QMessageBox.critical(self, '错误', f'转换失败！\n\n{result.stderr}')
            
            self.convert_button.setEnabled(True)
            self.convert_button.setText('开始转换')
            
        except Exception as e:
            logger.error(f'转换异常: {e}')
            QMessageBox.critical(self, '错误', f'转换失败！\n\n{str(e)}')
            self.convert_button.setEnabled(True)
            self.convert_button.setText('开始转换')
