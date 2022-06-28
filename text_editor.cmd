@echo off
set "PYTHONPATH=%PYTHONPATH%;%~dp0"
start pythonw "%~dp0\main.py" %1
