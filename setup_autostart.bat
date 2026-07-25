@echo off
:: setup_autostart.bat
:: Yeh script Windows Task Scheduler mein monitor ko register karta hai
:: Taaki PC start hone par AUTOMATICALLY background mein chale
:: 
:: Administrator ke taur par chalao (Right-click → "Run as administrator")

cd /d "%~dp0"

:: Python executable path dhundho
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do set PYTHONW=%%i
if "%PYTHONW%"=="" (
    for /f "tokens=*" %%i in ('where python 2^>nul') do set PYTHONW=%%i
)

if "%PYTHONW%"=="" (
    echo ERROR: Python nahi mila! Pehle Python install karo.
    pause
    exit /b 1
)

echo Python found: %PYTHONW%
echo Monitor path: %~dp0monitor.py

:: Task Scheduler mein task create karo
schtasks /create /tn "PharmaBharatMonitor" ^
    /tr "\"%PYTHONW%\" \"%~dp0monitor.py\"" ^
    /sc ONLOGON ^
    /delay 0001:00 ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo  SUCCESS! Task Scheduler mein register ho gaya.
    echo  Ab har baar PC on hone par monitor automatically start hoga.
    echo  Jobs check hoti rahegi — app band ho tab bhi!
    echo.
    echo  Task ka naam: PharmaBharatMonitor
    echo  Dekhne ke liye: Task Scheduler kholo → PharmaBharatMonitor
    echo  Hatane ke liye: schtasks /delete /tn PharmaBharatMonitor /f
    echo ============================================================
) else (
    echo.
    echo ERROR: Task create nahi ho paya.
    echo Yeh script Administrator ke taur par chalao.
    echo Right-click → "Run as administrator"
)

pause
