@echo off
chcp 65001 >nul
rem Cham mot luot review pilot. Chay NGAY sau khi het gio va da bam Save tren CVAT.
cd /d "%~dp0"
if not defined NUSC_ROOT set "NUSC_ROOT=%~dp0data\nuscenes"
set /p NAME=Ten ban (vd Thuy):
set /p SET=Bo du lieu (A hoac B):
set /p MODE=Che do (tay hoac tool):
set /p TASK=ID task CVAT cua bo nay:
set /p MIN=So phut da lam:
".venv\Scripts\python.exe" scripts\pilot_score.py --task-id %TASK% --name "%NAME%" --set %SET% --mode %MODE% --minutes %MIN% --nusc-root "%NUSC_ROOT%"
pause
