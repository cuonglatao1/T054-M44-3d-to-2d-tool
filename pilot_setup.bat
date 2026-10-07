@echo off
chcp 65001 >nul
rem Tao 2 task pilot (bo A va bo B) tren CVAT cua ban. Moi nguoi chay dung file nay de co cung du lieu + cung loi.
cd /d "%~dp0"
if not defined NUSC_ROOT set "NUSC_ROOT=%~dp0data\nuscenes"
if not exist ".venv\Scripts\python.exe" (
  echo [LOI] Chua cai dat. Bam dup setup_windows.bat truoc.
  pause
  exit /b 1
)
if not exist ".cvat.env" (
  echo [LOI] Chua co file .cvat.env. Xem docs\HUONG-DAN-CVAT.md muc 2.
  pause
  exit /b 1
)
echo Tao bo A (Boston, 5 frame)...
".venv\Scripts\python.exe" scripts\cvat_create_task.py --nusc-root "%NUSC_ROOT%" --split val --start-frame 10 --max-frames 5 --labels noisy --seed 0 --name "PILOT A"
echo.
echo Tao bo B (Singapore, 5 frame)...
".venv\Scripts\python.exe" scripts\cvat_create_task.py --nusc-root "%NUSC_ROOT%" --split val --start-frame 60 --max-frames 5 --labels noisy --seed 0 --name "PILOT B"
echo.
echo GHI LAI 2 so "task ..." o tren vao sheet pilot. KHONG mo thu muc out\cvat_tasks (co dap an).
pause
