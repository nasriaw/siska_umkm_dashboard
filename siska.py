import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Konfigurasi halaman
st.set_page_config(
    page_title="SISKA - Sistem Informasi Sederhana Keuangan & Akuntansi",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi database dengan nilai default
def init_db():
    conn = sqlite3.connect('siska.db')
    cursor = conn.cursor()
    
    # Hapus tabel jika ada untuk memastikan struktur yang benar
    cursor.execute("DROP TABLE IF EXISTS transaksi")
    cursor.execute("DROP TABLE IF EXISTS akun")
    cursor.execute("DROP TABLE IF EXISTS kategori")
    cursor.execute("DROP TABLE IF EXISTS aset")
    cursor.execute("DROP TABLE IF EXISTS pajak")
    cursor.execute("DROP TABLE IF EXISTS users")
    
    # Tabel akun
    cursor.execute('''
        CREATE TABLE akun (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_akun TEXT UNIQUE,
            nama_akun TEXT,
            jenis_akun TEXT,
            sub_akun TEXT,
            saldo_awal REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel transaksi - dengan kolom akun_id
    cursor.execute('''
        CREATE TABLE transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal DATE,
            keterangan TEXT,
            akun_id INTEGER,
            debit REAL,
            kredit REAL,
            bukti_transaksi TEXT,
            approved BOOLEAN DEFAULT FALSE,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (akun_id) REFERENCES akun (id)
        )
    ''')
    
    # Tabel kategori
    cursor.execute('''
        CREATE TABLE kategori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_kategori TEXT UNIQUE,
            jenis_kategori TEXT,
            deskripsi TEXT
        )
    ''')
    
    # Tabel aset
    cursor.execute('''
        CREATE TABLE aset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_aset TEXT,
            jenis_aset TEXT,
            nilai_aset REAL,
            tanggal_pembelian DATE,
            umur_ekonomis INTEGER,
            sisa_umur INTEGER,
            depresiasi REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel pajak
    cursor.execute('''
        CREATE TABLE pajak (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jenis_pajak TEXT,
            tarif REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel users
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert data default
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                   ("admin", "admin123", "admin"))
    
    # Insert akun default dengan nilai
    akun_default = [
        ('1.1', 'Kas', 'Aset Lancar', '', 5000000),
        ('1.2', 'Bank BCA', 'Aset Lancar', '', 10000000),
        ('1.3', 'Bank Mandiri', 'Aset Lancar', '', 7500000),
        ('2.1', 'Piutang Usaha', 'Aset Lancar', '', 3000000),
        ('3.1', 'Persediaan Barang', 'Aset Lancar', '', 8500000),
        ('4.1', 'Peralatan Kantor', 'Aset Tetap', '', 15000000),
        ('4.2', 'Kendaraan', 'Aset Tetap', '', 50000000),
        ('5.1', 'Utang Usaha', 'Kewajiban', '', 2000000),
        ('5.2', 'Utang Gaji', 'Kewajiban', '', 1500000),
        ('6.1', 'Modal Awal', 'Ekuitas', '', 100000000),
        ('7.1', 'Penjualan Produk', 'Pendapatan', '', 50000000),
        ('8.1', 'Biaya Operasional', 'Biaya', '', 25000000),
        ('8.2', 'Biaya Gaji', 'Biaya', '', 15000000),
        ('8.3', 'Biaya Sewa', 'Biaya', '', 12000000),
    ]
    cursor.executemany('INSERT INTO akun (kode_akun, nama_akun, jenis_akun, sub_akun, saldo_awal) VALUES (?, ?, ?, ?, ?)', akun_default)
    
    # Insert kategori default
    kategori_default = [
        ('Makanan', 'Pendapatan', 'Pendapatan dari penjualan makanan'),
        ('Minuman', 'Pendapatan', 'Pendapatan dari penjualan minuman'),
        ('Elektronik', 'Pendapatan', 'Pendapatan dari penjualan elektronik'),
        ('Gaji', 'Biaya', 'Pengeluaran untuk gaji karyawan'),
        ('Sewa', 'Biaya', 'Pengeluaran untuk sewa tempat usaha'),
        ('Listrik', 'Biaya', 'Pengeluaran untuk tagihan listrik'),
        ('Air', 'Biaya', 'Pengeluaran untuk tagihan air'),
        ('Marketing', 'Biaya', 'Biaya pemasaran dan promosi'),
        ('Transport', 'Biaya', 'Biaya transportasi operasional'),
    ]
    cursor.executemany('INSERT INTO kategori (nama_kategori, jenis_kategori, deskripsi) VALUES (?, ?, ?)', kategori_default)
    
    # Insert pajak default
    pajak_default = [
        ('PPh 21', 5),
        ('PPN', 10),
        ('PPh 23', 15),
        ('BPHTB', 5),
    ]
    cursor.executemany('INSERT INTO pajak (jenis_pajak, tarif) VALUES (?, ?)', pajak_default)
    
    # Insert transaksi contoh
    # Pertama dapatkan ID akun
    cursor.execute("SELECT id FROM akun WHERE kode_akun = '1.1'")
    kas_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM akun WHERE kode_akun = '7.1'")
    penjualan_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM akun WHERE kode_akun = '8.2'")
    gaji_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM akun WHERE kode_akun = '8.3'")
    sewa_id = cursor.fetchone()[0]
    
    transaksi_default = [
        ('2024-01-15', 'Pembelian Kas', kas_id, 0, 500000, 'TR001', 1, 'admin'),
        ('2024-01-16', 'Penjualan Produk', penjualan_id, 1500000, 0, 'TR002', 1, 'admin'),
        ('2024-01-17', 'Pembayaran Gaji', gaji_id, 0, 5000000, 'TR003', 1, 'admin'),
        ('2024-01-18', 'Pembayaran Sewa', sewa_id, 0, 3000000, 'TR004', 1, 'admin'),
    ]
    cursor.executemany('INSERT INTO transaksi (tanggal, keterangan, akun_id, debit, kredit, bukti_transaksi, approved, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', transaksi_default)
    
    # Insert aset contoh
    aset_default = [
        ('Laptop ASUS', 'Peralatan', 8000000, '2024-01-01', 3, 2, 2666667),
        ('Mobil Avanza', 'Kendaraan', 250000000, '2024-01-01', 5, 4, 50000000),
        ('Meja Kantor', 'Peralatan', 5000000, '2024-01-01', 10, 8, 1000000),
    ]
    cursor.executemany('INSERT INTO aset (nama_aset, jenis_aset, nilai_aset, tanggal_pembelian, umur_ekonomis, sisa_umur, depresiasi) VALUES (?, ?, ?, ?, ?, ?, ?)', aset_default)
    
    conn.commit()
    conn.close()

# Fungsi untuk mengambil data dari database
def get_data(table_name):
    conn = sqlite3.connect('siska.db')
    df = pd.read_sql_query(f'SELECT * FROM {table_name}', conn)
    conn.close()
    return df

def get_akun():
    return get_data('akun')

def get_transaksi():
    return get_data('transaksi')

def get_kategori():
    return get_data('kategori')

def get_aset():
    return get_data('aset')

def get_pajak():
    return get_data('pajak')

def get_saldo_akun():
    conn = sqlite3.connect('siska.db')
    query = '''
        SELECT 
            a.kode_akun,
            a.nama_akun,
            a.jenis_akun,
            COALESCE(SUM(t.debit), 0) - COALESCE(SUM(t.kredit), 0) + a.saldo_awal as saldo
        FROM akun a
        LEFT JOIN transaksi t ON a.id = t.akun_id
        GROUP BY a.kode_akun, a.nama_akun, a.jenis_akun
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Fungsi untuk menyimpan data ke database
def save_data(table_name, data):
    conn = sqlite3.connect('siska.db')
    data.to_sql(table_name, conn, if_exists='append', index=False)
    conn.close()

# Fungsi untuk mendapatkan ID akun dari nama akun
def get_akun_id(nama_akun):
    conn = sqlite3.connect('siska.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM akun WHERE nama_akun = ?", (nama_akun,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Fungsi untuk membuat PDF
def create_pdf_laporan(data, filename):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, height - inch, "LAPORAN KEUANGAN SISKA")
    p.setFont("Helvetica", 12)
    p.drawString(inch, height - 1.5 * inch, f"Periode: {date.today().strftime('%d-%m-%Y')}")
    
    # Tabel data
    y = height - 2 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, y, "No.")
    p.drawString(2 * inch, y, "Kode Akun")
    p.drawString(3.5 * inch, y, "Nama Akun")
    p.drawString(5.5 * inch, y, "Jenis Akun")
    p.drawString(7 * inch, y, "Saldo")
    
    y -= 0.5 * inch
    p.setFont("Helvetica", 10)
    for i, row in data.iterrows():
        p.drawString(inch, y, str(i + 1))
        p.drawString(2 * inch, y, row['kode_akun'])
        p.drawString(3.5 * inch, y, row['nama_akun'])
        p.drawString(5.5 * inch, y, row['jenis_akun'])
        p.drawString(7 * inch, y, f"Rp {row['saldo']:,.0f}")
        y -= 0.3 * inch
        if y < inch:
            p.showPage()
            y = height - inch
    
    p.save()
    buffer.seek(0)
    return buffer

