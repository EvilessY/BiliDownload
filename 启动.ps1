# Bilibili Downloader Launcher
Write-Host "Starting Bilibili Downloader..." -ForegroundColor Green

# Add FFmpeg to PATH for this session
$ffmpegPath = "C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
$env:Path = $env:Path + ";" + $ffmpegPath

# Also set it for child processes
$env:FFMPEG_PATH = $ffmpegPath

try {
    ffmpeg -version | Out-Null
    Write-Host "FFmpeg is ready!" -ForegroundColor Green
} catch {
    Write-Host "Warning: FFmpeg not found" -ForegroundColor Yellow
}

# Start Python with the updated environment
$pythonPath = "C:\Users\yiyic\AppData\Local\Programs\Python\Python313\python.exe"
$env:Path = $env:Path + ";" + $ffmpegPath
& $pythonPath main.py

Write-Host ""
Write-Host "Press any key to exit..."
$Host.UI.RawUI.ReadKey() | Out-Null
