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

def force_patch_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("CREATE TABLE IF NOT EXISTS prestasi (id INTEGER PRIMARY KEY AUTOINCREMENT, nisn TEXT, nama_siswa TEXT, kelas TEXT, jenis_prestasi TEXT, poin INTEGER, tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS master_prestasi (id INTEGER PRIMARY KEY AUTOINCREMENT, nama_prestasi TEXT UNIQUE, poin INTEGER)")
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
            cursor.executemany("INSERT OR IGNORE INTO master_prestasi (nama_prestasi, poin) VALUES (?, ?)", [('Mewakili Sekolah di Olimpiade', 30), ('Juara 1 Lomba Tingkat Kota/Kabupaten', 50), ('Juara 1 Lomba Tingkat Provinsi', 75), ('Juara 1 Lomba Tingkat Nasional', 100)])
            
        cursor.execute("SELECT COUNT(*) FROM master_kelas")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT OR IGNORE INTO master_kelas (nama_kelas) VALUES (?)", [('X IPA 1',), ('X IPS 1',), ('XI IPA 1',), ('XI IPA 2',), ('XI IPS 1',), ('XII IPA 1',), ('XII IPA 2',), ('XII IPS 1',)])

        cursor.execute("SELECT COUNT(*) FROM master_mapel")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT OR IGNORE INTO master_mapel (nama_mapel) VALUES (?)", [('Matematika',), ('Bahasa Indonesia',), ('Bahasa Inggris',), ('Pendidikan Kewarganegaraan',), ('Teknologi Informasi dan Komputer',), ('Literasi Digital',), ('Bahasa Arab',), ('Geografi',), ('Penjaskes',), ('Fisika',), ('Biologi',), ('Budi Pekerti',), ('Sosiologi',), ('Ekonomi',)])

        conn.commit()
    except Exception as e: print("DB Patch Error:", e)
    finally: conn.close()

init_db()
force_patch_database()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

MAPEL_MASTER = {'X': ['Matematika Dasar', 'Bahasa Indonesia'], 'XI IPA': ['Matematika']}

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
        return render_template('login.html', error="Kredensial tidak sesuai!")
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

    trend_pelanggaran, trend_prestasi = [0]*6, [0]*6
    b_pelanggaran = conn.execute("SELECT strftime('%m', tanggal) as bulan, COUNT(*) as total FROM pelanggaran GROUP BY bulan").fetchall()
    for r in b_pelanggaran:
        if r['bulan'] and 7 <= int(r['bulan']) <= 12: trend_pelanggaran[int(r['bulan'])-7] = r['total']
            
    b_prestasi = conn.execute("SELECT strftime('%m', tanggal) as bulan, SUM(poin) as total FROM prestasi GROUP BY bulan").fetchall()
    for r in b_prestasi:
        if r['bulan'] and r['total'] and 7 <= int(r['bulan']) <= 12: trend_prestasi[int(r['bulan'])-7] = r['total']

    conn.close()
    return render_template('dashboard/index.html', nama_user=session['nama'], total_siswa=total_siswa, kelas_x=kelas_x, kelas_xi=kelas_xi, kelas_xii=kelas_xii, total_pelanggaran=total_pelanggaran, sp_aktif=sp_aktif, recent_logs=recent_logs, kehadiran_rata=kehadiran_rata, trend_pelanggaran=trend_pelanggaran, trend_prestasi=trend_prestasi)

@app.route('/users')
def manage_users():
    if not is_admin_or_super(): return redirect(url_for('login'))
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    m_kelas = conn.execute("SELECT * FROM master_kelas ORDER BY nama_kelas ASC").fetchall()
    m_mapel = conn.execute("SELECT * FROM master_mapel ORDER BY nama_mapel ASC").fetchall()
    conn.close()
    return render_template('dashboard/users.html', nama_user=session['nama'], users=users, current_role=session.get('role', '').lower(), m_kelas=m_kelas, m_mapel=m_mapel)

@app.route('/users/add_master', methods=['POST'])
def add_master_data():
    if not is_superadmin(): return redirect(url_for('manage_users'))
    tipe, nama = request.form.get('tipe'), request.form.get('nama', '').strip()
    if nama:
        conn = get_db_connection()
        try:
            conn.execute(f"INSERT INTO master_{tipe} (nama_{tipe}) VALUES (?)", (nama,))
            conn.commit()
            flash(f"Data {tipe} '{nama}' ditambahkan!", "success")
        except sqlite3.IntegrityError: flash("Data sudah ada!", "error")
        finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete_master', methods=['POST'])