# Fungsi untuk menghitung total keuangan
def hitung_total_keuangan():
    saldo_akun_df = get_saldo_akun()
    total_aset = saldo_akun_df[saldo_akun_df['jenis_akun'].isin(['Aset Lancar', 'Aset Tetap'])]['saldo'].sum()
    total_kewajiban = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Kewajiban']['saldo'].sum()
    total_modal = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Ekuitas']['saldo'].sum()
    total_pendapatan = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Pendapatan']['saldo'].sum()
    total_biaya = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Biaya']['saldo'].sum()
    laba_rugi = total_pendapatan - total_biaya
    
    return {
        'total_aset': total_aset,
        'total_kewajiban': total_kewajiban,
        'total_modal': total_modal,
        'total_pendapatan': total_pendapatan,
        'total_biaya': total_biaya,
        'laba_rugi': laba_rugi
    }

# Inisialisasi database
init_db()

# Sidebar
with st.sidebar:
    # Tampilkan logo jika file ada
    logo_path = os.path.join(BASE_DIR, "logo_SISKA.png")
    if os.path.exists(logo_path):
        try:
            st.image(logo_path, use_column_width=True)
        except TypeError:
            st.image(logo_path)
    
    st.markdown("---")
    
    # Menu navigasi
    menu = st.radio(
        "Menu",
        ["Dashboard", "Akun", "Transaksi", "Kategori", "Laporan", "Pajak", "Aset", "Neraca", "Print Laporan PDF", "Admin"]
    )
    
    st.markdown("---")
    
    # Informasi pengembang
    st.markdown("### Pengembang")
    st.markdown("Ir. M. Nasri AW, M.Eng.Sc, M.Kom")
    st.markdown("Dosen STIE Indonesia Malang")
    st.markdown("@2024")

