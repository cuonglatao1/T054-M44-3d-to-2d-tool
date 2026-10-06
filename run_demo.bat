@echo off
chcp 65001 >nul
rem Bam dup de chay M44 tren 10 frame nuScenes-mini (tap val) va mo bao cao trong trinh duyet.
rem Du lieu mac dinh: data\nuscenes trong thu muc nay. Dat bien NUSC_ROOT neu de cho khac.
cd /d "%~dp0"
if not defined NUSC_ROOT set "NUSC_ROOT=%~dp0data\nuscenes"

if not exist ".venv\Scripts\python.exe" (
  echo [LOI] Chua cai dat. Bam dup setup_windows.bat truoc.
  pause
  exit /b 1
)
if not exist "%NUSC_ROOT%\v1.0-mini" (
  echo [LOI] Khong thay nuScenes-mini tai: %NUSC_ROOT%
  echo Tai https://www.nuscenes.org/data/v1.0-mini.tgz va giai nen vao thu muc tren
  echo ^(ben trong phai co samples, sweeps, maps, v1.0-mini^).
  pause
  exit /b 1
)

echo === M44 - 2D-3D Consistency Checker ===
echo Dang chay tren 10 frame (lan dau: tai model YOLO + chay YOLO, vai phut neu khong co GPU)...
".venv\Scripts\python.exe" scripts\run_all.py --nusc-root "%NUSC_ROOT%" --split val --max-frames 10 --out out\demo_live
if errorlevel 1 (
  echo [LOI] Chay that bai. Chup man hinh loi va gui vao kenh Discord cua nhom.
  pause
  exit /b 1
)
echo Xong. Dang mo bao cao...
start "" "%~dp0out\demo_live\index.html"
