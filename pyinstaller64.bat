@echo off
chcp 65001 >nul
rem ==========================================
rem ---  VMD适配：生成 exe                  ---
rem ---  1) 编译 Cython 扩展（需要 MSVC）   ---
rem ---  2) 用 PyInstaller 打包             ---
rem ==========================================
cd /d %~dp0
cls

call D:\ProgramData\miniconda\Scripts\activate.bat vmdsizing_cn

rem --- 加载 MSVC 编译环境（64 位）；如 VS 版本/路径不同请自行修改 ---
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

cd src
python setup_install.py build_ext --inplace
if errorlevel 1 goto :error
cd ..

pyinstaller --clean vmdising_np64.spec
if errorlevel 1 goto :error

copy /y archive\Readme.txt dist\Readme.txt

echo.
echo ===== 生成完成，输出位于 dist 目录 =====
pause
exit /b 0

:error
echo.
echo ===== 生成失败，请查看上方错误信息 =====
pause
exit /b 1
