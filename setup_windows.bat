@echo off
chcp 65001 >nul
rem Cai dat moi truong cho M44 (chi can lam 1 lan). Yeu cau: Python 3.10-3.12 tu python.org.
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [LOI] Chua co Python. Tai Python 3.11 tai https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^).
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Tao moi truong ao .venv ...
  py -3.11 -m venv .venv 2>nul || py -3 -m venv .venv
)

echo Cai thu vien ^(lan dau mat 5-10 phut, tai khoang 1 GB^)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [LOI] Cai thu vien that bai. Chup man hinh loi va gui vao kenh Discord cua nhom.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -c "import torch, ultralytics, nuscenes; print('OK - torch', torch.__version__, '| GPU:', torch.cuda.is_available())"
echo.
echo Xong. Buoc tiep theo: giai nen nuScenes-mini vao thu muc data\nuscenes roi bam dup run_demo.bat
pause
