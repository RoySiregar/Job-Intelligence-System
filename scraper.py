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

# --- FUNGSI DATABASE ---
def is_job_exists(cursor, job_id):
    try:
        cursor.execute("SELECT id FROM raw_jobs WHERE job_id = %s", (job_id,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat cek duplikat: {err}")
        return False

def save_to_database(cursor, conn, job_data):
    try:
        # Menambahkan kolom status secara eksplisit
        sql = """INSERT IGNORE INTO raw_jobs 
                 (job_id, title, company_name, location, job_url, status) 
                 VALUES (%s, %s, %s, %s, %s, 'NEW')"""
        val = (job_data['job_id'], job_data['title'], job_data['company'], 
               job_data['location'], job_data['url'])
        cursor.execute(sql, val)
        # --- PERBAIKAN 3: BATCH COMMIT (Setiap data baru masuk langsung simpan) ---
        conn.commit() 
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat menyimpan: {err}")


def run_scraper():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"❌ Gagal koneksi ke database: {err}")
        return 

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Headless=True agar lebih ringan
        
        # --- PERBAIKAN 2: ANTI-BOT (Headers & Context) ---
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        current_page = 1
        total_saved = 0
        stop_scraping = False
        consecutive_duplicates = 0
        MAX_TOLERANCE = 15
        
        while not stop_scraping:
            target_url = f"https://id.jobstreet.com/id/jobs/in-Batam-Kepulauan-Riau?sortmode=ListedDate&page={current_page}"
            print(f"\n🌍 Membuka Halaman {current_page}...")
            
            try:
                # --- PERBAIKAN 2: ANTI-BOT (Delay antar halaman) ---
                if current_page > 1:
                    wait_page = random.uniform(5, 8)
                    print(f"⏳ Jeda antar halaman {wait_page:.2f} detik...")
                    time.sleep(wait_page)

                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                
                # Simulasi scroll pelan untuk memicu lazy loading & terlihat manusiawi
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(1)
                
                try:
                    page.wait_for_selector('[data-automation="jobTitle"]', timeout=10000)
                except:
                    print(f"Elements tidak ditemukan. Mungkin sudah habis.")
                    break
                
                job_cards = page.locator('//div[.//a[@data-automation="jobTitle"]]').element_handles()
                
                page_saved_count = 0
                for card in job_cards:
                    try:
                        title_el = card.query_selector('[data-automation="jobTitle"]')
                        if title_el:
                            title = title_el.inner_text()
                            partial_url = title_el.get_attribute('href')
                            full_url = f"https://id.jobstreet.com{partial_url}"
                            
                            match = re.search(r'-(\d{6,10})(\?|$)', partial_url)
                            job_id = match.group(1) if match else full_url.split('?')[0][-10:]
                            
                            if is_job_exists(cursor, job_id):
                                consecutive_duplicates += 1
                                if consecutive_duplicates >= MAX_TOLERANCE:
                                    print(f"🛑 Batas duplikat ({MAX_TOLERANCE}) tercapai. Berhenti.")
                                    stop_scraping = True
                                    break
                                continue

                            consecutive_duplicates = 0 
                            
                            company_el = card.query_selector('[data-automation="jobCompany"]')
                            location_el = card.query_selector('[data-automation="jobLocation"]')
                            company = company_el.inner_text() if company_el else "Perusahaan Dirahasiakan"
                            location = location_el.inner_text() if location_el else "Batam"
                            
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
                        continue
                
                if stop_scraping:
                    break 

                print(f"✅ Halaman {current_page} selesai. {page_saved_count} IT disimpan.")

                # Klik Next Button dengan lebih aman
                next_button = page.locator('a[aria-label="Next"]').first
                if next_button.is_visible():
                    current_page += 1
                else:
                    break

            except Exception as e:
                print(f"❌ Kesalahan: {e}")
                break
                
        browser.close()
        cursor.close()
        conn.close()
        print(f"\n🎉 SELESAI! Total {total_saved} lowongan baru ditambahkan.")

if __name__ == "__main__":
    run_scraper()