import mysql.connector
import json
import os
import time  # Ditambahkan untuk jeda waktu
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# ==========================================
# KONFIGURASI DATABASE & API
# ==========================================
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'autopilot_jobs_db'
}

# --- MASUKKAN API KEY GEMINI ANDA DI SINI ---
API_KEY = "AIzaSyBS4r3GzKsZr1vG57UER9kiA-VxzsLKFV0"

# Inisialisasi Client Gemini
client = genai.Client(api_key=API_KEY)

# ==========================================
# FUNGSI PENDUKUNG
# ==========================================
def load_my_profile():
    if not os.path.exists('profile.json'):
        return None
    with open('profile.json', 'r', encoding='utf-8') as file:
        return json.load(file)

def get_draft_ready_job():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        # Ambil 1 lowongan yang statusnya DRAFT_READY
        cursor.execute("SELECT id, title, company_name, job_description FROM raw_jobs WHERE status = 'DRAFT_READY' AND job_description IS NOT NULL LIMIT 1")
        return cursor.fetchone()
    except Exception as e:
        print(f"❌ Error DB: {e}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def save_ai_result(job_id, keywords, cover_letter):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        sql = "UPDATE raw_jobs SET skills_required = %s, cover_letter = %s, status = 'APPLIED' WHERE id = %s"
        cursor.execute(sql, (keywords, cover_letter, job_id))
        conn.commit()
    except Exception as e:
        print(f"❌ Error Update DB: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def generate_pdf_with_playwright(html_content, output_filename):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(path=output_filename, format="A4", print_background=True)
        browser.close()

# ==========================================
# FUNGSI UTAMA AI PROCESSSOR
# ==========================================
def process_all_jobs():
    print("🚀 Memulai pemrosesan massal Auto-Pilot AI (Dynamic PDF Generation)...")
    
    my_real_profile = load_my_profile()
    if not my_real_profile:
        print("❌ File profile.json tidak ditemukan.")
        return 
        
    profile_string = json.dumps(my_real_profile, indent=2)
    processed_count = 0
    
    if not os.path.exists("Tailored_CVs"):
        os.makedirs("Tailored_CVs")
        
    if not os.path.exists('template.html'):
        print("❌ File template.html tidak ditemukan!")
        return
        
    with open('template.html', 'r', encoding='utf-8') as f:
        html_template = f.read()
    
    while True:
        job = get_draft_ready_job()
        
        if not job:
            print(f"\n🎉 Selesai! Tidak ada lagi lowongan DRAFT_READY. Total PDF: {processed_count}")
            break

        print(f"\n🤖 Menganalisis CV untuk: {job['title']} di {job['company_name']}...")

        prompt = f"""
        Anda adalah asisten karir profesional. Buat Cover Letter dan susun ulang Profil Kandidat ke dalam potongan kode HTML murni.

        PROFIL ASLI KANDIDAT:
        {profile_string}

        DESKRIPSI PEKERJAAN ({job['title']} di {job['company_name']}):
        {job['job_description']}

        INSTRUKSI:
        1. 100% BAHASA INGGRIS.
        2. Gunakan tag HTML dasar (<p>, <ul>, <li>, <strong>).
        3. 'summary_html': 1 paragraf ringkasan profesional.
        4. 'skills_html': Urutkan skill yang paling relevan di depan.
        5. 'experience_html' & 'projects_html': Gunakan bullet points, fokus pada fakta teknis (C#, .NET, MQTT, MySQL).
        6. 'education_focus': 3-4 topik CS relevan.
        
        Berikan jawaban HANYA dalam JSON:
        {{
            "keywords": "...",
            "cover_letter": "...",
            "summary_html": "...",
            "skills_html": "...",
            "experience_html": "...",
            "projects_html": "...",
            "education_focus": "..."
        }}
        """

        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash', # Menggunakan model 2.0 Flash
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2 
                )
            )
            
            ai_data = json.loads(response.text.strip())
            
            # 1. Simpan ke Database
            save_ai_result(job['id'], ai_data['keywords'], ai_data['cover_letter'])
            
            # 2. Merakit HTML Final
            final_html = html_template
            final_html = final_html.replace('{{NAME}}', my_real_profile['personal_info']['name'])
            
            p_info = my_real_profile['personal_info']
            exp = my_real_profile['work_experience'][0]
            
            line1 = f"{p_info['location']} | {p_info.get('phone', '')} | <a href='mailto:{p_info['email']}'>{p_info['email']}</a>"
            github_text = p_info['github'].replace('https://', '')
            portfolio_val = p_info.get('portfolio', '')
            portfolio_url = f"https://{portfolio_val}" if not portfolio_val.startswith('http') else portfolio_val
            line2 = f"<a href='{p_info['linkedin']}'>{p_info['linkedin']}</a> | <a href='{p_info['github']}'>{github_text}</a> | <a href='{portfolio_url}'>{portfolio_val}</a>"
            
            final_html = final_html.replace('{{CONTACT_INFO}}', f"{line1}<br>{line2}")

            job_header = f"<p><strong>{exp['role']}</strong> | {exp['company']}<br><i>{exp['division']}</i> | {exp['duration']}</p>"
            
            final_html = final_html.replace('{{SUMMARY}}', ai_data['summary_html'])
            final_html = final_html.replace('{{SKILLS}}', ai_data['skills_html'])
            final_html = final_html.replace('{{EXPERIENCE}}', job_header + ai_data['experience_html'])
            final_html = final_html.replace('{{PROJECTS}}', ai_data['projects_html'])
            final_html = final_html.replace('{{EDUCATION_FOCUS}}', ai_data['education_focus'])
            
            # 3. Cetak PDF
            safe_company = "".join([c for c in job['company_name'] if c.isalnum() or c==' ']).strip().replace(' ', '_')
            pdf_filename = f"Tailored_CVs/CV_Roy_{safe_company}.pdf"
            
            generate_pdf_with_playwright(final_html, pdf_filename)
            
            processed_count += 1
            print(f"✅ Berhasil! PDF tersimpan: {pdf_filename}")
            
            # Jeda 30 detik untuk menjaga kuota API Free Tier
            print("⏳ Menunggu 30 detik sebelum lowongan berikutnya...")
            time.sleep(30)

        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("⚠️ Kuota API habis/Limit tercapai. Menunggu 60 detik sebelum mencoba kembali...")
                time.sleep(60)
                continue # Retry lowongan yang sama
            else:
                print(f"❌ Terjadi kesalahan: {e}")
                break

if __name__ == "__main__":
    process_all_jobs()