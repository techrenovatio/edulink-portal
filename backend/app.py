import os
from datetime import timedelta
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash

from modules.database import init_db, get_db_connection
from modules.auth import verify_login

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

init_db()

def is_admin():
    return 'user_id' in session and str(session.get('role', '')).strip().lower() == 'admin'

@app.route('/')
def home():
    conn = get_db_connection()
    try:
        total_siswa = conn.execute("SELECT COUNT(*) FROM siswa").fetchone()[0]
    except Exception:
        total_siswa = 0
    finally:
        conn.close()
    return render_template('index.html', total_siswa=total_siswa)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard_overview'))

    if request.method == 'POST':
        role = request.form.get('role', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = verify_login(username, password, role)

        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['nama'] = user['nama']
            session['role'] = str(user['role']).strip().lower()
            return redirect(url_for('dashboard_overview'))
        else:
            return render_template('login.html', error="Kredensial atau Peran tidak sesuai!")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard_overview():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    total_siswa = conn.execute("SELECT COUNT(*) FROM siswa").fetchone()[0]
    kelas_x = conn.execute("SELECT COUNT(*) FROM siswa WHERE kelas LIKE 'X %'").fetchone()[0]
    kelas_xi = conn.execute("SELECT COUNT(*) FROM siswa WHERE kelas LIKE 'XI %'").fetchone()[0]
    kelas_xii = conn.execute("SELECT COUNT(*) FROM siswa WHERE kelas LIKE 'XII %'").fetchone()[0]
    total_pelanggaran = conn.execute("SELECT COUNT(*) FROM pelanggaran").fetchone()[0]
    
    sp_query = """
        SELECT nisn, SUM(poin) as total_poin 
        FROM pelanggaran 
        GROUP BY nisn 
        HAVING total_poin >= 50
    """
    sp_aktif = len(conn.execute(sp_query).fetchall())
    recent_logs = conn.execute("SELECT * FROM pelanggaran ORDER BY tanggal DESC LIMIT 5").fetchall()
    conn.close()
    
    return render_template('dashboard/index.html', 
                           nama_user=session['nama'],
                           total_siswa=total_siswa,
                           kelas_x=kelas_x,
                           kelas_xi=kelas_xi,
                           kelas_xii=kelas_xii,
                           total_pelanggaran=total_pelanggaran,
                           sp_aktif=sp_aktif,
                           recent_logs=recent_logs)

@app.route('/users')
def manage_users():
    if not is_admin():
        return redirect(url_for('login'))
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, role, nama FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('dashboard/users.html', nama_user=session['nama'], users=users)

@app.route('/users/add', methods=['POST'])
def add_user():
    if not is_admin():
        return redirect(url_for('login'))
    nama = request.form.get('nama', '').strip()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    role = request.form.get('role', '').strip().lower()
    
    if nama and username and password and role:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)", (username, hashed_password, role, nama))
            conn.commit()
        except Exception as e:
            pass
        finally:
            conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        return redirect(url_for('login'))
    if user_id != session.get('user_id'):
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/users/delete-multiple', methods=['POST'])
def delete_multiple_users():
    if not is_admin():
        return redirect(url_for('login'))
    user_ids = request.form.getlist('user_ids')
    current_user_id = str(session.get('user_id'))
    valid_ids = [uid for uid in user_ids if uid.isdigit() and uid != current_user_id]
    
    if valid_ids:
        conn = get_db_connection()
        query = f"DELETE FROM users WHERE id IN ({','.join(['?']*len(valid_ids))})"
        conn.execute(query, valid_ids)
        conn.commit()
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/siswa', methods=['GET', 'POST'])
def siswa():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    conn = get_db_connection()

    if request.method == 'POST':
        nisn = request.form.get('nisn', '').strip()
        nama_siswa = request.form.get('nama_siswa', '').strip()
        jenis_kelamin = request.form.get('jenis_kelamin', '').strip()
        kelas = request.form.get('kelas', '').strip()
        nama_wali = request.form.get('nama_wali', '').strip()
        no_hp_wali = request.form.get('no_hp_wali', '').strip()

        if nisn and nama_siswa and kelas:
            try:
                conn.execute(
                    "INSERT INTO siswa (nisn, nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali) VALUES (?, ?, ?, ?, ?, ?)",
                    (nisn, nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali)
                )
                conn.commit()
            except Exception as e:
                pass
        
        conn.close()
        return redirect(url_for('siswa'))

    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY kelas ASC, nama_siswa ASC").fetchall()
    conn.close()
    return render_template('dashboard/siswa.html', nama_user=session['nama'], siswa_list=daftar_siswa)

