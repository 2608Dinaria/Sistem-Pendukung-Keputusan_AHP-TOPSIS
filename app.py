import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import time
import streamlit.components.v1 as components

# Import modul internal
from database import (
    init_db, get_all_alternatives, get_alternative_by_id,
    add_alternative, update_alternative, delete_alternative,
    save_ranking_session, get_all_sessions, get_results_by_session,
    get_latest_session_results, delete_session, update_actual_status,
    import_alternatives_from_dataframe, get_ahp_config, save_ahp_config,
    get_all_sessions, get_results_by_session, get_latest_session_results, delete_session
)
from datetime import datetime
from auth import init_session, login, logout
from ahp import calculate_ahp, CRITERIA_NAMES
from topsis import calculate_topsis, CRITERIA_KEYS
from utils import (
    generate_ranking_chart, 
    generate_confusion_matrix_chart, export_to_excel, export_to_csv,
    generate_excel_template
)

# --- KONFIGURASI HALAMAN ---
# Harus dieksekusi pertama kali sebelum elemen Streamlit lainnya.
# Jika belum login, sidebar otomatis di 'collapsed' untuk menyembunyikan area kosong.
# Jika sudah login, set ke 'expanded' atau 'auto'.
is_logged_in = st.session_state.get('logged_in', False)
st.set_page_config(
    page_title="SPK BANTUAN - AHP TOPSIS",
    page_icon="🌱",
    initial_sidebar_state="expanded" if is_logged_in else "collapsed"
)

# --- FUNGSI HELPER MODAL (NATIVE - AUTO CLOSE) ---
@st.dialog("Pesan Sistem")
def auto_notification_dialog(message, icon="✅"):
    st.write(f"### {icon} {message}")
    time.sleep(0.5)
    st.rerun()

# --- INISIALISASI ---
init_db()
init_session()

# --- TRIGGER NOTIFIKASI (Tampil PERTAMA sebelum konten lain) ---
if 'msg_modal' in st.session_state:
    msg, icon = st.session_state.pop('msg_modal')
    # Jalankan Modal (Centred)
    auto_notification_dialog(msg, icon)
    
    # HENTIKAN eksekusi halaman di sini agar konten utama (hasil/tabel) 
    # baru muncul SETELAH modal otomatis tertutup (rerun).
    st.stop()
# Inisialisasi default nilai AHP di session state (coba load dari DB dulu)
if 'ahp_matrix_inputs' not in st.session_state:
    db_config = get_ahp_config()
    if db_config:
        st.session_state.ahp_matrix_inputs = db_config
    else:
        # Default jika DB kosong (untuk 3 kriteria)
        st.session_state.ahp_matrix_inputs = {
            "c1_c2": "1 - Sama penting dengan",
            "c1_c3": "1 - Sama penting dengan",
            "c2_c3": "1 - Sama penting dengan"
        }

# Definisikan pemetaan skala Saaty ke nilai numerik
SAATY_SCALE = {
    "9 - Mutlak lebih penting dari": 9.0,
    "8 - Mendekati mutlak lebih penting dari": 8.0,
    "7 - Sangat lebih penting dari": 7.0,
    "6 - Mendekati sangat lebih penting dari": 6.0,
    "5 - Lebih penting dari": 5.0,
    "4 - Mendekati lebih penting dari": 4.0,
    "3 - Sedikit lebih penting dari": 3.0,
    "2 - Mendekati sedikit lebih penting dari": 2.0,
    "1 - Sama penting dengan": 1.0,
    "1/2 - Mendekati sedikit kurang penting dari": 1/2,
    "1/3 - Sedikit kurang penting dari": 1/3,
    "1/4 - Mendekati kurang penting dari": 1/4,
    "1/5 - Kurang penting dari": 1/5,
    "1/6 - Mendekati sangat kurang penting dari": 1/6,
    "1/7 - Sangat kurang penting dari": 1/7,
    "1/8 - Mendekati mutlak kurang penting dari": 1/8,
    "1/9 - Mutlak kurang penting dari": 1/9
}

# --- VALIDASI & MIKRASI KUNCI AHP ---
# Jika ada kunci lama (misal: "1 - Sama Penting") di session_state yang tidak ada di SAATY_SCALE baru, reset ke default.
if 'ahp_matrix_inputs' in st.session_state:
    updated_inputs = {}
    default_key = "1 - Sama penting dengan"
    for k, v in st.session_state.ahp_matrix_inputs.items():
        if v not in SAATY_SCALE:
            # Cari barangkali hanya masalah "Sama Penting" vs "Sama penting dengan"
            if "1 - Sama Penting" in v:
                updated_inputs[k] = default_key
            else:
                # Untuk keamanan, jika tidak cocok sama sekali, kembalikan ke "Sama penting dengan"
                updated_inputs[k] = default_key
        else:
            updated_inputs[k] = v
    st.session_state.ahp_matrix_inputs = updated_inputs

