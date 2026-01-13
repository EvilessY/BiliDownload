import os
import ffmpeg
from logger import logger

class AudioConverter:
    @staticmethod
    def extract_audio(video_file, audio_file, audio_format='mp3', bitrate='192k'):
        try:
            logger.info(f'开始提取音频: {video_file} -> {audio_file}')
            
            codec_map = {
                'mp3': 'libmp3lame',
                'aac': 'aac',
                'flac': 'flac'
            }
            
            codec = codec_map.get(audio_format, 'libmp3lame')
            
            (
                ffmpeg
                .input(video_file)
                .output(audio_file, acodec=codec, audio_bitrate=bitrate)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f'音频提取完成: {audio_file}')
            return True
            
        except ffmpeg.Error as e:
            logger.error(f'音频提取失败: {e.stderr.decode("utf-8")}')
            return False
        except Exception as e:
            logger.error(f'音频提取异常: {e}')
            return False
    
    @staticmethod
    def convert_audio(input_file, output_file, output_format='mp3', bitrate='192k'):
        try:
            logger.info(f'开始转换音频: {input_file} -> {output_file}')
            
            codec_map = {
                'mp3': 'libmp3lame',
                'aac': 'aac',
                'flac': 'flac'
            }
            
            codec = codec_map.get(output_format, 'libmp3lame')
            
            (
                ffmpeg
                .input(input_file)
                .output(output_file, acodec=codec, audio_bitrate=bitrate)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f'音频转换完成: {output_file}')
            return True
            
        except ffmpeg.Error as e:
            logger.error(f'音频转换失败: {e.stderr.decode("utf-8")}')
            return False
        except Exception as e:
            logger.error(f'音频转换异常: {e}')
            return False
    
    @staticmethod
    def get_audio_info(file_path):
        try:
            probe = ffmpeg.probe(file_path)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            
            if audio_stream:
                return {
                    'codec': audio_stream.get('codec_name'),
                    'sample_rate': audio_stream.get('sample_rate'),
                    'channels': audio_stream.get('channels'),
                    'duration': float(probe['format'].get('duration', 0)),
                    'bit_rate': audio_stream.get('bit_rate')
                }
            return None
        except Exception as e:
            logger.error(f'获取音频信息失败: {e}')
            return None

class VideoConverter:
    @staticmethod
    def convert_video(input_file, output_file, output_format='mp4', video_codec='libx264', audio_codec='aac'):
        try:
            logger.info(f'开始转换视频: {input_file} -> {output_file}')
            
            (
                ffmpeg
                .input(input_file)
                .output(output_file, vcodec=video_codec, acodec=audio_codec)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f'视频转换完成: {output_file}')
            return True
            
        except ffmpeg.Error as e:
            logger.error(f'视频转换失败: {e.stderr.decode("utf-8")}')
            return False
        except Exception as e:
            logger.error(f'视频转换异常: {e}')
            return False
    
    @staticmethod
    def get_video_info(file_path):
        try:
            probe = ffmpeg.probe(file_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            
            info = {
                'duration': float(probe['format'].get('duration', 0)),
                'size': int(probe['format'].get('size', 0)),
                'format': probe['format'].get('format_name', '')
            }
            
            if video_stream:
                info['video'] = {
                    'codec': video_stream.get('codec_name'),
                    'width': video_stream.get('width'),
                    'height': video_stream.get('height'),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'bit_rate': video_stream.get('bit_rate')
                }
            
            if audio_stream:
                info['audio'] = {
                    'codec': audio_stream.get('codec_name'),
                    'sample_rate': audio_stream.get('sample_rate'),
                    'channels': audio_stream.get('channels'),
                    'bit_rate': audio_stream.get('bit_rate')
                }
            
            return info
        except Exception as e:
            logger.error(f'获取视频信息失败: {e}')
            return None

audio_converter = AudioConverter()
video_converter = VideoConverter()
