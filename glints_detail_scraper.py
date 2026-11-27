"""
glints_detail_scraper.py  —  Detail scraper khusus GLINTS
===========================================================
Padanan detail_scraper.py (yang khusus JobStreet). File ini TIDAK mengubah
scraper.py / detail_scraper.py. Tugasnya:

  1. (Login) Pakai sesi Glints tersimpan, atau minta login manual sekali.
  2. Ambil lowongan Glints dari raw_jobs yang job_description-nya masih NULL.
  3. Buka halaman detail Glints, ekstrak deskripsi (multi-strategi).
  4. Hitung skor (mesin skor sama dengan detail_scraper.py).
  5. Simpan job_description + match_score + status.

Cara pakai:
  run.bat glints_detail_scraper.py
  run.bat glints_detail_scraper.py 10           (batasi 10 untuk tes)
  run.bat glints_detail_scraper.py 10 --debug   (detail strategi ekstraksi)
  run.bat glints_detail_scraper.py --relogin    (paksa login ulang)

Sesi login disimpan di glints_auth.json (cookies + localStorage) dan dipakai
bersama oleh glints_scraper.py juga.
"""

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import re
import json
import time
import random
import html as html_lib
import mysql.connector
from playwright.sync_api import sync_playwright

from glints_auth import new_context

# ==============================
# DATABASE CONFIG
# ==============================
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'autopilot_jobs_db'
}

LIMIT = None
for arg in sys.argv[1:]:
    if arg.isdigit():
        LIMIT = int(arg)
        break
DEBUG = ("--debug" in sys.argv)
FORCE_LOGIN = ("--relogin" in sys.argv)

# ==============================
# SCORING ENGINE (sama dengan detail_scraper.py)
# ==============================
ROLE_SCORES = {
    "backend": 5, "frontend": 5, "fullstack": 6, "developer": 5,
    "software engineer": 6, "programmer": 5, "devops": 5, "qa": 4,
    "automation": 4, "data analyst": 4, "data engineer": 5,
    "it support": 3, "network": 3, "cloud": 4, "cybersecurity": 5,
}
TECH_SCORES = {
    "python": 4, "c#": 4, ".net": 4, "java": 4, "javascript": 4,
    "react": 3, "vue": 3, "nodejs": 3, "mysql": 3, "postgresql": 3,
    "docker": 4, "linux": 3, "mqtt": 4, "iot": 4, "plc": 5,
    "scada": 5, "modbus": 5,
}
FRESH_GRAD = {"fresh graduate": 6, "entry level": 5, "junior": 4, "0-2 years": 5}
NEGATIVE = {"senior": -6, "manager": -8, "lead": -5, "director": -10, "5 years": -5, "7 years": -7}


def calculate_score(title, description):
    score = 0
    title = (title or "").lower()
    description = (description or "").lower()
    text = f"{title} {description}"

    for keyword, value in ROLE_SCORES.items():
        if keyword in title:
            score += value * 2
        elif keyword in text:
            score += value

    for keyword, value in TECH_SCORES.items():
        if keyword in text:
            score += value

    for keyword, value in FRESH_GRAD.items():
        if keyword in text:
            score += value

    for keyword, value in NEGATIVE.items():
        if keyword in text:
            score += value

    return score


