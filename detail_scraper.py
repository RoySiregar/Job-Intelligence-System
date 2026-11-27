# ==============================
# detail_scraper.py
# ==============================

import os
import re
import time
import random
import mysql.connector

from playwright.sync_api import sync_playwright

# ==============================
# DATABASE CONFIG
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

ROLE_SCORES = {
    "backend": 5,
    "frontend": 5,
    "fullstack": 6,
    "developer": 5,
    "software engineer": 6,
    "programmer": 5,
    "devops": 5,
    "qa": 4,
    "automation": 4,
    "data analyst": 4,
    "data engineer": 5,
    "it support": 3,
    "network": 3,
    "cloud": 4,
    "cybersecurity": 5,
}

TECH_SCORES = {
    "python": 4,
    "c#": 4,
    ".net": 4,
    "java": 4,
    "javascript": 4,
    "react": 3,
    "vue": 3,
    "nodejs": 3,
    "mysql": 3,
    "postgresql": 3,
    "docker": 4,
    "linux": 3,
    "mqtt": 4,
    "iot": 4,
    "plc": 5,
    "scada": 5,
    "modbus": 5,
}

FRESH_GRAD = {
    "fresh graduate": 6,
    "entry level": 5,
    "junior": 4,
    "0-2 years": 5,
}

NEGATIVE = {
    "senior": -6,
    "manager": -8,
    "lead": -5,
    "director": -10,
    "5 years": -5,
    "7 years": -7,
}

# ==============================
# CALCULATE SCORE
# ==============================

def calculate_score(title, description):

    score = 0

    title = title.lower()
    description = description.lower()

    text = f"{title} {description}"

    # Prioritas title
    for keyword, value in ROLE_SCORES.items():

        if keyword in title:
            score += value * 2

        elif keyword in text:
            score += value

    # Tech stack
    for keyword, value in TECH_SCORES.items():

        if keyword in text:
            score += value

    # Fresh grad
    for keyword, value in FRESH_GRAD.items():

        if keyword in text:
            score += value

    # Negative
    for keyword, value in NEGATIVE.items():

        if keyword in text:
            score += value

    return score

# ==============================
# GET JOBS
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

        print(f"❌ DB Error: {err}")
        return []

    finally:

        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# ==============================
# UPDATE DB
# ==============================

def update_job(cursor, db_id, description, score, status):

    sql = """
    UPDATE raw_jobs
    SET
        job_description = %s,
        match_score = %s,
        status = %s
    WHERE id = %s
    """

    cursor.execute(
        sql,
        (description, score, status, db_id)
    )

# ==============================
# MAIN DETAIL SCRAPER
# ==============================

def run_detail_scraper():

    jobs = get_jobs_without_description()

    if not jobs:
        print("✅ Semua lowongan sudah diproses")
        return

    debug_folder = "Screenshot_debug"

    if not os.path.exists(debug_folder):
        os.makedirs(debug_folder)

    print(f"🔍 {len(jobs)} lowongan akan diproses")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="id-ID"
        )

        context.set_extra_http_headers({
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Referer": "https://id.jobstreet.com/",
            "DNT": "1"
        })

        for job in jobs:

            wait_time = random.uniform(4, 8)

            print(f"\n⏳ Delay {wait_time:.2f} detik")

            time.sleep(wait_time)

            print(f"🌍 {job['title']}")

            page = context.new_page()

            try:

                success = False

                for attempt in range(3):

                    try:

                        page.goto(
                            job['job_url'],
                            wait_until="domcontentloaded",
                            timeout=30000
                        )

                        page.mouse.move(
                            random.randint(100, 500),
                            random.randint(100, 500)
                        )

                        page.mouse.wheel(0, 800)

                        success = True
                        break

                    except:
                        print(f"⚠️ Retry {attempt+1}")
                        time.sleep(3)

                if not success:
                    continue

                selectors = [
                    '[data-automation="jobDescription"]',
                    '[data-automation="jobAdDetails"]',
                    '.job-description'
                ]

                description_text = None

                for sel in selectors:

                    try:

                        page.wait_for_selector(sel, timeout=7000)

                        description_text = page.locator(sel).inner_text()

                        break

                    except:
                        continue

                if not description_text:

                    print("⚠️ Deskripsi tidak ditemukan")

                    safe_title = re.sub(
                        r'[^a-zA-Z0-9]',
                        '_',
                        job['title']
                    )

                    page.screenshot(
                        path=os.path.join(
                            debug_folder,
                            f"{safe_title}.png"
                        )
                    )

                    continue

                # Clean text
                description_text = re.sub(
                    r'\s+',
                    ' ',
                    description_text
                ).strip()

                score = calculate_score(
                    job['title'],
                    description_text
                )

                # FILTER LOWONGAN
                if score >= 15:
                    status = "HIGH_MATCH"

                elif score >= 10:
                    status = "MEDIUM_MATCH"

                elif score >= 6:
                    status = "LOW_MATCH"

                else:
                    status = "REJECTED"

                update_job(
                    cursor,
                    job['id'],
                    description_text,
                    score,
                    status
                )

                conn.commit()

                print(f"✅ Score: {score} | Status: {status}")

            except Exception as e:

                print(f"❌ ERROR: {e}")

            finally:

                page.close()

        browser.close()

    cursor.close()
    conn.close()

    print("\n🎉 Semua detail selesai diproses")


if __name__ == "__main__":
    run_detail_scraper()