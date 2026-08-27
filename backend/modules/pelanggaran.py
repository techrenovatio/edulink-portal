from modules.database import get_db_connection

def tambah_pelanggaran(nisn, nama_siswa, kelas, jenis_pelanggaran, poin):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO pelanggaran (nisn, nama_siswa, kelas, jenis_pelanggaran, poin) VALUES (?, ?, ?, ?, ?)",
        (nisn, nama_siswa, kelas, jenis_pelanggaran, poin)
    )
    conn.commit()
    conn.close()

def get_all_pelanggaran():
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM pelanggaran ORDER BY tanggal DESC").fetchall()
    conn.close()
    return data