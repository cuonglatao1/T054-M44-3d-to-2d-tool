@echo off
chcp 65001 >nul
rem Pilot phan 2: cham nhan tu gan. Chay 2 lan: "truoc" (gan xong, CHUA bam M44 Check) va "sau" (da sua theo tool).
cd /d "%~dp0"
if not defined NUSC_ROOT set "NUSC_ROOT=%~dp0data\nuscenes"
set /p NAME=Ten ban (vd Thuy):
set /p STAGE=Lan cham (truoc hoac sau):
set /p TASK=ID task PILOT GAN NHAN:
set /p MIN=So phut cua giai doan nay:
".venv\Scripts\python.exe" scripts\pilot_label_score.py --task-id %TASK% --name "%NAME%" --stage %STAGE% --minutes %MIN% --nusc-root "%NUSC_ROOT%"
pause
