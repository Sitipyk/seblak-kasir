# app.py
import streamlit as st
import sqlite3
import pandas as pd
import datetime
import qrcode
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
from collections import defaultdict
import hashlib
import csv
import os

# ----------------------------
# CONFIG & CONSTANTS
# ----------------------------
DB_PATH = "kasir_seblak.db"

# Ganti link berikut dengan link/ID pembayaran resmi merchantmu
LINK_OVO   = "https://contoh-link-ovo.com/pay"
LINK_GOPAY = "https://contoh-link-gopay.com/pay"
LINK_DANA  = "https://contoh-link-dana.com/pay"
LINK_QRIS  = "https://contoh-link-qris.com/pay"

st.set_page_config(page_title="Sistem Kasir Seblak", page_icon="🍜", layout="wide")

# ----------------------------
# HELPERS: DB, QR, AUTH
# ----------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Buat database & tabel bila belum ada, plus sample data & users."""
    conn = get_db_connection()
    cur = conn.cursor()
    # products table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS produk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT UNIQUE,
        tipe TEXT,
        harga INTEGER,
        stok INTEGER
    )
    """)
    # transaksi table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transaksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        waktu TEXT,
        menu TEXT,
        toppings TEXT,
        jumlah INTEGER,
        metode_pembayaran TEXT,
        total_harga INTEGER
    )
    """)
    # users table (simple)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        role TEXT
    )
    """)
    conn.commit()

    # insert sample products bila tabel kosong
    cur.execute("SELECT COUNT(*) as c FROM produk")
    if cur.fetchone()["c"] == 0:
        sample = [
            ("Seblak Original","menu",15000,50),
            ("Seblak Kerupuk","menu",12000,40),
            ("Seblak Ceker","menu",18000,30),
            ("Seblak Makaroni","menu",16000,35),
            ("Kerupuk","topping",3000,100),
            ("Ceker","topping",5000,50),
            ("Makaroni","topping",4000,60),
            ("Sosis","topping",5000,40),
            ("Telur","topping",4000,30),
        ]
        cur.executemany("INSERT INTO produk (nama, tipe, harga, stok) VALUES (?,?,?,?)", sample)
        conn.commit()

    # insert default users bila kosong (username: admin / kasir, password: admin123 / kasir123)
    cur.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        users = [
            ("admin", hash_pwd("admin123"), "admin"),
            ("kasir", hash_pwd("kasir123"), "kasir")
        ]
        cur.executemany("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)", users)
        conn.commit()

    conn.close()

def hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_pwd(password: str, pwd_hash: str) -> bool:
    return hash_pwd(password) == pwd_hash

def generate_qr_bytes(data: str):
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ----------------------------
# DB OPERATIONS
# ----------------------------
def fetch_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM produk ORDER BY tipe, nama")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_product_by_name(nama):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM produk WHERE nama = ?", (nama,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def add_product_db(nama, tipe, harga, stok):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO produk (nama, tipe, harga, stok) VALUES (?,?,?,?)", (nama, tipe, harga, stok))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()

def update_stock_db(nama, delta):
    """delta negatif untuk mengurangi, positif untuk tambah"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT stok FROM produk WHERE nama = ?", (nama,))
    r = cur.fetchone()
    if not r:
        conn.close()
        return False, "Produk tidak ditemukan"
    new_stok = r["stok"] + delta
    if new_stok < 0:
        conn.close()
        return False, "Stok tidak cukup"
    cur.execute("UPDATE produk SET stok = ? WHERE nama = ?", (new_stok, nama))
    conn.commit()
    conn.close()
    return True, None

def delete_product_db(nama):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM produk WHERE nama = ?", (nama,))
    conn.commit()
    conn.close()
    return True

def record_transaction_db(waktu, menu, toppings, jumlah, metode_pembayaran, total_harga):
    conn = get_db_connection()
    cur = conn.cursor()
    toppings_str = ",".join(toppings)
    cur.execute("""
        INSERT INTO transaksi (waktu, menu, toppings, jumlah, metode_pembayaran, total_harga)
        VALUES (?,?,?,?,?,?)
    """, (waktu, menu, toppings_str, jumlah, metode_pembayaran, total_harga))
    conn.commit()
    conn.close()

