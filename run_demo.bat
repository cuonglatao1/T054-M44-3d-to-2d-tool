@echo off
chcp 65001 >nul
rem Bam dup de chay M44 tren 10 frame nuScenes-mini (tap val) va mo bao cao trong trinh duyet.
rem Can: WSL distro "mmdet3d" (D:\WSL\mmdet3d) va du lieu D:\data\nuscenes.

echo === M44 - 2D-3D Consistency Checker ===
echo Dang chay tren 10 frame nuScenes-mini (lan dau mat ~30 giay de chay YOLO)...
echo.
wsl -d mmdet3d -u root -- bash -c "source /opt/m3d/bin/activate && cd /mnt/d/m44-consistency-checker/weights && python ../scripts/run_all.py --info /mnt/d/data/nuscenes/nuscenes_infos_val.pkl --data-root /mnt/d/data/nuscenes --out ../out/demo_live --max-frames 10 --cfg ../configs/tuned.json 2>&1 | grep -E 'frames|detections|report'"
if errorlevel 1 (
  echo.
  echo Loi khi chay. Kiem tra WSL distro mmdet3d va thu muc D:\data\nuscenes.
  pause
  exit /b 1
)
echo.
echo Xong. Dang mo bao cao...
start "" "%~dp0out\demo_live\index.html"
