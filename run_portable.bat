@echo off
REM ============================================================
REM Portable launcher — aman dipakai di laptop lain.
REM Mencoba Python 3.11 lewat "py", lalu fallback ke "python".
REM
REM Contoh:
REM   run_portable.bat scraper.py
REM   run_portable.bat glints_detail_scraper.py 10 --debug
REM ============================================================
cd /d "%~dp0"

py -3.11 %* 2>nul
if %errorlevel%==0 goto :eof

python %*
