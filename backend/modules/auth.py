from werkzeug.security import check_password_hash
from modules.database import get_db_connection

def verify_login(username, password, role):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND role = ?", 
        (username, role)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        return dict(user)
    return None