# ==============================
# DATABASE
# ==============================
def get_glints_jobs_without_description():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT id, title, company_name, job_url
            FROM raw_jobs
            WHERE job_description IS NULL
              AND (job_url LIKE '%glints.com%' OR category = 'GLINTS')
            ORDER BY id ASC
        """
        if LIMIT:
            query += f" LIMIT {int(LIMIT)}"
        cursor.execute(query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def update_job(cursor, db_id, description, score, status):
    sql = """
        UPDATE raw_jobs
        SET job_description = %s, match_score = %s, status = %s
        WHERE id = %s
    """
    cursor.execute(sql, (description, score, status, db_id))


# ==============================
# TEXT CLEANING
# ==============================
def clean_text(raw):
    if not raw:
        return ""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h[1-6])>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    s = s.strip()
    return s[:20000]


# ==============================
# EXTRACTION (multi-strategi)
# ==============================
def _find_jobposting(obj):
    if isinstance(obj, list):
        for it in obj:
            r = _find_jobposting(it)
            if r:
                return r
        return None
    if isinstance(obj, dict):
        t = obj.get("@type")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            return obj
        if "@graph" in obj:
            r = _find_jobposting(obj["@graph"])
            if r:
                return r
        for v in obj.values():
            if isinstance(v, (dict, list)):
                r = _find_jobposting(v)
                if r:
                    return r
    return None


def extract_jsonld(page):
    try:
        scripts = page.eval_on_selector_all(
            'script[type="application/ld+json"]',
            "els => els.map(e => e.textContent)"
        )
    except Exception:
        return None
    for raw in scripts or []:
        if not raw or not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        jp = _find_jobposting(data)
        if jp and jp.get("description"):
            return jp
    return None


GLINTS_SELECTORS = [
    '[data-testid="job-description"]',
    '[data-testid="jobDescription"]',
    '[data-cy="job-description"]',
    'div[class*="JobDescriptionsc"]',
    'div[class*="JobDescription"]',
    'div[class*="jobDescription"]',
    'section[class*="description"]',
    'div[class*="description"]',
    '.job-description',
    'article',
]


def extract_by_selectors(page):
    best = ""
    for sel in GLINTS_SELECTORS:
        try:
            loc = page.locator(sel)
            count = loc.count()
        except Exception:
            continue
        for i in range(min(count, 5)):
            try:
                t = loc.nth(i).inner_text(timeout=1500) or ""
            except Exception:
                continue
            if len(t) > len(best):
                best = t
    return best.strip()


def extract_main_heuristic(page):
    try:
        txt = page.evaluate(
            "() => { const m = document.querySelector('main') || document.body; return m ? m.innerText : ''; }"
        ) or ""
    except Exception:
        txt = ""
    m = re.search(
        r"(Job Description|Deskripsi Pekerjaan|Job Requirements|Kualifikasi|Responsibilit)",
        txt, re.IGNORECASE
    )
    if m:
        txt = txt[m.start():]
    return txt.strip()


def extract_og(page):
    try:
        return (page.eval_on_selector('meta[property="og:description"]', "e => e.content") or "").strip()
    except Exception:
        return ""


def extract_description(page):
    """Return (text, source). Prioritas: JSON-LD > selector Glints > <main> > og:description."""
    candidates = []

    jp = extract_jsonld(page)
    if jp:
        candidates.append(("json-ld", clean_text(jp.get("description", ""))))
    sel = extract_by_selectors(page)
    if sel:
        candidates.append(("selectors", clean_text(sel)))
    main = extract_main_heuristic(page)
    if main:
        candidates.append(("main", clean_text(main)))
    og = extract_og(page)
    if og:
        candidates.append(("og:description", clean_text(og)))

    for src in ("json-ld", "selectors"):
        for name, txt in candidates:
            if name == src and len(txt) >= 80:
                return txt, name

    if candidates:
        name, txt = max(candidates, key=lambda x: len(x[1]))
        if txt:
            return txt, name
    return "", "none"


# ==============================
# MAIN
# ==============================
def run_glints_detail_scraper():
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )

            # Login / sesi dilakukan SEBELUM cek lowongan (agar jeda login selalu muncul).
            context = new_context(browser, force_login=FORCE_LOGIN)

            jobs = get_glints_jobs_without_description()
            if not jobs:
                print("✅ Tidak ada lowongan Glints yang perlu diproses (semua sudah punya deskripsi).")
                browser.close()
                return

            debug_folder = "Screenshot_debug_glints"
            if not os.path.exists(debug_folder):
                os.makedirs(debug_folder)

            print(f"🔍 {len(jobs)} lowongan Glints akan diproses" + (f" (limit {LIMIT})" if LIMIT else ""))

            success = 0
            for job in jobs:
                wait_time = random.uniform(3.5, 7.0)
                print(f"\n⏳ Delay {wait_time:.2f} detik ...")
                time.sleep(wait_time)

                print(f"🌍 {job['title']} — {job['company_name']}")
                page = context.new_page()

                try:
                    ok = False
                    for attempt in range(3):
                        try:
                            page.goto(job['job_url'], wait_until="domcontentloaded", timeout=30000)
                            page.mouse.move(random.randint(100, 600), random.randint(100, 500))
                            page.mouse.wheel(0, 800)
                            time.sleep(random.uniform(1.0, 2.0))
                            ok = True
                            break
                        except Exception:
                            print(f"⚠️ Retry {attempt + 1}")
                            time.sleep(3)

                    if not ok:
                        print("❌ Gagal membuka halaman.")
                        continue

                    for label in ["See more", "Read more", "Show more", "Lihat selengkapnya", "Selengkapnya"]:
                        try:
                            btn = page.get_by_text(label, exact=False).first
                            if btn.is_visible():
                                btn.click(timeout=1500)
                                time.sleep(0.4)
                                break
                        except Exception:
                            continue
                    for label in ["Accept all", "Accept", "Terima semua", "Setuju"]:
                        try:
                            btn = page.get_by_role("button", name=re.compile(label, re.I)).first
                            if btn.is_visible():
                                btn.click(timeout=1200)
                                time.sleep(0.3)
                                break
                        except Exception:
                            continue

                    page.mouse.wheel(0, 1200)
                    time.sleep(0.6)

                    description, source = extract_description(page)

                    if DEBUG:
                        print(f"   ↳ source={source} len={len(description)}")

                    if not description or len(description) < 40:
                        print("⚠️ Deskripsi tidak ditemukan — simpan screenshot + HTML untuk inspeksi.")
                        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', job['title'])[:60]
                        try:
                            page.screenshot(path=os.path.join(debug_folder, f"{safe_title}.png"))
                            with open(os.path.join(debug_folder, f"{safe_title}.html"), "w", encoding="utf-8") as f:
                                f.write(page.content())
                        except Exception:
                            pass
                        continue

                    score = calculate_score(job['title'], description)

                    if score >= 15:
                        status = "HIGH_MATCH"
                    elif score >= 10:
                        status = "MEDIUM_MATCH"
                    elif score >= 6:
                        status = "LOW_MATCH"
                    else:
                        status = "REJECTED"

                    update_job(cursor, job['id'], description, score, status)
                    conn.commit()

                    success += 1
                    print(f"✅ [{source}] {len(description)} chars | Score: {score} | Status: {status}")

                except Exception as e:
                    print(f"❌ ERROR: {e}")

                finally:
                    try:
                        page.close()
                    except Exception:
                        pass

            browser.close()
            print(f"\n🎉 Selesai. {success}/{len(jobs)} lowongan Glints berhasil diisi deskripsi.")

    except mysql.connector.Error as err:
        print(f"❌ Gagal koneksi ke database: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    run_glints_detail_scraper()
