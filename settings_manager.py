import json
import os
from config import CONFIG_DIR
from logger import logger

DEFAULT_CONFIG = {
    'default_download_path': os.path.join(os.path.expanduser('~'), 'Downloads', 'Bilibili'),
    'default_quality': '1080P',
    'default_video_format': 'mp4',
    'default_audio_format': 'mp3',
    'max_concurrent_downloads': 5,
    'download_cover': True,
    'auto_resume': True
}

class SettingsManager:
    def __init__(self):
        self.config_file = os.path.join(CONFIG_DIR, 'settings.json')
        self.config = self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f'加载配置文件失败: {e}')
                return DEFAULT_CONFIG.copy()
        else:
            return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info('配置保存成功')
            return True
        except Exception as e:
            logger.error(f'保存配置文件失败: {e}')
            return False
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config()
    
    def reset_to_default(self):
        self.config = DEFAULT_CONFIG.copy()
        self.save_config()

settings = SettingsManager()
