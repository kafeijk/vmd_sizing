@echo off
chcp 65001 >nul
rem ==========================================
rem ---  VMD适配：启动图形界面（GUI）      ---
rem ==========================================
cd /d %~dp0
cls

rem --- 切换到项目用的 conda 环境（如路径不同请自行修改）---
call D:\ProgramData\miniconda\Scripts\activate.bat vmdsizing_cn

python src\executor.py --out_log 1 --verbose 20 --is_saving 1

pause
