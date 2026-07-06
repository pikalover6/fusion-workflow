@echo off
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%~dp0fusion-flow.py" %*
) else (
  python "%~dp0fusion-flow.py" %*
)
