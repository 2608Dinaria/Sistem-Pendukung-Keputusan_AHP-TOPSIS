import hashlib
import streamlit as st
from database import get_db_connection

def hash_password(password):
    """Meng-hash password menggunakan algoritma SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    """Memvalidasi username dan password dari database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hashed = hash_password(password)
    
    cursor.execute("""
    SELECT * FROM tb_admin 
    WHERE username = ? AND password = ?
    """, (username, password_hashed))
    row = cursor.fetchone()
    conn.close()
    
    return row is not None

def init_session():
    """Inisialisasi session state untuk status login admin."""
    # Cek query parameters untuk melacak status login setelah refresh
    if "logged_in" in st.query_params and st.query_params["logged_in"] == "true":
        st.session_state.logged_in = True
        st.session_state.username = st.query_params.get("username", "admin")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None

def login(username, password):
    """Proses login admin."""
    if check_login(username, password):
        st.session_state.logged_in = True
        st.session_state.username = username
        # Simpan status ke query params agar persisten saat refresh
        st.query_params["logged_in"] = "true"
        st.query_params["username"] = username
        return True
    return False

def logout():
    """Proses logout admin."""
    st.session_state.logged_in = False
    st.session_state.username = None
    # Hapus status di query params
    st.query_params.clear()
    # Reset page
    if 'current_page' in st.session_state:
        st.session_state.current_page = "Dashboard"
