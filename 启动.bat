@echo off
chcp 65001 > nul
echo Starting Bilibili Downloader...

set PATH=%PATH%;C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin
set FFMPEG_PATH=C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin

"C:\Users\yiyic\AppData\Local\Programs\Python\Python313\python.exe" main.py

pause
