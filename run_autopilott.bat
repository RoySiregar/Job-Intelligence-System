@echo off
echo ===================================================
echo Memulai Auto-Pilot Job Scraper...
echo Waktu eksekusi: %date% %time%
echo ===================================================

:: Berpindah ke folder proyek Anda
cd /d C:\Roy\AutoPilot-Jobs

:: Menyimpan log eksekusi harian
echo === Eksekusi: %date% %time% === >> log_otomatis.txt

echo [1/3] Menjalankan Scraper Utama...
python scraper.py >> log_otomatis.txt 2>&1

echo [2/3] Menjalankan Detail Scraper...
python detail_scraper.py >> log_otomatis.txt 2>&1

echo [3/3] Menjalankan AI Processor (Cover Letter & CV)...
python ai_processor.py >> log_otomatis.txt 2>&1

echo ===================================================
echo Semua tugas selesai! Silakan cek folder Tailored_CVs
echo ===================================================
pause