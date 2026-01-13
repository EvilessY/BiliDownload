import os
import threading
import time
import requests
import subprocess
from queue import Queue
from logger import logger
from bilibili_api import api

FFMPEG_PATH = os.environ.get('FFMPEG_PATH', os.path.join('C:', 'ffmpeg', 'ffmpeg-8.0.1-essentials_build', 'bin'))

def check_ffmpeg():
    try:
        ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
        result = subprocess.run([ffmpeg_exe, '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

class DownloadTask:
    def __init__(self, video_info, output_path, quality, format_type, download_cover=True, custom_filename=None, max_retries=3, skip_exists_check=False):
        self.video_info = video_info
        self.output_path = output_path
        self.quality = quality
        self.format_type = format_type
        self.download_cover = download_cover
        self.custom_filename = custom_filename
        self.max_retries = max_retries
        self.skip_exists_check = skip_exists_check
        
        self.bvid = video_info['bvid']
        self.cid = video_info['cid']
        self.title = video_info['title']
        
        self.status = 'pending'
        self.progress = 0
        self.downloaded_size = 0
        self.total_size = 0
        self.speed = 0
        self.eta = 0
        self.error = None
        
        self._paused = False
        self._stopped = False
        self._thread = None
        self._temp_file = None
        self._resume_data = None
        
        self.progress_callback = None
        self.complete_callback = None
        self.error_callback = None
    
    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning(f'任务已在运行: {self.title}')
            return
        
        self._paused = False
        self._stopped = False
        self.status = 'downloading'
        self._thread = threading.Thread(target=self._download)
        self._thread.start()
    
    def pause(self):
        if self.status == 'downloading':
            self._paused = True
            self.status = 'paused'
            logger.info(f'暂停下载: {self.title}')
    
    def resume(self):
        if self.status == 'paused':
            self._paused = False
            self.status = 'downloading'
            logger.info(f'继续下载: {self.title}')
    
    def stop(self):
        self._stopped = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self.status = 'error'
        self.error = '用户停止'
        logger.info(f'停止下载: {self.title}')
    
    def _download(self):
        try:
            if not check_ffmpeg():
                raise Exception('FFmpeg未安装，无法进行视频合并和音频提取。请先安装FFmpeg。')
            
            streams = api.get_video_streams(self.bvid, self.cid, self.quality)
            if not streams:
                raise Exception('无法获取视频流')
            
            video_url = streams['dash']['video'][0]['baseUrl']
            audio_url = streams['dash']['audio'][0]['baseUrl']
            
            filename = self.custom_filename if self.custom_filename else self._sanitize_filename(self.title)
            
            if self.format_type in ['mp3', 'aac', 'flac']:
                temp_audio_file = os.path.join(self.output_path, f'{filename}_audio.tmp')
                final_file = os.path.join(self.output_path, f'{filename}.{self.format_type}')
                
                if not self.skip_exists_check and os.path.exists(final_file):
                    logger.info(f'文件已存在，跳过下载: {final_file}')
                    self.status = 'skipped'
                    if self.complete_callback:
                        self.complete_callback(self)
                    return
                
                self._download_file(audio_url, temp_audio_file)
                
                if self._stopped:
                    return
                
                self._extract_audio(temp_audio_file, final_file)
                
                if os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
            else:
                temp_video_file = os.path.join(self.output_path, f'{filename}_video.tmp')
                temp_audio_file = os.path.join(self.output_path, f'{filename}_audio.tmp')
                final_file = os.path.join(self.output_path, f'{filename}.{self.format_type}')
                
                if not self.skip_exists_check and os.path.exists(final_file):
                    logger.info(f'文件已存在，跳过下载: {final_file}')
                    self.status = 'skipped'
                    if self.complete_callback:
                        self.complete_callback(self)
                    return
                
                self._download_file(video_url, temp_video_file)
                
                if self._stopped:
                    return
                
                self._download_file(audio_url, temp_audio_file)
                
                if self._stopped:
                    return
                
                self._merge_video_audio(temp_video_file, temp_audio_file, final_file)
                
                if os.path.exists(temp_video_file):
                    os.remove(temp_video_file)
                if os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
            
            if self.download_cover and self.format_type not in ['mp3', 'aac', 'flac']:
                self._download_cover(filename)
            
            self.status = 'completed'
            self.progress = 100
            
            if self.complete_callback:
                self.complete_callback(self)
            
            logger.info(f'下载完成: {self.title}')
            
        except Exception as e:
            self.status = 'error'
            self.error = str(e)
            logger.error(f'下载失败: {self.title}, 错误: {e}')
            
            if self.error_callback:
                self.error_callback(self)
    
    def _download_file(self, url, output_file):
        headers = api.session.headers.copy()
        
        resume_header = {}
        if os.path.exists(output_file):
            resume_header['Range'] = f'bytes={os.path.getsize(output_file)}-'
        
        response = requests.get(url, headers={**headers, **resume_header}, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        if resume_header:
            total_size += os.path.getsize(output_file)
        
        self.total_size = total_size
        
        mode = 'ab' if resume_header else 'wb'
        
        start_time = time.time()
        last_update_time = start_time
        last_downloaded = self.downloaded_size
        
        with open(output_file, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self._stopped:
                    break
                
                while self._paused:
                    time.sleep(0.1)
                    if self._stopped:
                        break
                
                if self._stopped:
                    break
                
                f.write(chunk)
                self.downloaded_size += len(chunk)
                
                current_time = time.time()
                if current_time - last_update_time >= 0.5:
                    elapsed = current_time - last_update_time
                    downloaded_delta = self.downloaded_size - last_downloaded
                    
                    self.speed = downloaded_delta / elapsed if elapsed > 0 else 0
                    
                    if self.speed > 0:
                        remaining = self.total_size - self.downloaded_size
                        self.eta = remaining / self.speed
                    
                    self.progress = (self.downloaded_size / self.total_size * 100) if self.total_size > 0 else 0
                    
                    if self.progress_callback:
                        self.progress_callback(self)
                    
                    last_update_time = current_time
                    last_downloaded = self.downloaded_size
    
    def _extract_audio(self, video_file, audio_file):
        try:
            logger.info(f'开始提取音频: {video_file} -> {audio_file}')
            
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
            codec = 'libmp3lame' if audio_file.endswith('.mp3') else 'aac'
            
            cmd = [
                ffmpeg_exe,
                '-i', video_file,
                '-vn',
                '-acodec', codec,
                '-ab', '192k',
                '-y',
                audio_file
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            logger.info(f'音频提取完成: {audio_file}')
            
        except Exception as e:
            logger.error(f'音频提取失败: {e}')
            raise
    
    def _merge_video_audio(self, video_file, audio_file, output_file):
        try:
            logger.info(f'开始合并视频和音频: {video_file} + {audio_file} -> {output_file}')
            
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe') if os.name == 'nt' else 'ffmpeg'
            
            cmd = [
                ffmpeg_exe,
                '-i', video_file,
                '-i', audio_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-y',
                output_file
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            logger.info(f'视频和音频合并完成: {output_file}')
            
        except Exception as e:
            logger.error(f'视频和音频合并失败: {e}')
            raise
    
    def _download_cover(self, filename):
        try:
            pic_url = self.video_info.get('pic')
            if not pic_url:
                return
            
            cover_file = os.path.join(self.output_path, f'{filename}_cover.jpg')
            
            response = api.session.get(pic_url)
            response.raise_for_status()
            
            with open(cover_file, 'wb') as f:
                f.write(response.content)
            
            logger.info(f'封面下载完成: {cover_file}')
            
        except Exception as e:
            logger.error(f'封面下载失败: {e}')
    
    def _sanitize_filename(self, filename):
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

class DownloadManager:
    def __init__(self, max_concurrent=5):
        self.max_concurrent = max_concurrent
        self.queue = Queue()
        self.active_tasks = []
        self.completed_tasks = []
        self.failed_tasks = []
        self._running = False
        self._worker_thread = None
    
    def add_task(self, task):
        self.queue.put(task)
        logger.info(f'添加下载任务: {task.title}')
        self._process_queue()
    
    def _process_queue(self):
        while len(self.active_tasks) < self.max_concurrent and not self.queue.empty():
            task = self.queue.get()
            self.active_tasks.append(task)
            
            if not task.progress_callback:
                task.progress_callback = self._on_progress
            if not task.complete_callback:
                task.complete_callback = self._on_complete
            if not task.error_callback:
                task.error_callback = self._on_error
            
            task.start()
    
    def _on_progress(self, task):
        pass
    
    def _on_complete(self, task):
        self.active_tasks.remove(task)
        self.completed_tasks.append(task)
        self._process_queue()
    
    def _on_error(self, task):
        self.active_tasks.remove(task)
        self.failed_tasks.append(task)
        self._process_queue()
    
    def pause_task(self, task):
        task.pause()
    
    def resume_task(self, task):
        task.resume()
    
    def stop_task(self, task):
        task.stop()
    
    def get_task_status(self, task):
        return {
            'title': task.title,
            'status': task.status,
            'progress': task.progress,
            'downloaded_size': task.downloaded_size,
            'total_size': task.total_size,
            'speed': task.speed,
            'eta': task.eta
        }
    
    def get_all_tasks(self):
        return {
            'active': [self.get_task_status(t) for t in self.active_tasks],
            'queued': list(self.queue.queue),
            'completed': [t.title for t in self.completed_tasks],
            'failed': [t.title for t in self.failed_tasks]
        }

download_manager = DownloadManager()
