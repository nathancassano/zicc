@echo off
setlocal
call "%~dp0msvc-env.cmd"
if errorlevel 1 exit /b 1
if not defined PYTHON set "PYTHON=python"
%PYTHON% "%~dp0check-entry.py"
exit /b %errorlevel%
