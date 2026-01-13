from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from bilibili_api import api
from logger import logger

class QRCodeCheckThread(QThread):
    status_changed = pyqtSignal(str)
    login_success = pyqtSignal()
    login_failed = pyqtSignal(str)
    
    def __init__(self, qrcode_key):
        super().__init__()
        self.qrcode_key = qrcode_key
        self._running = True
    
    def run(self):
        while self._running:
            status = api.check_qrcode_status(self.qrcode_key)
            
            if status == 'waiting':
                self.status_changed.emit('waiting')
            elif status == 'scanned':
                self.status_changed.emit('scanned')
            elif status == 'success':
                self.login_success.emit()
                break
            elif status == 'expired':
                self.login_failed.emit('二维码已过期')
                break
            elif status == 'error':
                self.login_failed.emit('登录失败')
                break
            
            self.msleep(2000)
    
    def stop(self):
        self._running = False
        self.wait()

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qrcode_key = None
        self.qrcode_thread = None
        self.init_ui()
        self.show_qrcode()
    
    def init_ui(self):
        self.setWindowTitle('扫码登录')
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel('请使用B站手机APP扫码登录')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('font-size: 16px; font-weight: bold; margin: 20px 0;')
        layout.addWidget(title_label)
        
        self.qrcode_label = QLabel()
        self.qrcode_label.setAlignment(Qt.AlignCenter)
        self.qrcode_label.setMinimumSize(300, 300)
        self.qrcode_label.setStyleSheet('border: 2px solid #ccc; border-radius: 10px;')
        layout.addWidget(self.qrcode_label)
        
        self.status_label = QLabel('正在生成二维码...')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('margin: 20px 0;')
        layout.addWidget(self.status_label)
        
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton('刷新二维码')
        self.refresh_button.clicked.connect(self.refresh_qrcode)
        button_layout.addWidget(self.refresh_button)
        
        self.cancel_button = QPushButton('取消')
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def show_qrcode(self):
        self.qrcode_key, qrcode_image = api.get_qrcode()
        
        if qrcode_image:
            pixmap = QPixmap()
            pixmap.loadFromData(qrcode_image)
            scaled_pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qrcode_label.setPixmap(scaled_pixmap)
            self.status_label.setText('请使用B站手机APP扫码')
            
            self.start_qrcode_check()
        else:
            self.status_label.setText('二维码生成失败')
    
    def start_qrcode_check(self):
        if self.qrcode_thread:
            self.qrcode_thread.stop()
        
        self.qrcode_thread = QRCodeCheckThread(self.qrcode_key)
        self.qrcode_thread.status_changed.connect(self.on_qrcode_status_changed)
        self.qrcode_thread.login_success.connect(self.on_login_success)
        self.qrcode_thread.login_failed.connect(self.on_login_failed)
        self.qrcode_thread.start()
    
    def on_qrcode_status_changed(self, status):
        if status == 'waiting':
            self.status_label.setText('请使用B站手机APP扫码')
        elif status == 'scanned':
            self.status_label.setText('已扫码，请在手机上确认登录')
    
    def on_login_success(self):
        self.status_label.setText('登录成功！')
        logger.info('用户登录成功')
        api.save_cookies()
        self.accept()
    
    def on_login_failed(self, error_msg):
        self.status_label.setText(f'登录失败: {error_msg}')
        logger.error(f'登录失败: {error_msg}')
        QMessageBox.critical(self, '错误', error_msg)
    
    def refresh_qrcode(self):
        self.show_qrcode()
    
    def closeEvent(self, event):
        if self.qrcode_thread:
            self.qrcode_thread.stop()
        event.accept()
