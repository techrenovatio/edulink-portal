import os
from datetime import timedelta
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash

from modules.database import init_db, get_db_connection

current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_dir)
template_dir = os.path.join(base_dir, 'frontend', 'templates')
static_dir = os.path.join(base_dir, 'frontend', 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

app.secret_key = 'syekhyusuf_tangerang_secret_key_2026_change_this'
app.config['SESSION_COOKIE_NAME'] = 'syekhyusuf_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# --- SUPER AUTO-PATCH DATABASE ---
def force_patch_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("CREATE TABLE IF NOT EXISTS prestasi (id INTEGER PRIMARY KEY AUTOINCREMENT, nisn TEXT, nama_siswa TEXT, kelas TEXT, jenis_prestasi TEXT, poin INTEGER, tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS master_prestasi (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_prestasi TEXT UNIQUE, poin INTEGER)")
        
        # FITUR BARU: Tabel Dinamis Kelas dan Mata Pelajaran
        cursor.execute("CREATE TABLE IF NOT EXISTS master_kelas (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_kelas TEXT UNIQUE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS master_mapel (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_mapel TEXT UNIQUE)")
        
        def add_col(table, col_name, col_type_default):
            cursor.execute(f"PRAGMA table_info({table})")
            if col_name not in [c['name'] for c in cursor.fetchall()]:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type_default}")

        add_col('siswa', 'status_siswa', "TEXT DEFAULT 'Aktif'")
        add_col('pelanggaran', 'kelas', "TEXT DEFAULT '-'")
        add_col('presensi_harian', 'deskripsi', "TEXT DEFAULT ''")
        add_col('presensi_harian', 'jurnal_kelas', "TEXT DEFAULT ''")
        add_col('users', 'nip', "TEXT DEFAULT '-'")
        add_col('users', 'bidang_pelajaran', "TEXT DEFAULT '-'")
        add_col('users', 'status_walikelas', "TEXT DEFAULT 'Bukan'")
        add_col('users', 'mengajar_kelas', "TEXT DEFAULT 'Semua'")
        add_col('users', 'mengajar_mapel', "TEXT DEFAULT 'Semua'")
        add_col('users', 'can_print', "INTEGER DEFAULT 0")

        cursor.execute("SELECT COUNT(*) FROM master_prestasi")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT OR IGNORE INTO master_prestasi (nama_prestasi, poin) VALUES (?, ?)", [
                ('Mewakili Sekolah di Olimpiade', 30),
                ('Juara 1 Lomba Tingkat Kota/Kabupaten', 50),
                ('Juara 1 Lomba Tingkat Provinsi', 75),
                ('Juara 1 Lomba Tingkat Nasional', 100)
            ])
            
        cursor.execute("SELECT COUNT(*) FROM master_kelas")
        if cursor.fetchone()[0] == 0:
            default_kelas = [('X IPA 1',), ('X IPS 1',), ('XI IPA 1',), ('XI IPA 2',), ('XI IPS 1',), ('XII IPA 1',), ('XII IPA 2',), ('XII IPS 1',)]
            cursor.executemany("INSERT OR IGNORE INTO master_kelas (nama_kelas) VALUES (?)", default_kelas)

        cursor.execute("SELECT COUNT(*) FROM master_mapel")
        if cursor.fetchone()[0] == 0:
            default_mapel = [('Matematika',), ('Bahasa Indonesia',), ('Bahasa Inggris',), ('Pendidikan Kewarganegaraan',), ('Teknologi Informasi dan Komputer',), ('Literasi Digital',), ('Bahasa Arab',), ('Geografi',), ('Penjaskes',), ('Fisika',), ('Biologi',), ('Budi Pekerti',), ('Sosiologi',), ('Ekonomi',)]
            cursor.executemany("INSERT OR IGNORE INTO master_mapel (nama_mapel) VALUES (?)", default_mapel)

        conn.commit()
    except Exception as e:
        print("Database Patch Error:", e)
    finally:
        conn.close()

