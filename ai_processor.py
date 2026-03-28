import mysql.connector
import json
import os
import time
from groq import Groq
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# 1. LOAD CONFIGURATION
load_dotenv()

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'autopilot_jobs_db'
}

api_key_env = os.getenv("GROQ_API_KEY")
if not api_key_env:
    print("❌ ERROR: GROQ_API_KEY tidak ditemukan!")
    exit()

client = Groq(api_key=api_key_env)

# 2. FUNGSI PENDUKUNG
def load_my_profile():
    if not os.path.exists('profile.json'): 
        print("❌ ERROR: profile.json tidak ditemukan!")
        return None
    with open('profile.json', 'r', encoding='utf-8') as file:
        return json.load(file)

def get_batch_jobs(limit=1):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, title, company_name, job_description FROM raw_jobs WHERE status = 'DRAFT_READY' AND job_description IS NOT NULL LIMIT %s"
        cursor.execute(query, (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Error DB (Get Jobs): {e}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def save_ai_result(job_id, keywords, cover_letter):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # Mengubah keywords menjadi string jika berupa list untuk database
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
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
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content)
            page.wait_for_timeout(1000)
            page.pdf(path=output_filename, format="A4", print_background=True)
            browser.close()
    except Exception as e:
        print(f"❌ Gagal membuat PDF: {e}")

# 3. FUNGSI PROSES UTAMA
def process_all_jobs():
    print("🚀 Memulai Auto-Pilot (Groq Llama-3.1 Mode)...")
    
    my_real_profile = load_my_profile()
    if not my_real_profile: return 
    
    # Ringkas data untuk AI
    brief_data = {
        "summary": my_real_profile['summary'],
        "skills": my_real_profile['core_skills'],
        "experience": my_real_profile['work_experience'][0]['role']
    }
    profile_for_ai = json.dumps(brief_data)
    
    processed_count = 0
    if not os.path.exists("Tailored_CVs"): os.makedirs("Tailored_CVs")
    if not os.path.exists('template.html'): return
        
    with open('template.html', 'r', encoding='utf-8') as f:
        html_template = f.read()
    
    while True:
        jobs = get_batch_jobs(limit=1)
        if not jobs:
            print(f"\n🎉 SELESAI! Total CV: {processed_count}")
            break

        job = jobs[0]
        print(f"\n📦 Memproses: {job['title']} di {job['company_name']}...")

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a professional career coach. Output MUST be in JSON format only."},
                    {"role": "user", "content": f"""
                        Task: Create tailored CV content.
                        CANDIDATE: {profile_for_ai}
                        JOB: {job['job_description']}

                        Return this exact JSON:
                        {{
                            "keywords": "3-5 matching skills",
                            "cover_letter": "Professional cover letter content",
                            "summary_html": "2-3 sentence professional summary",
                            "skills_html": "Relevant skills as <li> tags",
                            "experience_html": "3-5 bullet points (<li>) focusing on .NET, IoT, and SQL",
                            "projects_html": "2 relevant projects as <li> tags",
                            "education_focus": "Bachelor of Computer Science"
                        }}
                    """}
                ],
                model="llama-3.1-8b-instant", 
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            
            res = json.loads(chat_completion.choices[0].message.content)
            
            # 1. Update DB
            save_ai_result(job['id'], res.get('keywords'), res.get('cover_letter'))
            
            # 2. Merakit HTML
            final_html = html_template
            p_info = my_real_profile.get('personal_info', {})
            exp = my_real_profile['work_experience'][0]
            
            # --- KONTAK (2 BARIS RAPI) ---
            portfolio_url = "https://portofolio-roy-nu.vercel.app/"
            line1 = f"{p_info.get('location')} | {p_info.get('phone')} | <a href='mailto:{p_info.get('email')}'>{p_info.get('email')}</a>"
            
            links = [
                f"<a href='{p_info.get('linkedin')}'>id.linkedin.com/in/roysiregar</a>",
                f"<a href='{p_info.get('github')}'>github.com/RoySiregar</a>",
                f"<a href='{portfolio_url}'>portofolio-roy-nu.vercel.app</a>"
            ]
            line2 = " | ".join(links)
            
            # --- EXPERIENCE HEADER (DENGAN DIVISI & NOTE) ---
            division = "BG6 - Manufacturing & Operation Management Center (Visual & Program Development Section)"
            note = "Note: Assigned as a full-time Software Developer managing enterprise applications, operating under an Automation Operator contract."
            
            job_header = f"""
            <div class="work-header">
                <strong>{exp['company']}</strong> | Batam, Indonesia<br>
                <strong>{exp['role']} / Industrial IoT Developer</strong> | {exp['duration']}<br>
                <small>Division: {division}</small><br>
                <small><i>{note}</i></small>
            </div>
            """
            
            # --- REPLACE PLACEHOLDERS ---
            final_html = final_html.replace('{{NAME}}', p_info.get('name', 'Roy Antoni Siregar'))
            final_html = final_html.replace('{{CONTACT_INFO}}', f"{line1}<br>{line2}")
            final_html = final_html.replace('{{SUMMARY}}', res.get('summary_html', ''))
            final_html = final_html.replace('{{SKILLS}}', f"<ul>{res.get('skills_html', '')}</ul>")
            final_html = final_html.replace('{{EXPERIENCE}}', job_header + f"<ul>{res.get('experience_html', '')}</ul>")
            final_html = final_html.replace('{{PROJECTS}}', f"<ul>{res.get('projects_html', '')}</ul>")
            final_html = final_html.replace('{{EDUCATION_FOCUS}}', res.get('education_focus', 'Informatics Engineering'))
            
            # Tambahan Informasi Statis
            final_html = final_html.replace('{{LANGUAGES}}', "English (Professional working proficiency), Bahasa Indonesia (Native)")
            final_html = final_html.replace('{{AVAILABILITY}}', "Ready to start immediately")
            final_html = final_html.replace('{{LOCATION_DETAILS}}', "Batam Resident (No relocation required)")
            
            # 3. Cetak PDF
            safe_company = "".join([c for c in job['company_name'] if c.isalnum() or c==' ']).strip().replace(' ', '_')
            pdf_filename = f"Tailored_CVs/CV_Roy_{safe_company}.pdf"
            generate_pdf_with_playwright(final_html, pdf_filename)
            
            processed_count += 1
            print(f"✅ Berhasil! PDF tersimpan: {pdf_filename}")
            time.sleep(3)

        except Exception as e:
            print(f"❌ Error Groq ID {job['id']}: {e}")
            time.sleep(10)
            continue

if __name__ == "__main__":
    process_all_jobs()