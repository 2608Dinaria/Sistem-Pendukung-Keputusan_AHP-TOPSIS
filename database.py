import sqlite3
import hashlib
from datetime import datetime
import os
import pandas as pd

DB_NAME = "db_bantuan.db"

def get_db_connection():
    """Membuat koneksi ke database SQLite."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inisialisasi database: membuat tabel dan mengisi dummy data jika kosong."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabel Admin
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_admin (
        id_admin INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    """)

    # 2. Tabel Alternatif (Kelompok Tani)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_alternatif (
        id_alternatif INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_kelompok TEXT NOT NULL,
        desa_kelurahan TEXT DEFAULT 'Tidak Diketahui',
        luas_lahan REAL NOT NULL,
        produktivitas REAL NOT NULL,
        jumlah_petani INTEGER NOT NULL,
        status_aktual TEXT DEFAULT 'Bukan Penerima'
    )
    """)
    
    # MIGRASI: Cek apakah kolom desa_kelurahan sudah ada (untuk DB lama)
    cursor.execute("PRAGMA table_info(tb_alternatif)")
    alt_cols = [col[1] for col in cursor.fetchall()]
    if "desa_kelurahan" not in alt_cols:
        cursor.execute("ALTER TABLE tb_alternatif ADD COLUMN desa_kelurahan TEXT DEFAULT 'Tidak Diketahui'")
        
    # MIGRASI: Cek apakah kolom is_active sudah ada (untuk filter data berjalan)
    if "is_active" not in alt_cols:
        cursor.execute("ALTER TABLE tb_alternatif ADD COLUMN is_active INTEGER DEFAULT 1")

    # 3. Tabel Sesi Hitung (Master Riwayat)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_sesi_hitung (
        id_sesi INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_sesi TEXT NOT NULL,
        tanggal_simpan DATETIME DEFAULT CURRENT_TIMESTAMP,
        bobot_c1 REAL,
        bobot_c2 REAL,
        bobot_c3 REAL
    )
    """)

    # 4. Tabel Hasil Perhitungan (Detail Riwayat)
    # Cek apakah id_sesi ada, jika tidak drop dan recreate (MIGRASI)
    cursor.execute("PRAGMA table_info(tb_hasil)")
    cols = [col[1] for col in cursor.fetchall()]
    if cols and "id_sesi" not in cols:
        cursor.execute("DROP TABLE tb_hasil")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_hasil (
        id_hasil INTEGER PRIMARY KEY AUTOINCREMENT,
        id_sesi INTEGER NOT NULL,
        id_alternatif INTEGER NOT NULL,
        nilai_preferensi REAL NOT NULL,
        ranking INTEGER NOT NULL,
        FOREIGN KEY(id_sesi) REFERENCES tb_sesi_hitung(id_sesi) ON DELETE CASCADE,
        FOREIGN KEY(id_alternatif) REFERENCES tb_alternatif(id_alternatif) ON DELETE CASCADE
    )
    """)

    # 4. Tabel Konfigurasi AHP (Persistensi input perbandingan)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_config_ahp (
        id_config INTEGER PRIMARY KEY AUTOINCREMENT,
        var_key TEXT NOT NULL UNIQUE,
        var_value TEXT NOT NULL
    )
    """)
    conn.commit()

    # Seed Admin Default jika belum ada
    cursor.execute("SELECT COUNT(*) FROM tb_admin")
    if cursor.fetchone()[0] == 0:
        username = "admin"
        password_plain = "admin123"
        password_hashed = hashlib.sha256(password_plain.encode()).hexdigest()
        cursor.execute("INSERT INTO tb_admin (username, password) VALUES (?, ?)", (username, password_hashed))
        conn.commit()

    # Seed Dummy Data Alternatif jika belum ada (minimal 10 kelompok tani)
    cursor.execute("SELECT COUNT(*) FROM tb_alternatif")
    if cursor.fetchone()[0] == 0:
        dummy_data = [
            ("Kelompok Tani Tunas Harapan", 5.5, 2.25, 25, "Penerima"),
            ("Kelompok Tani Mekar Sari", 4.2, 2.33, 18, "Bukan Penerima"),
            ("Kelompok Tani Subur Makmur", 8.0, 2.31, 35, "Penerima"),
            ("Kelompok Tani Mulyo Agung", 6.2, 1.81, 22, "Penerima"),
            ("Kelompok Tani Tani Mukti", 3.5, 1.86, 15, "Bukan Penerima"),
            ("Kelompok Tani Budi Luhur", 7.1, 2.11, 30, "Penerima"),
            ("Kelompok Tani Karya Mandiri", 5.0, 2.00, 20, "Bukan Penerima"),
            ("Kelompok Tani Sri Rejeki", 4.8, 1.92, 17, "Bukan Penerima"),
            ("Kelompok Tani Hijau Daun", 6.8, 2.09, 28, "Penerima"),
            ("Kelompok Tani Tani Sejahtera", 5.9, 2.00, 24, "Bukan Penerima")
        ]
        cursor.executemany("""
        INSERT INTO tb_alternatif (nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """, [ (d[0], "Tidak Diketahui", d[1], d[2], d[3], d[4]) for d in dummy_data ])
        conn.commit()

    conn.close()

