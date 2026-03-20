from playwright.sync_api import sync_playwright
import mysql.connector
import re

# Konfigurasi Koneksi Database Laragon
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '', # Kosongkan karena default Laragon tidak pakai password
    'database': 'autopilot_jobs_db'
}

def save_to_database(job_data):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Menggunakan INSERT IGNORE agar lowongan yang sama tidak tersimpan ganda
        sql = """INSERT IGNORE INTO raw_jobs 
                 (job_id, title, company_name, location, job_url) 
                 VALUES (%s, %s, %s, %s, %s)"""
        
        val = (job_data['job_id'], job_data['title'], job_data['company'], 
               job_data['location'], job_data['url'])
        
        cursor.execute(sql, val)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"❌ Error DB: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def run_scraper():
    with sync_playwright() as p:
        # Tambahkan argumen user_agent agar lebih terlihat seperti manusia, bukan bot
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        target_url = "https://id.jobstreet.com/id/jobs/in-Batam-Kepulauan-Riau?sortmode=ListedDate"
        print("🌍 Membuka JobStreet Batam...")
        
        try:
            page.goto(target_url, wait_until="domcontentloaded")
            
            # Kita ganti targetnya. Alih-alih mencari <article>, kita cari judul pekerjaannya langsung
            print("⏳ Menunggu elemen lowongan kerja muncul...")
            page.wait_for_selector('[data-automation="jobTitle"]', timeout=15000)
            
            # Jika berhasil lewat dari wait_for_selector, berarti data ada
            # Ambil semua elemen pembungkus yang memiliki judul pekerjaan
            job_cards = page.locator('//div[.//a[@data-automation="jobTitle"]]').element_handles()
            
            print(f"✅ Ditemukan {len(job_cards)} potensi kartu pekerjaan. Mulai ekstraksi...")
            
            saved_count = 0
            
            for card in job_cards:
                try:
                    title_el = card.query_selector('[data-automation="jobTitle"]')
                    company_el = card.query_selector('[data-automation="jobCompany"]')
                    location_el = card.query_selector('[data-automation="jobLocation"]')
                    
                    if title_el:
                        title = title_el.inner_text()
                        partial_url = title_el.get_attribute('href')
                        full_url = f"https://id.jobstreet.com{partial_url}"
                        
                        match = re.search(r'-(\d{6,10})(\?|$)', partial_url)
                        job_id = match.group(1) if match else full_url.split('?')[0][-10:]
                        
                        company = company_el.inner_text() if company_el else "Perusahaan Dirahasiakan"
                        location = location_el.inner_text() if location_el else "Batam"
                        
                        keywords = ['backend', 'back end', 'fullstack', 'full stack', 'software', 'programmer', 'developer', 'it', 'engineer', 'data']
                        if any(kw in title.lower() for kw in keywords):
                            job_data = {
                                "job_id": job_id,
                                "title": title,
                                "company": company,
                                "location": location,
                                "url": full_url
                            }
                            
                            save_to_database(job_data)
                            print(f"💾 Disimpan: {title} | {company}")
                            saved_count += 1
                except Exception as e:
                    pass # Abaikan error per kartu agar loop tetap berjalan
                    
            print(f"\n🎉 Selesai! {saved_count} lowongan IT berhasil dimasukkan ke database.")
            
        except Exception as e:
            print(f"❌ Terjadi kesalahan atau Timeout: {e}")
            print("📸 Mengambil screenshot untuk dianalisis (lihat file error_screenshot.png di folder Anda)")
            page.screenshot(path="error_screenshot.png")
            
        finally:
            browser.close()

# BLOK EKSEKUSI UTAMA
if __name__ == "__main__":
    run_scraper()