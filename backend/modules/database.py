import sqlite3
import os

def get_db_connection():
    # Menentukan lokasi database di dalam folder backend
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    db_path = os.path.join(backend_dir, 'edulink.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Agar hasil query bisa dipanggil seperti dictionary
    return conn

def init_db():
    conn = get_db_connection()
    
    # Membuat tabel pengguna jika belum ada
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            nama TEXT NOT NULL
        )
    ''')
    
    # Menyuntikkan akun Admin Dummy jika tabel masih kosong
    admin = conn.execute("SELECT * FROM users WHERE username = 'admin123'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
            ('admin123', 'rahasia2026', 'admin', 'Administrator Utama')
        )
        conn.commit()
        print("✅ Database diinisialisasi & Akun Admin dibuat!")
        
    conn.close()