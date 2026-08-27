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

# --- KONFIGURASI KEAMANAN TINGGI (SECURITY HARDENING) ---
app.secret_key = 'edulink_super_secret_key_2026_change_this_to_random_bytes'

# Proteksi Cookie Sesi
app.config['SESSION_COOKIE_HTTPONLY'] = True    # Mencegah pencurian cookie via JavaScript XSS
app.config['SESSION_COOKIE_SECURE'] = True      # Cookie hanya dikirim via koneksi HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Mencegah serangan CSRF
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2) # Auto logout dalam 2 jam

# Inisialisasi Database
init_db()

# --- ROUTES ---

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
            session['role'] = user['role']
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

# --- FITUR KELOLA PENGGUNA (USER MANAGEMENT) ---

@app.route('/users')
def manage_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, role, nama FROM users ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('dashboard/users.html', nama_user=session['nama'], users=users)

@app.route('/users/add', methods=['POST'])
def add_user():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    nama = request.form.get('nama', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', '').strip()
    
    if nama and username and password and role:
        # Hash password sebelum dimasukkan ke DB
        hashed_password = generate_password_hash(password, method='scrypt')
        
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (nama, username, password, role) VALUES (?, ?, ?, ?)",
                (nama, username, hashed_password, role)
            )
            conn.commit()
        except Exception as e:
            print("Gagal membuat user:", e)
        finally:
            conn.close()
            
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    if user_id != session.get('user_id'):
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
    return redirect(url_for('manage_users'))

@app.route('/users/delete-multiple', methods=['POST'])
def delete_multiple_users():
    if 'user_id' not in session or session.get('role') != 'admin':
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

@app.route('/poin')
def poin():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard/poin.html')

@app.route('/rapor')
def rapor():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard/rapor.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)