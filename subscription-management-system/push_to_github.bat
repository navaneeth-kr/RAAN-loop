@echo off
set "PATH=%PATH%;C:\Users\alanj\.gemini\antigravity\scratch\mingit\cmd"
echo ========================================================
echo  Pushing Subscription Management System to GitHub
echo  Repository: https://github.com/navaneeth-kr/RAAN-loop.git
echo ========================================================
git push -u origin main
if %errorlevel% neq 0 (
    echo.
    echo If the remote repository has existing commits, try:
    echo git push -u origin main --force
)
pause
