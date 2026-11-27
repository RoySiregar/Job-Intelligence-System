from playwright.sync_api import sync_playwright
import mysql.connector
import re
import time
import random

# Konfigurasi Koneksi Database Laragon
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '', 
    'database': 'autopilot_jobs_db'
}

# --- PERSIAPAN REGEX KEYWORD ---

# 1. Role (Ditambahkan Frontend, Mobile, QA, Network, Support, dan istilah lokal)
role_keywords = [
    'backend', 'back end', 'fullstack', 'full stack', 'software', 'programmer', 
    'developer', 'it', 'engineer', 'data', 'iot', 'automation', 'system', 
    'database', 'dba', 'api', 'architect', 'devops', 
    'frontend', 'front end', 'web', 'mobile', 'android', 'ios', 
    'ui', 'ux', 'qa', 'tester', 'quality assurance', 
    'network', 'jaringan', 'infrastructure', 'security', 'cyber', 'cloud', 
    'support', 'helpdesk', 'admin', 'erp', 'sap',
    'informatika', 'informasi'
]

# 2. Teknologi (Ditambahkan stack populer lainnya dan protokol relevan)
tech_keywords = [
    'python', 'c#', '.net', 'dotnet', 'sql', 'mysql', 'postgresql', 
    'typescript', 'javascript', 'vue', 'react', 'node', 'nodejs', 
    'java', 'php', 'laravel', 'golang', 'c++', 'aws', 'azure', 'mqtt'
]

# 3. Industri & Domain Spesifik (Ditambahkan istilah manufaktur/sistem)
industry_keywords = ['iiot', 'mes', 'oee', 'manufacturing']

all_keywords = role_keywords + tech_keywords + industry_keywords
escaped_keywords = [re.escape(kw) for kw in all_keywords]

# (?<!\w) dan (?!\w) sangat efektif untuk C# dan .NET
KEYWORD_PATTERN = re.compile(r'(?<!\w)(' + '|'.join(escaped_keywords) + r')(?!\w)', re.IGNORECASE)


# --- FUNGSI DATABASE (Dioptimalkan) ---
def is_job_exists(cursor, job_id):
    try:
        cursor.execute("SELECT id FROM raw_jobs WHERE job_id = %s", (job_id,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat cek duplikat: {err}")
        return False

def save_to_database(cursor, job_data):
    try:
        sql = """INSERT IGNORE INTO raw_jobs 
                 (job_id, title, company_name, location, job_url) 
                 VALUES (%s, %s, %s, %s, %s)"""
        val = (job_data['job_id'], job_data['title'], job_data['company'], 
               job_data['location'], job_data['url'])
        cursor.execute(sql, val)
        # conn.commit() dipindah ke proses batch per halaman agar jauh lebih ringan
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat menyimpan: {err}")


def run_scraper():
    conn = None
    cursor = None
    
    try:
        # Buka koneksi SATU KALI saja di awal
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) # Headless=False agar browser terlihat
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Dimulai dari halaman 1
            current_page = 1
            total_saved = 0
                
            while True:
                target_url = f"https://id.jobstreet.com/id/jobs/in-Batam-Kepulauan-Riau?sortmode=ListedDate&page={current_page}"
                print(f"\n🌍 Membuka JobStreet Batam - Halaman {current_page}...")
                
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Simulasi scroll untuk memastikan lazy loading termuat
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(1)
                    
                    # Tunggu elemen muncul
                    try:
                        page.wait_for_selector('[data-automation="jobTitle"]', timeout=10000)
                    except:
                        print(f"ℹ️ Elements tidak ditemukan di hal {current_page}. Mungkin sudah habis.")
                        break
                    
                    job_cards = page.locator('article').element_handles()
                    print(f"⏳ Mengekstrak {len(job_cards)} potensi kartu pekerjaan...")
                    
                    page_saved_count = 0
                    for card in job_cards:
                        try:
                            title_el = card.query_selector('[data-automation="jobTitle"]')
                            company_el = card.query_selector('[data-automation="jobCompany"]')
                            location_el = card.query_selector('[data-automation="jobLocation"]')
                            
                            if title_el:
                                title = title_el.inner_text()
                                partial_url = title_el.get_attribute('href')
                                full_url = f"https://id.jobstreet.com{partial_url}"
                                
                                # Ekstrak Job ID
                                match = re.search(r'-(\d{6,10})(\?|$)', partial_url)
                                job_id = match.group(1) if match else full_url.split('?')[0][-10:]
                                
                                # Cek database, lewati jika sudah ada
                                if is_job_exists(cursor, job_id):
                                    continue
                                
                                company = company_el.inner_text() if company_el else "Perusahaan Dirahasiakan"
                                location = location_el.inner_text() if location_el else "Batam"
                                
                                # Filter Keyword IT menggunakan Regex yang lebih akurat
                                if KEYWORD_PATTERN.search(title):
                                    job_data = {
                                        "job_id": job_id,
                                        "title": title,
                                        "company": company,
                                        "location": location,
                                        "url": full_url
                                    }
                                    save_to_database(cursor, job_data)
                                    page_saved_count += 1
                                    total_saved += 1
                        except Exception as e:
                            print(f"⚠️ Gagal mengekstrak kartu: {e}")
                            continue
                
                    # BATCH COMMIT: Simpan data database secara sekaligus per halaman
                    conn.commit()
                    print(f"✅ Halaman {current_page} selesai. {page_saved_count} lowongan baru disimpan.")

                    # --- LOGIKA PAGINATION (VERSI TERBARU SEEK/JOBSTREET) ---
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    
                    next_button = page.locator('[data-automation="page-next"], [aria-label="Next"], [aria-label="Selanjutnya"], [title="Next"], [title="Selanjutnya"]').first
                    
                    if next_button.is_visible() and next_button.get_attribute('disabled') is None:
                        current_page += 1
                        # Jeda acak 2-4 detik agar tidak terbaca bot agresif
                        time.sleep(random.uniform(2, 4))
                    else:
                        print("\n🏁 Tidak ada lagi tombol 'Next'. Semua halaman telah diproses.")
                        break

                except Exception as e:
                    print(f"❌ Kesalahan pada halaman {current_page}: {e}")
                    page.screenshot(path=f"error_page_{current_page}.png")
                    conn.commit()
                    break
                
            print(f"\n🎉 TOTAL AKHIR: {total_saved} lowongan IT berhasil masuk database.")
            browser.close()

    except mysql.connector.Error as err:
        print(f"❌ Gagal koneksi ke database: {err}")
    finally:
        # Menutup database dengan aman
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("🔒 Koneksi Database berhasil ditutup.")

if __name__ == "__main__":
    run_scraper()