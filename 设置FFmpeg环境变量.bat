@echo off
echo 正在设置FFmpeg环境变量...

setx PATH "%PATH%;C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin" /M

echo.
echo FFmpeg环境变量已设置！
echo 请重新启动命令行窗口或重启电脑以使更改生效。
echo.
pause