# --- FITUR BARU: EDIT DATA SISWA ---
@app.route('/siswa/edit/<nisn>', methods=['POST'])
def edit_siswa(nisn):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    nama_siswa = request.form.get('edit_nama_siswa', '').strip()
    jenis_kelamin = request.form.get('edit_jenis_kelamin', '').strip()
    kelas = request.form.get('edit_kelas', '').strip()
    nama_wali = request.form.get('edit_nama_wali', '').strip()
    no_hp_wali = request.form.get('edit_no_hp_wali', '').strip()
    
    conn = get_db_connection()
    try:
        conn.execute("""
            UPDATE siswa 
            SET nama_siswa=?, jenis_kelamin=?, kelas=?, nama_wali=?, no_hp_wali=? 
            WHERE nisn=?
        """, (nama_siswa, jenis_kelamin, kelas, nama_wali, no_hp_wali, nisn))
        conn.commit()
    except Exception as e:
        print("Gagal update siswa:", e)
    finally:
        conn.close()
        
    return redirect(url_for('siswa'))

@app.route('/siswa/delete/<nisn>', methods=['POST'])
def delete_siswa(nisn):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM siswa WHERE nisn = ?", (nisn,))
        conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()
    return redirect(url_for('siswa'))

@app.route('/poin', methods=['GET', 'POST'])
def poin():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    conn = get_db_connection()

    if request.method == 'POST':
        nisn = request.form.get('nisn', '').strip()
        nama_siswa = request.form.get('nama_siswa', '').strip()
        kelas = request.form.get('kelas', '').strip()
        jenis_pelanggaran = request.form.get('jenis_pelanggaran', '').strip()
        poin_val = request.form.get('poin', 0)
        tanggal = request.form.get('tanggal', '').strip()

        if nisn and nama_siswa and jenis_pelanggaran and tanggal:
            try:
                conn.execute("INSERT INTO pelanggaran (nisn, nama_siswa, kelas, jenis_pelanggaran, poin, tanggal) VALUES (?, ?, ?, ?, ?, ?)", (nisn, nama_siswa, kelas, jenis_pelanggaran, int(poin_val), tanggal))
                conn.commit()
            except Exception as e:
                pass

        conn.close()
        return redirect(url_for('poin'))
    
    daftar_siswa = conn.execute("SELECT nisn, nama_siswa, kelas FROM siswa").fetchall()
    daftar_pelanggaran = conn.execute("SELECT * FROM pelanggaran ORDER BY tanggal DESC LIMIT 20").fetchall()
    master_pelanggaran = conn.execute("SELECT * FROM master_pelanggaran ORDER BY poin ASC").fetchall()
    conn.close()
    
    siswa_dict = {s['nisn']: {'nama': s['nama_siswa'], 'kelas': s['kelas']} for s in daftar_siswa}
    return render_template('dashboard/poin.html', nama_user=session['nama'], siswa_map=siswa_dict, pelanggaran_list=daftar_pelanggaran, master_pelanggaran=master_pelanggaran)

