import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import matplotlib.pyplot as plt
from collections import defaultdict
import qrcode
from io import BytesIO
from PIL import Image

# ----------------------------
# KONFIGURASI & LINK QR
# ----------------------------
# Ganti link berikut dengan link/ID pembayaran asli milikmu
LINK_OVO   = "https://contoh-link-ovo.com/pay"
LINK_GOPAY = "https://contoh-link-gopay.com/pay"
LINK_DANA  = "https://contoh-link-dana.com/pay"
LINK_QRIS  = "https://contoh-link-qris.com/pay"

st.set_page_config(
    page_title="Sistem Kasir Seblak",
    page_icon="🍜",
    layout="wide"
)

# ----------------------------
# FUNGSI QR
# ----------------------------
def generate_qr(data: str):
    """Generate QR code dan kembalikan bytes PNG."""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ----------------------------
# INISIALISASI DATA
# ----------------------------
def init_data():
    if 'produk' not in st.session_state:
        st.session_state.produk = {
            'Seblak Original': {'harga': 15000, 'stok': 50, 'tipe': 'menu'},
            'Seblak Kerupuk': {'harga': 12000, 'stok': 40, 'tipe': 'menu'},
            'Seblak Ceker': {'harga': 18000, 'stok': 30, 'tipe': 'menu'},
            'Seblak Makaroni': {'harga': 16000, 'stok': 35, 'tipe': 'menu'},
            'Kerupuk': {'harga': 3000, 'stok': 100, 'tipe': 'topping'},
            'Ceker': {'harga': 5000, 'stok': 50, 'tipe': 'topping'},
            'Makaroni': {'harga': 4000, 'stok': 60, 'tipe': 'topping'},
            'Sosis': {'harga': 5000, 'stok': 40, 'tipe': 'topping'},
            'Telur': {'harga': 4000, 'stok': 30, 'tipe': 'topping'}
        }
    if 'transaksi' not in st.session_state:
        st.session_state.transaksi = []
    if 'laporan' not in st.session_state:
        st.session_state.laporan = defaultdict(lambda: {'terjual': 0, 'pendapatan': 0})
    if 'statistik' not in st.session_state:
        st.session_state.statistik = defaultdict(lambda: {'terjual': 0})

def tambah_produk(nama, harga, stok, tipe):
    st.session_state.produk[nama] = {'harga': harga, 'stok': stok, 'tipe': tipe}

def update_stok(nama, jumlah):
    if nama in st.session_state.produk:
        st.session_state.produk[nama]['stok'] -= jumlah
        return True
    return False

def proses_transaksi(menu, toppings, jumlah, metode_pembayaran, total_harga):
    if not update_stok(menu, jumlah):
        st.error(f"Stok {menu} tidak mencukupi!")
        return False
    for topping in toppings:
        if not update_stok(topping, jumlah):
            st.error(f"Stok {topping} tidak mencukupi!")
            return False
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transaksi = {
        'waktu': waktu,
        'menu': menu,
        'toppings': toppings,
        'jumlah': jumlah,
        'metode_pembayaran': metode_pembayaran,
        'total_harga': total_harga
    }
    st.session_state.transaksi.append(transaksi)
    bulan = waktu[:7]
    st.session_state.laporan[bulan]['terjual'] += jumlah
    st.session_state.laporan[bulan]['pendapatan'] += total_harga
    st.session_state.statistik[menu]['terjual'] += jumlah
    for topping in toppings:
        st.session_state.statistik[topping]['terjual'] += jumlah
    return True

def hitung_total(menu, toppings, jumlah):
    harga_menu = st.session_state.produk[menu]['harga']
    harga_toppings = sum([st.session_state.produk[t]['harga'] for t in toppings])
    return (harga_menu + harga_toppings) * jumlah

# ----------------------------
# MULAI APP
# ----------------------------
init_data()
st.title("🍜 Sistem Kasir Seblak")
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Kasir", "Stok", "Laporan Penjualan", "Statistik", "Pengaturan"]
)