init_db()
force_patch_database()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Variabel ini dibiarkan untuk backward compatibility di route lain jika diperlukan,
# namun untuk Users akan menggunakan data dari DB langsung.
MAPEL_MASTER = {
    'X': ['Matematika Dasar', 'Bahasa Indonesia', 'Bahasa Inggris', 'Pendidikan Kewarganegaraan', 'Teknologi Informasi dan Komputer', 'Literasi Digital', 'Bahasa Arab', 'Geografi', 'Penjaskes', 'Fisika', 'Biologi', 'Budi Pekerti', 'Sosiologi', 'Ekonomi'],
    'XI IPA': ['Matematika', 'Bahasa Indonesia', 'Bahasa Inggris', 'Pendidikan Kewarganegaraan', 'Teknologi Informasi dan Komputer', 'Literasi Digital', 'Bahasa Arab', 'Geografi', 'Penjaskes', 'Fisika', 'Biologi', 'Budi Pekerti'],
    'XI IPS': ['Matematika', 'Bahasa Indonesia', 'Bahasa Inggris', 'Pendidikan Kewarganegaraan', 'Teknologi Informasi dan Komputer', 'Literasi Digital', 'Bahasa Arab', 'Geografi', 'Penjaskes', 'Sosiologi', 'Budi Pekerti'],
    'XII IPA': ['Matematika', 'Bahasa Indonesia', 'Bahasa Inggris', 'Pendidikan Kewarganegaraan', 'Teknologi Informasi dan Komputer', 'Literasi Digital', 'Bahasa Arab', 'Geografi', 'Penjaskes', 'Fisika', 'Biologi', 'Budi Pekerti'],
    'XII IPS': ['Matematika', 'Bahasa Indonesia', 'Bahasa Inggris', 'Pendidikan Kewarganegaraan', 'Teknologi Informasi dan Komputer', 'Literasi Digital', 'Bahasa Arab', 'Geografi', 'Penjaskes', 'Sosiologi', 'Budi Pekerti']
}

def is_superadmin(): return 'user_id' in session and str(session.get('role', '')).strip().lower() == 'superadmin'
def is_admin_or_super(): return 'user_id' in session and str(session.get('role', '')).strip().lower() in ['admin', 'superadmin']

