import mysql.connector
from datetime import datetime

# ==============================
# CONFIG DATABASE
# ==============================
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '', 
    'database': 'autopilot_jobs_db'
}

def mark_as_applied():
    print("--- Lowongan Kerja Terapan (Manual Marker) ---")
    job_id = input("Masukkan Job ID (contoh: b/91007202): ").strip()

    if not job_id:
        print("❌ Error: Job ID tidak boleh kosong!")
        return

    try:
        # Koneksi ke database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Cek apakah job_id tersebut ada di database
        cursor.execute("SELECT title, company_name, status FROM raw_jobs WHERE job_id = %s", (job_id,))
        job = cursor.fetchone()

        if job:
            title, company, current_status = job
            print(f"🔍 Menemukan: {title} di {company}")
            print(f"🕒 Status saat ini: {current_status}")
            
            confirm = input(f"Tandai sebagai APPLIED sekarang? (y/n): ").lower()
            
            if confirm == 'y':
                # Update status dan waktu lamar
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                sql = """
                    UPDATE raw_jobs 
                    SET status = 'APPLIED', 
                        applied_at = %s 
                    WHERE job_id = %s
                """
                cursor.execute(sql, (now, job_id))
                conn.commit()
                
                print(f"✅ BERHASIL: {title} telah ditandai APPLIED pada {now}")
            else:
                print("⚠️ Pembatalan: Status tidak diubah.")
        else:
            print(f"❌ Error: Job ID '{job_id}' tidak ditemukan di database.")

    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    mark_as_applied()