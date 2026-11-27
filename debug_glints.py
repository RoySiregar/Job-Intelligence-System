"""
Debug helper: jalankan dengan  run.bat debug_glints.py
Membuka 1 halaman Glints (headless=False, sama seperti scraper) lalu mencetak
struktur anchor + sampel judul/perusahaan supaya ketahuan kenapa 0 tersimpan.
"""
import json
import time
from playwright.sync_api import sync_playwright

URL = ("https://glints.com/id/en/opportunities/jobs/explore?country=ID"
       "&locationId=654dbd43-0da6-44a1-8fa6-3f2879b8fbdf"
       "&locationName=Batam%2C+Kepulauan+Riau&lowestLocationLevel=3&page=1")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="id-ID",
    )
    page = context.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(1)

    total = page.evaluate("document.querySelectorAll('a[href*=\"/opportunities/jobs/\"]').length")
    uniq = page.evaluate("new Set([...document.querySelectorAll('a[href*=\"/opportunities/jobs/\"]')].map(a=>a.getAttribute('href'))).size")
    samples = page.evaluate("""() => {
        const as = [...document.querySelectorAll('a[href*="/opportunities/jobs/"]')];
        const out = [];
        for (const a of as) {
            const href = a.getAttribute('href') || '';
            const clean = href.split('?')[0].split('#')[0].replace(/\\/+$/, '');
            const jobId = clean.split('/').pop();
            if (!jobId || jobId.length < 20 || jobId === 'explore') continue;
            const anchorText = (a.innerText || '').trim();
            let t = '', n = a;
            for (let i = 0; i < 6 && n; i++) {
                const x = (n.innerText || '').trim();
                if (x.split('\\n').filter(s => s.trim()).length >= 2 && x.length < 500) { t = x; break; }
                n = n.parentElement;
            }
            out.push({ jobId, anchorText: anchorText.replace(/\\n/g, ' | ').slice(0, 80), cardText: (t || anchorText).replace(/\\n/g, ' | ').slice(0, 160) });
            if (out.length >= 12) break;
        }
        return out;
    }""")

    print("TOTAL_ANCHORS", total, "UNIQUE_HREF", uniq)
    print(json.dumps(samples, ensure_ascii=False, indent=2))
    browser.close()