@app.route('/')
def home():
    conn = get_db_connection()
    try: total_siswa = conn.execute("SELECT COUNT(*) FROM siswa WHERE status_siswa='Aktif'").fetchone()[0]
    except: total_siswa = 0
    finally: conn.close()
    return render_template('index.html', total_siswa=total_siswa)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard_overview'))
    if request.method == 'POST':
        form_role = request.form.get('role', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            db_role = str(user['role']).strip().lower()
            if db_role == form_role or (form_role == 'admin' and db_role == 'superadmin'):
                session.permanent = True
                session['user_id'] = user['id']
                session['nama'] = user['nama']
                session['role'] = db_role
                session['mengajar_kelas'] = user['mengajar_kelas'] if 'mengajar_kelas' in user.keys() else 'Semua'
                session['mengajar_mapel'] = user['mengajar_mapel'] if 'mengajar_mapel' in user.keys() else 'Semua'
                session['can_print'] = user['can_print'] if 'can_print' in user.keys() else 0
                return redirect(url_for('dashboard_overview'))
        return render_template('login.html', error="Kredensial atau Peran tidak sesuai!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard_overview():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    
    total_siswa = conn.execute("SELECT COUNT(*) FROM siswa WHERE status_siswa='Aktif'").fetchone()[0]
    kelas_x = conn.execute("SELECT COUNT(*) FROM siswa WHERE kelas LIKE 'X %' AND status_siswa='Aktif'").fetchone()[0]
    kelas_xi = conn.execute("SELECT COUNT(*) FROM siswa WHERE kelas LIKE 'XI %' AND status_siswa='Aktif'").fetchone()[0]
    kelas_xii = conn.execute("SELECT COUNT(*) FROM siswa WHERE kelas LIKE 'XII %' AND status_siswa='Aktif'").fetchone()[0]
    total_pelanggaran = conn.execute("SELECT COUNT(*) FROM pelanggaran").fetchone()[0]
    sp_aktif = len(conn.execute("SELECT nisn, SUM(poin) as total_poin FROM pelanggaran GROUP BY nisn HAVING total_poin >= 50").fetchall())
    
    hadir_count = conn.execute("SELECT COUNT(*) FROM presensi_harian WHERE status='HADIR'").fetchone()[0]
    total_presensi = conn.execute("SELECT COUNT(*) FROM presensi_harian").fetchone()[0]
    kehadiran_rata = round((hadir_count / total_presensi * 100), 1) if total_presensi > 0 else 100.0

    recent_logs = conn.execute("""
        SELECT tanggal, nisn, nama_siswa, jenis_pelanggaran as aktivitas, poin, 'Pelanggaran' as tipe FROM pelanggaran
        UNION ALL
        SELECT tanggal, nisn, nama_siswa, jenis_prestasi as aktivitas, poin, 'Prestasi' as tipe FROM prestasi
        ORDER BY tanggal DESC LIMIT 5
    """).fetchall()

    trend_pelanggaran = [0, 0, 0, 0, 0, 0]
    bulan_counts_pelanggaran = conn.execute("SELECT strftime('%m', tanggal) as bulan, COUNT(*) as total FROM pelanggaran GROUP BY bulan").fetchall()
    for row in bulan_counts_pelanggaran:
        if row['bulan']:
            b = int(row['bulan'])
            if 7 <= b <= 12: trend_pelanggaran[b - 7] = row['total']
            
    trend_prestasi = [0, 0, 0, 0, 0, 0]
    bulan_counts_prestasi = conn.execute("SELECT strftime('%m', tanggal) as bulan, SUM(poin) as total FROM prestasi GROUP BY bulan").fetchall()
    for row in bulan_counts_prestasi:
        if row['bulan'] and row['total']:
            b = int(row['bulan'])
            if 7 <= b <= 12: trend_prestasi[b - 7] = row['total']

    conn.close()
    return render_template('dashboard/index.html', nama_user=session['nama'], total_siswa=total_siswa, kelas_x=kelas_x, kelas_xi=kelas_xi, kelas_xii=kelas_xii, total_pelanggaran=total_pelanggaran, sp_aktif=sp_aktif, recent_logs=recent_logs, kehadiran_rata=kehadiran_rata, trend_pelanggaran=trend_pelanggaran, trend_prestasi=trend_prestasi)

@app.route('/users')
def manage_users():
    if not is_admin_or_super(): return redirect(url_for('login'))
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    
    # Ambil data dinamis kelas & mapel
    m_kelas = conn.execute("SELECT * FROM master_kelas ORDER BY nama_kelas ASC").fetchall()
    m_mapel = conn.execute("SELECT * FROM master_mapel ORDER BY nama_mapel ASC").fetchall()
    
    conn.close()
    return render_template('dashboard/users.html', nama_user=session['nama'], users=users, current_role=session.get('role', '').lower(), m_kelas=m_kelas, m_mapel=m_mapel)

# --- RUTING BARU: KELOLA MASTER KELAS & MAPEL ---
@app.route('/users/add_master', methods=['POST'])
def add_master_data():
    if not is_superadmin(): return redirect(url_for('manage_users'))
    tipe = request.form.get('tipe')
    nama = request.form.get('nama', '').strip()
    
    if nama:
        conn = get_db_connection()
        try:
            if tipe == 'kelas':
                conn.execute("INSERT INTO master_kelas (nama_kelas) VALUES (?)", (nama,))
            elif tipe == 'mapel':
                conn.execute("INSERT INTO master_mapel (nama_mapel) VALUES (?)", (nama,))
            conn.commit()
            flash(f"Data {tipe} '{nama}' berhasil ditambahkan!", "success")
        except sqlite3.IntegrityError:
            flash(f"GAGAL: Data '{nama}' sudah ada di database!", "error")
        finally:
            conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete_master', methods=['POST'])
def delete_master_data():
    if not is_superadmin(): return redirect(url_for('manage_users'))
    tipe = request.form.get('tipe')
    id_master = request.form.get('id_master')
    
    if id_master:
        conn = get_db_connection()
        try:
            if tipe == 'kelas':
                conn.execute("DELETE FROM master_kelas WHERE id = ?", (id_master,))
            elif tipe == 'mapel':
                conn.execute("DELETE FROM master_mapel WHERE id = ?", (id_master,))
            conn.commit()
            flash(f"Data master {tipe} berhasil dihapus!", "success")
        except:
            flash("Gagal menghapus data master.", "error")
        finally:
            conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/add', methods=['POST'])
def add_user():
    if not is_admin_or_super(): return redirect(url_for('login'))
    nama = request.form.get('nama', '').strip()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    role = request.form.get('role', '').strip().lower()
    can_print = int(request.form.get('can_print', 0))
    nip = request.form.get('nip', '-').strip()
    bidang_pelajaran = request.form.get('bidang_pelajaran', '-').strip()
    status_walikelas = request.form.get('status_walikelas', 'Bukan')
    
    m_kelas = request.form.getlist('mengajar_kelas')
    m_mapel = request.form.getlist('mengajar_mapel')
    mengajar_kelas = ", ".join(m_kelas) if m_kelas else "Semua"
    mengajar_mapel = ", ".join(m_mapel) if m_mapel else "Semua"
    
    if role in ['admin', 'superadmin'] and not is_superadmin(): 
        flash("Anda tidak diizinkan membuat akun Administrator.", "error")
        return redirect(url_for('manage_users'))
        
    if nama and username and password and role:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, role, nama, nip, bidang_pelajaran, status_walikelas, mengajar_kelas, mengajar_mapel, can_print) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (username, hashed_password, role, nama, nip, bidang_pelajaran, status_walikelas, mengajar_kelas, mengajar_mapel, can_print))
            conn.commit()
            flash(f"Akun {nama} berhasil dibuat!", "success")
        except sqlite3.IntegrityError: flash(f"GAGAL: Username '{username}' sudah terpakai!", "error")
        except: flash("Terjadi kesalahan sistem.", "error")
        finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if not is_admin_or_super(): return redirect(url_for('login'))
    nama = request.form.get('edit_nama', '').strip()
    role = request.form.get('edit_role', '').strip().lower()
    password = request.form.get('edit_password', '')
    can_print = int(request.form.get('edit_can_print', 0))
    nip = request.form.get('edit_nip', '-').strip()
    bidang_pelajaran = request.form.get('edit_bidang_pelajaran', '-').strip()
    status_walikelas = request.form.get('status_walikelas', 'Bukan')
    
    m_kelas = request.form.getlist('edit_mengajar_kelas')
    m_mapel = request.form.getlist('edit_mengajar_mapel')
    mengajar_kelas = ", ".join(m_kelas) if m_kelas else "Semua"
    mengajar_mapel = ", ".join(m_mapel) if m_mapel else "Semua"

    if role in ['admin', 'superadmin'] and not is_superadmin(): 
        flash("Anda tidak diizinkan mengubah role ke Admin.", "error")
        return redirect(url_for('manage_users'))
        
    conn = get_db_connection()
    try:
        if password: 
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            conn.execute("UPDATE users SET nama=?, role=?, password=?, nip=?, bidang_pelajaran=?, status_walikelas=?, mengajar_kelas=?, mengajar_mapel=?, can_print=? WHERE id=?", (nama, role, hashed_password, nip, bidang_pelajaran, status_walikelas, mengajar_kelas, mengajar_mapel, can_print, user_id))
        else: 
            conn.execute("UPDATE users SET nama=?, role=?, nip=?, bidang_pelajaran=?, status_walikelas=?, mengajar_kelas=?, mengajar_mapel=?, can_print=? WHERE id=?", (nama, role, nip, bidang_pelajaran, status_walikelas, mengajar_kelas, mengajar_mapel, can_print, user_id))
        conn.commit()
        flash("Profil berhasil disimpan!", "success")
    except sqlite3.IntegrityError: flash("Username bentrok!", "error")
    except: flash("Terjadi kesalahan.", "error")
    finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin_or_super(): return redirect(url_for('login'))
    if user_id != session.get('user_id'):
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash("Akun berhasil dihapus.", "success")
        except: flash("Gagal dihapus.", "error")
        finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete-multiple', methods=['POST'])
