import os
from playwright.sync_api import sync_playwright
import mysql.connector
import time
import random

# ==============================
# CONFIG DATABASE
# ==============================
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'autopilot_jobs_db'
}

# ==============================
# SCORING ENGINE
# ==============================
def calculate_score(title, description):
    score = 0
    text = (title + " " + description).lower()

    # Skill matching
    if "c#" in text: score += 3
    if ".net" in text: score += 3
    if "python" in text: score += 2
    if "mysql" in text: score += 2
    if "mqtt" in text: score += 4
    if "iot" in text: score += 4

    # Role matching
    if "backend" in text: score += 3
    if "automation" in text: score += 3
    if "engineer" in text: score += 2

    # Negative filter
    if "senior" in text: score -= 5
    if "manager" in text: score -= 5
    if "5 years" in text: score -= 3

    return score


# ==============================
# GET JOB DATA
# ==============================
def get_jobs_without_description():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, title, company_name, job_url 
            FROM raw_jobs 
            WHERE job_description IS NULL
        """)

        jobs = cursor.fetchall()
        return jobs

    except mysql.connector.Error as err:
        print(f"❌ Error DB: {err}")
        return []

    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


# ==============================
# UPDATE DATABASE
# ==============================
def update_job_description(cursor, db_id, description_text, score):
    sql = """
        UPDATE raw_jobs 
        SET job_description = %s, 
            status = 'DRAFT_READY',
            match_score = %s
        WHERE id = %s
    """
    cursor.execute(sql, (description_text, score, db_id))


# ==============================
# MAIN SCRAPER
# ==============================
def run_detail_scraper():
    jobs = get_jobs_without_description()

    if not jobs:
        print("✅ Semua lowongan sudah memiliki deskripsi.")
        return
    
    debug_folder = "Screenshot_debug"
    if not os.path.exists(debug_folder):
        os.makedirs(debug_folder)

    print(f"🔍 Ditemukan {len(jobs)} job, mulai scraping...\n")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- PERBAIKAN 2: ANTI-BOT (Headers Lengkap) ---
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Menambahkan header ekstra agar terlihat seperti browser asli
        context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Referer": "https://id.jobstreet.com/",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1"
        })

        page = context.new_page()

        for job in jobs:
            # --- PERBAIKAN 2: ANTI-BOT (Jeda lebih lama & random) ---
            wait_time = random.uniform(5, 10)
            print(f"⏳ Menunggu {wait_time:.2f} detik...")
            time.sleep(wait_time)

            print(f"🌍 Memproses: {job['title']} | {job['company_name']}")

            try:
                for attempt in range(3):
                    try:
                        page.goto(job['job_url'], wait_until="domcontentloaded", timeout=30000)
                        # Gerakkan mouse sedikit untuk simulasi manusia
                        page.mouse.move(random.randint(0, 500), random.randint(0, 500))
                        break
                    except:
                        print(f"⚠️ Retry {attempt+1} untuk {job['title']}")
                        time.sleep(3)

                selectors = [
                    '[data-automation="jobDescription"]',
                    '[data-automation="jobAdDetails"]',
                    '.job-description'
                ]

                description_el = None
                for sel in selectors:
                    try:
                        page.wait_for_selector(sel, timeout=7000)
                        description_el = page.locator(sel)
                        break
                    except:
                        continue

                if description_el:
                    full_description = description_el.inner_text()
                    score = calculate_score(job['title'], full_description)

                    # Simpan data
                    update_job_description(cursor, job['id'], full_description, score)
                    
                    # --- PERBAIKAN 3: BATCH/INCREMENTAL COMMIT ---
                    # Commit setiap kali satu data berhasil diambil agar tidak hilang jika terputus
                    conn.commit() 
                    print(f"✅ SUCCESS | Score: {score} | Data disimpan ke DB.")

                else:
                    print("⚠️ Deskripsi tidak ditemukan")
                    safe_title = "".join([c for c in job['title'] if c.isalnum() or c == " "]).strip().replace(" ", "_")
                    page.screenshot(path=os.path.join(debug_folder, f"error_{safe_title}.png"))

            except Exception as e:
                print(f"❌ ERROR pada {job['title']}: {e}")

        browser.close()

    cursor.close()
    conn.close()
    print("\n🎉 SELESAI! Semua data sudah diproses dan tersimpan.")

if __name__ == "__main__":
    run_detail_scraper()