import sqlite3
import os
from werkzeug.security import generate_password_hash

def get_db_connection():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    db_path = os.path.join(backend_dir, 'edulink.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            nama TEXT NOT NULL
        )
    ''')
    
    admin = conn.execute("SELECT * FROM users WHERE username = 'admin123'").fetchone()
    if not admin:
        # Gunakan pbkdf2:sha256 (Standar paling stabil & aman)
        hashed_password = generate_password_hash('rahasia2026', method='pbkdf2:sha256')
        
        conn.execute(
            "INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
            ('admin123', hashed_password, 'admin', 'Administrator Utama')
        )
        conn.commit()
        print("✅ Database diinisialisasi & Akun Admin diamankan!")
        
    conn.close()