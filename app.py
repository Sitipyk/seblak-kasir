import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import matplotlib.pyplot as plt
from collections import defaultdict

# Konfigurasi halaman
st.set_page_config(
    page_title="Sistem Kasir Seblak",
    page_icon="🍜",
    layout="wide"
)

# Fungsi untuk inisialisasi data
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

# Fungsi untuk menambah produk
def tambah_produk(nama, harga, stok, tipe):
    st.session_state.produk[nama] = {'harga': harga, 'stok': stok, 'tipe': tipe}

# Fungsi untuk update stok
def update_stok(nama, jumlah):
    if nama in st.session_state.produk:
        st.session_state.produk[nama]['stok'] -= jumlah
        return True
    return False

# Fungsi untuk proses transaksi
def proses_transaksi(menu, toppings, jumlah, metode_pembayaran, total_harga):
    # Update stok menu
    if not update_stok(menu, jumlah):
        st.error(f"Stok {menu} tidak mencukupi!")
        return False
    
    # Update stok topping
    for topping in toppings:
        if not update_stok(topping, jumlah):
            st.error(f"Stok {topping} tidak mencukupi!")
            return False
    
    # Catat transaksi
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
    
    # Update laporan
    bulan = waktu[:7]  # Format YYYY-MM
    st.session_state.laporan[bulan]['terjual'] += jumlah
    st.session_state.laporan[bulan]['pendapatan'] += total_harga
    
    # Update statistik produk
    st.session_state.statistik[menu]['terjual'] += jumlah
    for topping in toppings:
        st.session_state.statistik[topping]['terjual'] += jumlah
    
    return True

# Fungsi untuk menghitung total harga
def hitung_total(menu, toppings, jumlah):
    harga_menu = st.session_state.produk[menu]['harga']
    harga_toppings = sum([st.session_state.produk[t]['harga'] for t in toppings])
    return (harga_menu + harga_toppings) * jumlah

# Inisialisasi data
init_data()

# Tampilan antarmuka
st.title("🍜 Sistem Kasir Seblak")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Kasir", "Stok", "Laporan Penjualan", "Statistik", "Pengaturan"])

