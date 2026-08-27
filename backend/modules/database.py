import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'edulink.db')

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

    conn.commit()
    conn.close()