import os
from playwright.sync_api import sync_playwright

def create_pdf_from_manual_text():
    # 1. Pastikan template ada
    if not os.path.exists('template.html'):
        print("❌ Error: File template.html tidak ditemukan!")
        return

# 2. Data yang akan dimasukkan ke Template (Fokus: Engineer on Site & IT Specialist)
    data_cv = {
        "NAME": "ROY ANTONI SIREGAR",
        "CONTACT_INFO": "Batam, Indonesia | +62 821 5436 7080 | <a href='mailto:roysiregar09@gmail.com' style='color: #0000EE; text-decoration: none;'>roysiregar09@gmail.com</a><br><a href='https://id.linkedin.com/in/roysiregar' style='color: #0000EE; text-decoration: none;'>linkedin.com/in/roysiregar</a> | <a href='https://github.com/RoySiregar' style='color: #0000EE; text-decoration: none;'>github.com/RoySiregar</a> | <a href='https://portofolio-roy-nu.vercel.app' style='color: #0000EE; text-decoration: none;'>portofolio-roy-nu.vercel.app</a>",
        
        "SUMMARY": "Engineer on Site & IT Specialist (Bachelor of Computer Science) with extensive experience in deploying and troubleshooting high-precision monitoring and vision systems within a Tier-1 manufacturing environment (PT Pegatron). Certified in IT Support by Kominfo RI. Expert in 1st layer hardware handling, network connectivity, and cybersecurity for IoT devices. Physically fit and accustomed to on-site/on-call deployment, including equipment installation at height.",
        
        "EXPERIENCE": """
        <div class="work-title-row">
            <span>PT PEGAUNIHAN TECHNOLOGY INDONESIA (PEGATRON)</span>
            <span>Februari 2024 – Sekarang</span>
        </div>
        <i>On-Site Systems & Automation Engineer | Div: BG6 - Manufacturing Center</i>
        <ul>
            <li><strong>Vision System Troubleshooting:</strong> Responsible for on-site maintenance of AOI systems, resolving hardware and software incidents to prevent production downtime.</li>
            <li><strong>IT Device & Security Management:</strong> Managed security and data integrity of factory-floor IT devices, implementing safeguards for industrial IoT systems (MQTT/Kafka).</li>
            <li><strong>Incident Response:</strong> Acted as primary on-site responder for technical incidents, providing root cause analysis and resolution reports to management.</li>
            <li><strong>Equipment Installation:</strong> Led the physical setup and calibration of automated inspection equipment, accustomed to high mobility in dynamic shop-floor environments.</li>
            <li><strong>System Health Monitoring:</strong> Developed performance reports utilizing data analytics to identify operational risks before they impacted production.</li>
        </ul>
        """,
        
        "PROJECTS": """
        <ul>
            <li><strong>Hardware Infrastructure for Automated Phone Rigs:</strong> Engineered and assembled large-scale physical hardware rigs involving complex wiring, structural assembly, and network security protocols.</li>
            <li><strong>Real-Time Monitoring & Security Dashboard:</strong> Designed an integrated system to monitor shop-floor device health, providing an early warning system for technical failures or security anomalies.</li>
        </ul>
        """,
        
        "SKILLS": """
        <ul>
            <li><strong>Security & Monitoring:</strong> CCTV/AOI Troubleshooting, Data Security, System Integrity, Incident Management.</li>
            <li><strong>Networking & IT:</strong> LAN/WiFi Installation, 1st Layer Handling, Hardware Diagnostics, IoT Connectivity.</li>
            <li><strong>Software & Tools:</strong> C#, Python, SQL, Network Monitoring Tools.</li>
            <li><strong>Physical Readiness:</strong> On-call readiness, comfortable working at height, high physical stamina (active fitness practitioner).</li>
        </ul>
        """,
        
        "EDUCATION_FOCUS": "Sistem Keamanan, Arsitektur Jaringan, IoT",
        "LANGUAGES": "Inggris (Aktif), Bahasa Indonesia (Native)",
        "AVAILABILITY": "Ready to work immediately",
        "LOCATION_DETAILS": "Batam Resident (Ready for On-site/Field Work)"
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