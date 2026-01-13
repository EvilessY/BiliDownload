import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

VIDEO_FORMATS = ['mp4', 'avi', 'flv']
AUDIO_FORMATS = ['mp3', 'aac', 'flac']
QUALITY_OPTIONS = ['1080P', '720P', '480P', '360P']
MAX_CONCURRENT_DOWNLOADS = 5