def delete_master_data():
    if not is_superadmin(): return redirect(url_for('manage_users'))
    tipe, id_master = request.form.get('tipe'), request.form.get('id_master')
    if id_master:
        conn = get_db_connection()
        try:
            conn.execute(f"DELETE FROM master_{tipe} WHERE id = ?", (id_master,))
            conn.commit()
            flash("Data dihapus!", "success")
        except: flash("Gagal dihapus.", "error")
        finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/add', methods=['POST'])
def add_user():
    if not is_admin_or_super(): return redirect(url_for('login'))
    nama, username, password, role = request.form.get('nama', ''), request.form.get('username', '').lower(), request.form.get('password', ''), request.form.get('role', '').lower()
    can_print = int(request.form.get('can_print', 0))
    nip, bidang, status_walikelas = request.form.get('nip', '-'), request.form.get('bidang_pelajaran', '-'), request.form.get('status_walikelas', 'Bukan')
    
    m_kelas, m_mapel = request.form.getlist('mengajar_kelas'), request.form.getlist('mengajar_mapel')
    m_kelas_str = ", ".join(m_kelas) if m_kelas else "Semua"
    m_mapel_str = ", ".join(m_mapel) if m_mapel else "Semua"
    
    if role in ['admin', 'superadmin'] and not is_superadmin(): return redirect(url_for('manage_users'))
    if nama and username and password:
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, role, nama, nip, bidang_pelajaran, status_walikelas, mengajar_kelas, mengajar_mapel, can_print) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (username, generate_password_hash(password, method='pbkdf2:sha256'), role, nama, nip, bidang, status_walikelas, m_kelas_str, m_mapel_str, can_print))
            conn.commit()
            flash("Akun dibuat!", "success")
        except: flash("Username terpakai!", "error")
        finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if not is_admin_or_super(): return redirect(url_for('login'))
    nama, role, password = request.form.get('edit_nama', ''), request.form.get('edit_role', '').lower(), request.form.get('edit_password', '')
    can_print, nip, bidang = int(request.form.get('edit_can_print', 0)), request.form.get('edit_nip', '-'), request.form.get('edit_bidang_pelajaran', '-')
    status_walikelas = request.form.get('edit_status_walikelas', 'Bukan')
    
    m_kelas = ", ".join(request.form.getlist('edit_mengajar_kelas')) or "Semua"
    m_mapel = ", ".join(request.form.getlist('edit_mengajar_mapel')) or "Semua"

    if role in ['admin', 'superadmin'] and not is_superadmin(): return redirect(url_for('manage_users'))
    conn = get_db_connection()
    try:
        if password: conn.execute("UPDATE users SET nama=?, role=?, password=?, nip=?, bidang_pelajaran=?, status_walikelas=?, mengajar_kelas=?, mengajar_mapel=?, can_print=? WHERE id=?", (nama, role, generate_password_hash(password, method='pbkdf2:sha256'), nip, bidang, status_walikelas, m_kelas, m_mapel, can_print, user_id))
        else: conn.execute("UPDATE users SET nama=?, role=?, nip=?, bidang_pelajaran=?, status_walikelas=?, mengajar_kelas=?, mengajar_mapel=?, can_print=? WHERE id=?", (nama, role, nip, bidang, status_walikelas, m_kelas, m_mapel, can_print, user_id))
        conn.commit()
        flash("Profil disimpan!", "success")
    except: flash("Gagal edit.", "error")
    finally: conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin_or_super(): return redirect(url_for('login'))
    if user_id != session.get('user_id'):
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete-multiple', methods=['POST'])
def delete_multiple_users():
    if not is_admin_or_super(): return redirect(url_for('login'))
    user_ids = [uid for uid in request.form.getlist('user_ids') if uid.isdigit() and uid != str(session.get('user_id'))]
    if user_ids:
        conn = get_db_connection()
        conn.execute(f"DELETE FROM users WHERE id IN ({','.join(['?']*len(user_ids))})", user_ids)
        conn.commit()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/siswa', methods=['GET', 'POST'])
