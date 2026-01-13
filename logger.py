import logging
import os
from datetime import datetime
from config import LOGS_DIR

class Logger:
    def __init__(self):
        self.logger = logging.getLogger('BilibiliDownload')
        self.logger.setLevel(logging.DEBUG)
        
        log_file = os.path.join(LOGS_DIR, f'bilibili_download_{datetime.now().strftime("%Y%m%d")}.log')
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        self.logger.debug(message)

logger = Logger()
