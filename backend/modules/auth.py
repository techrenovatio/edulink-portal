from .database import get_db_connection
from werkzeug.security import check_password_hash

def verify_login(username, password, role):
    conn = get_db_connection()
    
    # Mencegah SQL Injection dengan Parameterized Query (?)
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND role = ?",
        (username, role)
    ).fetchone()
    
    conn.close()
    
    # Verifikasi Password Hash
    if user and check_password_hash(user['password'], password):
        return dict(user)
        
    return None