def siswa():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        nisn, nama, jk, kelas, wali, hp, status = request.form.get('nisn', ''), request.form.get('nama_siswa', ''), request.form.get('jenis_kelamin', ''), request.form.get('kelas', ''), request.form.get('nama_wali', ''), request.form.get('no_hp_wali', ''), request.form.get('status_siswa', 'Aktif')
        if nisn and nama and kelas:
            try:
                conn.execute("INSERT INTO siswa (nisn, nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali, status_siswa) VALUES (?, ?, ?, ?, ?, ?, ?)", (nisn, nama, jk, kelas, wali, hp, status))
                conn.commit()
            except: pass
        return redirect(url_for('siswa'))
    
    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY CASE WHEN status_siswa='Aktif' THEN 1 ELSE 2 END, kelas ASC, nama_siswa ASC").fetchall()
    conn.close()
    return render_template('dashboard/siswa.html', nama_user=session['nama'], siswa_list=daftar_siswa)

@app.route('/siswa/edit/<nisn>', methods=['POST'])
def edit_siswa(nisn):
    if 'user_id' not in session: return redirect(url_for('login'))
    nama, jk, kelas, wali, hp, status = request.form.get('edit_nama_siswa', ''), request.form.get('edit_jenis_kelamin', ''), request.form.get('edit_kelas', ''), request.form.get('edit_nama_wali', ''), request.form.get('edit_no_hp_wali', ''), request.form.get('edit_status_siswa', 'Aktif')
    conn = get_db_connection()
    conn.execute("UPDATE siswa SET nama_siswa=?, jenis_kelamin=?, kelas=?, nama_wali=?, no_hp_wali=?, status_siswa=? WHERE nisn=?", (nama, jk, kelas, wali, hp, status, nisn))
    conn.commit()
    conn.close()
    return redirect(url_for('siswa'))

@app.route('/siswa/delete/<nisn>', methods=['POST'])
def delete_siswa(nisn):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM siswa WHERE nisn = ?", (nisn,))
    conn.commit()
    conn.close()
    return redirect(url_for('siswa'))

@app.route('/poin', methods=['GET', 'POST'])
def poin():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        tipe, nisn, nama, kelas, jenis, poin_val, tgl = request.form.get('tipe_catatan', 'pelanggaran'), request.form.get('nisn', ''), request.form.get('nama_siswa', ''), request.form.get('kelas', '-'), request.form.get('jenis_catatan', ''), request.form.get('poin', 0), request.form.get('tanggal', '')
        if nisn and nama and jenis and tgl:
            try:
                table = 'prestasi' if tipe == 'prestasi' else 'pelanggaran'
                col = 'jenis_prestasi' if tipe == 'prestasi' else 'jenis_pelanggaran'
                conn.execute(f"INSERT INTO {table} (nisn, nama_siswa, kelas, {col}, poin, tanggal) VALUES (?, ?, ?, ?, ?, ?)", (nisn, nama, kelas, jenis, int(poin_val), tgl))
                conn.commit()
                flash("Catatan disimpan!", "success")
            except: flash("Gagal menyimpan.", "error")
        return redirect(url_for('poin'))
    
    try:
        daftar_siswa = conn.execute("SELECT nisn, nama_siswa, kelas FROM siswa WHERE status_siswa='Aktif'").fetchall()
        riwayat_gabungan = conn.execute("SELECT tanggal, nisn, nama_siswa, jenis_pelanggaran as aktivitas, poin, 'Pelanggaran' as tipe FROM pelanggaran UNION ALL SELECT tanggal, nisn, nama_siswa, jenis_prestasi as aktivitas, poin, 'Prestasi' as tipe FROM prestasi ORDER BY tanggal DESC LIMIT 20").fetchall()
        master_pelanggaran = conn.execute("SELECT * FROM master_pelanggaran ORDER BY poin ASC").fetchall()
        master_prestasi = conn.execute("SELECT * FROM master_prestasi ORDER BY poin ASC").fetchall()
    except Exception as e:
        riwayat_gabungan, master_pelanggaran, master_prestasi, daftar_siswa = [], [], [], []
    finally: conn.close()
    
    siswa_dict = {s['nisn']: {'nama': s['nama_siswa'], 'kelas': s['kelas']} for s in daftar_siswa}
    return render_template('dashboard/poin.html', nama_user=session['nama'], siswa_map=siswa_dict, riwayat_list=riwayat_gabungan, master_pelanggaran=master_pelanggaran, master_prestasi=master_prestasi)

@app.route('/poin/tambah-master', methods=['POST'])
def tambah_master_pelanggaran():
    if not is_admin_or_super(): return redirect(url_for('poin'))
    tipe, nama, poin_val = request.form.get('tipe_master', 'pelanggaran'), request.form.get('nama_master', ''), request.form.get('poin_master', 0)
    if nama and poin_val:
        conn = get_db_connection()
        try:
            table = 'master_prestasi' if tipe == 'prestasi' else 'master_pelanggaran'
            col = 'nama_prestasi' if tipe == 'prestasi' else 'nama_pelanggaran'
            conn.execute(f"INSERT INTO {table} ({col}, poin) VALUES (?, ?)", (nama, int(poin_val)))
            conn.commit()
            flash("Master ditambahkan!", "success")
        except: flash("Gagal menambahkan.", "error")
        finally: conn.close()
    return redirect(url_for('poin'))