def delete_multiple_users():
    if not is_admin_or_super(): return redirect(url_for('login'))
    user_ids = request.form.getlist('user_ids')
    current_user_id = str(session.get('user_id'))
    valid_ids = [uid for uid in user_ids if uid.isdigit() and uid != current_user_id]
    if valid_ids:
        conn = get_db_connection()
        conn.execute(f"DELETE FROM users WHERE id IN ({','.join(['?']*len(valid_ids))})", valid_ids)
        conn.commit()
        conn.close()
        flash(f"{len(valid_ids)} Akun dihapus.", "success")
    return redirect(url_for('manage_users'))

@app.route('/siswa', methods=['GET', 'POST'])
def siswa():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        nisn = request.form.get('nisn', '').strip()
        nama_siswa = request.form.get('nama_siswa', '').strip()
        jenis_kelamin = request.form.get('jenis_kelamin', '').strip()
        kelas = request.form.get('kelas', '').strip()
        nama_wali = request.form.get('nama_wali', '').strip()
        no_hp_wali = request.form.get('no_hp_wali', '').strip()
        status_siswa = request.form.get('status_siswa', 'Aktif').strip()
        if nisn and nama_siswa and kelas:
            try:
                conn.execute("INSERT INTO siswa (nisn, nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali, status_siswa) VALUES (?, ?, ?, ?, ?, ?, ?)", (nisn, nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali, status_siswa))
                conn.commit()
            except: pass
        conn.close()
        return redirect(url_for('siswa'))
    
    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY CASE WHEN status_siswa='Aktif' THEN 1 ELSE 2 END, kelas ASC, nama_siswa ASC").fetchall()
    conn.close()
    return render_template('dashboard/siswa.html', nama_user=session['nama'], siswa_list=daftar_siswa)