# Konten utama
if menu == "Dashboard":
    st.title("Dashboard Keuangan")
    
    # Hitung total keuangan
    total = hitung_total_keuangan()
    
    # Ringkasan keuangan dengan nilai aktual
    st.markdown("### Ringkasan Keuangan")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Aset", f"Rp {total['total_aset']:,.0f}")
    with col2:
        st.metric("Total Kewajiban", f"Rp {total['total_kewajiban']:,.0f}")
    with col3:
        st.metric("Modal", f"Rp {total['total_modal']:,.0f}")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.metric("Total Pendapatan", f"Rp {total['total_pendapatan']:,.0f}")
    with col5:
        st.metric("Total Biaya", f"Rp {total['total_biaya']:,.0f}")
    with col6:
        st.metric("Laba/Rugi", f"Rp {total['laba_rugi']:,.0f}")
    
    # Grafik
    st.markdown("### Grafik Keuangan")
    fig, ax = plt.subplots(figsize=(10, 5))
    categories = ['Aset', 'Kewajiban', 'Modal']
    values = [total['total_aset'], total['total_kewajiban'], total['total_modal']]
    ax.bar(categories, values)
    ax.set_ylabel('Amount (Rp)')
    st.pyplot(fig)
    
    # Transaksi terakhir
    st.markdown("### Transaksi Terakhir")
    transaksi_df = get_transaksi()
    if not transaksi_df.empty:
        # Tambahkan nama akun ke transaksi
        transaksi_df = transaksi_df.merge(get_akun(), left_on='akun_id', right_on='id')
        st.dataframe(transaksi_df[['tanggal', 'keterangan', 'nama_akun', 'debit', 'kredit']].head(10), use_container_width=True)
    else:
        st.info("Belum ada transaksi")

