@echo off
REM ============================================================
REM Launcher proyek JIS & Auto CV
REM Memakai Python 3.11 karena di situlah semua dependensi
REM (playwright, groq, mysql-connector-python, python-dotenv)
REM sudah terinstal. Python 3.13 di PATH masih kosong.
REM
REM Cara pakai:
REM   run.bat scraper.py
REM   run.bat detail_scraper.py
REM   run.bat glints_scraper.py
REM   run.bat ai_processor.py
REM   run.bat mark_applied.py
REM ============================================================

cd /d "%~dp0"
"C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe" %*
