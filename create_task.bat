@echo off
chcp 65001 >nul
rem Tao task CVAT 3D tu nuScenes-mini tren CVAT ghi trong .cvat.env (CVAT local cua ban).
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
set "NAME=M44 task"
set /p NAME=Ten task [M44 task]:
set "START=50"
set /p START=Bat dau tu frame so (tap val 0-80) [50]:
set "COUNT=10"
set /p COUNT=So frame [10]:
echo Nhan san: none = task trong de tu gan, gt = nhan goc nuScenes, noisy = nhan co cai loi + dap an
set "LABELS=none"
set /p LABELS=Chon none / gt / noisy [none]:
".venv\Scripts\python.exe" scripts\cvat_create_task.py --nusc-root "%NUSC_ROOT%" --split val --start-frame %START% --max-frames %COUNT% --name "%NAME%" --labels %LABELS%
pause
