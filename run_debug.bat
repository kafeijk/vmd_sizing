@echo off
chcp 65001 >nul
rem ==========================================
rem ---  VMD适配：以调试模式启动（输出详细   ---
rem ---  日志，用于排查问题）               ---
rem ==========================================
cd /d %~dp0
cls

call D:\ProgramData\miniconda\Scripts\activate.bat vmdsizing_cn

python src\executor.py --out_log 1 --verbose 10 --is_saving 1

pause
