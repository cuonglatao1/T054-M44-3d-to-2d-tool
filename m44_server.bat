@echo off
chcp 65001 >nul
rem Bat dich vu M44 (giu cua so nay mo trong luc lam viec). Trang huong dan tu mo trong trinh duyet.
cd /d "%~dp0"
if not defined NUSC_ROOT set "NUSC_ROOT=%~dp0data\nuscenes"
if not exist ".venv\Scripts\python.exe" (
  echo [LOI] Chua cai dat. Bam dup setup_windows.bat truoc.
  pause
  exit /b 1
)
if not exist ".cvat.env" (
  echo [LOI] Chua co file .cvat.env. Copy .cvat.env.example thanh .cvat.env va dien thong tin CVAT.
  pause
  exit /b 1
)
echo Dich vu M44 dang chay. Dong cua so nay de tat.
".venv\Scripts\python.exe" scripts\m44_server.py --open
pause
