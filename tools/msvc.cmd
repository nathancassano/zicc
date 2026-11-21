@echo off
setlocal
if defined VSCMD_ARG_TGT_ARCH goto compile
set "TASK_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%TASK_VSWHERE%" exit /b 1
for /f "usebackq delims=" %%I in (`"%TASK_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "TASK_VSROOT=%%I"
if not defined TASK_VSROOT exit /b 1
call "%TASK_VSROOT%\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
:compile
cl /D__far= %*
exit /b %errorlevel%
