@echo off
rem Dong bo len GitHub sau khi ban tu sua code bang tay.
rem Cach dung: sync.bat            (message tu dong)
rem            sync.bat fix: sua luat 3.2.9
cd /d "%~dp0"
python .claude\hooks\git_sync.py %*
pause