# --- HALAMAN LOGIN ADMIN ---
if not st.session_state.logged_in:
    def login_view():
        col1, col2, col3 = st.columns([0.5, 3, 0.5])
        with col2:
            t1, t2, t3 = st.columns([1.1, 1, 0.9])
            with t2:
                st.markdown("### Login Sistem")
            with st.form("login_form"):
                d1, d2, d3 = st.columns([0.1, 2.8, 0.1])
                with d2:
                    st.write("Silakan masukkan kredensial Anda untuk mengakses sistem.")
                username = st.text_input("Username", placeholder="Masukkan username")
                password = st.text_input("Password", type="password", placeholder="Masukkan password")
                
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
                with btn_col2:
                    submit_login = st.form_submit_button("Login", use_container_width=True)
                
                if submit_login:
                    if login(username, password):
                        st.session_state.msg_modal = ("Berhasil Login", "🔓")
                        st.rerun()
                    else:
                        st.error("Username atau password salah.")
            
            st.divider()
            st.caption("© 2026 Bidang Perkebunan, Dinas Pertanian dan Ketahanan Pangan Prov.Sumut")
            
    # Gunakan st.navigation untuk memaksa Streamlit menghapus sidebar state yang tersisa
    pg_login = st.Page(login_view, title="Login", icon="🔒")
    pg = st.navigation([pg_login], position="hidden")
    pg.run()