elif menu == "Akun":
    st.title("Manajemen Akun")
    
    # Tampilkan daftar akun
    st.markdown("### Daftar Akun")
    akun_df = get_akun()
    st.dataframe(akun_df, use_container_width=True)
    
    # Form tambah akun
    st.markdown("### Tambah Akun Baru")
    with st.form("form_akun"):
        col1, col2 = st.columns(2)
        
        with col1:
            kode_akun = st.text_input("Kode Akun", value="9.1")
            nama_akun = st.text_input("Nama Akun", value="Akun Baru")
            jenis_akun = st.selectbox("Jenis Akun", ["Aset Lancar", "Aset Tetap", "Kewajiban", "Ekuitas", "Pendapatan", "Biaya"], index=4)
        
        with col2:
            sub_akun = st.text_input("Sub Akun", value="")
            saldo_awal = st.number_input("Saldo Awal", min_value=0, step=1000, value=0)
        
        submitted = st.form_submit_button("Simpan Akun")
        
        if submitted:
            new_akun = pd.DataFrame({
                'kode_akun': [kode_akun],
                'nama_akun': [nama_akun],
                'jenis_akun': [jenis_akun],
                'sub_akun': [sub_akun],
                'saldo_awal': [saldo_awal]
            })
            save_data('akun', new_akun)
            st.success("Akun berhasil ditambahkan!")
            st.rerun()

elif menu == "Transaksi":
    st.title("Manajemen Transaksi")
    
    # Form tambah transaksi
    st.markdown("### Tambah Transaksi Baru")
    with st.form("form_transaksi"):
        col1, col2 = st.columns(2)
        
        with col1:
            tanggal = st.date_input("Tanggal", value=datetime.now().date())
            keterangan = st.text_input("Keterangan", value="Pembelian Barang")
            nama_akun = st.selectbox("Akun", get_akun()['nama_akun'].tolist())
            debit = st.number_input("Debit", min_value=0, step=1000, value=0)
        
        with col2:
            kredit = st.number_input("Kredit", min_value=0, step=1000, value=0)
            bukti_transaksi = st.text_input("Bukti Transaksi", value="TR005")
            created_by = st.text_input("Dibuat Oleh", value="admin")
        
        submitted = st.form_submit_button("Simpan Transaksi")
        
        if submitted:
            akun_id = get_akun_id(nama_akun)
            if akun_id:
                new_transaksi = pd.DataFrame({
                    'tanggal': [tanggal],
                    'keterangan': [keterangan],
                    'akun_id': [akun_id],
                    'debit': [debit],
                    'kredit': [kredit],
                    'bukti_transaksi': [bukti_transaksi],
                    'created_by': [created_by]
                })
                save_data('transaksi', new_transaksi)
                st.success("Transaksi berhasil disimpan!")
                st.rerun()
            else:
                st.error("Akun tidak ditemukan!")
    
    # Tampilkan daftar transaksi
    st.markdown("### Daftar Transaksi")
    transaksi_df = get_transaksi()
    if not transaksi_df.empty:
        # Tambahkan nama akun ke transaksi
        transaksi_df = transaksi_df.merge(get_akun(), left_on='akun_id', right_on='id')
        st.dataframe(transaksi_df[['tanggal', 'keterangan', 'nama_akun', 'debit', 'kredit', 'bukti_transaksi']].head(10), use_container_width=True)
    else:
        st.info("Belum ada transaksi")

