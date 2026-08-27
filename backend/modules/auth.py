from werkzeug.security import check_password_hash
from modules.database import get_db_connection

def verify_login(username, password, role):
    if not username or not password or not role:
        return None

    username_clean = str(username).strip().lower()
    role_clean = str(role).strip().lower()

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE LOWER(TRIM(username)) = ?", 
        (username_clean,)
    ).fetchone()
    conn.close()

    if user:
        u_dict = dict(user)
        db_role = str(u_dict.get('role', '')).strip().lower()

        # Cocokkan role dan password hash
        if db_role == role_clean and check_password_hash(u_dict['password'], password):
            return u_dict

    return None