def fetch_transactions(month_prefix=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if month_prefix:
        cur.execute("SELECT * FROM transaksi WHERE waktu LIKE ? ORDER BY waktu DESC", (f"{month_prefix}%",))
    else:
        cur.execute("SELECT * FROM transaksi ORDER BY waktu DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------------------
# BUSINESS LOGIC
# ----------------------------
def safe_process_transaction(menu, toppings, jumlah, metode_pembayaran, total_harga):
    """
    Lakukan cek stok dulu semua, jika semua cukup -> lakukan pengurangan stok dalam satu transaksi DB.
    Jika ada yang kurang, kembalikan False tanpa mengubah DB.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # cek stok menu
        cur.execute("SELECT stok FROM produk WHERE nama = ?", (menu,))
        r = cur.fetchone()
        if not r:
            return False, f"Menu {menu} tidak ditemukan."
        if r["stok"] < jumlah:
            return False, f"Stok {menu} tidak mencukupi."

        # cek topping
        for t in toppings:
            cur.execute("SELECT stok FROM produk WHERE nama = ?", (t,))
            rr = cur.fetchone()
            if not rr:
                return False, f"Topping {t} tidak ditemukan."
            if rr["stok"] < jumlah:
                return False, f"Stok {t} tidak mencukupi."

        # semua cukup -> mulai transaksi (manual)
        waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # kurangi stok menu
        cur.execute("UPDATE produk SET stok = stok - ? WHERE nama = ?", (jumlah, menu))
        # kurangi stok topping
        for t in toppings:
            cur.execute("UPDATE produk SET stok = stok - ? WHERE nama = ?", (jumlah, t))
        # catat transaksi
        toppings_str = ",".join(toppings)
        cur.execute("""
            INSERT INTO transaksi (waktu, menu, toppings, jumlah, metode_pembayaran, total_harga)
            VALUES (?,?,?,?,?,?)
        """, (waktu, menu, toppings_str, jumlah, metode_pembayaran, total_harga))
        conn.commit()
        return True, waktu
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

# ----------------------------
# AUTH
# ----------------------------
def attempt_login(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False, "User tidak ditemukan"
    if verify_pwd(password, row["password_hash"]):
        return True, row["role"]
    return False, "Password salah"

# ----------------------------
# INIT
# ----------------------------
if "initialized" not in st.session_state:
    # ensure DB and sample data exist
    if not os.path.exists(DB_PATH):
        # create DB file
        open(DB_PATH, "w").close()
    init_db()
    st.session_state["initialized"] = True

# ----------------------------
# LOGIN UI
# ----------------------------
st.title("🍜 Sistem Kasir Seblak")
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

with st.sidebar:
    st.header("Akun")
    if st.session_state.user is None:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", key="login_pwd", type="password")
        if st.button("Login"):
            ok, info = attempt_login(username.strip(), password)
            if ok:
                st.session_state.user = username.strip()
                st.session_state.role = info
                st.success(f"Login berhasil sebagai {st.session_state.user} ({st.session_state.role})")
                st.experimental_rerun()
            else:
                st.error(info)
        st.info("Default: admin/admin123 atau kasir/kasir123 (ubah di DB saat deploy)")
    else:
        st.write(f"**{st.session_state.user}** ({st.session_state.role})")
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.role = None
            st.experimental_rerun()

# require login
if st.session_state.user is None:
    st.warning("Silakan login terlebih dahulu (sidebar).")
    st.stop()

# ----------------------------
# MAIN TABS
# ----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Kasir", "Stok", "Laporan Penjualan", "Statistik", "Pengaturan"])

# ----------------------------
# TAB 1: KASIR
# ----------------------------
with tab1:
    st.header("Transaksi Kasir")
    produk_list = fetch_products()
    menu_options = [p["nama"] for p in produk_list if p["tipe"] == "menu"]
    topping_options = [p["nama"] for p in produk_list if p["tipe"] == "topping"]

    if not menu_options:
        st.info("Tidak ada menu. Tambah produk di tab Pengaturan.")
    else:
        selected_menu = st.selectbox("Pilih Menu Seblak", menu_options)
        if selected_menu:
            prod = get_product_by_name(selected_menu)
            st.write(f"Harga: Rp {prod['harga']:,} | Stok: {prod['stok']}")

        selected_toppings = st.multiselect("Pilih Topping", topping_options)
        if selected_toppings:
            st.write("Harga Topping:")
            for t in selected_toppings:
                p = get_product_by_name(t)
                st.write(f"- {t}: Rp {p['harga']:,} | Stok: {p['stok']}")

        jumlah = st.number_input("Jumlah", min_value=1, max_value=100, value=1)

        # Hitung total (cek produk ada)
        if selected_menu:
            harga_menu = get_product_by_name(selected_menu)["harga"]
            harga_toppings = sum([get_product_by_name(t)["harga"] for t in selected_toppings]) if selected_toppings else 0
            total_harga = (harga_menu + harga_toppings) * jumlah
            st.subheader(f"Total Harga: Rp {total_harga:,}")

        metode_pembayaran = st.radio("Metode Pembayaran",
            ["Tunai", "E-Wallet (OVO)", "E-Wallet (Gopay)", "E-Wallet (Dana)", "QRIS"]
        )

        # Tampilkan QR jika e-wallet
        qr_link = None
        if metode_pembayaran.startswith("E-Wallet") or metode_pembayaran == "QRIS":
            if metode_pembayaran == "E-Wallet (OVO)":
                qr_link = LINK_OVO
            elif metode_pembayaran == "E-Wallet (Gopay)":
                qr_link = LINK_GOPAY
            elif metode_pembayaran == "E-Wallet (Dana)":
                qr_link = LINK_DANA
            else:
                qr_link = LINK_QRIS
            st.subheader("Scan QR untuk Bayar")
            st.image(generate_qr_bytes(qr_link), width=200)

        if st.button("Proses Transaksi"):
            # validasi cepat
            if not selected_menu:
                st.error("Pilih menu terlebih dahulu.")
            else:
                ok, info = safe_process_transaction(selected_menu, selected_toppings, jumlah, metode_pembayaran, total_harga)
                if ok:
                    st.success("Transaksi berhasil diproses!")
                    st.subheader("Struk Pembayaran")
                    st.write(f"Menu: {selected_menu}")
                    st.write(f"Topping: {', '.join(selected_toppings) if selected_toppings else 'Tidak ada'}")
                    st.write(f"Jumlah: {jumlah}")
                    st.write(f"Total: Rp {total_harga:,}")
                    st.write(f"Metode Pembayaran: {metode_pembayaran}")
                    st.write(f"Waktu: {info}")  # waktu dikembalikan
                    if qr_link:
                        st.image(generate_qr_bytes(qr_link), width=200)
                else:
                    st.error(f"Transaksi gagal: {info}")

# ----------------------------
# TAB 2: STOK
# ----------------------------
with tab2:
    st.header("Manajemen Stok")
    produk_df = pd.DataFrame(fetch_products())
    if produk_df.empty:
        st.info("Belum ada produk.")
    else:
        produk_df_display = produk_df.copy()
        produk_df_display["Status"] = produk_df_display["stok"].apply(lambda s: "Hampir Habis" if s < 10 else ("Cukup" if s < 20 else "Banyak"))
        st.dataframe(produk_df_display[["nama","tipe","harga","stok","Status"]].rename(columns={
            "nama":"Nama","tipe":"Tipe","harga":"Harga","stok":"Stok"
        }), use_container_width=True)

    st.subheader("Tambah / Update Stok")
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        produk_pilih = st.selectbox("Pilih Produk", [p["nama"] for p in fetch_products()])
    with col2:
        jumlah_tambah = st.number_input("Jumlah yang Ditambahkan", min_value=1, max_value=1000, value=1)
    with col3:
        if st.button("Tambah Stok"):
            ok, msg = update_stock_db(produk_pilih, jumlah_tambah)
            if ok:
                st.success(f"Stok {produk_pilih} berhasil ditambah.")
            else:
                st.error(msg)

    st.subheader("Kurangi Stok (misal koreksi)")
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        produk_kurang = st.selectbox("Pilih Produk (kurangi)", [p["nama"] for p in fetch_products()], key="kurang_sel")
    with col2:
        jumlah_kurang = st.number_input("Jumlah yang Dikurangi", min_value=1, max_value=1000, value=1, key="kurang_num")
    with col3:
        if st.button("Kurangi Stok"):
            ok, msg = update_stock_db(produk_kurang, -jumlah_kurang)
            if ok:
                st.success(f"Stok {produk_kurang} berhasil dikurangi.")
            else:
                st.error(msg)

# ----------------------------
# TAB 3: LAPORAN PENJUALAN
# ----------------------------
with tab3:
    st.header("Laporan Penjualan")
    # kumpulkan semua transaksi
    semua_trx = fetch_transactions()
    if not semua_trx:
        st.info("Belum ada transaksi.")
    else:
        # Buat daftar bulan unik: YYYY-MM
        semua_bulan = sorted(list({t["waktu"][:7] for t in semua_trx}), reverse=True)
        pilihan_bulan = st.selectbox("Pilih Bulan", ["Semua"] + semua_bulan)
        if pilihan_bulan == "Semua":
            df = pd.DataFrame(semua_trx)
        else:
            df = pd.DataFrame(fetch_transactions(pilihan_bulan))

        if not df.empty:
            # perbaikan tampilan toppings
            if "toppings" in df.columns:
                df["toppings"] = df["toppings"].fillna("").apply(lambda s: s if s else "Tidak ada")
            st.dataframe(df, use_container_width=True)

            # Metrics
            total_terjual = int(df["jumlah"].sum())
            total_pendapatan = int(df["total_harga"].sum())
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Terjual", f"{total_terjual} porsi")
            with col2:
                st.metric("Total Pendapatan", f"Rp {total_pendapatan:,}")

            # Export CSV
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV Laporan", csv_bytes, file_name=f"laporan_{pilihan_bulan if pilihan_bulan!='Semua' else 'all'}.csv", mime="text/csv")
        else:
            st.info("Tidak ada transaksi di periode ini.")

# ----------------------------
# TAB 4: STATISTIK
# ----------------------------
with tab4:
    st.header("Statistik Penjualan")
    trx = fetch_transactions()
    if not trx:
        st.info("Belum ada data statistik.")
    else:
        # hitung produk terlaris: menu + toppings (toppings dihitung per porsi)
        counts = defaultdict(int)
        for t in trx:
            counts[t["menu"]] += t["jumlah"]
            if t["toppings"]:
                for top in t["toppings"].split(","):
                    if top:
                        counts[top] += t["jumlah"]
        df_stats = pd.DataFrame([{"Produk":k, "Terjual":v} for k,v in counts.items()]).sort_values("Terjual", ascending=False)
        st.subheader("Produk Terlaris")
        st.dataframe(df_stats, use_container_width=True)
        if not df_stats.empty:
            fig, ax = plt.subplots()
            ax.bar(df_stats["Produk"].head(10), df_stats["Terjual"].head(10))
            ax.set_title("10 Produk Terlaris")
            ax.set_ylabel("Jumlah Terjual")
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)

# ----------------------------
# TAB 5: PENGATURAN (admin only)
# ----------------------------
with tab5:
    st.header("Pengaturan Produk")
    if st.session_state.role != "admin":
        st.info("Hanya admin yang dapat mengubah pengaturan produk.")
    else:
        st.subheader("Tambah Produk Baru")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            new_nama = st.text_input("Nama Produk", key="new_nama")
        with col2:
            new_tipe = st.selectbox("Tipe Produk", ["menu", "topping"], key="new_tipe")
        with col3:
            new_harga = st.number_input("Harga", min_value=1000, max_value=1000000, value=10000, step=500, key="new_harga")
        with col4:
            new_stok = st.number_input("Stok Awal", min_value=0, max_value=100000, value=10, key="new_stok")

        if st.button("Tambah Produk Baru"):
            if not new_nama.strip():
                st.error("Nama produk tidak boleh kosong.")
            elif new_harga <= 0:
                st.error("Harga harus lebih dari 0.")
            elif new_stok < 0:
                st.error("Stok tidak boleh negatif.")
            else:
                ok, err = add_product_db(new_nama.strip(), new_tipe, int(new_harga), int(new_stok))
                if ok:
                    st.success(f"Produk {new_nama} berhasil ditambahkan.")
                else:
                    st.error(f"Gagal tambah produk: {err}")

        st.subheader("Hapus Produk")
        nama_hapus = st.selectbox("Pilih Produk untuk Dihapus", [p["nama"] for p in fetch_products()], key="del_prod")
        if st.button("Hapus Produk"):
            delete_product_db(nama_hapus)
            st.success(f"Produk {nama_hapus} berhasil dihapus.")

        st.subheader("Manage Users")
        st.write("Daftar user saat ini:")
        users = fetch_users()
        if users:
            st.table(pd.DataFrame(users))
        st.info("Untuk menambah/ubah password user, edit DB SQLite atau implement UI tambahan.")

# ----------------------------
# FOOTER
# ----------------------------
st.markdown("---")
st.markdown("Sistem Kasir Seblak © 2025 — Streamlit + SQLite + QR Code")

