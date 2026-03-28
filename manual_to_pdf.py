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
        
        "SUMMARY": "Computer Science Graduate (GPA 3.38) driving Digital Transformation and Industry 4.0 initiatives within a Tier-1 Electronics Manufacturing environment (PT Pegatron). Proven ability to translate complex factory business processes into full-stack digital solutions (C# .NET, Vue.js, SQL) that optimize resource utilization and eliminate waste in alignment with LEAN manufacturing principles. Expert in architecting real-time data pipelines (Kafka, MQTT) to empower management with data-driven decision-making.",
        
        "EXPERIENCE": """
        <div class="work-title-row">
            <span>PT PEGAUNIHAN TECHNOLOGY INDONESIA (PEGATRON)</span>
            <span>Februari 2024 – Present</span>
        </div>
        <i>Digital Transformation & Automation Engineer | Div: BG6 - Manufacturing & Operation Management Center</i>
        <ul>
            <li><strong>Factory Digitization & LEAN:</strong> Translated manual shop-floor processes into automated digital workflows, directly reducing cycle times and eliminating waste in data collection.</li>
            <li><strong>Critical Metrics Visualization:</strong> Designed interactive dashboard modules (Vue.js, ECharts) to monitor real-time performance (OEE, TEEP, Yield Rate) for management and line leaders.</li>
            <li><strong>Data Architecture:</strong> Architected MySQL databases and managed data synchronization via Kafka/MQTT to support predictive failure analysis and operational scenario planning.</li>
            <li><strong>I4.0 Industrialization:</strong> Collaborated with cross-functional teams to deploy advanced inspection technologies, including an AI-assisted AOI visualizer for defect mapping.</li>
            <li><strong>System Reliability:</strong> Developed backend services (C# .NET) for RobotService and HistoricalDataService, ensuring system uptime and accurate automated error rate calculations.</li>
        </ul>
        """,
        
        "PROJECTS": """
        <ul>
            <li><strong>Future Factory OEE & Productivity Dashboard:</strong> Full-stack real-time monitoring system providing clear visualization of bottlenecks across multiple production floors.</li>
            <li><strong>Multi-Tier Failure Analysis Engine:</strong> Integrated breakdown system connecting yield reports to granular machine failure data via MySQL/FTP synchronization.</li>
            <li><strong>High-Precision AOI Visual Analysis:</strong> Sophisticated inspection viewer with reactive coordinate-to-image scaling, optimizing resource utilization during QA processes.</li>
        </ul>
        """,
        
        "SKILLS": """
        <ul>
            <li><strong>I4.0 & Manufacturing:</strong> Digital Transformation Roadmap, LEAN Manufacturing, Smart Industry Readiness Index (SIRI), Cycle Time Reduction.</li>
            <li><strong>Visualization & Analytics:</strong> ECharts, Real-time Dashboards, OEE / TEEP / Yield Metrics, "What-If" Data Modeling.</li>
            <li><strong>Software Engineering:</strong> C# (.NET 6/8), Vue.js, Python, JavaScript/TypeScript, SQL (Advanced Indexing).</li>
            <li><strong>Integration & IIoT:</strong> Kafka, MQTT, FTP, RESTful APIs, System Architecture.</li>
        </ul>
        """,
        
        "EDUCATION_FOCUS": "System Design & Analysis, Database Management, IoT Architecture",
        "LANGUAGES": "English (Professional Working Proficiency), Bahasa Indonesia (Native)",
        "AVAILABILITY": "Ready to start immediately (Onsite Batam)",
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
        
        output_file = "CV_Roy_Antoni_Siregar.pdf"
        page.pdf(path=output_file, format="A4", print_background=True)
        browser.close()
        
        print(f"✅ BERHASIL! File disimpan sebagai: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    create_pdf_from_manual_text()