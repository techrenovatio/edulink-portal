from modules.database import get_db_connection

def get_rekap_absensi():
    conn = get_db_connection()
    # Dummy data / query absensi
    conn.close()
    return []