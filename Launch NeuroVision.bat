@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch_neurovision.ps1"
if errorlevel 1 (
  echo.
  echo NeuroVision could not start. See the message above.
  pause
)
endlocal
