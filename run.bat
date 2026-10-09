@echo off
REM Cach dung: run.bat "duong\dan\ban_ve.pdf" [them tham so...]
chcp 65001 >nul
set PYTHONPATH=%~dp0src
python -m pccc_checker run %*
pause
