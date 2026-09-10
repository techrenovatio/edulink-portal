import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
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
    return render_template('index.html')

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
    return render_template('dashboard/index.html', nama_user=session['nama'])

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
            conn.execute(
                "INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
                (username, hashed_password, role, nama)
            )
            conn.commit()
        except Exception as e:
            print("Gagal membuat user:", e)
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

@app.route('/siswa')
def siswa():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY kelas ASC, nama_siswa ASC").fetchall()
    conn.close()
    
    return render_template('dashboard/siswa.html', nama_user=session['nama'], siswa_list=daftar_siswa)

# --- PERBAIKAN LOGIKA SIMPAN POIN (POST METHOD ALLOWED) ---
@app.route('/poin', methods=['GET', 'POST'])
def poin():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    conn = get_db_connection()

    # Jika Formulir dikirimkan (Submit)
    if request.method == 'POST':
        nisn = request.form.get('nisn', '').strip()
        nama_siswa = request.form.get('nama_siswa', '').strip()
        kelas = request.form.get('kelas', '').strip()
        jenis_pelanggaran = request.form.get('jenis_pelanggaran', '').strip()
        poin_val = request.form.get('poin', 0)

        # Simpan ke Database
        if nisn and nama_siswa and jenis_pelanggaran:
            try:
                conn.execute(
                    "INSERT INTO pelanggaran (nisn, nama_siswa, kelas, jenis_pelanggaran, poin) VALUES (?, ?, ?, ?, ?)",
                    (nisn, nama_siswa, kelas, jenis_pelanggaran, int(poin_val))
                )
                conn.commit()
            except Exception as e:
                print("Gagal menyimpan data pelanggaran:", e)

        conn.close()
        # Redirect ke halaman yang sama agar tidak submit ulang saat di-refresh
        return redirect(url_for('poin'))
    
    # Jika menampilkan halaman (GET)
    daftar_siswa = conn.execute("SELECT nisn, nama_siswa, kelas FROM siswa").fetchall()
    daftar_pelanggaran = conn.execute("SELECT * FROM pelanggaran ORDER BY tanggal DESC LIMIT 20").fetchall()
    conn.close()
    
    siswa_dict = {s['nisn']: {'nama': s['nama_siswa'], 'kelas': s['kelas']} for s in daftar_siswa}
    
    return render_template('dashboard/poin.html', 
                           nama_user=session['nama'], 
                           siswa_map=siswa_dict, 
                           pelanggaran_list=daftar_pelanggaran)

@app.route('/laporan')
def laporan():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
        
    search_query = request.args.get('q', '').strip()
    
    conn = get_db_connection()
    siswa_data = None
    pelanggaran_data = []
    total_poin = 0
    
    if search_query:
        siswa_data = conn.execute(
            "SELECT * FROM siswa WHERE nisn = ? OR nama_siswa LIKE ?", 
            (search_query, f"%{search_query}%")
        ).fetchone()
        
        if siswa_data:
            pelanggaran_data = conn.execute(
                "SELECT * FROM pelanggaran WHERE nisn = ? ORDER BY tanggal DESC", 
                (siswa_data['nisn'],)
            ).fetchall()
            total_poin = sum(p['poin'] for p in pelanggaran_data)
            
    conn.close()
    
    return render_template('dashboard/laporan.html', 
                           nama_user=session['nama'],
                           siswa=siswa_data,
                           pelanggaran=pelanggaran_data,
                           total_poin=total_poin,
                           search_query=search_query)

@app.route('/absensi')
def absensi():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    daftar_siswa = conn.execute("SELECT * FROM siswa ORDER BY kelas ASC, nama_siswa ASC").fetchall()
    conn.close()
    
    return render_template('dashboard/absensi.html', 
                           nama_user=session['nama'], 
                           siswa_list=daftar_siswa)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')