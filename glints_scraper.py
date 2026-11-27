import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright
import mysql.connector
import re
import time
import random

from glints_auth import new_context

FORCE_LOGIN = ("--relogin" in sys.argv)

# ==============================
# 1. KONFIGURASI DATABASE
# ==============================
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'autopilot_jobs_db'
}

# ==============================
# 2. KEYWORD ENGINE (Sama dengan JobStreet)
# ==============================
role_keywords = [
    'backend', 'back end', 'fullstack', 'full stack', 'software', 'programmer',
    'developer', 'it', 'engineer', 'data', 'iot', 'automation', 'system',
    'database', 'dba', 'api', 'architect', 'devops',
    'frontend', 'front end', 'web', 'mobile', 'android', 'ios',
    'ui', 'ux', 'qa', 'tester', 'quality assurance',
    'network', 'jaringan', 'infrastructure', 'security', 'cyber', 'cloud',
    'support', 'helpdesk', 'admin', 'erp', 'sap', 'informatika', 'informasi'
]

tech_keywords = [
    'python', 'c#', '.net', 'dotnet', 'sql', 'mysql', 'postgresql',
    'typescript', 'javascript', 'vue', 'react', 'node', 'nodejs',
    'java', 'php', 'laravel', 'golang', 'c++', 'aws', 'azure', 'mqtt'
]

industry_keywords = ['iiot', 'mes', 'oee', 'manufacturing']

all_keywords = role_keywords + tech_keywords + industry_keywords
escaped_keywords = [re.escape(kw) for kw in all_keywords]
KEYWORD_PATTERN = re.compile(r'(?<!\w)(' + '|'.join(escaped_keywords) + r')(?!\w)', re.IGNORECASE)


# ==============================
# 3. HELPERS
# ==============================
def normalize_job(href):
    """Return (full_url, job_id) dengan membuang query/fragment/trailing slash."""
    if not href:
        return None, None
    full = href if href.startswith('http') else f"https://glints.com{href}"
    clean = full.split('?')[0].split('#')[0].rstrip('/')
    job_id = clean.rsplit('/', 1)[-1]
    return full, job_id