@app.route('/siswa/edit/<nisn>', methods=['POST'])
def edit_siswa(nisn):
    if 'user_id' not in session: return redirect(url_for('login'))
    nama_siswa = request.form.get('edit_nama_siswa', '').strip()
    jenis_kelamin = request.form.get('edit_jenis_kelamin', '').strip()
    kelas = request.form.get('edit_kelas', '').strip()
    nama_wali = request.form.get('edit_nama_wali', '').strip()
    no_hp_wali = request.form.get('edit_no_hp_wali', '').strip()
    status_siswa = request.form.get('edit_status_siswa', 'Aktif').strip()
    conn = get_db_connection()
    try:
        conn.execute("UPDATE siswa SET nama_siswa=?, jenis_kelamin=?, kelas=?, nama_wali=?, no_hp_wali=?, status_siswa=? WHERE nisn=?", (nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali, status_siswa, nisn))
        conn.commit()
    except: pass
    finally: conn.close()
    return redirect(url_for('siswa'))

@app.route('/siswa/delete/<nisn>', methods=['POST'])
def delete_siswa(nisn):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM siswa WHERE nisn = ?", (nisn,))
        conn.commit()
    except: pass
    finally: conn.close()
    return redirect(url_for('siswa'))

@app.route('/poin', methods=['GET', 'POST'])
def poin():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        tipe_catatan = request.form.get('tipe_catatan', 'pelanggaran')
        nisn = request.form.get('nisn', '').strip()
        nama_siswa = request.form.get('nama_siswa', '').strip()
        kelas = request.form.get('kelas', '-').strip()
        jenis_catatan = request.form.get('jenis_catatan', '').strip()
        poin_val = request.form.get('poin', 0)
        tanggal = request.form.get('tanggal', '').strip()
        
        if nisn and nama_siswa and jenis_catatan and tanggal:
            try:
                if tipe_catatan == 'prestasi':
                    conn.execute("INSERT INTO prestasi (nisn, nama_siswa, kelas, jenis_prestasi, poin, tanggal) VALUES (?, ?, ?, ?, ?, ?)", (nisn, nama_siswa, kelas, jenis_catatan, int(poin_val), tanggal))
                else:
                    conn.execute("INSERT INTO pelanggaran (nisn, nama_siswa, kelas, jenis_pelanggaran, poin, tanggal) VALUES (?, ?, ?, ?, ?, ?)", (nisn, nama_siswa, kelas, jenis_catatan, int(poin_val), tanggal))
                conn.commit()
                flash("Catatan aktivitas siswa berhasil disimpan!", "success")
            except Exception as e: 
                flash(f"Terjadi kesalahan saat menyimpan: {e}", "error")
        return redirect(url_for('poin'))
    
    try:
        daftar_siswa = conn.execute("SELECT nisn, nama_siswa, kelas FROM siswa WHERE status_siswa='Aktif'").fetchall()
        riwayat_gabungan = conn.execute("""
            SELECT tanggal, nisn, nama_siswa, jenis_pelanggaran as aktivitas, poin, 'Pelanggaran' as tipe FROM pelanggaran
            UNION ALL
            SELECT tanggal, nisn, nama_siswa, jenis_prestasi as aktivitas, poin, 'Prestasi' as tipe FROM prestasi
            ORDER BY tanggal DESC LIMIT 20
        """).fetchall()
        
        master_pelanggaran = conn.execute("SELECT * FROM master_pelanggaran ORDER BY poin ASC").fetchall()
        master_prestasi = conn.execute("SELECT * FROM master_prestasi ORDER BY poin ASC").fetchall()
    except Exception as e:
        print("Error loading /poin:", e)
        flash("Sedang memulihkan struktur database, harap coba lagi.", "error")
        riwayat_gabungan, master_pelanggaran, master_prestasi, daftar_siswa = [], [], [], []
    finally:
        conn.close()
    
    siswa_dict = {s['nisn']: {'nama': s['nama_siswa'], 'kelas': s['kelas']} for s in daftar_siswa}
    return render_template('dashboard/poin.html', nama_user=session['nama'], siswa_map=siswa_dict, riwayat_list=riwayat_gabungan, master_pelanggaran=master_pelanggaran, master_prestasi=master_prestasi)