# --- FUNGSI CRUD ALTERNATIF ---

def get_all_alternatives(search_query=None):
    """Mengambil semua data alternatif dari database, opsional pencarian."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        query = "%" + search_query + "%"
        cursor.execute("""
        SELECT * FROM tb_alternatif 
        WHERE nama_kelompok LIKE ? AND is_active = 1
        ORDER BY id_alternatif DESC
        """, (query,))
    else:
        cursor.execute("SELECT * FROM tb_alternatif WHERE is_active = 1 ORDER BY id_alternatif DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_alternative_by_id(id_alt):
    """Mengambil satu data alternatif berdasarkan ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tb_alternatif WHERE id_alternatif = ?", (id_alt,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_alternative(nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual="Bukan Penerima"):
    """Menambah data alternatif baru."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tb_alternatif (nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual, is_active)
    VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual))
    conn.commit()
    conn.close()
    return True

def update_alternative(id_alt, nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual):
    """Memperbarui data alternatif."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tb_alternatif 
    SET nama_kelompok = ?, desa_kelurahan = ?, luas_lahan = ?, produktivitas = ?, jumlah_petani = ?, status_aktual = ?
    WHERE id_alternatif = ?
    """, (nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual, id_alt))
    conn.commit()
    conn.close()
    return True

def delete_alternative(id_alt):
    """Menghapus data alternatif beserta hasil perhitungannya."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tb_alternatif WHERE id_alternatif = ?", (id_alt,))
    conn.commit()
    conn.close()
    return True

def update_actual_status(id_alt, status):
    """Memperbarui status aktual dari kelompok tani (Penerima / Bukan Penerima)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tb_alternatif 
    SET status_aktual = ?
    WHERE id_alternatif = ?
    """, (status, id_alt))
    conn.commit()
    conn.close()
    return True

# --- FUNGSI HASIL PERHITUNGAN RIWAYAT ---

