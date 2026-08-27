from werkzeug.security import check_password_hash
from modules.database import get_db_connection

def verify_login(username, password, role):
    if not username or not password or not role:
        return None
        
    username_clean = username.strip().lower()
    role_clean = role.strip().lower()
    
    conn = get_db_connection()
    # Pencocokan fleksibel tanpa membedakan huruf besar/kecil di database
    user = conn.execute(
        "SELECT * FROM users WHERE LOWER(TRIM(username)) = ? AND LOWER(TRIM(role)) = ?", 
        (username_clean, role_clean)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        return dict(user)
    return None