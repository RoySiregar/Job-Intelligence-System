import os
from playwright.sync_api import sync_playwright

def create_pdf_from_manual_text():
    # 1. Pastikan template ada
    if not os.path.exists('template.html'):
        print("❌ Error: File template.html tidak ditemukan!")
        return

# 2. Data yang akan dimasukkan ke Template (Fokus: Software & Automation Systems Developer - PT TDK Electronics Indonesia)
    data_cv = {
        "NAME": "ROY ANTONI SIREGAR",
        "CONTACT_INFO": "Batam, Indonesia | +62 821 5436 7080 | <a href='mailto:royxflow09@gmail.com' style='color: #0000EE; text-decoration: none;'>royxflow09@gmail.com</a><br>LinkedIn: <a href='https://linkedin.com/in/roysiregar' style='color: #0000EE; text-decoration: none;'>linkedin.com/in/roysiregar</a> | Portfolio: <a href='https://portofolio-roy-nu.vercel.app' style='color: #0000EE; text-decoration: none;'>portofolio-roy-nu.vercel.app</a> | GitHub: <a href='https://github.com/RoySiregar' style='color: #0000EE; text-decoration: none;'>github.com/RoySiregar</a>",
        
        "SUMMARY": "Detail-oriented Software & Automation Systems Developer (Bachelor of Computer Science) permanently domiciled in Batam, with hands-on experience building and maintaining software systems and data pipelines in a high-volume electronics manufacturing environment. Strong foundation in C# (.NET), Python, REST API integration, SQL Server / relational databases, and Git, with practical exposure to manufacturing execution/monitoring workflows, equipment data acquisition, and root cause troubleshooting. Eager to bridge PC software engineering and industrial automation systems at PT TDK Electronics Indonesia, backed by clear English communication, structured documentation habits, and readiness to learn additional automation platforms and industrial protocols.",
        
        "EXPERIENCE": """
        <div class="work-title-row">
            <span>PT PEGAUNIHAN TECHNOLOGY INDONESIA (PEGATRON) | Batam, Indonesia</span>
            <span>February 2025 – Present</span>
        </div>
        <i>Software Engineer / Systems Developer | BG6 – Manufacturing & Operation Management Center (Visual & Program Development Section)</i>
        <ul>
            <li><strong>PC & Backend Application Development:</strong> Designed, developed, and maintained backend services, APIs, and internal web applications using C# (.NET) and Python to support production reporting, equipment monitoring, and shop-floor workflows.</li>
            <li><strong>Database Architecture & SQL:</strong> Designed and maintained relational database tables and queries across MS SQL Server, MySQL, and PostgreSQL (using DBeaver and MySQL Workbench), supporting structured data storage, integrity, and operational reporting.</li>
            <li><strong>System & Telemetry Integration:</strong> Built data-processing and API integration logic to collect and synchronize equipment telemetry and inspection/defect records across manufacturing systems and dashboards.</li>
            <li><strong>Troubleshooting, Maintenance & Documentation:</strong> Debugged application and system issues, performed root cause analysis (RCA) on equipment/process anomalies, maintained technical documentation, and collaborated with engineering teams and supervisors in English and Bahasa Indonesia.</li>
        </ul>
        """,
        
        "PROJECTS": """
        <ul>
            <li><strong>Real-Time Telemetry & OEE Analytics System:</strong>
                <ul style="margin-top: 4px; margin-bottom: 8px;">
                    <li><strong>Role:</strong> Backend & Integration Engineer.</li>
                    <li><strong>Impact:</strong> Engineered data-ingestion and processing logic for continuous machine and sensor streams to support real-time Overall Equipment Effectiveness (OEE) monitoring on the manufacturing floor.</li>
                </ul>
            </li>
            <li><strong>Automated Failure Analysis Engine (RCA) & Production Tracking (ProductionReportAPI):</strong>
                <ul style="margin-top: 4px; margin-bottom: 0px;">
                    <li><strong>Role:</strong> Backend & Database Developer.</li>
                    <li><strong>Impact:</strong> Built automated anomaly-detection workflows, inspection data endpoints, and structured database models/DTOs to streamline defect analysis and operational status tracking.</li>
                </ul>
            </li>
        </ul>
        """,
        
        "SKILLS": """
        <ul>
            <li><strong>PC Software & Programming:</strong> C# (.NET / ASP.NET Core), Python, JavaScript / TypeScript, Asynchronous & Data-Processing Logic, REST API Integration, Git / GitHub / Gitea.</li>
            <li><strong>Databases & Data Modeling:</strong> MS SQL Server, MySQL, PostgreSQL, Relational Schema Design & Normalization (3NF), Querying & Diagnostics, DBeaver, MySQL Workbench.</li>
            <li><strong>Industrial & System Integration:</strong> Manufacturing / MES & OEE Workflows, Telemetry & Equipment Data Pipelines, Socket / Network Communication Concepts, Fault Detection & Root Cause Analysis (RCA).</li>
            <li><strong>Core Competencies:</strong> System Troubleshooting & Debugging, Technical Documentation, Cross-Functional Collaboration, Structured Reporting, Clear English Communication.</li>
        </ul>
        """,
        
        "EDUCATION_FOCUS": "Software Engineering, Computer Architecture, Networking Fundamentals, and Database Systems<br><strong>Certifications:</strong> Intermediate Data Science (FGA Komdigi, 2025), IT Support (FGA Kominfo, 2024), Belajar Dasar-Dasar DevOps (Dicoding, 2023)",
        "LANGUAGES": "English (Intermediate / Professional Technical Communication), Bahasa Indonesia (Native)",
        "AVAILABILITY": "Available within a 1-month notice period",
        "LOCATION_DETAILS": "Permanently domiciled in Batam; open to business travel/site deployment as required"
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