def save_ranking_session(nama_sesi, weights, results_list):
    """
    Menyimpan sesi perhitungan baru ke dalam riwayat.
    weights: list/array [w1, w2, w3]
    results_list: list of tuples (id_alternatif, nilai_preferensi, ranking)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Simpan Master Sesi
        cursor.execute("""
        INSERT INTO tb_sesi_hitung (nama_sesi, bobot_c1, bobot_c2, bobot_c3)
        VALUES (?, ?, ?, ?)
        """, (nama_sesi, weights[0], weights[1], weights[2]))
        
        id_sesi = cursor.lastrowid
        
        # 2. Simpan Detail Hasil
        for item in results_list:
            cursor.execute("""
            INSERT INTO tb_hasil (id_sesi, id_alternatif, nilai_preferensi, ranking)
            VALUES (?, ?, ?, ?)
            """, (id_sesi, item[0], item[1], item[2]))
            
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving ranking session: {e}")
        return False
    finally:
        conn.close()

def get_all_sessions():
    """Mengambil semua daftar sesi perhitungan yang tersimpan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tb_sesi_hitung ORDER BY tanggal_simpan DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_results_by_session(id_sesi):
    """Mengambil hasil perangkingan untuk sesi tertentu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT h.id_hasil, h.id_alternatif, h.nilai_preferensi, h.ranking,
           s.id_sesi, s.nama_sesi, s.tanggal_simpan, s.bobot_c1, s.bobot_c2, s.bobot_c3,
           a.nama_kelompok, a.desa_kelurahan, a.luas_lahan, a.produktivitas, a.jumlah_petani, a.status_aktual
    FROM tb_hasil h
    JOIN tb_sesi_hitung s ON h.id_sesi = s.id_sesi
    JOIN tb_alternatif a ON h.id_alternatif = a.id_alternatif
    WHERE h.id_sesi = ?
    ORDER BY h.ranking ASC
    """, (id_sesi,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_session(id_sesi):
    """Menghapus satu sesi riwayat."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tb_sesi_hitung WHERE id_sesi = ?", (id_sesi,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_latest_session_results():
    """Mengambil hasil dari sesi terbaru."""
    sessions = get_all_sessions()
    if not sessions:
        return []
    return get_results_by_session(sessions[0]['id_sesi'])

def save_results(results_list):
    """Fungsi pembungkus lama (compatibility) - Sekarang membuat sesi otomatis."""
    now_str = datetime.now().strftime("%d %b %Y, %H:%M")
    # Coba ambil bobot dari session state jika ada, atau default
    import streamlit as st
    weights = [0.33, 0.33, 0.34] # Default jika tidak ada
    return save_ranking_session(f"Perhitungan Otomatis ({now_str})", weights, results_list)

def import_alternatives_from_dataframe(df, clear_existing=True):
    """Mengimpor data alternatif kelompok tani secara massal dari Pandas DataFrame (hasil upload Excel)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if clear_existing:
            cursor.execute("DELETE FROM tb_hasil")
            cursor.execute("DELETE FROM tb_sesi_hitung") # Hapus riwayat sesi juga agar tidak ada ghost sessions
            cursor.execute("DELETE FROM tb_alternatif")
        else:
            cursor.execute("UPDATE tb_alternatif SET is_active = 0")
        conn.commit()
        
        for _, row in df.iterrows():
            # Mengambil status aktual dengan default Bukan Penerima jika kosong
            status = row.get('status_aktual', 'Bukan Penerima')
            if pd.isna(status) or str(status).strip() not in ['Penerima', 'Bukan Penerima']:
                status = 'Bukan Penerima'
            
            cursor.execute("""
            INSERT INTO tb_alternatif (nama_kelompok, desa_kelurahan, luas_lahan, produktivitas, jumlah_petani, status_aktual, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                str(row['nama_kelompok']),
                str(row.get('desa_kelurahan', 'Tidak Diketahui')),
                float(row['luas_lahan']),
                float(row['produktivitas']),
                int(row['jumlah_petani']),
                str(status)
            ))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error importing alternatives: {e}")
        return False
    finally:
        conn.close()

def get_ahp_config():
    """Mengambil konfigurasi matriks AHP dari database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT var_key, var_value FROM tb_config_ahp")
    rows = cursor.fetchall()
    conn.close()
    return {row['var_key']: row['var_value'] for row in rows}

def save_ahp_config(config_dict):
    """Menyimpan konfigurasi matriks AHP ke database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for key, value in config_dict.items():
            cursor.execute("""
            INSERT INTO tb_config_ahp (var_key, var_value) 
            VALUES (?, ?) 
            ON CONFLICT(var_key) DO UPDATE SET var_value = excluded.var_value
            """, (key, value))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving AHP config: {e}")
        return False
    finally:
        conn.close()
