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
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [col['name'] for col in cursor.fetchall()]
    
    if 'nip' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN nip TEXT DEFAULT '-'")
    if 'bidang_pelajaran' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN bidang_pelajaran TEXT DEFAULT '-'")
    if 'status_walikelas' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN status_walikelas TEXT DEFAULT 'Bukan'")
    if 'mengajar_kelas' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN mengajar_kelas TEXT DEFAULT 'Semua'")
    if 'mengajar_mapel' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN mengajar_mapel TEXT DEFAULT 'Semua'")
    if 'can_print' not in columns: cursor.execute("ALTER TABLE users ADD COLUMN can_print INTEGER DEFAULT 0")
        
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

    # FITUR BARU: Tabel Pencatatan Prestasi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestasi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nisn TEXT NOT NULL,
            nama_siswa TEXT NOT NULL,
            kelas TEXT NOT NULL,
            jenis_prestasi TEXT NOT NULL,
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

    cursor.execute("PRAGMA table_info(siswa)")
    siswa_cols = [col['name'] for col in cursor.fetchall()]
    if 'status_siswa' not in siswa_cols:
        cursor.execute("ALTER TABLE siswa ADD COLUMN status_siswa TEXT DEFAULT 'Aktif'")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_pelanggaran (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pelanggaran TEXT UNIQUE NOT NULL,
            poin INTEGER NOT NULL
        )
    ''')

    # FITUR BARU: Tabel Master Opsi Prestasi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_prestasi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_prestasi TEXT UNIQUE NOT NULL,
            poin INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presensi_harian (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal DATE NOT NULL,
            nisn TEXT NOT NULL,
            mata_pelajaran TEXT NOT NULL,
            pertemuan INTEGER NOT NULL,
            status TEXT NOT NULL,
            guru_id INTEGER,
            UNIQUE(tanggal, nisn, mata_pelajaran)
        )
    ''')
    
    cursor.execute("PRAGMA table_info(presensi_harian)")
    presensi_cols = [col['name'] for col in cursor.fetchall()]
    if 'deskripsi' not in presensi_cols:
        cursor.execute("ALTER TABLE presensi_harian ADD COLUMN deskripsi TEXT DEFAULT ''")

    # Insert Default Master Pelanggaran
    cursor.execute("SELECT COUNT(*) FROM master_pelanggaran")
    if cursor.fetchone()[0] == 0:
        default_data = [
            ('Terlambat Masuk Sekolah (>15 Menit)', 10),
            ('Tidak Mengikuti Upacara Bendera', 25),
            ('Meninggalkan Jam Pelajaran (Bolos)', 50),
            ('Rokok / VAPE di Lingkungan Sekolah', 75)
        ]
        cursor.executemany("INSERT INTO master_pelanggaran (nama_pelanggaran, poin) VALUES (?, ?)", default_data)
        
    # Insert Default Master Prestasi
    cursor.execute("SELECT COUNT(*) FROM master_prestasi")
    if cursor.fetchone()[0] == 0:
        default_prestasi = [
            ('Mewakili Sekolah di Olimpiade', 30),
            ('Juara 1 Lomba Tingkat Kota/Kabupaten', 50),
            ('Juara 1 Lomba Tingkat Provinsi', 75),
            ('Juara 1 Lomba Tingkat Nasional', 100)
        ]
        cursor.executemany("INSERT INTO master_prestasi (nama_prestasi, poin) VALUES (?, ?)", default_prestasi)
    
    cursor.execute("DELETE FROM users WHERE username = 'admin123'")
    hashed_pwd = generate_password_hash('rahasia2026', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (username, password, role, nama, nip, bidang_pelajaran, status_walikelas, mengajar_kelas, mengajar_mapel, can_print) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('admin123', hashed_pwd, 'superadmin', 'Administrator Utama', '-', '-', 'Bukan', 'Semua', 'Semua', 1)
    )

    conn.commit()
    conn.close()