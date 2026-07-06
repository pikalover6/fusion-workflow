@echo off
set "FUSION_SCRIPT=%USERPROFILE%\.local\share\fusion-workflow\bin\fusion-flow.py"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%FUSION_SCRIPT%" %*
) else (
  python "%FUSION_SCRIPT%" %*
)