# --- PERBAIKAN FITUR: RUTE LAPORAN YANG DIPERKAYA ---
@app.route('/laporan')
def laporan():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Menangkap Parameter Form Filter
    search_query = request.args.get('q', '').strip()
    kelas_query = request.args.get('kelas', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    conn = get_db_connection()
    
    # Ambil data Master Kelas untuk Dropdown Filter
    try: m_kelas = conn.execute("SELECT * FROM master_kelas ORDER BY nama_kelas ASC").fetchall()
    except: m_kelas = []

    # State Container
    view_mode = 'default' # (default | class | individual)
    siswa_data, class_data = None, []
    pelanggaran_data, prestasi_data = [], []
    total_poin_pelanggaran, total_poin_prestasi = 0, 0
    kehadiran = {'Hadir': 0, 'Sakit': 0, 'Izin': 0, 'Alfa': 0, 'Persentase': 100.0}
    default_data = {'top_prestasi': [], 'radar_sp': [], 'jurnal': []}

    # Merangkai Query Filter Tanggal
    date_filter_query = ""
    date_params = []
    if start_date and end_date:
        date_filter_query = " AND tanggal BETWEEN ? AND ?"
        date_params = [start_date, end_date + " 23:59:59"]

    if search_query:
        # MODE 1: DETAIL INDIVIDU
        view_mode = 'individual'
        siswa_data = conn.execute("SELECT * FROM siswa WHERE nisn = ? OR nama_siswa LIKE ?", (search_query, f"%{search_query}%")).fetchone()
        if siswa_data:
            nisn = siswa_data['nisn']
            
            pelanggaran_data = conn.execute(f"SELECT * FROM pelanggaran WHERE nisn = ? {date_filter_query} ORDER BY tanggal DESC", [nisn] + date_params).fetchall()
            total_poin_pelanggaran = sum(p['poin'] for p in pelanggaran_data)
            
            prestasi_data = conn.execute(f"SELECT * FROM prestasi WHERE nisn = ? {date_filter_query} ORDER BY tanggal DESC", [nisn] + date_params).fetchall()
            total_poin_prestasi = sum(p['poin'] for p in prestasi_data)

            absensi_data = conn.execute(f"SELECT status, COUNT(*) as total FROM presensi_harian WHERE nisn = ? {date_filter_query} GROUP BY status", [nisn] + date_params).fetchall()
            total_hari = 0
            for row in absensi_data:
                s_val, c_val = row['status'], row['total']
                if s_val == 'HADIR': kehadiran['Hadir'] = c_val
                elif s_val == 'SAKIT': kehadiran['Sakit'] = c_val
                elif s_val == 'IZIN': kehadiran['Izin'] = c_val
                elif s_val == 'ALFA': kehadiran['Alfa'] = c_val
                total_hari += c_val
            if total_hari > 0: kehadiran['Persentase'] = round((kehadiran['Hadir'] / total_hari) * 100, 1)

    elif kelas_query:
        # MODE 2: REKAP KOLEKTIF PER KELAS
        view_mode = 'class'
        students = conn.execute("SELECT nisn, nama_siswa FROM siswa WHERE kelas = ? AND status_siswa = 'Aktif' ORDER BY nama_siswa ASC", (kelas_query,)).fetchall()
        for s in students:
            nisn = s['nisn']
            pel = conn.execute(f"SELECT SUM(poin) FROM pelanggaran WHERE nisn = ? {date_filter_query}", [nisn] + date_params).fetchone()[0] or 0
            pres = conn.execute(f"SELECT SUM(poin) FROM prestasi WHERE nisn = ? {date_filter_query}", [nisn] + date_params).fetchone()[0] or 0
            
            abs_raw = conn.execute(f"SELECT status, COUNT(*) as total FROM presensi_harian WHERE nisn = ? {date_filter_query} GROUP BY status", [nisn] + date_params).fetchall()
            h, i, sk, a = 0, 0, 0, 0
            for r in abs_raw:
                if r['status'] == 'HADIR': h = r['total']
                elif r['status'] == 'IZIN': i = r['total']
                elif r['status'] == 'SAKIT': sk = r['total']
                elif r['status'] == 'ALFA': a = r['total']
            tot_hari = h + i + sk + a
            perc = round((h / tot_hari * 100), 1) if tot_hari > 0 else 100.0
            
            class_data.append({'nisn': nisn, 'nama_siswa': s['nama_siswa'], 'pelanggaran': pel, 'prestasi': pres, 'h': h, 'i': i, 's': sk, 'a': a, 'persentase': perc})
    else:
        # MODE 3: DEFAULT WIDGETS
        view_mode = 'default'
        try:
            default_data['top_prestasi'] = conn.execute("SELECT nisn, nama_siswa, kelas, SUM(poin) as total FROM prestasi GROUP BY nisn ORDER BY total DESC LIMIT 5").fetchall()
            default_data['radar_sp'] = conn.execute("SELECT nisn, nama_siswa, kelas, SUM(poin) as total FROM pelanggaran GROUP BY nisn HAVING total >= 50 ORDER BY total DESC LIMIT 5").fetchall()
            default_data['jurnal'] = conn.execute("SELECT p.tanggal, p.mata_pelajaran, p.jurnal_kelas, u.nama as guru FROM presensi_harian p LEFT JOIN users u ON p.guru_id = u.id WHERE p.jurnal_kelas != '' AND p.jurnal_kelas IS NOT NULL GROUP BY p.tanggal, p.mata_pelajaran ORDER BY p.tanggal DESC LIMIT 5").fetchall()
        except Exception as e: print("Widget Data Error:", e)
            
    conn.close()
    return render_template('dashboard/laporan.html', nama_user=session['nama'], m_kelas=m_kelas, view_mode=view_mode, siswa=siswa_data, pelanggaran=pelanggaran_data, prestasi=prestasi_data, total_poin_pelanggaran=total_poin_pelanggaran, total_poin_prestasi=total_poin_prestasi, kehadiran=kehadiran, class_data=class_data, default_data=default_data, search_query=search_query, kelas_query=kelas_query, start_date=start_date, end_date=end_date)

@app.route('/api/get_presensi', methods=['POST'])
def get_presensi():
    if 'user_id' not in session: return jsonify({"status": "error", "message": "Unauthorized"}), 401
    tanggal, mapel = request.json.get('tanggal'), request.json.get('mata_pelajaran')
    conn = get_db_connection()
    records = conn.execute("SELECT nisn, status, deskripsi, jurnal_kelas FROM presensi_harian WHERE tanggal=? AND mata_pelajaran=?", (tanggal, mapel)).fetchall()
    conn.close()
    return jsonify({"status": "success", "data": [dict(r) for r in records]})

@app.route('/presensi', methods=['GET', 'POST'])
def presensi():
    if 'user_id' not in session: 
        if request.method == 'POST': return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        tanggal, mapel, pertemuan, jurnal_kelas = data.get('tanggal'), data.get('mata_pelajaran'), data.get('pertemuan'), data.get('jurnal_kelas', '')
        records, guru_id = data.get('records', []), session['user_id']
        
        if not tanggal or not records or not mapel or not pertemuan: return jsonify({"status": "error", "message": "Data tidak lengkap"}), 400
        try:
            for rec in records:
                nisn, status, deskripsi = rec.get('nisn'), rec.get('status'), rec.get('deskripsi', '')
                existing = conn.execute("SELECT id FROM presensi_harian WHERE tanggal=? AND nisn=? AND mata_pelajaran=?", (tanggal, nisn, mapel)).fetchone()
                if existing: conn.execute("UPDATE presensi_harian SET status=?, pertemuan=?, guru_id=?, deskripsi=?, jurnal_kelas=? WHERE id=?", (status, pertemuan, guru_id, deskripsi, jurnal_kelas, existing['id']))
                else: conn.execute("INSERT INTO presensi_harian (tanggal, nisn, mata_pelajaran, pertemuan, status, guru_id, deskripsi, jurnal_kelas) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (tanggal, nisn, mapel, pertemuan, status, guru_id, deskripsi, jurnal_kelas))
            conn.commit()
            return jsonify({"status": "success", "message": "Presensi disimpan!"})
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
    return render_template('dashboard/presensi.html', nama_user=session['nama'], siswa_list=daftar_siswa, akumulasi=akumulasi, mapel_master=MAPEL_MASTER, hak_kelas=session.get('mengajar_kelas', 'Semua'), hak_mapel=session.get('mengajar_mapel', 'Semua'), role=session.get('role', 'guru'))

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')