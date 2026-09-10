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
    
    # Hapus user admin123 lama jika bermasalah, lalu buat ulang dengan hash presisi
    cursor.execute("DELETE FROM users WHERE username = 'admin123'")
    hashed_pwd = generate_password_hash('rahasia2026', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
        ('admin123', hashed_pwd, 'admin', 'Administrator Utama')
    )

    conn.commit()
    conn.close()