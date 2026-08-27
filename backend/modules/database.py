import sqlite3
import os
from werkzeug.security import generate_password_hash

# Memastikan jalur database SQLite SELALU konsisten di folder backend/edulink.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'edulink.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabel Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Tabel Pelanggaran / Poin
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
    
    # AUTO-SEED AKUN ADMIN: Jika database kosong/belum ada admin, buat otomatis
    admin_exists = cursor.execute("SELECT id FROM users WHERE username = 'admin123'").fetchone()
    if not admin_exists:
        hashed_password = generate_password_hash('rahasia2026')
        cursor.execute(
            "INSERT INTO users (nama, username, password, role) VALUES (?, ?, ?, ?)",
            ('Administrator Utama', 'admin123', hashed_password, 'admin')
        )
        print("Akun Admin Default Berhasil Dibuat!")

    conn.commit()
    conn.close()