# ------------------------------------------------------------------
# TAB 1 : KASIR
# ------------------------------------------------------------------
with tab1:
    st.header("Transaksi Kasir")
    menu_options = [p for p in st.session_state.produk if st.session_state.produk[p]['tipe'] == 'menu']
    selected_menu = st.selectbox("Pilih Menu Seblak", menu_options)

    if selected_menu:
        harga_menu = st.session_state.produk[selected_menu]['harga']
        stok_menu = st.session_state.produk[selected_menu]['stok']
        st.write(f"Harga: Rp {harga_menu:,} | Stok: {stok_menu}")

    topping_options = [p for p in st.session_state.produk if st.session_state.produk[p]['tipe'] == 'topping']
    selected_toppings = st.multiselect("Pilih Topping", topping_options)

    if selected_toppings:
        st.write("Harga Topping:")
        for topping in selected_toppings:
            st.write(f"- {topping}: Rp {st.session_state.produk[topping]['harga']:,} | Stok: {st.session_state.produk[topping]['stok']}")

    jumlah = st.number_input("Jumlah", min_value=1, max_value=50, value=1)

    if selected_menu:
        total_harga = hitung_total(selected_menu, selected_toppings, jumlah)
        st.subheader(f"Total Harga: Rp {total_harga:,}")

    metode_pembayaran = st.radio(
        "Metode Pembayaran",
        ["Tunai", "E-Wallet (OVO)", "E-Wallet (Gopay)", "E-Wallet (Dana)", "QRIS"]
    )

    # === Tampilkan QR ketika e-wallet dipilih ===
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
        st.image(generate_qr(qr_link), width=200)

    if st.button("Proses Transaksi"):
        if selected_menu:
            if proses_transaksi(selected_menu, selected_toppings, jumlah, metode_pembayaran, total_harga):
                st.success("Transaksi berhasil diproses!")
                st.subheader("Struk Pembayaran")
                st.write(f"Menu: {selected_menu}")
                st.write(f"Topping: {', '.join(selected_toppings) if selected_toppings else 'Tidak ada'}")
                st.write(f"Jumlah: {jumlah}")
                st.write(f"Total: Rp {total_harga:,}")
                st.write(f"Metode Pembayaran: {metode_pembayaran}")
                st.write(f"Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                # tampilkan ulang QR di struk bila e-wallet
                if metode_pembayaran != "Tunai":
                    st.image(generate_qr(qr_link), width=200)
            else:
                st.error("Transaksi gagal. Stok tidak mencukupi.")
        else:
            st.error("Silakan pilih menu terlebih dahulu.")

# ------------------------------------------------------------------
# TAB 2 : STOK
# ------------------------------------------------------------------
with tab2:
    st.header("Manajemen Stok")
    produk_data = []
    for produk, info in st.session_state.produk.items():
        produk_data.append({
            'Nama': produk,
            'Tipe': info['tipe'],
            'Harga': info['harga'],
            'Stok': info['stok'],
            'Status': 'Hampir Habis' if info['stok'] < 10 else 'Cukup' if info['stok'] < 20 else 'Banyak'
        })
    df_stok = pd.DataFrame(produk_data)
    st.dataframe(df_stok, use_container_width=True)

    st.subheader("Produk yang Hampir Habis")
    df_habis = df_stok[df_stok['Status'] == 'Hampir Habis']
    if not df_habis.empty:
        st.dataframe(df_habis[['Nama', 'Stok']], use_container_width=True)
    else:
        st.info("Tidak ada produk yang hampir habis.")

    st.subheader("Tambah/Update Stok")
    col1, col2, col3 = st.columns(3)
    with col1:
        produk_tambah = st.selectbox("Pilih Produk", list(st.session_state.produk.keys()))
    with col2:
        jumlah_tambah = st.number_input("Jumlah yang Ditambahkan", min_value=1, max_value=100, value=1)
    with col3:
        st.write("")
        if st.button("Tambah Stok"):
            st.session_state.produk[produk_tambah]['stok'] += jumlah_tambah
            st.success(f"Stok {produk_tambah} berhasil ditambah menjadi {st.session_state.produk[produk_tambah]['stok']}")

# ------------------------------------------------------------------
# TAB 3 : LAPORAN
# ------------------------------------------------------------------
with tab3:
    st.header("Laporan Penjualan")
    bulan_options = sorted(list(st.session_state.laporan.keys()), reverse=True)
    if not bulan_options:
        st.info("Belum ada data penjualan.")
    else:
        selected_bulan = st.selectbox("Pilih Bulan", bulan_options)
        if selected_bulan:
            laporan = st.session_state.laporan[selected_bulan]
            st.metric("Total Terjual", f"{laporan['terjual']} porsi")
            st.metric("Total Pendapatan", f"Rp {laporan['pendapatan']:,}")
            transaksi_bulan = [t for t in st.session_state.transaksi if t['waktu'].startswith(selected_bulan)]
            if transaksi_bulan:
                st.dataframe(pd.DataFrame(transaksi_bulan), use_container_width=True)
            else:
                st.info("Tidak ada transaksi pada bulan ini.")

# ------------------------------------------------------------------
# TAB 4 : STATISTIK
# ------------------------------------------------------------------
with tab4:
    st.header("Statistik Penjualan")
    if not st.session_state.statistik:
        st.info("Belum ada data statistik.")
    else:
        produk_terlaris = [{'Produk': p, 'Terjual': i['terjual']} for p, i in st.session_state.statistik.items()]
        df_terlaris = pd.DataFrame(produk_terlaris).sort_values('Terjual', ascending=False)
        st.dataframe(df_terlaris, use_container_width=True)
        if not df_terlaris.empty:
            fig, ax = plt.subplots()
            ax.bar(df_terlaris['Produk'].head(10), df_terlaris['Terjual'].head(10))
            ax.set_title('10 Produk Terlaris')
            ax.set_ylabel('Jumlah Terjual')
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)

# ------------------------------------------------------------------
# TAB 5 : PENGATURAN
# ------------------------------------------------------------------
with tab5:
    st.header("Pengaturan Produk")
    st.subheader("Tambah Produk Baru")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        new_nama = st.text_input("Nama Produk")
    with col2:
        new_harga = st.number_input("Harga", min_value=1000, max_value=100000, value=10000, step=1000)
    with col3:
        new_stok = st.number_input("Stok Awal", min_value=1, max_value=100, value=10)
    with col4:
        new_tipe = st.selectbox("Tipe Produk", ["menu", "topping"])
    if st.button("Tambah Produk Baru"):
        if new_nama and new_nama not in st.session_state.produk:
            tambah_produk(new_nama, new_harga, new_stok, new_tipe)
            st.success(f"Produk {new_nama} berhasil ditambahkan!")
        else:
            st.error("Nama produk sudah ada atau tidak valid.")

    st.subheader("Hapus Produk")
    hapus_produk = st.selectbox("Pilih Produk untuk Dihapus", list(st.session_state.produk.keys()))
    if st.button("Hapus Produk"):
        if hapus_produk:
            del st.session_state.produk[hapus_produk]
            st.success(f"Produk {hapus_produk} berhasil dihapus!")

# ------------------------------------------------------------------
st.markdown("---")
st.markdown("Sistem Kasir Seblak © 2025 - Dibuat dengan Streamlit + QR Code")
