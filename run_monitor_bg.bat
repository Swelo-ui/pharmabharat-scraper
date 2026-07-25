@echo off
:: run_monitor_bg.bat
:: Background mein silently chalta hai (no console window)
:: Laptop start hone par automatically chalane ke liye:
::   1. Win+R → shell:startup → Enter
::   2. Is .bat file ka shortcut us folder mein paste karo

cd /d "%~dp0"
start "" /B pythonw monitor.py
echo Monitor started in background! Log file: monitor.log