@app.route('/poin/tambah-master', methods=['POST'])
def tambah_master_pelanggaran():
    if not is_admin_or_super(): return redirect(url_for('poin'))
    tipe_master = request.form.get('tipe_master', 'pelanggaran')
    nama = request.form.get('nama_master', '').strip()
    poin_val = request.form.get('poin_master', 0)
    
    if nama and poin_val:
        conn = get_db_connection()
        try:
            if tipe_master == 'prestasi':
                conn.execute("INSERT INTO master_prestasi (nama_prestasi, poin) VALUES (?, ?)", (nama, int(poin_val)))
            else:
                conn.execute("INSERT INTO master_pelanggaran (nama_pelanggaran, poin) VALUES (?, ?)", (nama, int(poin_val)))
            conn.commit()
            flash(f"Master {tipe_master} berhasil ditambahkan!", "success")
        except: 
            flash("Gagal menambahkan! Nama mungkin sudah digunakan.", "error")
        finally: conn.close()
    return redirect(url_for('poin'))

@app.route('/laporan')
def laporan():
    if 'user_id' not in session: return redirect(url_for('login'))
    search_query = request.args.get('q', '').strip()
    conn = get_db_connection()
    siswa_data = None
    pelanggaran_data = []
    total_poin = 0
    kehadiran = {'Hadir': 0, 'Sakit': 0, 'Izin': 0, 'Alfa': 0, 'Persentase': 100.0}
    if search_query:
        siswa_data = conn.execute("SELECT * FROM siswa WHERE nisn = ? OR nama_siswa LIKE ?", (search_query, f"%{search_query}%")).fetchone()
        if siswa_data:
            pelanggaran_data = conn.execute("SELECT * FROM pelanggaran WHERE nisn = ? ORDER BY tanggal DESC", (siswa_data['nisn'],)).fetchall()
            total_poin = sum(p['poin'] for p in pelanggaran_data)
            absensi_data = conn.execute("SELECT status, COUNT(*) as total FROM presensi_harian WHERE nisn = ? GROUP BY status", (siswa_data['nisn'],)).fetchall()
            total_hari = 0
            for row in absensi_data:
                status_val = row['status']
                count_val = row['total']
                if status_val == 'HADIR': kehadiran['Hadir'] = count_val
                elif status_val == 'SAKIT': kehadiran['Sakit'] = count_val
                elif status_val == 'IZIN': kehadiran['Izin'] = count_val
                elif status_val == 'ALFA': kehadiran['Alfa'] = count_val
                total_hari += count_val
            if total_hari > 0: kehadiran['Persentase'] = round((kehadiran['Hadir'] / total_hari) * 100, 1)
    conn.close()
    return render_template('dashboard/laporan.html', nama_user=session['nama'], siswa=siswa_data, pelanggaran=pelanggaran_data, total_poin=total_poin, kehadiran=kehadiran, search_query=search_query)

