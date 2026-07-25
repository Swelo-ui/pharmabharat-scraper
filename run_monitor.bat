@echo off
:: run_monitor.bat
:: Double-click karo ya Task Scheduler mein add karo
:: App band ho tab bhi yeh background mein chalta rahega

cd /d "%~dp0"
echo.
echo ============================================================
echo  PharmaBharat + PharmaRecruiter Background Monitor
echo  Dono sites se naye jobs check hote rahenge (har 30-60 min)
echo  Telegram par notification aayegi jab bhi naya job mile
echo  Band karne ke liye: Ctrl+C ya window close karo
echo ============================================================
echo.

python monitor.py
pause
