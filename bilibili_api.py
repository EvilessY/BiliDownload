import requests
import time
import json
import qrcode
import os
from io import BytesIO
from PIL import Image
from logger import logger

COOKIE_FILE = 'cookies.json'

class BilibiliAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        })
        self.cookies = {}
        self.is_logged_in = False
        self.last_request_time = 0
        self.request_delay = 2.0
        self.max_retries = 5
        self.load_cookies()
    
    def save_cookies(self):
        try:
            with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cookies, f, ensure_ascii=False, indent=2)
            logger.info('Cookies已保存')
        except Exception as e:
            logger.error(f'保存Cookies失败: {e}')
    
    def load_cookies(self):
        try:
            if os.path.exists(COOKIE_FILE):
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    self.cookies = json.load(f)
                    self.session.cookies.update(self.cookies)
                    logger.info('Cookies已加载')
                    
                    if self.verify_login():
                        self.is_logged_in = True
                        logger.info('自动登录成功')
                        return True
            return False
        except Exception as e:
            logger.error(f'加载Cookies失败: {e}')
            return False
    
    def verify_login(self):
        try:
            url = 'https://api.bilibili.com/x/space/myinfo'
            response = self.session.get(url)
            data = response.json()
            return data.get('code') == 0
        except:
            return False
    
    def clear_cookies(self):
        try:
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)
            self.cookies = {}
            self.session.cookies.clear()
            self.is_logged_in = False
            logger.info('Cookies已清除')
        except Exception as e:
            logger.error(f'清除Cookies失败: {e}')
    
    def _request_with_retry(self, url, max_retries=None):
        if max_retries is None:
            max_retries = self.max_retries
        
        time.sleep(1)
        
        for attempt in range(max_retries):
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                if time_since_last < self.request_delay:
                    time.sleep(self.request_delay - time_since_last)
                
                response = self.session.get(url)
                self.last_request_time = time.time()
                
                data = response.json()
                
                if data.get('code') == -799:
                    logger.warning(f'请求被限制，等待后重试 (尝试 {attempt + 1}/{max_retries})')
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3
                        logger.info(f'等待 {wait_time} 秒后重试...')
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f'达到最大重试次数，放弃请求')
                        return None
                
                return response
            except Exception as e:
                logger.error(f'请求异常 (尝试 {attempt + 1}/{max_retries}): {e}')
                if attempt < max_retries -1:
                    time.sleep((attempt + 1) * 3)
                    continue
                else:
                    return None
        return None
    
    def get_qrcode(self):
        try:
            url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
            response = self.session.get(url)
            data = response.json()
            
            if data.get('code') == 0:
                qrcode_key = data['data']['qrcode_key']
                qrcode_url = data['data']['url']
                
                qr = qrcode.QRCode(version=1, box_size=10, border=2)
                qr.add_data(qrcode_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = buffered.getvalue()
                
                return qrcode_key, img_str
            else:
                logger.error(f'获取二维码失败: {data}')
                return None, None
        except Exception as e:
            logger.error(f'获取二维码异常: {e}')
            return None, None
    
    def check_qrcode_status(self, qrcode_key):
        try:
            url = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}'
            response = self.session.get(url)
            data = response.json()
            
            code = data.get('code')
            if code == 0:
                status = data['data']['code']
                if status == 86101:
                    return 'waiting'
                elif status == 86090:
                    return 'scanned'
                elif status == 0:
                    url = data['data']['url']
                    if url:
                        for cookie in url.split('?')[1].split('&'):
                            key, value = cookie.split('=')
                            self.cookies[key] = value
                        self.session.cookies.update(self.cookies)
                        self.is_logged_in = True
                        logger.info('登录成功')
                        return 'success'
                else:
                    return 'expired'
            return 'error'
        except Exception as e:
            logger.error(f'检查二维码状态异常: {e}')
            return 'error'
    
    def get_user_info(self):
        if not self.is_logged_in:
            return None
        
        try:
            url = 'https://api.bilibili.com/x/space/myinfo'
            response = self.session.get(url)
            data = response.json()
            
            if data.get('code') == 0:
                return data['data']
            return None
        except Exception as e:
            logger.error(f'获取用户信息异常: {e}')
            return None
    
    def get_video_info(self, url):
        try:
            bvid = self.extract_bvid(url)
            if not bvid:
                logger.error(f'无法提取BVID: {url}')
                return None
            
            api_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
            response = self._request_with_retry(api_url)
            
            if response is None:
                return None
            
            data = response.json()
            
            if data.get('code') == 0:
                video_data = data['data']
                pages = video_data.get('pages', [])
                
                info = {
                    'bvid': video_data.get('bvid'),
                    'aid': video_data.get('aid'),
                    'title': video_data.get('title'),
                    'desc': video_data.get('desc'),
                    'author': video_data['owner'].get('name'),
                    'mid': video_data['owner'].get('mid'),
                    'duration': self.format_duration(video_data.get('duration')),
                    'pubdate': video_data.get('pubdate'),
                    'pic': video_data.get('pic'),
                    'cid': video_data.get('cid'),
                    'pages': pages,
                    'is_collection': False,
                    'is_multi_page': len(pages) > 1
                }
                return info
            else:
                logger.error(f'获取视频信息失败: {data}')
                return None
        except Exception as e:
            logger.error(f'获取视频信息异常: {e}')
            return None
    
    def get_collection_info(self, url):
        try:
            if '/video/av' in url or '/video/BV' in url:
                return None
            
            import re
            match = re.search(r'bilibili\.com/opus/(\d+)', url)
            if match:
                return self.get_opus_info(match.group(1))
            
            match = re.search(r'bilibili\.com/collection/(\d+)', url)
            if match:
                return self.get_series_info(match.group(1), 'collection')
            
            match = re.search(r'bilibili\.com/medialist/detail/ml(\d+)', url)
            if match:
                return self.get_series_info(match.group(1), 'medialist')
            
            match = re.search(r'bilibili\.com/series/(\d+)', url)
            if match:
                return self.get_series_info(match.group(1), 'series')
            
            match = re.search(r'bilibili\.com/list/(\d+)', url)
            if match:
                return self.get_series_info(match.group(1), 'list')
            
            return None
        except Exception as e:
            logger.error(f'获取合集信息异常: {e}')
            return None
    
    def get_opus_info(self, oid):
        try:
            api_url = f'https://api.bilibili.com/x/space/opus/detail?opus_id={oid}'
            response = self.session.get(api_url)
            data = response.json()
            
            if data.get('code') == 0:
                opus_data = data['data']
                videos = []
                if 'list' in opus_data:
                    for item in opus_data['list']:
                        if 'modules' in item:
                            for module in item['modules']:
                                if module.get('module_type') == 'module_dynamic':
                                    if 'major' in module:
                                        if 'archive' in module['major']:
                                            video = module['major']['archive']
                                            videos.append({
                                                'bvid': video.get('bvid'),
                                                'title': video.get('title'),
                                                'duration': self.format_duration(video.get('duration_text', ''))
                                            })
                
                return {
                    'title': opus_data.get('summary', {}).get('title', '合集'),
                    'videos': videos,
                    'is_collection': True
                }
            return None
        except Exception as e:
            logger.error(f'获取动态合集信息异常: {e}')
            return None
    
    def get_series_info(self, sid, series_type):
        try:
            if series_type == 'collection':
                api_url = f'https://api.bilibili.com/x/polymer/space/seasons_archives_list?mid={sid}&sort_reverse=false&page_num=1&page_size=30'
            elif series_type == 'medialist':
                api_url = f'https://api.bilibili.com/x/polymer/web-space/medialist?mid={sid}&ps=30&pn=1'
            elif series_type == 'list':
                api_url = f'https://api.bilibili.com/x/series/series?series_id={sid}'
            else:
                api_url = f'https://api.bilibili.com/x/series/series?series_id={sid}'
            
            response = self.session.get(api_url)
            data = response.json()
            
            if data.get('code') == 0:
                videos = []
                if series_type == 'collection':
                    archives = data['data'].get('archives', [])
                    title = data['data'].get('meta', {}).get('name', '合集')
                elif series_type == 'medialist':
                    archives = data['data'].get('list', {}).get('ves', [])
                    title = data['data'].get('list', {}).get('info', {}).get('title', '合集')
                else:
                    archives = data['data'].get('archives', [])
                    title = data['data'].get('meta', {}).get('name', '合集')
                
                for video in archives:
                    videos.append({
                        'bvid': video.get('bvid'),
                        'title': video.get('title'),
                        'duration': self.format_duration(video.get('duration', ''))
                    })
                
                return {
                    'title': title,
                    'videos': videos,
                    'is_collection': True
                }
            return None
        except Exception as e:
            logger.error(f'获取系列信息异常: {e}')
            return None
    
    def get_video_streams(self, bvid, cid, quality='1080P'):
        try:
            quality_map = {
                '1080P': 80,
                '720P': 64,
                '480P': 32,
                '360P': 16
            }
            
            qn = quality_map.get(quality, 80)
            api_url = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=16&fourk=1'
            response = self._request_with_retry(api_url)
            
            if response is None:
                return None
            
            data = response.json()
            
            if data.get('code') == 0:
                return data['data']
            else:
                logger.error(f'获取视频流失败: {data}')
                return None
        except Exception as e:
            logger.error(f'获取视频流异常: {e}')
            return None
    
    def extract_bvid(self, url):
        import re
        match = re.search(r'BV[a-zA-Z0-9]+', url)
        if match:
            return match.group(0)
        return None
    
    def format_duration(self, seconds):
        if isinstance(seconds, str):
            return seconds
        minutes = seconds // 60
        seconds = seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        else:
            return f'{minutes:02d}:{seconds:02d}'
    
    def get_user_videos(self, url, page_num=None):
        try:
            import re
            match = re.search(r'space\.bilibili\.com/(\d+)', url)
            if not match:
                logger.error(f'无法提取用户ID: {url}')
                return None
            
            mid = match.group(1)
            videos = []
            page_size = 30
            
            if page_num is None:
                page = 1
                while True:
                    api_url = f'https://api.bilibili.com/x/space/arc/search?mid={mid}&ps={page_size}&pn={page}&order=pubdate&order_avoided=true'
                    response = self._request_with_retry(api_url)
                    
                    if response is None:
                        break
                    
                    data = response.json()
                    
                    if data.get('code') == 0:
                        archives = data['data'].get('list', {}).get('vlist', [])
                        if not archives:
                            break
                        
                        for video in archives:
                            videos.append({
                                'bvid': video.get('bvid'),
                                'aid': video.get('aid'),
                                'title': video.get('title'),
                                'desc': video.get('description'),
                                'author': video.get('author'),
                                'mid': video.get('mid'),
                                'duration': self.format_duration(video.get('length', 0)),
                                'pubdate': video.get('created'),
                                'pic': video.get('pic'),
                                'cid': video.get('aid'),
                                'pages': [{'cid': video.get('aid'), 'page': 1}],
                                'is_collection': False
                            })
                        
                        page += 1
                    else:
                        logger.error(f'获取用户视频列表失败: {data}')
                        break
            else:
                api_url = f'https://api.bilibili.com/x/space/arc/search?mid={mid}&ps={page_size}&pn={page_num}&order=pubdate&order_avoided=true'
                response = self._request_with_retry(api_url)
                
                if response is None:
                    return None
                
                data = response.json()
                
                if data.get('code') == 0:
                    archives = data['data'].get('list', {}).get('vlist', [])
                    
                    for video in archives:
                        videos.append({
                            'bvid': video.get('bvid'),
                            'aid': video.get('aid'),
                            'title': video.get('title'),
                            'desc': video.get('description'),
                            'author': video.get('author'),
                            'mid': video.get('mid'),
                            'duration': self.format_duration(video.get('length', 0)),
                            'pubdate': video.get('created'),
                            'pic': video.get('pic'),
                            'cid': video.get('aid'),
                            'pages': [{'cid': video.get('aid'), 'page': 1}],
                            'is_collection': False
                        })
                else:
                    logger.error(f'获取用户视频列表失败: {data}')
                    return None
            
            logger.info(f'获取到 {len(videos)} 个视频')
            return videos
        except Exception as e:
            logger.error(f'获取用户视频列表异常: {e}')
            return None
    
    def logout(self):
        self.cookies = {}
        self.session = requests.Session()
        self.is_logged_in = False
        logger.info('已退出登录')

api = BilibiliAPI()