with tab1:  # Tab Kasir
    st.header("Transaksi Kasir")
    
    # Pilih menu
    menu_options = [p for p in st.session_state.produk if st.session_state.produk[p]['tipe'] == 'menu']
    selected_menu = st.selectbox("Pilih Menu Seblak", menu_options)
    
    # Tampilkan harga menu
    if selected_menu:
        harga_menu = st.session_state.produk[selected_menu]['harga']
        stok_menu = st.session_state.produk[selected_menu]['stok']
        st.write(f"Harga: Rp {harga_menu:,} | Stok: {stok_menu}")
    
    # Pilih topping
    topping_options = [p for p in st.session_state.produk if st.session_state.produk[p]['tipe'] == 'topping']
    selected_toppings = st.multiselect("Pilih Topping", topping_options)
    
    # Tampilkan harga topping
    if selected_toppings:
        st.write("Harga Topping:")
        for topping in selected_toppings:
            harga_topping = st.session_state.produk[topping]['harga']
            stok_topping = st.session_state.produk[topping]['stok']
            st.write(f"- {topping}: Rp {harga_topping:,} | Stok: {stok_topping}")
    
    # Input jumlah
    jumlah = st.number_input("Jumlah", min_value=1, max_value=50, value=1)
    
    # Hitung total harga
    if selected_menu:
        total_harga = hitung_total(selected_menu, selected_toppings, jumlah)
        st.subheader(f"Total Harga: Rp {total_harga:,}")
    
    # Metode pembayaran
    metode_pembayaran = st.radio("Metode Pembayaran", ["Tunai", "E-Wallet (OVO)", "E-Wallet (Gopay)", "E-Wallet (Dana)"])
    
    # Tombol proses transaksi
    if st.button("Proses Transaksi"):
        if selected_menu:
            if proses_transaksi(selected_menu, selected_toppings, jumlah, metode_pembayaran, total_harga):
                st.success("Transaksi berhasil diproses!")
                
                # Tampilkan struk
                st.subheader("Struk Pembayaran")
                st.write(f"Menu: {selected_menu}")
                st.write(f"Topping: {', '.join(selected_toppings) if selected_toppings else 'Tidak ada'}")
                st.write(f"Jumlah: {jumlah}")
                st.write(f"Total: Rp {total_harga:,}")
                st.write(f"Metode Pembayaran: {metode_pembayaran}")
                st.write(f"Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.error("Transaksi gagal. Stok tidak mencukupi.")
        else:
            st.error("Silakan pilih menu terlebih dahulu.")

with tab2:  # Tab Stok
    st.header("Manajemen Stok")
    
    # Tampilkan stok produk
    st.subheader("Daftar Stok Produk")
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
    
    # Filter produk yang hampir habis
    st.subheader("Produk yang Hampir Habis")
    df_hampir_habis = df_stok[df_stok['Status'] == 'Hampir Habis']
    if not df_hampir_habis.empty:
        st.dataframe(df_hampir_habis[['Nama', 'Stok']], use_container_width=True)
    else:
        st.info("Tidak ada produk yang hampir habis.")
    
    # Form untuk menambah stok
    st.subheader("Tambah/Update Stok")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        produk_tambah = st.selectbox("Pilih Produk", list(st.session_state.produk.keys()))
    
    with col2:
        jumlah_tambah = st.number_input("Jumlah yang Ditambahkan", min_value=1, max_value=100, value=1)
    
    with col3:
        st.write("")  # Untuk alignment
        if st.button("Tambah Stok"):
            st.session_state.produk[produk_tambah]['stok'] += jumlah_tambah
            st.success(f"Stok {produk_tambah} berhasil ditambah menjadi {st.session_state.produk[produk_tambah]['stok']}")

with tab3:  # Tab Laporan Penjualan
    st.header("Laporan Penjualan")
    
    # Pilih bulan untuk laporan
    bulan_options = sorted(list(st.session_state.laporan.keys()), reverse=True)
    if not bulan_options:
        st.info("Belum ada data penjualan.")
    else:
        selected_bulan = st.selectbox("Pilih Bulan", bulan_options)
        
        if selected_bulan:
            laporan = st.session_state.laporan[selected_bulan]
            st.subheader(f"Laporan Penjualan Bulan {selected_bulan}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Terjual", f"{laporan['terjual']} porsi")
            with col2:
                st.metric("Total Pendapatan", f"Rp {laporan['pendapatan']:,}")
            
            # Tampilkan transaksi per bulan
            st.subheader("Detail Transaksi")
            transaksi_bulan = [t for t in st.session_state.transaksi if t['waktu'].startswith(selected_bulan)]
            
            if transaksi_bulan:
                df_transaksi = pd.DataFrame(transaksi_bulan)
                st.dataframe(df_transaksi, use_container_width=True)
            else:
                st.info("Tidak ada transaksi pada bulan yang dipilih.")

with tab4:  # Tab Statistik
    st.header("Statistik Penjualan")
    
    if not st.session_state.statistik:
        st.info("Belum ada data statistik.")
    else:
        # Produk terlaris
        st.subheader("Produk Terlaris")
        produk_terlaris = []
        for produk, info in st.session_state.statistik.items():
            produk_terlaris.append({
                'Produk': produk,
                'Terjual': info['terjual']
            })
        
        df_terlaris = pd.DataFrame(produk_terlaris).sort_values('Terjual', ascending=False)
        st.dataframe(df_terlaris, use_container_width=True)
        
        # Grafik produk terlaris
        if not df_terlaris.empty:
            fig, ax = plt.subplots()
            ax.bar(df_terlaris['Produk'].head(10), df_terlaris['Terjual'].head(10))
            ax.set_title('10 Produk Terlaris')
            ax.set_ylabel('Jumlah Terjual')
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)

with tab5:  # Tab Pengaturan
    st.header("Pengaturan Produk")
    
    # Tambah produk baru
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
    
    # Hapus produk
    st.subheader("Hapus Produk")
    hapus_produk = st.selectbox("Pilih Produk untuk Dihapus", list(st.session_state.produk.keys()))
    
    if st.button("Hapus Produk"):
        if hapus_produk:
            del st.session_state.produk[hapus_produk]
            st.success(f"Produk {hapus_produk} berhasil dihapus!")

# Footer
st.markdown("---")
st.markdown("Sistem Kasir Seblak © 2023 - Dibuat dengan Streamlit")