@app.route('/api/get_presensi', methods=['POST'])
def get_presensi():
    if 'user_id' not in session: return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    tanggal = data.get('tanggal')
    mapel = data.get('mata_pelajaran')
    conn = get_db_connection()
    records = conn.execute("SELECT nisn, status, deskripsi, jurnal_kelas FROM presensi_harian WHERE tanggal=? AND mata_pelajaran=?", (tanggal, mapel)).fetchall()
    conn.close()
    result = [dict(r) for r in records]
    return jsonify({"status": "success", "data": result})

@app.route('/presensi', methods=['GET', 'POST'])
def presensi():
    if 'user_id' not in session: 
        if request.method == 'POST': return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        tanggal = data.get('tanggal')
        mapel = data.get('mata_pelajaran')
        pertemuan = data.get('pertemuan')
        jurnal_kelas = data.get('jurnal_kelas', '')
        records = data.get('records', [])
        guru_id = session['user_id']
        
        if not tanggal or not records or not mapel or not pertemuan: 
            return jsonify({"status": "error", "message": "Data Presensi tidak lengkap"}), 400
        try:
            for record in records:
                nisn = record.get('nisn')
                status = record.get('status')
                deskripsi = record.get('deskripsi', '')
                
                existing = conn.execute("SELECT id FROM presensi_harian WHERE tanggal=? AND nisn=? AND mata_pelajaran=?", (tanggal, nisn, mapel)).fetchone()
                if existing: 
                    conn.execute("UPDATE presensi_harian SET status=?, pertemuan=?, guru_id=?, deskripsi=?, jurnal_kelas=? WHERE id=?", (status, pertemuan, guru_id, deskripsi, jurnal_kelas, existing['id']))
                else: 
                    conn.execute("INSERT INTO presensi_harian (tanggal, nisn, mata_pelajaran, pertemuan, status, guru_id, deskripsi, jurnal_kelas) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (tanggal, nisn, mapel, pertemuan, status, guru_id, deskripsi, jurnal_kelas))
            conn.commit()
            return jsonify({"status": "success", "message": "Presensi kelas berhasil disimpan!"})
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
        finally: conn.close()

    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY CASE WHEN status_siswa='Aktif' THEN 1 ELSE 2 END, kelas ASC, nama_siswa ASC").fetchall()
    akumulasi_raw = conn.execute("SELECT nisn, status, COUNT(*) as count FROM presensi_harian GROUP BY nisn, status").fetchall()
    akumulasi = {}
    for row in akumulasi_raw:
        nisn = row['nisn']
        if nisn not in akumulasi: akumulasi[nisn] = {'Hadir':0, 'Izin':0, 'Sakit':0, 'Alfa':0}
        status_key = row['status'].capitalize()
        if status_key in akumulasi[nisn]: akumulasi[nisn][status_key] = row['count']
        
    conn.close()
    hak_kelas = session.get('mengajar_kelas', 'Semua')
    hak_mapel = session.get('mengajar_mapel', 'Semua')
    role = session.get('role', 'guru')
    return render_template('dashboard/presensi.html', nama_user=session['nama'], siswa_list=daftar_siswa, akumulasi=akumulasi, mapel_master=MAPEL_MASTER, hak_kelas=hak_kelas, hak_mapel=hak_mapel, role=role)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')