elif menu == "Kategori":
    st.title("Manajemen Kategori")
    
    # Tampilkan daftar kategori
    st.markdown("### Daftar Kategori")
    kategori_df = get_kategori()
    st.dataframe(kategori_df, use_container_width=True)
    
    # Form tambah kategori
    st.markdown("### Tambah Kategori Baru")
    with st.form("form_kategori"):
        col1, col2 = st.columns(2)
        
        with col1:
            nama_kategori = st.text_input("Nama Kategori", value="Kategori Baru")
            jenis_kategori = st.selectbox("Jenis Kategori", ["Pendapatan", "Biaya"], index=0)
        
        with col2:
            deskripsi = st.text_input("Deskripsi", value="Deskripsi kategori baru")
        
        submitted = st.form_submit_button("Simpan Kategori")
        
        if submitted:
            new_kategori = pd.DataFrame({
                'nama_kategori': [nama_kategori],
                'jenis_kategori': [jenis_kategori],
                'deskripsi': [deskripsi]
            })
            save_data('kategori', new_kategori)
            st.success("Kategori berhasil ditambahkan!")
            st.rerun()

elif menu == "Laporan":
    st.title("Laporan Keuangan")
    
    # Hitung total keuangan
    total = hitung_total_keuangan()
    
    # Pilih periode
    st.markdown("### Pilih Periode")
    periode = st.selectbox("Periode", ["Harian", "Mingguan", "Bulanan", "Tahunan"], index=2)
    
    # Tampilkan laporan
    st.markdown("### Laporan Laba Rugi")
    laba_rugi_df = pd.DataFrame({
        'Pendapatan': [total['total_pendapatan']],
        'Biaya': [total['total_biaya']],
        'Laba Bersih': [total['laba_rugi']]
    })
    st.dataframe(laba_rugi_df, use_container_width=True)
    
    st.markdown("### Laporan Arus Kas")
    arus_kas_df = pd.DataFrame({
        'Masuk': [total['total_pendapatan']],
        'Keluar': [total['total_biaya']],
        'Netto': [total['laba_rugi']]
    })
    st.dataframe(arus_kas_df, use_container_width=True)

elif menu == "Pajak":
    st.title("Manajemen Pajak")
    
    # Tampilkan daftar pajak
    st.markdown("### Daftar Pajak")
    pajak_df = get_pajak()
    st.dataframe(pajak_df, use_container_width=True)
    
    # Form tambah pajak
    st.markdown("### Tambah Pajak Baru")
    with st.form("form_pajak"):
        col1, col2 = st.columns(2)
        
        with col1:
            jenis_pajak = st.text_input("Jenis Pajak", value="Pajak Baru")
        
        with col2:
            tarif = st.number_input("Tarif (%)", min_value=0.0, max_value=100.0, step=0.1, value=10.0)
        
        submitted = st.form_submit_button("Simpan Pajak")
        
        if submitted:
            new_pajak = pd.DataFrame({
                'jenis_pajak': [jenis_pajak],
                'tarif': [tarif]
            })
            save_data('pajak', new_pajak)
            st.success("Pajak berhasil ditambahkan!")
            st.rerun()

