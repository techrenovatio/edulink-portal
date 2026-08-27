from .database import get_db_connection

def verify_login(username, password, role):
    conn = get_db_connection()
    
    # Mencari pengguna di database yang datanya cocok
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ? AND role = ?",
        (username, password, role)
    ).fetchone()
    
    conn.close()
    
    if user:
        return dict(user) # Kembalikan data user jika cocok
    return None # Kembalikan None jika gagal (password salah, dll)