@app.route('/poin/tambah-master', methods=['POST'])
def tambah_master_pelanggaran():
    if not is_admin():
        return redirect(url_for('poin'))
    nama = request.form.get('nama_pelanggaran', '').strip()
    poin_val = request.form.get('poin_pelanggaran', 0)
    if nama and poin_val:
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO master_pelanggaran (nama_pelanggaran, poin) VALUES (?, ?)", (nama, int(poin_val)))
            conn.commit()
        except Exception as e:
            pass
        finally:
            conn.close()
    return redirect(url_for('poin'))

# --- PERBAIKAN LOGIKA LAPORAN UNTUK MENGHITUNG ABSENSI ---
@app.route('/laporan')
def laporan():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
        
    search_query = request.args.get('q', '').strip()
    conn = get_db_connection()
    siswa_data = None
    pelanggaran_data = []
    total_poin = 0
    
    # Inisialisasi data kehadiran
    kehadiran = {'Hadir': 0, 'Sakit': 0, 'Izin': 0, 'Alfa': 0, 'Persentase': 100.0}
    
    if search_query:
        siswa_data = conn.execute("SELECT * FROM siswa WHERE nisn = ? OR nama_siswa LIKE ?", (search_query, f"%{search_query}%")).fetchone()
        
        if siswa_data:
            pelanggaran_data = conn.execute("SELECT * FROM pelanggaran WHERE nisn = ? ORDER BY tanggal DESC", (siswa_data['nisn'],)).fetchall()
            total_poin = sum(p['poin'] for p in pelanggaran_data)
            
            # Hitung rekap absensi dari database
            absensi_data = conn.execute("SELECT status, COUNT(*) as total FROM absensi WHERE nisn = ? GROUP BY status", (siswa_data['nisn'],)).fetchall()
            
            total_hari = 0
            for row in absensi_data:
                status_val = row['status']
                count_val = row['total']
                if status_val == 'HADIR': kehadiran['Hadir'] = count_val
                elif status_val == 'SAKIT': kehadiran['Sakit'] = count_val
                elif status_val == 'IZIN': kehadiran['Izin'] = count_val
                elif status_val == 'ALFA': kehadiran['Alfa'] = count_val
                total_hari += count_val
            
            if total_hari > 0:
                kehadiran['Persentase'] = round((kehadiran['Hadir'] / total_hari) * 100, 1)

    conn.close()
    return render_template('dashboard/laporan.html', 
                           nama_user=session['nama'],
                           siswa=siswa_data,
                           pelanggaran=pelanggaran_data,
                           total_poin=total_poin,
                           kehadiran=kehadiran,
                           search_query=search_query)

# --- FITUR BARU: BACKEND SIMPAN ABSENSI HARIAN (AJAX) ---
@app.route('/absensi', methods=['GET', 'POST'])
def absensi():
    if 'user_id' not in session: 
        if request.method == 'POST':
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.json
        tanggal = data.get('tanggal')
        records = data.get('records', [])
        
        if not tanggal or not records:
            return jsonify({"status": "error", "message": "Data tidak lengkap"}), 400
            
        try:
            for record in records:
                nisn = record.get('nisn')
                status = record.get('status')
                
                # Cek jika data presensi di hari tersebut untuk siswa terkait sudah ada
                existing = conn.execute("SELECT id FROM absensi WHERE tanggal=? AND nisn=?", (tanggal, nisn)).fetchone()
                if existing:
                    # Update status
                    conn.execute("UPDATE absensi SET status=? WHERE id=?", (status, existing['id']))
                else:
                    # Insert data baru
                    conn.execute("INSERT INTO absensi (tanggal, nisn, status) VALUES (?, ?, ?)", (tanggal, nisn, status))
            
            conn.commit()
            return jsonify({"status": "success", "message": "Presensi harian berhasil direkam ke database!"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            conn.close()

    # GET Request untuk load HTML
    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY kelas ASC, nama_siswa ASC").fetchall()
    conn.close()
    
    return render_template('dashboard/absensi.html', nama_user=session['nama'], siswa_list=daftar_siswa)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')