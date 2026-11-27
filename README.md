# JIS & Auto CV — Job Intelligence System

Sistem otomasi pencarian kerja: **scrape lowongan** (JobStreet & Glints) → **ambil deskripsi** →
**skor kecocokan** → **generate CV + cover letter** dengan LLM (Groq) → **PDF**.

Dokumen ini dibuat agar proyek bisa **dilanjutkan di laptop lain** dengan cepat: dependency,
konfigurasi, **skema database**, alur pipeline, sampai troubleshooting.

---

## Daftar Isi
1. [Fitur](#1-fitur)
2. [Alur Pipeline](#2-alur-pipeline)
3. [Tech Stack & Prasyarat](#3-tech-stack--prasyarat)
4. [Struktur Proyek](#4-struktur-proyek)
5. [Setup di Laptop Baru](#5-setup-di-laptop-baru)
6. [Konfigurasi](#6-konfigurasi)
7. [Cara Menjalankan](#7-cara-menjalankan)
8. [Database](#8-database)
9. [Detail Teknis](#9-detail-teknis)
10. [Troubleshooting](#10-troubleshooting)
11. [Keamanan & Privasi](#11-keamanan--privasi)
12. [Checklist Pindah Laptop](#12-checklist-pindah-laptop)
13. [Known Issues / TODO](#13-known-issues--todo)

---

## 1. Fitur

- **Multi-sumber:** JobStreet (`scraper.py`) dan Glints (`glints_scraper.py`).
- **Detail scraper terpisah per sumber** (selector berbeda):
  - JobStreet → `detail_scraper.py`
  - Glints → `glints_detail_scraper.py` (butuh **login**; sesi disimpan)
- **Filter keyword IT** berbasis regex kata utuh (backend, frontend, data, IoT, dst).
- **Deduplikasi** berdasarkan `job_id` (UNIQUE di DB).
- **Skoring kecocokan** (role/tech/fresh-grad/negative) → band HIGH/MEDIUM/LOW/REJECTED.
- **Auto CV + Cover Letter** dengan **Groq** (`llama-3.1-8b-instant`) → **PDF** ke `Tailored_CVs/`.
- **Penanda APPLIED** manual (`mark_applied.py`).

---

## 2. Alur Pipeline

```
                ┌────────────────────┐        ┌────────────────────┐
   JOBSTREET →  │ scraper.py         │        │ glints_scraper.py  │  ← login (sekali)
   GLINTS    →  │ (listing → raw_jobs│        │ (listing → raw_jobs│
                └─────────┬──────────┘        └─────────┬──────────┘
                          │                             │
                          ▼                             ▼
              ┌────────────────────┐        ┌────────────────────────────┐
              │ detail_scraper.py  │        │ glints_detail_scraper.py   │
              │ (JobStreet detail) │        │ (Glints detail, login)     │
              └─────────┬──────────┘        └───────────┬────────────────┘
                        └──────────────┬──────────────────┘
                                       ▼
                         raw_jobs.job_description + match_score + status
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │ ai_processor.py (Groq)    │ → Tailored_CVs/*.pdf
                         │ status DRAFT_READY        │   + cover letter ke DB
                         └───────────────────────────┘
                                       │
                                       ▼
                         mark_applied.py → status APPLIED
```

Status penting:
- `scraper.py`/`detail_scraper.py`/`glints_detail_scraper.py` menulis `job_description`, `match_score`, dan status `HIGH_MATCH/MEDIUM_MATCH/LOW_MATCH/REJECTED`.
- **`ai_processor.py` hanya memproses `status = 'DRAFT_READY'`** dan `job_description IS NOT NULL`. Lihat [Known Issues](#13-known-issues--todo) untuk menjembatani status ini.

---

## 3. Tech Stack & Prasyarat

| Komponen | Versi/ketentuan |
|---|---|
| OS | Windows (batch `.bat`, Playwright non-headless) |
| Python | **3.11** (proyek memakai `C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe`) |
| Database | **MySQL 8+** (lokal; Laragon/MySQL Server) |
| Browser otomatis | Playwright + **Chromium** (`playwright install chromium`) |
| LLM | **Groq API** (`GROQ_API_KEY`) |

Python dependencies (lihat `requirements.txt`):
```
groq
playwright
mysql-connector-python
python-dotenv
```

---

## 4. Struktur Proyek

```
JIS & Auto CV/
├─ run.bat                      # launcher utama (Python 3.11 path hardcoded)
├─ run_portable.bat             # launcher portable (py -3.11 / python)
├─ run_autopilott.bat           # ⚠ jalur lama (C:\Roy\AutoPilot-Jobs) — perlu diperbarui
├─ requirements.txt
├─ schema.sql                   # ✅ SKEMA DB AKURAT (pakai ini, bukan setup_db.sql)
├─ setup_db.sql                 # ⚠ legacy/outdated
├─ .env                         # GROQ_API_KEY (RAHASIA, tidak di-commit)
├─ .gitignore
├─ profile.json                 # data pribadi kandidat (PRIBADI, tidak di-commit)
├─ profile.example.json         # template profile.json
├─ template.html                # template CV (placeholder {{...}})
│
├─ scraper.py                   # JobStreet — listing
├─ detail_scraper.py            # JobStreet — detail (selector JobStreet)
├─ glints_auth.py               # helper login/sesi Glints (dipakai 2 skrip Glints)
├─ glints_scraper.py            # Glints — listing (pakai login)
├─ glints_detail_scraper.py     # Glints — detail (pakai login; multi-strategi ekstraksi)
├─ ai_processor.py              # Groq → cover letter + CV PDF
├─ manual_to_pdf.py             # generator PDF manual sekali pakai (konten hardcoded)
├─ mark_applied.py              # tandai APPLIED by job_id
│
├─ CV_Manual/                   # (gitignored) PDF CV manual
├─ Tailored_CVs/                # (gitignored) OUTPUT PDF hasil AI
├─ Screenshot_debug/            # screenshot gagal JobStreet
├─ Screenshot_debug_glints/     # (gitignored) screenshot + HTML gagal Glints
├─ glints_auth.json             # (gitignored) sesi login Glints
├─ glints_error_page_*.png      # (gitignored) error page Glints
└─ log_otomatis.txt             # (gitignored) log eksekusi terjadwal
```

---

## 5. Setup di Laptop Baru

### 5.1 Install prasyarat
- **Python 3.11** → centang *Add python.exe to PATH*.
- **MySQL 8 / Laragon** → jalankan service MySQL (port `3306`).
- **Git** (opsional, untuk clone).

### 5.2 Ambil proyek
```powershell
git clone <repo-url>
cd "JIS & Auto CV"
```
Atau copy foldernya (termasuk file pribadi: `.env`, `profile.json` — lihat catatan keamanan).

### 5.3 Install dependency Python
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```
> Alternatif virtualenv:
> ```powershell
> py -3.11 -m venv .venv
> .\.venv\Scripts\activate
> pip install -r requirements.txt
> playwright install chromium
> ```

### 5.4 Siapkan database
```powershell
mysql -u root -p < schema.sql
```
Atau buka Laragon/HeidiSQL/DBeaver → jalankan isi `schema.sql`.
> ⚠️ **Jangan** pakai `setup_db.sql` (versi lama, kolom `job_id/location/job_url/category` tidak ada).

### 5.5 Buat `.env`
Buat file `.env` di root proyek:
```
GROQ_API_KEY=isi_api_key_groq_anda
```

### 5.6 Buat `profile.json`
```powershell
Copy-Item profile.example.json profile.json
```
Lalu isi data asli Anda. Struktur (lihat `profile.example.json`):
```
personal_info: { name, location, phone, email, linkedin, github, portfolio }
summary: "..."
core_skills: [ ... 8 item ... ]
work_experience: [ { role, company, division, duration, responsibilities[3] } ]
key_projects: [ { name, description } x3 ]
education: "..."
```
> `ai_processor.py` mengambil: `summary`, `core_skills`, `work_experience[0].role`, dan `personal_info` untuk kontak.

### 5.7 Launcher Python
`run.bat` men-**hardcode** path Python 3.11. Di laptop baru:
- Edit `run.bat` (baris terakhir) ke path Python Anda, **atau**
- Pakai `run_portable.bat` (mencoba `py -3.11`, lalu `python`).

Contoh:
```powershell
run_portable.bat scraper.py
```

### 5.8 Cek koneksi DB
```powershell
python -c "import mysql.connector; c=mysql.connector.connect(host='127.0.0.1',user='root',password='',database='autopilot_jobs_db'); print('DB OK'); c.close()"
```

---

## 6. Konfigurasi

### 6.1 Kredensial DB (hardcoded di tiap skrip)
Saat ini `db_config` ditulis di **setiap** file:
```
scraper.py, detail_scraper.py, glints_scraper.py,
glints_detail_scraper.py, ai_processor.py, mark_applied.py
```
```python
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',              # default kosong (Laragon). Ganti bila beda.
    'database': 'autopilot_jobs_db'
}
```
> Jika user/password MySQL berbeda di laptop baru, ubah di **semua** file di atas. (Saran ke depan: satukan ke satu modul `db.py`.)

### 6.2 `.env`
| Key | Fungsi |
|---|---|
| `GROQ_API_KEY` | API key Groq untuk `ai_processor.py` |

### 6.3 `profile.json`
Data pribadi untuk prompt AI & CV. **Jangan di-commit** (berisi PII).

### 6.4 `glints_auth.json`
Sesi login Glints (cookies + localStorage). Dibuat otomatis setelah login pertama.
- Login ulang: `run.bat glints_detail_scraper.py --relogin` (atau hapus file).
- Waktu login default **120 detik** (`LOGIN_WAIT_SECONDS` di `glints_auth.py`); bisa tekan **ENTER** untuk lanjut lebih cepat.

---

## 7. Cara Menjalankan

Semua contoh memakai `run.bat`. Ganti dengan `run_portable.bat` bila perlu.

### 7.1 Pipeline JobStreet
```powershell
run.bat scraper.py            # listing JobStreet → raw_jobs
run.bat detail_scraper.py     # isi job_description + skor + status (JobStreet)
run.bat ai_processor.py       # generate CV/cover letter (status DRAFT_READY)
```

### 7.2 Pipeline Glints
```powershell
run.bat glints_scraper.py                 # listing Glints → raw_jobs (LOGIN di sini, sekali)
run.bat glints_detail_scraper.py          # isi deskripsi Glints (pakai sesi tersimpan)
# tes kecil:
run.bat glints_detail_scraper.py 5 --debug
# login ulang:
run.bat glints_detail_scraper.py --relogin
```
- Saat pertama run, Chrome terbuka. **Login manual**, lalu tekan **ENTER** di terminal.
- `--debug` menampilkan `source` ekstraksi (json-ld / selectors / main) + panjang teks.
- Gagal ekstrak → dump `Screenshot_debug_glints/<judul>.png` + `.html` untuk tuning selector.

### 7.3 AI Processor
```powershell
run.bat ai_processor.py
```
- Butuh `GROQ_API_KEY` + `profile.json` + `template.html`.
- Output: `Tailored_CVs/CV_Roy_<Company>.pdf`.
- Hanya memproses baris `status='DRAFT_READY'` & `job_description IS NOT NULL`.

### 7.4 Manual
```powershell
run.bat mark_applied.py       # tandai APPLIED (input job_id)
run.bat manual_to_pdf.py      # PDF manual sekali pakai (edit data di dalam file)
```

---

## 8. Database

Database: **`autopilot_jobs_db`** (MySQL 8). Skema akurat ada di **`schema.sql`**.

### 8.1 `raw_jobs` — tabel AKTIF (dipakai semua skrip)

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK AI | ID internal |
| `job_id` | VARCHAR(50) UNIQUE | ID dari sumber (JobStreet angka / Glints UUID) |
| `title` | VARCHAR(255) | Judul lowongan |
| `company_name` | VARCHAR(255) | Perusahaan |
| `location` | VARCHAR(255) | Lokasi |
| `job_url` | TEXT | URL detail |
| `job_description` | LONGTEXT | Deskripsi (diisi detail scraper) |
| `skills_required` | TEXT | Diisi AI |
| `cover_letter` | LONGTEXT | Diisi AI |
| `scraped_at` | DATETIME | Waktu listing di-scrape |
| `status` | ENUM | Lihat di bawah |
| `applied_at` | DATETIME | Waktu ditandai APPLIED |
| `match_score` | INT | Skor kecocokan |
| `tech_stack` | TEXT | (opsional) |
| `processed_at` | TIMESTAMP | (opsional) |
| `category` | VARCHAR(100) | `GLINTS` untuk sumber Glints; JobStreet = NULL |

**ENUM `status`:** `RAW`, `HIGH_MATCH`, `MEDIUM_MATCH`, `LOW_MATCH`, `REJECTED`, `DRAFT_READY`, `APPLIED`.

### 8.2 Siklus status (pipeline aktif)
```
RAW (baru daftar)
  → HIGH_MATCH / MEDIUM_MATCH / LOW_MATCH / REJECTED (setelah detail + skor)
  → DRAFT_READY (siap dibuatkan CV)  ← ai_processor mencari status ini
  → APPLIED (sudah dilamar; mark_applied)
```

### 8.3 Skema lanjutan (v2) — sudah ada di DB, **belum dipakai** skrip saat ini
- **`jobs`** — versi ternormalisasi (source/source_job_id/skor/band/duplikat/retry, dll).
- **`job_applications`** — riwayat CV/cover letter per job (FK ke `jobs`).
- **`job_keywords`** — keyword + weight + kind (ROLE/TECH/INDUSTRY/FRESH_GRAD/NEGATIVE).
- **`scrape_runs`** — log tiap run scraper (pages/jobs/duplikat/failed/status).
- **Views:** `v_shortlist`, `v_pipeline_stats`, `v_duplicate_jobs`.

> Jika nanti ingin bermigrasi ke skema v2, skrip perlu diarahkan ke `jobs` (belum sekarang).

### 8.4 Catatan
- `shelf_locations2` (data lokasi rak) **tidak terkait** proyek ini — abaikan.
- `setup_db.sql` **outdated** → gunakan `schema.sql`.

### 8.5 Restore DB
```powershell
mysql -u root -p autopilot_jobs_db < schema.sql
# atau (schema.sql sudah CREATE DATABASE)
mysql -u root -p < schema.sql
```

### 8.6 Query berguna
```sql
-- Ringkasan per kategori & status
SELECT category, status, COUNT(*) FROM raw_jobs GROUP BY category, status;

-- Lowongan yang belum punya deskripsi
SELECT source, COUNT(*) FROM (
  SELECT CASE WHEN job_url LIKE '%glints.com%' THEN 'GLINTS' ELSE 'JOBSTREET' END AS source
  FROM raw_jobs WHERE job_description IS NULL
) t GROUP BY source;

-- Top match siap dilamar
SELECT title, company_name, match_score, job_url
FROM raw_jobs
WHERE job_description IS NOT NULL AND status IN ('HIGH_MATCH','DRAFT_READY')
ORDER BY match_score DESC LIMIT 20;

-- Promosikan HIGH_MATCH menjadi DRAFT_READY agar diproses AI
UPDATE raw_jobs SET status='DRAFT_READY'
WHERE status='HIGH_MATCH' AND job_description IS NOT NULL;
```

---

## 9. Detail Teknis

### 9.1 Scraping
- **JobStreet:** `article` cards + `[data-automation="jobTitle|jobCompany|jobLocation"]`; paginasi tombol Next.
- **Glints (listing):** anchor `a[href*="/opportunities/jobs/"]`; ambil 1 link terbaik per `job_id` (UUID), judul dari teks anchor, perusahaan dari container. Dedupe per `job_id`.
- **Glints (detail):** ekstraksi berlapis: **JSON-LD `JobPosting`** → selector Glints (`[data-testid*=job-description]`, `div[class*="JobDescription"]`, dst) → heuristik `<main>` ("Job Description/Deskripsi/Kualifikasi") → `og:description`.
- Anti-bot: browser non-headless, UA Chrome, locale `id-ID`, Referer, delay acak, klik "See more"/cookie banner.

### 9.2 Scoring Engine (sama untuk JobStreet & Glints)
- **ROLE**: cocok di title ×2, di teks ×1.
- **TECH**: +nilai per tech ditemukan.
- **FRESH_GRAD**: + nilai (fresh graduate, entry level, junior, 0-2 years).
- **NEGATIVE**: − nilai (senior, manager, lead, director, "5 years", "7 years").
- Threshold status: **≥15 HIGH**, **≥10 MEDIUM**, **≥6 LOW**, selain itu **REJECTED**.

### 9.3 AI Processor
- Model: `llama-3.1-8b-instant` (Groq), output **JSON**.
- Input: ringkasan profil (`summary`, `core_skills`, `work_experience[0].role`) + `job_description`.
- Output JSON: `keywords`, `cover_letter`, `summary_html`, `skills_html`, `experience_html`, `projects_html`, `education_focus`.
- Render ke `template.html` (placeholder: `{{NAME}}`, `{{CONTACT_INFO}}`, `{{SUMMARY}}`, `{{SKILLS}}`, `{{EXPERIENCE}}`, `{{PROJECTS}}`, `{{EDUCATION_FOCUS}}`, `{{LANGUAGES}}`, `{{AVAILABILITY}}`, `{{LOCATION_DETAILS}}`) → **Playwright PDF**.
- Simpan hasil: `skills_required`, `cover_letter`, `status='APPLIED'`; PDF di `Tailored_CVs/`.

### 9.4 Login Glints
- Helper: `glints_auth.py` → `new_context(browser, force_login=False)`.
- Sesi di `glints_auth.json` (cookies + localStorage), dipakai bersama `glints_scraper.py` & `glints_detail_scraper.py`.
- Hapus file / `--relogin` untuk login ulang.

---

## 10. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| `Can't connect to MySQL ... (10061)` | MySQL/Laragon mati | Jalankan service MySQL |
| `Unknown column 'job_id'` / insert gagal | DB pakai `setup_db.sql` lama | Import **`schema.sql`** |
| `UnicodeEncodeError: 'charmap' ... cp1252` | Console non-UTF8 (Task Scheduler) | `chcp 65001` / set `PYTHONIOENCODING=utf-8` (skrip sudah `reconfigure`) |
| `Executable doesn't exist ... chromium` | Browser Playwright belum ada | `playwright install chromium` |
| `ModuleNotFoundError: groq` | `groq` belum terinstal | `pip install -r requirements.txt` |
| Glints `0 ... disimpan` | Ekstraksi/login | Login dulu; jalankan `glints_detail_scraper.py 5 --debug`; cek `Screenshot_debug_glints/*.html` |
| Detail Glints kosong / login wall | Sesi kedaluwarsa | `--relogin` atau hapus `glints_auth.json` |
| `ai_processor`: `Total CV: 0` | Tidak ada `status='DRAFT_READY'` | Jalankan SQL promosi HIGH_MATCH → DRAFT_READY |
| `run_autopilott.bat` gagal | `cd` ke path lama `C:\Roy\AutoPilot-Jobs` | Edit baris `cd /d` ke folder proyek |
| `detail_scraper.py` gagal di URL Glints | Selector JobStreet ≠ Glints | Pakai `glints_detail_scraper.py` |

---

## 11. Keamanan & Privasi

**Jangan commit / jangan bagikan publik:**
- `.env` → berisi `GROQ_API_KEY`.
- `profile.json` → data pribadi (nama, telepon, email, dll).
- `glints_auth.json` → token sesi login Glints.
- `CV_Manual/`, `Tailored_CVs/` → PDF pribadi.
- `manual_to_pdf.py` → **berisi data kontak pribadi hardcoded** (tinjau sebelum publikasi).
- `log_otomatis.txt` → log berisi judul/perusahaan.

`.gitignore` sudah mencakup: `.env`, `CV/`, `CV_Manual/`, `Tailored_CVs/`, `__pycache__/`, `*.png`, `glints_auth.json`, `Screenshot_debug_glints/`, `profile.json`, `log_otomatis.txt`.
> Pastikan repo **private** jika tetap menyimpan sebagian data pribadi.

---

## 12. Checklist Pindah Laptop

- [ ] Install **Python 3.11**, **MySQL 8/Laragon**, **Git**.
- [ ] Ambil proyek (clone/copy).
- [ ] `pip install -r requirements.txt`
- [ ] `playwright install chromium`
- [ ] Import **`schema.sql`** ke MySQL.
- [ ] Buat `.env` → `GROQ_API_KEY`.
- [ ] Buat `profile.json` dari `profile.example.json` (isi data asli).
- [ ] Pastikan `template.html` ada.
- [ ] Cek `db_config` di semua skrip (host/user/password/database).
- [ ] Siapkan launcher: edit `run.bat` **atau** pakai `run_portable.bat`.
- [ ] Tes: `run.bat scraper.py` (JobStreet) / `run.bat glints_scraper.py` (login Glints).
- [ ] Tes detail + `ai_processor.py` dengan 1 lowongan.

---

## 13. Known Issues / TODO

1. **`setup_db.sql` outdated** → gunakan `schema.sql`.
2. **`run_autopilott.bat`** masih `cd` ke `C:\Roy\AutoPilot-Jobs` (path lama) → perbarui.
3. **Status mismatch**: `ai_processor.py` butuh `DRAFT_READY`, sedangkan detail scraper menulis `HIGH/MEDIUM/LOW/REJECTED`. Jembatani dengan SQL promosi (lihat §8.6) atau ubah detail scraper untuk menulis `DRAFT_READY` pada match tinggi.
4. **`requirements.txt`** sebelumnya tidak memuat `groq` (sudah diperbaiki) dan memuat `google-genai` yang tak terpakai.
5. **Glints selector** bisa berubah sewaktu-waktu → andalkan JSON-LD + dump HTML untuk tuning.
6. **Skema v2** (`jobs`, dll) belum terhubung ke skrip; migrasi belum dilakukan.
7. **db_config duplikat** di banyak file → saran: satukan ke `db.py`.

---

## Lampiran — Ringkas

**Prasyarat cepat**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
mysql -u root -p < schema.sql
```

**Jalankan cepat**
```powershell
run_portable.bat scraper.py
run_portable.bat detail_scraper.py
run_portable.bat glints_scraper.py
run_portable.bat glints_detail_scraper.py 5 --debug
run_portable.bat ai_processor.py
```
