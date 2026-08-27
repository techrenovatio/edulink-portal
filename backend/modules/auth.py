from werkzeug.security import check_password_hash
from modules.database import get_db_connection

def verify_login(username, password, role):
    if not username or not password or not role:
        return None

    # Bersihkan spasi dan ubah ke huruf kecil untuk pencocokan presisi
    username_clean = username.strip().lower()
    role_clean = role.strip().lower()

    conn = get_db_connection()
    
    # Ambil data user berdasarkan username (case-insensitive)
    user = conn.execute(
        "SELECT * FROM users WHERE LOWER(TRIM(username)) = ?", 
        (username_clean,)
    ).fetchone()
    
    conn.close()

    # Jika user ditemukan
    if user:
        db_user = dict(user)
        db_role = str(db_user.get('role', '')).strip().lower()

        # Validasi role dan password hash
        if db_role == role_clean and check_password_hash(db_user['password'], password):
            return db_user

    return None