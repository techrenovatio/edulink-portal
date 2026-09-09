import sqlite3
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'edulink.db')

nama_depan_pria = ["Ahmad", "Muhammad", "Rian", "Budi", "Dimas", "Fajar", "Rizky", "Diki", "Faisal", "Eko", "Gilang", "Hafiz", "Irfan", "Kevin", "Lutfi"]
nama_depan_wanita = ["Siti", "Anisa", "Citra", "Dini", "Elsa", "Fitri", "Gita", "Indah", "Lani", "Maya", "Nadia", "Putri", "Rina", "Santi", "Tia"]
nama_belakang = ["Pratama", "Saputra", "Hidayat", "Santoso", "Wijaya", "Kusuma", "Nugroho", "Utomo", "Ramadhan", "Permana", "Lestari", "Wulandari", "Suryani"]

pelanggaran_master = [
    ("Terlambat Masuk Sekolah (>15 Menit)", 10),
    ("Tidak Mengikuti Upacara Bendera", 25),
    ("Meninggalkan Jam Pelajaran (Bolos)", 50),
    ("Rokok / VAPE di Lingkungan Sekolah", 75)
]

def generate_siswa_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Buat Tabel Siswa Jika Belum Ada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS siswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nisn TEXT UNIQUE NOT NULL,
            nama_siswa TEXT NOT NULL,
            jenis_kelamin TEXT NOT NULL,
            kelas TEXT NOT NULL,
            nama_wali TEXT NOT NULL,
            no_hp_wali TEXT NOT NULL
        )
    ''')

    # Bersihkan data lama agar disinkronkan bersih
    cursor.execute("DELETE FROM siswa")
    cursor.execute("DELETE FROM pelanggaran")

    print("Mengisi data siswa ke database...")

    # Konfigurasi Angkatan & Kelas
    alokasi_kelas = {
        "10": [("X IPA 1", 30), ("X IPS 1", 30)],                  # Total 60 Siswa
        "11": [("XI IPA 1", 30), ("XI IPA 2", 30), ("XI IPS 1", 30)], # Total 90 Siswa
        "12": [("XII IPA 1", 30), ("XII IPA 2", 30), ("XII IPS 1", 30)]# Total 90 Siswa
    }

    nisn_counter = 1000

    for angkatan, daftar_kelas in alokasi_kelas.items():
        for kelas, jumlah_siswa in daftar_kelas:
            for i in range(jumlah_siswa):
                nisn_counter += 1
                nisn = f"005123{nisn_counter}"
                
                # Selang-seling Pria dan Wanita
                jk = "L" if i % 2 == 0 else "P"
                if jk == "L":
                    nama = f"{random.choice(nama_depan_pria)} {random.choice(nama_belakang)}"
                    wali = f"Bpk. {random.choice(nama_belakang)}"
                else:
                    nama = f"{random.choice(nama_wanita_depan if 'nama_wanita_depan' in locals() else nama_depan_wanita)} {random.choice(nama_belakang)}"
                    wali = f"Ibu {random.choice(nama_belakang)}"

                no_hp = f"0812{random.randint(10000000, 99999999)}"

                cursor.execute(
                    "INSERT INTO siswa (nisn, nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali) VALUES (?, ?, ?, ?, ?, ?)",
                    (nisn, nama, jk, kelas, wali, no_hp)
                )

                # Tambahkan beberapa data pelanggaran acak (sekitar 10% siswa)
                if random.random() < 0.12:
                    pel, poin = random.choice(pelanggaran_master)
                    cursor.execute(
                        "INSERT INTO pelanggaran (nisn, nama_siswa, kelas, jenis_pelanggaran, poin) VALUES (?, ?, ?, ?, ?)",
                        (nisn, nama, kelas, pel, poin)
                    )

    conn.commit()
    
    total_siswa = cursor.execute("SELECT COUNT(*) FROM siswa").fetchone()[0]
    total_poin = cursor.execute("SELECT COUNT(*) FROM pelanggaran").fetchone()[0]
    
    conn.close()
    print(f"BERHASIL: Disinkronkan {total_siswa} data siswa (Kelas 10: 60, Kelas 11: 90, Kelas 12: 90) & {total_poin} riwayat pelanggaran.")

if __name__ == '__main__':
    generate_siswa_data()