elif menu == "Aset":
    st.title("Manajemen Aset")
    
    # Tampilkan daftar aset
    st.markdown("### Daftar Aset")
    aset_df = get_aset()
    st.dataframe(aset_df, use_container_width=True)
    
    # Form tambah aset
    st.markdown("### Tambah Aset Baru")
    with st.form("form_aset"):
        col1, col2 = st.columns(2)
        
        with col1:
            nama_aset = st.text_input("Nama Aset", value="Aset Baru")
            jenis_aset = st.selectbox("Jenis Aset", ["Peralatan", "Bangunan", "Kendaraan", "Lainnya"], index=0)
            nilai_aset = st.number_input("Nilai Aset", min_value=0, step=1000, value=10000000)
            tanggal_pembelian = st.date_input("Tanggal Pembelian", value=datetime.now().date())
        
        with col2:
            umur_ekonomis = st.number_input("Umur Ekonomis (tahun)", min_value=1, step=1, value=5)
            sisa_umur = st.number_input("Sisa Umur (tahun)", min_value=0, step=1, value=4)
            depresiasi = st.number_input("Depresiasi", min_value=0, step=1000, value=2000000)
        
        submitted = st.form_submit_button("Simpan Aset")
        
        if submitted:
            new_aset = pd.DataFrame({
                'nama_aset': [nama_aset],
                'jenis_aset': [jenis_aset],
                'nilai_aset': [nilai_aset],
                'tanggal_pembelian': [tanggal_pembelian],
                'umur_ekonomis': [umur_ekonomis],
                'sisa_umur': [sisa_umur],
                'depresiasi': [depresiasi]
            })
            save_data('aset', new_aset)
            st.success("Aset berhasil ditambahkan!")
            st.rerun()

elif menu == "Neraca":
    st.title("Neraca")
    
    # Hitung total keuangan
    total = hitung_total_keuangan()
    
    # Tampilkan neraca
    st.markdown("### Neraca Lajur")
    saldo_akun_df = get_saldo_akun()
    
    # Kelompokkan jenis akun
    aset_df = saldo_akun_df[saldo_akun_df['jenis_akun'].isin(['Aset Lancar', 'Aset Tetap'])]
    kewajiban_df = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Kewajiban']
    modal_df = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Ekuitas']
    
    # Tampilkan tabel
    st.markdown("### Aset")
    st.dataframe(aset_df, use_container_width=True)
    st.metric("Total Aset", f"Rp {total['total_aset']:,.0f}")
    
    st.markdown("### Kewajiban & Modal")
    st.dataframe(pd.concat([kewajiban_df, modal_df]), use_container_width=True)
    st.metric("Total Kewajiban", f"Rp {total['total_kewajiban']:,.0f}")
    st.metric("Total Modal", f"Rp {total['total_modal']:,.0f}")
    
    # Verifikasi neraca
    st.markdown("### Verifikasi Neraca")
    if abs(total['total_aset'] - (total['total_kewajiban'] + total['total_modal'])) < 0.01:
        st.success("Neraca Seimbang!")
    else:
        st.error("Neraca Tidak Seimbang!")

