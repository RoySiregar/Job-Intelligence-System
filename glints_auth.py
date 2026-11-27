"""
glints_auth.py — helper sesi login Glints (dipakai glints_scraper & glints_detail_scraper).

- Pertama kali (belum ada glints_auth.json): buka Glints, tunggu user login manual
  (hitungan mundur, tekan ENTER untuk lanjut lebih cepat), lalu simpan sesi.
- Run berikutnya: pakai sesi tersimpan (tidak perlu login lagi).
- Login ulang: jalankan dengan --relogin, atau hapus glints_auth.json.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AUTH_STATE_FILE = "glints_auth.json"
LOGIN_WAIT_SECONDS = 120
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def wait_for_login(seconds=LOGIN_WAIT_SECONDS):
    print("🔐 Silakan LOGIN di browser yang baru terbuka.")
    print(f"   Anda punya {seconds} detik. Tekan ENTER di terminal ini untuk lanjut lebih cepat.")
    try:
        import msvcrt  # Windows only
        deadline = time.time() + seconds
        last_shown = -10
        while time.time() < deadline:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b"\r", b"\n", b" "):
                    print("   ⏩ Lanjut sekarang.")
                    return
            rem = int(deadline - time.time())
            if rem != last_shown and rem % 10 == 0:
                print(f"   ... {rem} detik tersisa")
                last_shown = rem
            time.sleep(0.2)
        print("   ⏱️ Waktu tunggu habis, melanjutkan.")
    except Exception:
        try:
            input("Press ENTER when logged in...")
        except EOFError:
            time.sleep(seconds)


def new_context(browser, force_login=False):
    """Buat context Playwright dengan sesi login Glints (load atau buat baru)."""
    kwargs = dict(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="id-ID",
    )

    if os.path.exists(AUTH_STATE_FILE) and not force_login:
        print(f"🔐 Memakai sesi login tersimpan: {AUTH_STATE_FILE}")
        context = browser.new_context(storage_state=AUTH_STATE_FILE, **kwargs)
    else:
        print("🔐 Belum ada sesi login — browser dibuka untuk login manual...")
        context = browser.new_context(**kwargs)
        login_page = context.new_page()
        try:
            login_page.goto("https://glints.com/id/en/", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"⚠️ Tidak bisa membuka halaman Glints: {e}")
        try:
            login_page.bring_to_front()
        except Exception:
            pass
        wait_for_login()
        try:
            context.storage_state(path=AUTH_STATE_FILE)
            print(f"✅ Sesi login disimpan ke {AUTH_STATE_FILE} (run berikutnya tidak perlu login).")
        except Exception as e:
            print(f"⚠️ Gagal menyimpan sesi: {e}")
        try:
            login_page.close()
        except Exception:
            pass

    context.set_extra_http_headers({
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Referer": "https://glints.com/",
        "DNT": "1",
    })
    return context
