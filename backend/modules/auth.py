from werkzeug.security import check_password_hash
from modules.database import get_db_connection

def verify_login(username, password, role=None):
    if not username or not password:
        return None

    u_clean = username.strip().lower()

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    for user in users:
        db_user = dict(user)
        db_username = str(db_user.get('username', '')).strip().lower()

        if db_username == u_clean:
            if check_password_hash(db_user['password'], password):
                return db_user

    return None