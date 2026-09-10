import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'edulink.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            nama TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pelanggaran (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nisn TEXT NOT NULL,
            nama_siswa TEXT NOT NULL,
            kelas TEXT NOT NULL,
            jenis_pelanggaran TEXT NOT NULL,
            poin INTEGER NOT NULL,
            tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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

    # --- TABEL BARU: MASTER PELANGGARAN ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_pelanggaran (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pelanggaran TEXT UNIQUE NOT NULL,
            poin INTEGER NOT NULL
        )
    ''')

    # Seed data awal untuk master_pelanggaran jika masih kosong
    cursor.execute("SELECT COUNT(*) FROM master_pelanggaran")
    if cursor.fetchone()[0] == 0:
        default_data = [
            ('Terlambat Masuk Sekolah (>15 Menit)', 10),
            ('Tidak Mengikuti Upacara Bendera', 25),
            ('Meninggalkan Jam Pelajaran (Bolos)', 50),
            ('Rokok / VAPE di Lingkungan Sekolah', 75)
        ]
        cursor.executemany("INSERT INTO master_pelanggaran (nama_pelanggaran, poin) VALUES (?, ?)", default_data)
    
    # Reset dan pastikan akun admin123 selalu tersedia
    cursor.execute("DELETE FROM users WHERE username = 'admin123'")
    hashed_pwd = generate_password_hash('rahasia2026', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
        ('admin123', hashed_pwd, 'admin', 'Administrator Utama')
    )

    conn.commit()
    conn.close()