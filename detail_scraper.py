from playwright.sync_api import sync_playwright
import mysql.connector

# Konfigurasi Koneksi Database Laragon
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'autopilot_jobs_db'
}

def get_jobs_without_description():
    """Mengambil daftar lowongan yang kolom deskripsinya masih kosong/NULL."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True) # dictionary=True agar hasil bisa dipanggil seperti array asosiatif
        
        # Ambil ID dan URL yang belum punya deskripsi
        cursor.execute("SELECT id, title, company_name, job_url FROM raw_jobs WHERE job_description IS NULL")
        jobs = cursor.fetchall()
        return jobs
    except mysql.connector.Error as err:
        print(f"❌ Error DB: {err}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def update_job_description(db_id, description_text):
    """Menyimpan teks deskripsi kembali ke database dan mengubah statusnya."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Update deskripsi dan ubah status menjadi DRAFT_READY (Siap diproses AI)
        sql = "UPDATE raw_jobs SET job_description = %s, status = 'DRAFT_READY' WHERE id = %s"
        cursor.execute(sql, (description_text, db_id))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"❌ Error Update DB: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def run_detail_scraper():
    jobs = get_jobs_without_description()
    
    if not jobs:
        print("✅ Semua lowongan di database sudah memiliki deskripsi. Tidak ada yang perlu di-scrape.")
        return

    print(f"🔍 Ditemukan {len(jobs)} lowongan tanpa deskripsi. Memulai proses ekstraksi...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for job in jobs:
            print(f"\n🌍 Membuka: {job['title']} di {job['company_name']}")
            try:
                page.goto(job['job_url'], wait_until="domcontentloaded", timeout=30000)
                
                # Daftar kemungkinan target elemen deskripsi di JobStreet
                selectors = [
                    '[data-automation="jobDescription"]',
                    '[data-automation="jobAdDetails"]',
                    '[data-automation="job-description"]',
                    '.job-description'
                ]
                
                description_el = None
                
                # Coba satu per satu selector di atas
                for sel in selectors:
                    try:
                        # Tunggu maksimal 5 detik untuk tiap target
                        page.wait_for_selector(sel, timeout=5000)
                        description_el = page.locator(sel)
                        break  # Jika ketemu, langsung keluar dari loop pencarian
                    except:
                        continue # Jika tidak ketemu, lanjut coba target berikutnya
                
                if description_el:
                    # Teks berhasil ditemukan
                    full_description = description_el.inner_text()
                    update_job_description(job['id'], full_description)
                    print(f"✅ Deskripsi berhasil disimpan (Panjang teks: {len(full_description)} karakter)")
                else:
                    # Teks sama sekali tidak ditemukan dari semua target
                    print(f"⚠️ Gagal: Elemen deskripsi tidak ditemukan di halaman ini.")
                    # Buat nama file aman dari judul pekerjaan
                    safe_title = "".join([c for c in job['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    screenshot_path = f"error_detail_{safe_title}.png"
                    
                    page.screenshot(path=screenshot_path)
                    print(f"📸 Screenshot halaman disimpan sebagai: {screenshot_path}")
                
            except Exception as e:
                print(f"⚠️ Gagal memuat halaman secara keseluruhan: {e}")
                
        browser.close()
        print("\n🎉 Proses ekstraksi detail lowongan selesai!")

if __name__ == "__main__":
    run_detail_scraper()