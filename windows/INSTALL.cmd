@echo off
setlocal
cd /d "%~dp0"
set "SBPE_INSTALL_ROOT=%~f1"
if not "%~1"=="" goto selected
if exist "..\pypy\pypy3.exe" (
  for %%P in ("..") do set "SBPE_INSTALL_ROOT=%%~fP"
) else (
  for /f "usebackq delims=" %%P in (`powershell.exe -NoProfile -STA -File "%~dp0choose-folder.ps1"`) do set "SBPE_INSTALL_ROOT=%%P"
)
:selected
if not defined SBPE_INSTALL_ROOT exit /b 0
if not exist "%SBPE_INSTALL_ROOT%\pypy\pypy3.exe" (
  echo Choose your SBPE Windows folder containing pypy, plugins and config.ini.
  pause
  exit /b 1
)
"%SBPE_INSTALL_ROOT%\pypy\pypy3.exe" "%~dp0install_loading_probe.py" --root "%SBPE_INSTALL_ROOT%"
if errorlevel 1 (
  pause
  exit /b 1
)
pause