# --- HALAMAN SETELAH LOGIN ---
else:
    # 1. Definisikan Halaman Dashboard
    def dashboard_page():
        st.title("Sistem Pendukung Keputusan")
        st.subheader("Penerima Bantuan Sektor Perkebunan")
        st.write("""
            Selamat datang di portal resmi SPK Bidang Perkebunan. Sistem ini menggunakan metode 
            AHP (Analytic Hierarchy Process) dan TOPSIS untuk menentukan prioritas 
            penerima bantuan secara objektif dan transparan.
        """)
        st.divider()
        
        # Ambil data terbaru untuk dashboard
        alternatives = get_all_alternatives()
        ranking_results = get_latest_session_results()
            
        # Penjelasan Kriteria
        st.subheader("📋 Kriteria Penilaian Bantuan")
        st.write("Penilaian penerima bantuan perkebunan didasarkan pada 3 kriteria utama:")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.info("**C1. Luas Lahan**\n\n*   Tipe: Benefit\n*   Prioritas: **Lahan Luas**")
        with col_c2:
            st.warning("**C2. Produktivitas**\n\n*   Tipe: Cost\n*   Prioritas: **Produktivitas Rendah**")
        with col_c3:
            st.success("**C3. Jumlah Petani**\n\n*   Tipe: Benefit\n*   Prioritas: **Jumlah Petani Banyak**")
            
        st.divider()
        st.subheader("⚖️ Input Nilai Perbandingan Berpasangan (AHP)")
        st.write("Masukkan nilai kepentingan antar kriteria berdasarkan Skala Saaty (1–9).")
        
        scale_list = list(SAATY_SCALE.keys())
        
        with st.form("ahp_matrix_input_form"):
            col_c1_a, col_c1_b, col_c1_c = st.columns([1, 2, 1])
            with col_c1_a: st.write("**Luas Lahan (C1)**")
            with col_c1_b: c1_c2_sel = st.selectbox("C1 vs C2", options=scale_list, index=scale_list.index(st.session_state.ahp_matrix_inputs["c1_c2"]), key="c1_c2_sb", label_visibility="collapsed")
            with col_c1_c: st.write("**Produktivitas (C2)**")
            
            col_c2_a, col_c2_b, col_c2_c = st.columns([1, 2, 1])
            with col_c2_a: st.write("**Luas Lahan (C1)**")
            with col_c2_b: c1_c3_sel = st.selectbox("C1 vs C3", options=scale_list, index=scale_list.index(st.session_state.ahp_matrix_inputs["c1_c3"]), key="c1_c3_sb", label_visibility="collapsed")
            with col_c2_c: st.write("**Jumlah Petani (C3)**")
            
            col_c3_a, col_c3_b, col_c3_c = st.columns([1, 2, 1])
            with col_c3_a: st.write("**Produktivitas (C2)**")
            with col_c3_b: c2_c3_sel = st.selectbox("C2 vs C3", options=scale_list, index=scale_list.index(st.session_state.ahp_matrix_inputs["c2_c3"]), key="c2_c3_sb", label_visibility="collapsed")
            with col_c3_c: st.write("**Jumlah Petani (C3)**")
            
            submit_ahp_dash = st.form_submit_button("Simpan Perbandingan & Hitung Bobot")
            
            if submit_ahp_dash:
                st.session_state.ahp_matrix_inputs = {"c1_c2": c1_c2_sel, "c1_c3": c1_c3_sel, "c2_c3": c2_c3_sel}
                save_ahp_config(st.session_state.ahp_matrix_inputs)
                st.session_state.msg_modal = ("Perbandingan Kriteria Disimpan", "✅")
                st.rerun()
        
        st.markdown("#### 🏆 Hasil Pembobotan Kriteria (AHP)")
        v12, v13, v23 = SAATY_SCALE[st.session_state.ahp_matrix_inputs["c1_c2"]], SAATY_SCALE[st.session_state.ahp_matrix_inputs["c1_c3"]], SAATY_SCALE[st.session_state.ahp_matrix_inputs["c2_c3"]]
        matrix = np.array([[1, v12, v13], [1/v12, 1, v23], [1/v13, 1/v23, 1]])
        ahp_res = calculate_ahp(matrix)
        
        df_w = ahp_res["weights_dataframe"].copy()
        df_w["Bobot Prioritas (W)"] = df_w["Bobot Prioritas (W)"].map("{:.4f}".format)
        df_w["Persentase (%)"] = df_w["Persentase (%)"].map("{:.2f}%".format)
        st.table(df_w)
        
        if ahp_res["is_consistent"]:
            st.caption(f"✨ Matriks Konsisten (CR = {ahp_res['cr']:.4f})")
        else:
            st.warning(f"⚠️ Matriks Tidak Konsisten (CR = {ahp_res['cr']:.4f}). Disarankan untuk meninjau kembali perbandingan.")

    # 2. Definisikan Halaman Seleksi Prioritas
    def seleksi_prioritas_page():
        st.header("Seleksi Prioritas")
        st.write("Unggah data alternatif kelompok tani dan kelola data secara manual.")
        st.divider()
        
        st.subheader("Upload Data Alternatif via Excel")
        uploaded_file = st.file_uploader("Pilih file Excel alternatif (.xlsx, .xls)", type=["xlsx", "xls"])
        clear_db = st.checkbox("Kosongkan data lama di database sebelum mengunggah", value=True)
        
        if uploaded_file is not None and st.button("🚀 Upload"):
            try:
                df_raw = pd.read_excel(uploaded_file, header=None)
                target_keywords_map = {
                    'nama_kelompok': ['nama', 'kelompok'],
                    'desa_kelurahan': ['desa', 'kelurahan'],
                    'luas_lahan': ['luas', 'lahan'],
                    'produktivitas': ['produktivitas'],
                    'jumlah_petani': ['jumlah', 'petani', 'anggota']
                }
                def find_best_header(df_temp):
                    best_row = 0
                    max_matches = 0
                    for i in range(min(len(df_temp), 10)):
                        row_vals = [str(x).lower() for x in df_temp.iloc[i].values]
                        matches = sum(1 for k_list in target_keywords_map.values() if any(k in " ".join(row_vals) for k in k_list))
                        if matches > max_matches:
                            max_matches, best_row = matches, i
                        if matches == len(target_keywords_map): return i
                    return best_row
                
                header_row = find_best_header(df_raw)
                uploaded_file.seek(0)
                df_upload = pd.read_excel(uploaded_file, header=header_row)
                mapping = {key: next((col for col in df_upload.columns if any(k in str(col).lower().replace("_", " ").replace("-", " ") for k in k_list)), None) for key, k_list in target_keywords_map.items()}
                
                missing_cols = [k for k, v in mapping.items() if v is None]
                if missing_cols:
                    st.error(f"Format Excel salah! Kolom berikut tidak terdeteksi: {', '.join(missing_cols)}")
                else:
                    df_upload = df_upload.rename(columns={v: k for k, v in mapping.items()})
                    df_upload = df_upload[['nama_kelompok', 'desa_kelurahan', 'luas_lahan', 'produktivitas', 'jumlah_petani']] if 'desa_kelurahan' in df_upload.columns else df_upload[['nama_kelompok', 'luas_lahan', 'produktivitas', 'jumlah_petani']]
                    if 'desa_kelurahan' not in df_upload.columns: df_upload['desa_kelurahan'] = 'Tidak Diketahui'
                    
                    df_upload = df_upload.dropna(subset=['nama_kelompok'])
                    for col in ['luas_lahan', 'produktivitas', 'jumlah_petani']: df_upload[col] = pd.to_numeric(df_upload[col], errors='coerce')
                    df_upload = df_upload.dropna()
                    
                    if not df_upload.empty:
                        if import_alternatives_from_dataframe(df_upload, clear_existing=clear_db):
                            st.session_state.msg_modal = (f"Berhasil Impor {len(df_upload)} Data", "📥")
                            st.rerun()
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

        st.divider()
        st.subheader("📋 Daftar Alternatif Saat Ini")
        search_q = st.text_input("🔍 Cari Kelompok Tani", placeholder="Masukkan nama kelompok...")
        current_alts = get_all_alternatives(search_q)
        
        if current_alts:
            df_alts = pd.DataFrame(current_alts).sort_values('id_alternatif', ascending=True).reset_index(drop=True)
            df_alts.insert(0, 'No', range(1, len(df_alts) + 1))
            st.dataframe(df_alts[['No', 'nama_kelompok', 'desa_kelurahan', 'luas_lahan', 'produktivitas', 'jumlah_petani']], use_container_width=True, hide_index=True)
        
        with st.expander("⚙️ Kelola Alternatif Secara Manual"):
            crud_t1, crud_t2, crud_t3 = st.tabs(["➕ Tambah", "✏️ Edit", "❌ Hapus"])
            with crud_t1:
                with st.form("add_form"):
                    n = st.text_input("Nama Kelompok *")
                    d = st.text_input("Desa/Kelurahan")
                    l = st.number_input("Luas Lahan (Ha) *", min_value=0.0)
                    p = st.number_input("Produktivitas (Kw/Ha) *", min_value=0.0)
                    jt = st.number_input("Jumlah Petani *", min_value=1)
                    if st.form_submit_button("Simpan"):
                        if n.strip() and l > 0 and p > 0:
                            add_alternative(n, d, l, p, jt, "Bukan Penerima")
                            st.session_state.msg_modal = (f"Data '{n}' Ditambahkan", "➕"); st.rerun()
            with crud_t2:
                if current_alts:
                    alt_map = {a['id_alternatif']: f"{a['nama_kelompok']} (ID: {a['id_alternatif']})" for a in current_alts}
                    sid = st.selectbox("Pilih Data", options=list(alt_map.keys()), format_func=lambda x: alt_map[x])
                    sa = get_alternative_by_id(sid)
                    with st.form("edit_form"):
                        en = st.text_input("Nama *", value=sa['nama_kelompok'])
                        ed = st.text_input("Desa", value=sa.get('desa_kelurahan', ''))
                        el = st.number_input("Luas *", value=sa['luas_lahan'])
                        ep = st.number_input("Prod *", value=sa['produktivitas'])
                        ej = st.number_input("Petani *", value=int(sa['jumlah_petani']))
                        if st.form_submit_button("Update"):
                            update_alternative(sid, en, ed, el, ep, ej, sa['status_aktual'])
                            st.session_state.msg_modal = ("Perubahan Disimpan", "✏️"); st.rerun()
            with crud_t3:
                if current_alts:
                    did = st.selectbox("Pilih Hapus", options=[a['id_alternatif'] for a in current_alts], format_func=lambda x: next(a['nama_kelompok'] for a in current_alts if a['id_alternatif']==x))
                    if st.button("Ya, Hapus Data"):
                        delete_alternative(did); st.session_state.msg_modal = ("Terhapus", "🗑️"); st.rerun()

        if st.button("🚀 Mulai Perhitungan SPK", use_container_width=True, type="primary"):
            alts = get_all_alternatives()
            if not alts: st.warning("Data kosong!")
            else:
                v12, v13, v23 = SAATY_SCALE[st.session_state.ahp_matrix_inputs["c1_c2"]], SAATY_SCALE[st.session_state.ahp_matrix_inputs["c1_c3"]], SAATY_SCALE[st.session_state.ahp_matrix_inputs["c2_c3"]]
                A = np.array([[1, v12, v13], [1/v12, 1, v23], [1/v13, 1/v23, 1]])
                ahp_res = calculate_ahp(A)
                if ahp_res["is_consistent"]:
                    tRes = calculate_topsis(alts, ahp_res["weights"])
                    ranking_results_temp = tRes["results_dataframe"].to_dict('records')
                    for item in ranking_results_temp: item['nilai_preferensi'] = item.pop('preferensi')
                    st.session_state.current_results = {"ranking_results": ranking_results_temp, "weights": ahp_res["weights"], "timestamp": datetime.now().strftime('%d %b %Y, %H:%M'), "is_saved": False}
                    st.session_state.msg_modal = ("Perhitungan SPK Selesai", "🚀"); st.rerun()
        
        ranking_results = st.session_state.current_results["ranking_results"] if 'current_results' in st.session_state else get_latest_session_results()
        if ranking_results:
            st.divider()
            st.markdown("### 🏆 Hasil Keputusan & Perangkingan")
            df_results = pd.DataFrame(ranking_results)
            st.success(f"🎉 **Rekomendasi Utama:** {df_results.iloc[0]['nama_kelompok']} ({df_results.iloc[0]['nilai_preferensi']:.4f})")
            df_final_sp = df_results[['ranking', 'nama_kelompok', 'desa_kelurahan', 'luas_lahan', 'produktivitas', 'jumlah_petani', 'nilai_preferensi']].copy()
            df_final_sp = df_final_sp.rename(columns={
                'ranking': 'Ranking',
                'nama_kelompok': 'Nama Kelompok',
                'desa_kelurahan': 'Desa/Kelurahan',
                'luas_lahan': 'C1 (Ha)',
                'produktivitas': 'C2 (Kw/Ha)',
                'jumlah_petani': 'C3 (Org)',
                'nilai_preferensi': 'Nilai Preferensi (V)'
            })
            format_dict_sp = {
                "C1 (Ha)": "{:g}",
                "C2 (Kw/Ha)": "{:g}",
                "C3 (Org)": "{:g}",
                "Nilai Preferensi (V)": "{:.4f}"
            }
            st.dataframe(df_final_sp.style.format(format_dict_sp), use_container_width=True, hide_index=True)
            st.pyplot(generate_ranking_chart(df_results))
            if 'current_results' in st.session_state and not st.session_state.current_results.get("is_saved"):
                with st.container(border=True):
                    sn = st.text_input("Nama Sesi", value=st.session_state.current_results["timestamp"])
                    if st.button("💾 Simpan ke Riwayat"):
                        save_ranking_session(sn, st.session_state.current_results["weights"], [(int(r['id_alternatif']), float(r['nilai_preferensi']), int(r['ranking'])) for r in st.session_state.current_results["ranking_results"]])
                        st.session_state.current_results["is_saved"] = True; st.session_state.msg_modal = ("Tersimpan", "💾"); st.rerun()

    # 3. Definisikan Halaman Detail Perhitungan
    def detail_perhitungan_page():
        st.header("Detail Perhitungan (AHP-TOPSIS)")
        st.write("Halaman ini menampilkan rincian matematis langkah demi langkah dari proses perhitungan.")
        st.divider()
        
        alternatives = get_all_alternatives()
        ranking_results = st.session_state.current_results["ranking_results"] if 'current_results' in st.session_state else get_latest_session_results()
        
        if not alternatives or not ranking_results:
            st.warning("⚠️ Data belum diproses. Silakan mulai perhitungan di menu 'Seleksi Prioritas'.")
            return
            
        # Hitung AHP kembali untuk detail
        v12, v13, v23 = SAATY_SCALE[st.session_state.ahp_matrix_inputs["c1_c2"]], SAATY_SCALE[st.session_state.ahp_matrix_inputs["c1_c3"]], SAATY_SCALE[st.session_state.ahp_matrix_inputs["c2_c3"]]
        A = np.array([[1, v12, v13], [1/v12, 1, v23], [1/v13, 1/v23, 1]])
        ahp_res = calculate_ahp(A)
        
        # Hitung TOPSIS kembali untuk detail
        tRes = calculate_topsis(alternatives, ahp_res["weights"])

        # --- SEKSI AHP ---
        st.subheader("1. Perhitungan Analytic Hierarchy Process (AHP)")
        with st.expander("Lihat Detail Tahapan AHP", expanded=True):
            st.markdown("**1.1 Matriks Perbandingan Berpasangan (Pairwise Matrix)**")
            st.write("Membandingkan kepentingan antar kriteria berdasarkan Skala Saaty.")
            st.dataframe(ahp_res["pairwise_matrix"].style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**1.2 Jumlah per Kolom**")
            col_sums_df = pd.DataFrame([ahp_res["column_sums"]], columns=ahp_res["pairwise_matrix"].columns, index=["Jumlah"])
            st.dataframe(col_sums_df.style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**1.3 Normalisasi Matriks AHP**")
            st.write("Membagi setiap elemen dengan jumlah kolomnya.")
            st.dataframe(ahp_res["normalized_matrix"].style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**1.4 Bobot Prioritas Kriteria (W)**")
            st.write("Rata-rata baris dari matriks ternormalisasi.")
            st.dataframe(ahp_res["weights_dataframe"].style.format({"Bobot Prioritas (W)": "{:.4f}", "Persentase (%)": "{:.2f}%"}), hide_index=True, use_container_width=True)
            
            st.markdown("**1.5 Uji Konsistensi Matriks**")
            st.write("Menghitung Consistency Vector (CV) untuk validasi.")
            st.dataframe(ahp_res["consistency_dataframe"].style.format({
                "Bobot (W)": "{:.4f}",
                "A x W": "{:.4f}",
                "CV (A x W / W)": "{:.4f}"
            }), hide_index=True, use_container_width=True)
            
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                st.write(f"$\lambda_{{max}}$: `{ahp_res['lambda_max']:.4f}`")
                st.write(f"Consistency Index (CI): `{ahp_res['ci']:.4f}`")
            with col_cr2:
                st.write(f"Consistency Ratio (CR): `{ahp_res['cr']:.4f}`")
                st.write(f"Status: **{'KONSISTEN ✅' if ahp_res['is_consistent'] else 'TIDAK KONSISTEN ❌'}**")

        st.divider()

        # --- SEKSI TOPSIS ---
        st.subheader("2. Perhitungan TOPSIS")
        with st.expander("Lihat Detail Tahapan TOPSIS", expanded=True):
            st.markdown("**2.1 Matriks Keputusan (X)**")
            st.write("Data aktual alternatif untuk setiap kriteria.")
            st.dataframe(tRes["df_X"].style.format("{:.2f}"), use_container_width=True)
            
            st.markdown("**2.2 Matriks Ternormalisasi (R)**")
            st.write("Normalisasi data agar memiliki skala yang sama.")
            st.dataframe(tRes["df_R"].style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**2.3 Matriks Ternormalisasi Terbobot (Y)**")
            st.write("Matriks R dikalikan dengan bobot prioritas W dari AHP.")
            st.dataframe(tRes["df_Y"].style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**2.4 Solusi Ideal Positif (A+) dan Negatif (A-)**")
            st.write("Nilai terbaik dan terburuk untuk setiap kriteria (mempertimbangkan Benefit/Cost).")
            st.dataframe(tRes["df_ideal"].style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**2.5 Jarak Solusi Ideal (D+ dan D-) dan Nilai Preferensi (V)**")
            st.write("Kedekatan setiap alternatif terhadap solusi ideal beserta nilai preferensinya.")
            st.dataframe(tRes["df_distances"][['D+ (Jarak Ideal Positif)', 'D- (Jarak Ideal Negatif)', 'Nilai Preferensi (V)']].style.format("{:.4f}"), use_container_width=True)
            
            st.markdown("**2.6 Ranking Akhir Prioritas Penerima Bantuan**")
            st.write("Semakin tinggi nilai V, semakin direkomendasikan alternatif tersebut.")
            
            df_final = tRes["results_dataframe"][['ranking', 'nama_kelompok', 'desa_kelurahan', 'luas_lahan', 'produktivitas', 'jumlah_petani', 'preferensi']].copy()
            df_final = df_final.rename(columns={
                'ranking': 'Ranking',
                'nama_kelompok': 'Nama Kelompok',
                'desa_kelurahan': 'Desa/Kelurahan',
                'luas_lahan': 'C1 (Ha)',
                'produktivitas': 'C2 (Kw/Ha)',
                'jumlah_petani': 'C3 (Org)',
                'preferensi': 'Nilai Preferensi (V)'
            })
            format_dict = {
                "C1 (Ha)": "{:g}",
                "C2 (Kw/Ha)": "{:g}",
                "C3 (Org)": "{:g}",
                "Nilai Preferensi (V)": "{:.4f}"
            }
            st.dataframe(df_final.style.format(format_dict), use_container_width=True, hide_index=True)

    # 4. Definisikan Halaman Laporan & Riwayat
    def laporan_riwayat_page():
        st.header("Riwayat & Laporan")
        sessions = get_all_sessions()
        if not sessions: 
            st.warning("Belum ada riwayat.")
            return
        col1, col2 = st.columns([4, 1])
        with col1:
            sid = st.selectbox("Pilih Sesi", options=[s['id_sesi'] for s in sessions], format_func=lambda x: next(s['nama_sesi'] for s in sessions if s['id_sesi']==x))
        with col2:
            if st.button("🗑️ Hapus"):
                delete_session(sid); st.session_state.msg_modal = ("Dihapus", "🗑️"); st.rerun()
        
        results = get_results_by_session(sid)
        if results:
            df = pd.DataFrame(results)
            st.download_button("🟢 Excel", data=export_to_excel(df), file_name=f"SPK_{sid}.xlsx", use_container_width=True)
            cols_to_show = ['ranking', 'nama_kelompok', 'desa_kelurahan', 'luas_lahan', 'produktivitas', 'jumlah_petani', 'nilai_preferensi']
            rename_dict = {
                'ranking': 'Rank',
                'nama_kelompok': 'Kelompok',
                'desa_kelurahan': 'Desa/Kelurahan',
                'luas_lahan': 'Luas Lahan (Ha)',
                'produktivitas': 'Produktivitas (Kw/Ha)',
                'jumlah_petani': 'Jumlah Anggota Petani',
                'nilai_preferensi': 'V'
            }
            st.dataframe(df[cols_to_show].rename(columns=rename_dict), use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("Detail Perhitungan Sesi")
            st.write(f"Bobot AHP Kriteria pada sesi ini: **C1**: {df['bobot_c1'].iloc[0]:.4f} | **C2**: {df['bobot_c2'].iloc[0]:.4f} | **C3**: {df['bobot_c3'].iloc[0]:.4f}")
            
            with st.expander("Lihat Detail Tahapan TOPSIS Sesi Ini", expanded=False):
                weights = [df['bobot_c1'].iloc[0], df['bobot_c2'].iloc[0], df['bobot_c3'].iloc[0]]
                tRes = calculate_topsis(results, weights)
                
                if tRes:
                    st.markdown("**1. Matriks Keputusan (X)**")
                    st.write("Data aktual alternatif untuk setiap kriteria.")
                    st.dataframe(tRes["df_X"].style.format("{:.2f}"), use_container_width=True)
                    
                    st.markdown("**2. Matriks Ternormalisasi (R)**")
                    st.dataframe(tRes["df_R"].style.format("{:.4f}"), use_container_width=True)
                    
                    st.markdown("**3. Matriks Ternormalisasi Terbobot (Y)**")
                    st.dataframe(tRes["df_Y"].style.format("{:.4f}"), use_container_width=True)
                    
                    st.markdown("**4. Solusi Ideal Positif (A+) dan Negatif (A-)**")
                    st.dataframe(tRes["df_ideal"].style.format("{:.4f}"), use_container_width=True)
                    
                    st.markdown("**5. Jarak Solusi Ideal (D+ dan D-) dan Nilai Preferensi (V)**")
                    st.dataframe(tRes["df_distances"][['D+ (Jarak Ideal Positif)', 'D- (Jarak Ideal Negatif)', 'Nilai Preferensi (V)']].style.format("{:.4f}"), use_container_width=True)
        else:
            st.warning("⚠️ Sesi ini kosong. Data kelompok tani untuk perhitungan ini kemungkinan telah dihapus saat pengguna mengunggah data baru.")

    # 5. Definisikan Halaman Evaluasi Akurasi
    def evaluasi_akurasi_page():
        st.header("Evaluasi Akurasi")
        res = st.session_state.current_results["ranking_results"] if 'current_results' in st.session_state else get_latest_session_results()
        if not res:
            st.warning("Data kosong.")
            return
        df = pd.DataFrame(res)
        actual_statuses = {a['id_alternatif']: a['status_aktual'] for a in get_all_alternatives()}
        df['status_aktual'] = df['id_alternatif'].map(actual_statuses).fillna("Bukan Penerima")
        
        total = len(df)
        actual_count = len(df[df['status_aktual'] == "Penerima"])
        quota = st.number_input("Kuota Penerima (N Teratas)", min_value=1, max_value=total, value=int(actual_count if actual_count > 0 else 1))
        
        df['prediksi'] = ["Penerima" if r <= quota else "Bukan Penerima" for r in df['ranking']]
        correct = len(df[df['prediksi'] == df['status_aktual']])
        accuracy = (correct / total) * 100
        
        st.metric("Akurasi Sistem", f"{accuracy:.2f}%")
        st.write("Confusion Matrix sederhana:")
        st.table(pd.crosstab(df['status_aktual'], df['prediksi'], rownames=['Aktual'], colnames=['Prediksi']))

        # 2. Update Status Aktual menggunakan data_editor
        st.subheader("Atur Data Status Aktual Lapangan")
        st.write("Ubah status aktual kelompok tani secara langsung pada tabel di bawah (klik kolom 'Status Aktual Lapangan'), kemudian klik tombol **Simpan Status Aktual** di bawah tabel.")
        
        # Format data untuk editor
        editor_data = df[['id_alternatif', 'nama_kelompok', 'desa_kelurahan', 'status_aktual']].copy()
        
        edited_df = st.data_editor(
            editor_data,
            column_config={
                "id_alternatif": None,
                "nama_kelompok": st.column_config.TextColumn("Nama Kelompok Tani", disabled=True),
                "desa_kelurahan": st.column_config.TextColumn("Desa/Kelurahan", disabled=True),
                "status_aktual": st.column_config.SelectboxColumn(
                    "Status Aktual Lapangan",
                    options=["Penerima", "Bukan Penerima"],
                    required=True
                )
            },
            disabled=["nama_kelompok", "desa_kelurahan"],
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("💾 Simpan Status Aktual"):
            for idx, row in edited_df.iterrows():
                update_actual_status(int(row['id_alternatif']), row['status_aktual'])
            st.session_state.msg_modal = ("Status Aktual Diperbarui", "✅")
            st.rerun()
            
        st.divider()
        tp, tn, fp, fn = 0, 0, 0, 0
        comparison_list = []
        
        for _, row in df.iterrows():
            rank = row['ranking']
            sistem_rekomendasi = "Direkomendasikan" if rank <= quota else "Tidak Direkomendasikan"
            aktual_status = row['status_aktual']
            is_match = False
            if sistem_rekomendasi == "Direkomendasikan" and aktual_status == "Penerima":
                tp += 1; is_match = True
            elif sistem_rekomendasi == "Tidak Direkomendasikan" and aktual_status == "Bukan Penerima":
                tn += 1; is_match = True
            elif sistem_rekomendasi == "Direkomendasikan" and aktual_status == "Bukan Penerima":
                fp += 1
            elif sistem_rekomendasi == "Tidak Direkomendasikan" and aktual_status == "Penerima":
                fn += 1
                
            comparison_list.append({
                "Ranking": rank,
                "Nama Kelompok Tani": row['nama_kelompok'],
                "Desa/Kelurahan": row.get('desa_kelurahan', 'Tidak Diketahui'),
                "Hasil Rekomendasi": sistem_rekomendasi,
                "Status Aktual": aktual_status,
                "Kesesuaian": "✅" if is_match else "❌"
            })
            
        accuracy = (tp + tn) / total if total > 0 else 0.0
        st.subheader("🎯 Metrik Evaluasi")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.metric("Akurasi Sistem", f"{accuracy*100:.2f}%")
        with col_m2: st.metric("Prediksi Benar (Match)", f"{tp+tn}")
        with col_m3: st.metric("Prediksi Salah", f"{fp+fn}")
        
        st.latex(r"Akurasi = \frac{TP + TN}{TP + TN + FP + FN} \times 100\%")
        
        col_g1, col_g2 = st.columns([3, 2])
        with col_g1:
            st.markdown("### 📊 Visualisasi Confusion Matrix")
            fig_cm = generate_confusion_matrix_chart(tn, fp, fn, tp)
            st.pyplot(fig_cm)
        with col_g2:
            st.markdown("### 📝 Rincian Nilai")
            st.write(f"**TP: {tp}**, **TN: {tn}**, **FP: {fp}**, **FN: {fn}**")
            st.caption("TP: Sistem & Aktual Sesuai (Penerima). TN: Sistem & Aktual Sesuai (Bukan Penerima).")
        
        st.subheader("📋 Tabel Perbandingan Detail")
        st.dataframe(pd.DataFrame(comparison_list), use_container_width=True, hide_index=True)

    # 6. Definisikan Fungsi Logout (Halaman)
    def logout_page():
        logout()
        st.rerun()

    # --- DEFINISI HALAMAN ---
    pg_dash = st.Page(dashboard_page, title="Dashboard", icon="🏠")
    pg_seleksi = st.Page(seleksi_prioritas_page, title="Seleksi Prioritas", icon="🎯")
    pg_detail = st.Page(detail_perhitungan_page, title="Detail Perhitungan", icon="📈")
    pg_eval = st.Page(evaluasi_akurasi_page, title="Evaluasi Akurasi", icon="✅")
    pg_laporan = st.Page(laporan_riwayat_page, title="Laporan & Riwayat", icon="📂")
    pg_logout = st.Page(logout_page, title="Logout", icon="🚪")

    # Menu Evaluasi Akurasi (pg_eval) di-hide sementara sesuai permintaan
    pg = st.navigation([pg_dash, pg_seleksi, pg_detail, pg_laporan, pg_logout], position="hidden")

    # --- MEMBUAT SIDEBAR KUSTOM (Agar Judul di Atas) ---
    with st.sidebar:
        st.header("SPK BANTUAN")
        st.write("Sektor Perkebunan (AHP-TOPSIS)")
        st.divider()
        
        # Link Navigasi (Otomatis Highlight Halaman Aktif)
        st.page_link(pg_dash, label="Dashboard", icon="🏠")
        st.page_link(pg_seleksi, label="Seleksi Prioritas", icon="🎯")
        st.page_link(pg_detail, label="Detail Perhitungan", icon="📈")
        # st.page_link(pg_eval, label="Evaluasi Akurasi", icon="✅") # Di-hide sementara
        st.page_link(pg_laporan, label="Laporan & Riwayat", icon="📂")
        st.page_link(pg_logout, label="Logout", icon="🚪")

    # Jalankan Halaman Terpilih
    pg.run()
