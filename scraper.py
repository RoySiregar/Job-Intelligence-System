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

# --- FUNGSI DATABASE (Dioptimalkan) ---
def is_job_exists(cursor, job_id):
    try:
        cursor.execute("SELECT id FROM raw_jobs WHERE job_id = %s", (job_id,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat cek duplikat: {err}")
        return False

def save_to_database(cursor, conn, job_data):
    try:
        sql = """INSERT IGNORE INTO raw_jobs 
                 (job_id, title, company_name, location, job_url) 
                 VALUES (%s, %s, %s, %s, %s)"""
        val = (job_data['job_id'], job_data['title'], job_data['company'], 
               job_data['location'], job_data['url'])
        cursor.execute(sql, val)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat menyimpan: {err}")


def run_scraper():
    # --- BUKA KONEKSI DATABASE SATU KALI DI SINI ---
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"❌ Gagal koneksi ke database: {err}")
        return # Hentikan program jika gagal konek DB

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        current_page = 1
        total_saved = 0
        
        # --- KONFIGURASI TOLERANSI DUPLIKAT ---
        stop_scraping = False
        consecutive_duplicates = 0
        MAX_TOLERANCE = 15
        
        while not stop_scraping:
            target_url = f"https://id.jobstreet.com/id/jobs/in-Batam-Kepulauan-Riau?sortmode=ListedDate&page={current_page}"
            print(f"\n🌍 Membuka JobStreet Batam - Halaman {current_page}...")
            
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                
                try:
                    page.wait_for_selector('[data-automation="jobTitle"]', timeout=10000)
                except:
                    print(f"Elements tidak ditemukan di hal {current_page}. Mungkin sudah habis.")
                    break
                
                job_cards = page.locator('//div[.//a[@data-automation="jobTitle"]]').element_handles()
                print(f"⏳ Mengekstrak {len(job_cards)} potensi kartu pekerjaan...")
                
                page_saved_count = 0
                for card in job_cards:
                    try:
                        title_el = card.query_selector('[data-automation="jobTitle"]')
                        if title_el:
                            title = title_el.inner_text()
                            partial_url = title_el.get_attribute('href')
                            full_url = f"https://id.jobstreet.com{partial_url}"
                            
                            # Ekstrak Job ID
                            match = re.search(r'-(\d{6,10})(\?|$)', partial_url)
                            job_id = match.group(1) if match else full_url.split('?')[0][-10:]
                            
                            # --- CEK DUPLIKAT DENGAN TOLERANSI ---
                            if is_job_exists(cursor, job_id):
                                print(f"⏩ Lowongan ID {job_id} ({title}) sudah ada. Melewati...")
                                consecutive_duplicates += 1
                                
                                if consecutive_duplicates >= MAX_TOLERANCE:
                                    print(f"🛑 Menemukan {MAX_TOLERANCE} data lama berturut-turut. Menghentikan proses scraping...")
                                    stop_scraping = True
                                    break # Keluar dari loop card
                                    
                                continue # Lanjut ke card berikutnya

                            # --- PENTING: RESET COUNTER JIKA KETEMU DATA BARU ---
                            consecutive_duplicates = 0 
                            
                            company_el = card.query_selector('[data-automation="jobCompany"]')
                            location_el = card.query_selector('[data-automation="jobLocation"]')
                            company = company_el.inner_text() if company_el else "Perusahaan Dirahasiakan"
                            location = location_el.inner_text() if location_el else "Batam"
                            
                            # Filter Keyword IT
                            keywords = ['backend', 'back end', 'fullstack', 'full stack', 'software', 'programmer', 'developer', 'it', 'engineer', 'data', 'iot']
                            if any(kw in title.lower() for kw in keywords):
                                job_data = {
                                    "job_id": job_id,
                                    "title": title,
                                    "company": company,
                                    "location": location,
                                    "url": full_url
                                }
                                save_to_database(cursor, conn, job_data)
                                page_saved_count += 1
                                total_saved += 1
                                
                    except Exception as e:
                        print(f"⚠️ Error saat memproses 1 card: {e}")
                        continue
                
                if stop_scraping:
                    break # Keluar dari loop while (pindah halaman)

                print(f"✅ Halaman {current_page} selesai. {page_saved_count} lowongan baru IT disimpan.")

                # --- LOGIKA PAGINATION ---
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2) 

                next_button = page.locator('a[aria-label="Next"], a:has-text("Next")').first
                
                if next_button.is_visible():
                    print(f"➡️ Lanjut ke Halaman {current_page + 1}...")
                    current_page += 1
                    time.sleep(random.uniform(3, 5))
                else:
                    if len(job_cards) >= 30:
                         current_page += 1
                    else:
                         break

            except Exception as e:
                print(f"❌ Kesalahan pada halaman {current_page}: {e}")
                break
                
        print(f"\n🎉 SELESAI! Total {total_saved} lowongan baru berhasil ditambahkan.")
        
        # --- TUTUP BROWSER & DATABASE ---
        browser.close()
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run_scraper()