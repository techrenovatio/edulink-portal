from werkzeug.security import check_password_hash
from modules.database import get_db_connection

def verify_login(username, password, role):
    if not username or not password or not role:
        return None

    u_clean = username.strip().lower()
    r_clean = role.strip().lower()

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    for user in users:
        db_user = dict(user)
        # Cocokkan username dan role secara fleksibel (case-insensitive)
        if db_user['username'].strip().lower() == u_clean and db_user['role'].strip().lower() == r_clean:
            if check_password_hash(db_user['password'], password):
                return db_user

    return None