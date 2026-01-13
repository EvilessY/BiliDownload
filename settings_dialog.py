from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QSpinBox, QPushButton, 
                             QFormLayout, QGroupBox, QCheckBox, QMessageBox)
from settings_manager import settings
from config import VIDEO_FORMATS, AUDIO_FORMATS, QUALITY_OPTIONS

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle('设置')
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        download_group = QGroupBox('下载设置')
        download_layout = QFormLayout()
        
        self.path_input = QLineEdit()
        browse_button = QPushButton('浏览')
        browse_button.clicked.connect(self.browse_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        download_layout.addRow('默认保存路径:', path_layout)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_OPTIONS)
        download_layout.addRow('默认清晰度:', self.quality_combo)
        
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(VIDEO_FORMATS)
        download_layout.addRow('默认视频格式:', self.video_format_combo)
        
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(AUDIO_FORMATS)
        download_layout.addRow('默认音频格式:', self.audio_format_combo)
        
        self.max_downloads_spin = QSpinBox()
        self.max_downloads_spin.setMinimum(1)
        self.max_downloads_spin.setMaximum(10)
        self.max_downloads_spin.setValue(5)
        download_layout.addRow('最大同时下载数:', self.max_downloads_spin)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        other_group = QGroupBox('其他设置')
        other_layout = QVBoxLayout()
        
        self.download_cover_checkbox = QCheckBox('默认下载封面')
        other_layout.addWidget(self.download_cover_checkbox)
        
        self.auto_resume_checkbox = QCheckBox('自动断点续传')
        other_layout.addWidget(self.auto_resume_checkbox)
        
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)
        
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton('保存')
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        
        self.reset_button = QPushButton('恢复默认')
        self.reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_button)
        
        self.cancel_button = QPushButton('取消')
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        self.path_input.setText(settings.get('default_download_path'))
        self.quality_combo.setCurrentText(settings.get('default_quality'))
        self.video_format_combo.setCurrentText(settings.get('default_video_format'))
        self.audio_format_combo.setCurrentText(settings.get('default_audio_format'))
        self.max_downloads_spin.setValue(settings.get('max_concurrent_downloads'))
        self.download_cover_checkbox.setChecked(settings.get('download_cover'))
        self.auto_resume_checkbox.setChecked(settings.get('auto_resume'))
    
    def save_settings(self):
        settings.set('default_download_path', self.path_input.text())
        settings.set('default_quality', self.quality_combo.currentText())
        settings.set('default_video_format', self.video_format_combo.currentText())
        settings.set('default_audio_format', self.audio_format_combo.currentText())
        settings.set('max_concurrent_downloads', self.max_downloads_spin.value())
        settings.set('download_cover', self.download_cover_checkbox.isChecked())
        settings.set('auto_resume', self.auto_resume_checkbox.isChecked())
        
        QMessageBox.information(self, '成功', '设置已保存')
        self.accept()
    
    def reset_settings(self):
        reply = QMessageBox.question(self, '确认', '确定要恢复默认设置吗？',
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            settings.reset_to_default()
            self.load_settings()
    
    def browse_path(self):
        from PyQt5.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(self, '选择保存目录', self.path_input.text())
        if directory:
            self.path_input.setText(directory)
