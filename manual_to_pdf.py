import os
from playwright.sync_api import sync_playwright

def create_pdf_from_manual_text():
    # 1. Pastikan template ada
    if not os.path.exists('template.html'):
        print("❌ Error: File template.html tidak ditemukan!")
        return

    # 2. Data yang akan dimasukkan ke Template
    # Saya sudah merapikan teks manualmu ke dalam format HTML agar pas di template
    data_cv = {
        "NAME": "ROY ANTONI SIREGAR",
        "CONTACT_INFO": "Batam, Indonesia | +62 821 5436 7080 | <a href='mailto:roysiregar09@gmail.com' style='color: #0000EE; text-decoration: none;'>roysiregar09@gmail.com</a><br><a href='https://id.linkedin.com/in/roysiregar' style='color: #0000EE; text-decoration: none;'>linkedin.com/in/roysiregar</a> | <a href='https://github.com/RoySiregar' style='color: #0000EE; text-decoration: none;'>github.com/RoySiregar</a> | <a href='https://portofolio-roy-nu.vercel.app' style='color: #0000EE; text-decoration: none;'>portofolio-roy-nu.vercel.app</a>",
        
        "SUMMARY": "Computer Science Graduate (GPA 3.38) with 2 years of professional experience in Web Application Development. Highly proficient in analyzing system requirements, building RESTful APIs, and developing responsive web interfaces using modern frameworks (Next.js, React.js, Vue.js). A target-oriented professional with a strong foundation in backend development (Golang, PHP, .NET) and MySQL database optimization.",
        
        "EXPERIENCE": """
        <div class="work-title-row">
            <span>PT PEGAUNIHAN TECHNOLOGY INDONESIA (PEGATRON)</span>
            <span>Februari 2024 – Present</span>
        </div>
        <i>Software Engineer (Web Application Developer) | Div: BG6 - Manufacturing Center</i>
        <ul>
            <li><strong>System Analysis & Backend:</strong> Analyzed complex operational requirements and built robust RESTful APIs to support high-traffic production dashboards.</li>
            <li><strong>Frontend Development:</strong> Developed interactive and scalable web applications utilizing Next.js, React concepts, and Vue.js with responsive UI designs (Tailwind CSS, Bootstrap).</li>
            <li><strong>Database & Optimization:</strong> Engineered relational database schemas (MySQL) and implemented composite indexing strategies to drastically optimize real-time queries.</li>
            <li><strong>Debugging & Optimization:</strong> Conducted rigorous testing and continuous optimization of critical web applications to ensure high stability and minimal downtime.</li>
            <li><strong>Team Collaboration:</strong> Collaborated with cross-functional teams using Gitea, translating non-technical requirements into efficient technical solutions.</li>
        </ul>
        """,
        
        "PROJECTS": """
        <ul>
            <li><strong>Automated Analytics & Reporting Platform:</strong> Built a real-time monitoring web application with complex data aggregation logic to process massive datasets for automated reporting.</li>
            <li><strong>Multi-Tier Failure Analysis System:</strong> Created an integrated breakdown web portal connecting high-level reports to granular historical data via API integration.</li>
            <li><strong>Interactive Visual Viewer:</strong> Developed a responsive frontend application handling heavy image datasets with custom APIs to support interactive image manipulation.</li>
        </ul>
        """,
        
        "SKILLS": """
        <ul>
            <li><strong>Frontend Development:</strong> Next.js, React.js, Vue.js, JavaScript, HTML, Tailwind CSS, Bootstrap.</li>
            <li><strong>Backend Development:</strong> Golang, PHP, C# (.NET Core), RESTful API Architecture.</li>
            <li><strong>Database & Tools:</strong> MySQL (Advanced Indexing, Schema Design), PostgreSQL concept, Git/Gitea, Docker.</li>
            <li><strong>Soft Skills:</strong> System Analysis, Fast Learner, Target Oriented, Strong Communication.</li>
        </ul>
        """,
        
        "EDUCATION_FOCUS": "System Design & Analysis, Database Management, Web Architecture",
        "LANGUAGES": "English (Professional Working Proficiency), Bahasa Indonesia (Native)",
        "AVAILABILITY": "Available to start within one month (1-month notice period)",
        "LOCATION_DETAILS": "Batam Resident (No relocation required)"
    }

    # 3. Baca Template dan Replace Placeholder
    with open('template.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    for key, value in data_cv.items():
        html_content = html_content.replace(f"{{{{{key}}}}}", value)

    # 4. Render ke PDF pakai Playwright
    with sync_playwright() as p:
        print("⏳ Sedang merender PDF...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.wait_for_timeout(1000) # Tunggu sebentar agar CSS rapi
        
        output_file = r"C:\Roy\Job Intelligence System\JIS & Auto CV\CV_Manual\CV_Roy_Antoni_Siregar.pdf"
        page.pdf(path=output_file, format="A4", print_background=True)
        browser.close()
        
        print(f"✅ BERHASIL! File disimpan sebagai: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    create_pdf_from_manual_text()