def is_job_exists(cursor, job_id):
    try:
        cursor.execute("SELECT id FROM raw_jobs WHERE job_id = %s", (job_id,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat cek duplikat: {err}")
        return False


def save_to_database(cursor, job_data):
    """Simpan lowongan; return jumlah baris yang benar-benar di-insert (0 jika duplikat/error)."""
    try:
        sql = """INSERT IGNORE INTO raw_jobs
                 (job_id, title, company_name, location, job_url, category)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        val = (
            job_data['job_id'], job_data['title'], job_data['company'],
            job_data['location'], job_data['url'], job_data['category']
        )
        cursor.execute(sql, val)
        return cursor.rowcount
    except mysql.connector.Error as err:
        print(f"❌ Error DB saat menyimpan: {err}")
        return 0


def get_card_lines(handle):
    """
    Ambil baris teks dari container kartu terdekat.
    Naik ke parent sampai menemukan blok dengan >=2 baris (judul + perusahaan), maks 6 level.
    """
    try:
        txt = handle.evaluate("""el => {
            let n = el;
            for (let i = 0; i < 6 && n; i++) {
                const t = (n.innerText || '').trim();
                const lines = t.split('\\n').filter(x => x.trim());
                if (lines.length >= 2 && t.length < 500) return t;
                n = n.parentElement;
            }
            return (el.innerText || '').trim();
        }""")
    except Exception:
        txt = ""
    return [ln.strip() for ln in (txt or "").split('\n') if ln.strip()]


# ==============================
# 4. MAIN SCRAPER GLINTS
# ==============================
def run_glints_scraper():
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            context = new_context(browser, force_login=FORCE_LOGIN)
            page = context.new_page()

            current_page = 1
            total_saved = 0
            empty_page_count = 0

            while True:
                target_url = (
                    "https://glints.com/id/en/opportunities/jobs/explore?country=ID"
                    "&locationId=654dbd43-0da6-44a1-8fa6-3f2879b8fbdf"
                    "&locationName=Batam%2C+Kepulauan+Riau&lowestLocationLevel=3"
                    f"&page={current_page}"
                )
                print(f"\n🌍 Membuka Glints Batam - Halaman {current_page}...")

                try:
                    page.goto(target_url, wait_until="networkidle", timeout=60000)

                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 800)")
                        time.sleep(1)

                    handles = page.locator('a[href*="/opportunities/jobs/"]').element_handles()

                    # Kumpulkan 1 handle TERBAIK per job_id (anchor judul = paling banyak teks)
                    best = {}
                    for h in handles:
                        href = h.get_attribute('href')
                        full_url, job_id = normalize_job(href)
                        if not job_id or len(job_id) < 20 or job_id.lower() == 'explore':
                            continue
                        try:
                            atext = (h.inner_text() or '').strip()
                        except Exception:
                            atext = ''
                        if job_id not in best or len(atext) > len(best[job_id][1]):
                            best[job_id] = (h, atext, full_url)

                    if not best:
                        print(f"ℹ️ Tidak ada job card valid ditemukan di halaman {current_page}.")
                        empty_page_count += 1
                        if empty_page_count >= 2:
                            print("🏁 Sepertinya sudah mencapai akhir halaman Glints.")
                            break
                    else:
                        empty_page_count = 0

                    print(f"⏳ Mengekstrak {len(best)} lowongan unik dari {len(handles)} anchor di Glints...")

                    page_saved = 0
                    skipped = {'dup': 0, 'no_title': 0, 'no_kw': 0, 'db': 0}

                    for idx, (job_id, (handle, atext, full_url)) in enumerate(best.items()):
                        if is_job_exists(cursor, job_id):
                            skipped['dup'] += 1
                            continue

                        lines = get_card_lines(handle)
                        anchor_lines = [ln.strip() for ln in atext.split('\n') if ln.strip()]

                        # Judul: utamakan teks anchor (link judul), fallback ke baris container
                        title = anchor_lines[0] if anchor_lines else (lines[0] if lines else '')
                        if not title:
                            skipped['no_title'] += 1
                            continue

                        # Perusahaan: baris pertama container yang bukan judul
                        company = ''
                        for ln in lines:
                            if ln and ln != title and not ln.lower().startswith('quick'):
                                company = ln
                                break
                        if not company:
                            company = 'Perusahaan Dirahasiakan'

                        if current_page == 1 and idx < 3:
                            print(f"🔎 sample → title='{title}' | company='{company}' | id={job_id}")

                        if not KEYWORD_PATTERN.search(title):
                            skipped['no_kw'] += 1
                            continue

                        job_data = {
                            "job_id": job_id,
                            "title": title,
                            "company": company,
                            "location": "Batam",
                            "url": full_url,
                            "category": "GLINTS"
                        }
                        inserted = save_to_database(cursor, job_data)
                        if inserted:
                            page_saved += 1
                            total_saved += 1
                        else:
                            skipped['db'] += 1

                    conn.commit()
                    print(
                        f"✅ Halaman {current_page} selesai. {page_saved} tersimpan | "
                        f"skip: duplikat={skipped['dup']}, tanpa_judul={skipped['no_title']}, "
                        f"non-IT={skipped['no_kw']}, db={skipped['db']}"
                    )

                    current_page += 1
                    time.sleep(random.uniform(3, 6))

                except Exception as e:
                    print(f"❌ Kesalahan pada halaman {current_page}: {e}")
                    try:
                        page.screenshot(path=f"glints_error_page_{current_page}.png")
                    except Exception:
                        pass
                    break

            print(f"\n🎉 TOTAL AKHIR: {total_saved} lowongan Glints berhasil masuk database.")
            browser.close()

    except mysql.connector.Error as err:
        print(f"❌ Gagal koneksi ke database: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("🔒 Koneksi Database berhasil ditutup.")


if __name__ == "__main__":
    run_glints_scraper()
