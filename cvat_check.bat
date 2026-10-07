@echo off
chcp 65001 >nul
rem Kiem tra nhan cuboid cua mot task CVAT 3D va ghi thuoc tinh qc nguoc vao CVAT.
rem Can: .venv (setup_windows.bat), file .cvat.env (xem .cvat.env.example), du lieu nuScenes-mini.
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
set /p TASK_ID=Nhap ID task CVAT can kiem tra:
".venv\Scripts\python.exe" scripts\cvat_check.py --task-id %TASK_ID% --nusc-root "%NUSC_ROOT%"
if errorlevel 1 (
  echo [LOI] Chay that bai. Chup man hinh loi va gui vao kenh Discord cua nhom.
  pause
  exit /b 1
)
start "" "%~dp0out\cvat_check_%TASK_ID%\index.html"
pause