elif menu == "Print Laporan PDF":
    st.title("Print Laporan PDF")
    
    # Hitung total keuangan
    total = hitung_total_keuangan()
    
    # Pilih jenis laporan
    jenis_laporan = st.selectbox("Jenis Laporan", ["Neraca", "Laba Rugi", "Arus Kas"], index=0)
    
    # Tampilkan preview
    if jenis_laporan == "Neraca":
        st.markdown("### Preview Neraca")
        saldo_akun_df = get_saldo_akun()
        aset_df = saldo_akun_df[saldo_akun_df['jenis_akun'].isin(['Aset Lancar', 'Aset Tetap'])]
        kewajiban_df = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Kewajiban']
        modal_df = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Ekuitas']
        
        st.dataframe(aset_df, use_container_width=True)
        st.dataframe(pd.concat([kewajiban_df, modal_df]), use_container_width=True)
    
    elif jenis_laporan == "Laba Rugi":
        st.markdown("### Preview Laba Rugi")
        laba_rugi_df = pd.DataFrame({
            'Pendapatan': [total['total_pendapatan']],
            'Biaya': [total['total_biaya']],
            'Laba Bersih': [total['laba_rugi']]
        })
        st.dataframe(laba_rugi_df, use_container_width=True)
    
    elif jenis_laporan == "Arus Kas":
        st.markdown("### Preview Arus Kas")
        arus_kas_df = pd.DataFrame({
            'Masuk': [total['total_pendapatan']],
            'Keluar': [total['total_biaya']],
            'Netto': [total['laba_rugi']]
        })
        st.dataframe(arus_kas_df, use_container_width=True)
    
    # Tombol print
    if st.button("Print PDF"):
        if jenis_laporan == "Neraca":
            saldo_akun_df = get_saldo_akun()
            pdf_buffer = create_pdf_laporan(saldo_akun_df, f"neraca_{date.today()}.pdf")
            st.download_button(
                label="Download Neraca PDF",
                data=pdf_buffer,
                file_name=f"neraca_{date.today()}.pdf",
                mime="application/pdf"
            )
        elif jenis_laporan == "Laba Rugi":
            laba_rugi_df = pd.DataFrame({
                'item': ['Pendapatan', 'Biaya', 'Laba Bersih'],
                'jumlah': [total['total_pendapatan'], total['total_biaya'], total['laba_rugi']]
            })
            pdf_buffer = create_pdf_laporan(laba_rugi_df, f"laba_rugi_{date.today()}.pdf")
            st.download_button(
                label="Download Laba Rugi PDF",
                data=pdf_buffer,
                file_name=f"laba_rugi_{date.today()}.pdf",
                mime="application/pdf"
            )
        elif jenis_laporan == "Arus Kas":
            arus_kas_df = pd.DataFrame({
                'item': ['Masuk', 'Keluar', 'Netto'],
                'jumlah': [total['total_pendapatan'], total['total_biaya'], total['laba_rugi']]
            })
            pdf_buffer = create_pdf_laporan(arus_kas_df, f"arus_kas_{date.today()}.pdf")
            st.download_button(
                label="Download Arus Kas PDF",
                data=pdf_buffer,
                file_name=f"arus_kas_{date.today()}.pdf",
                mime="application/pdf"
            )

elif menu == "Admin":
    st.title("Admin Panel")
    
    # Login
    st.markdown("### Login Admin")
    username = st.text_input("Username", value="admin")
    password = st.text_input("Password", type="password", value="admin123")
    
    if st.button("Login"):
        conn = sqlite3.connect('siska.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            st.success("Login berhasil!")
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['role'] = user[3]
        else:
            st.error("Username atau password salah!")
    
    # Jika sudah login
    if 'logged_in' in st.session_state and st.session_state['logged_in']:
        st.markdown(f"### Selamat datang, {st.session_state['username']}!")
        
        # Manajemen user
        st.markdown("### Manajemen User")
        users_df = pd.read_sql_query("SELECT id, username, role FROM users", sqlite3.connect('siska.db'))
        st.dataframe(users_df, use_container_width=True)
        
        # Form tambah user
        st.markdown("### Tambah User Baru")
        with st.form("form_user"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username", value="userbaru")
                new_password = st.text_input("Password", type="password", value="password123")
            
            with col2:
                new_role = st.selectbox("Role", ["admin", "user"], index=1)
            
            submitted = st.form_submit_button("Simpan User")
            
            if submitted:
                conn = sqlite3.connect('siska.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                              (new_username, new_password, new_role))
                conn.commit()
                conn.close()
                st.success("User berhasil ditambahkan!")
                st.rerun()
        
        # Logout
        if st.button("Logout"):
            del st.session_state['logged_in']
            del st.session_state['username']
            del st.session_state['role']
            st.rerun()
