import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io
import os
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import numpy as np
import logging
import time
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Marker file to control automatic seeding after manual reset
SKIP_SEED_FILE = os.path.join(BASE_DIR, '.skip_seed')

def should_seed_defaults():
    """Return True when default data should be seeded.

    Administrators can create a skip file to prevent automatic reseeding after a manual reset.
    """
    return not os.path.exists(SKIP_SEED_FILE)

def check_credentials(username, password, allowed_roles=None):
    """Verify username/password against users table or Streamlit Secrets."""
    try:
        # Cek kecocokan dengan password admin utama dari Secrets terlebih dahulu
        admin_secret_pwd = st.secrets.get("ADMIN_PASSWORD", "siska123")
        if username == "admin" and password == admin_secret_pwd:
            return True

        # Jika tidak cocok dengan secrets, cek ke database sqlite
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password, role FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False
        stored_pwd, role = row[0], row[1]
        if stored_pwd != password:
            return False
        if allowed_roles and role not in allowed_roles:
            return False
        return True
    except Exception:
        logger.error('check_credentials error: %s', traceback.format_exc())
        return False

# Logging konfigurasi
LOG_PATH = os.path.join(BASE_DIR, 'siska.log')
logger = logging.getLogger('siska')
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOG_PATH)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)


def get_db_path():
    return os.path.join(BASE_DIR, 'siska.db')


def get_db_connection(timeout=30):
    """Return a sqlite3 connection using the app DB path and a timeout."""
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        return conn
    except Exception as e:
        logger.exception('Gagal membuka koneksi DB: %s', db_path)
        raise

# Konfigurasi halaman
st.set_page_config(
    page_title="SISKA - Sistem Informasi Sederhana Keuangan & Akuntansi",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi database dengan nilai default
def seed_default_data(cursor):
    """Insert data default demo jika tabel akun masih kosong."""
    cursor.execute("INSERT INTO akun (kode_akun, nama_akun, jenis_akun, sub_akun, saldo_awal) VALUES (?, ?, ?, ?, ?)",
                   ('1.1', 'Kas', 'Aset Lancar', 'Kas Kecil', 10000000.0))
    cursor.execute("INSERT INTO akun (kode_akun, nama_akun, jenis_akun, sub_akun, saldo_awal) VALUES (?, ?, ?, ?, ?)",
                   ('2.1', 'Utang Dagang', 'Kewajiban', 'Utang Usaha', 2500000.0))
    cursor.execute("INSERT INTO akun (kode_akun, nama_akun, jenis_akun, sub_akun, saldo_awal) VALUES (?, ?, ?, ?, ?)",
                   ('3.1', 'Modal Pemilik', 'Ekuitas', 'Modal Awal', 15000000.0))
    cursor.execute("INSERT INTO akun (kode_akun, nama_akun, jenis_akun, sub_akun, saldo_awal) VALUES (?, ?, ?, ?, ?)",
                   ('4.1', 'Pendapatan Jasa', 'Pendapatan', 'Pendapatan Usaha', 0.0))
    cursor.execute("INSERT INTO akun (kode_akun, nama_akun, jenis_akun, sub_akun, saldo_awal) VALUES (?, ?, ?, ?, ?)",
                   ('5.1', 'Biaya Operasional', 'Biaya', 'Biaya Kantor', 0.0))

    cursor.execute("INSERT INTO kategori (nama_kategori, jenis_kategori, deskripsi) VALUES (?, ?, ?)",
                   ('Pendapatan Penjualan', 'Pendapatan', 'Pendapatan dari jasa dan penjualan'))
    cursor.execute("INSERT INTO kategori (nama_kategori, jenis_kategori, deskripsi) VALUES (?, ?, ?)",
                   ('Biaya Kantor', 'Biaya', 'Pengeluaran operasional kantor'))

    cursor.execute("INSERT INTO aset (nama_aset, jenis_aset, nilai_aset, tanggal_pembelian, umur_ekonomis, sisa_umur, depresiasi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ('Laptop', 'Peralatan', 12000000.0, '2026-01-15', 5, 4, 2400000.0))

    cursor.execute("INSERT INTO pajak (jenis_pajak, tarif) VALUES (?, ?)",
                   ('PPN', 11.0))
    cursor.execute("INSERT INTO pajak (jenis_pajak, tarif) VALUES (?, ?)",
                   ('PPh 23', 2.0))

    # default admin credentials (changed per user request)
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                   ('admin', 'siska123', 'admin'))

    cursor.execute("INSERT INTO transaksi (tanggal, keterangan, akun_id, debit, kredit, bukti_transaksi, approved, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   ('2026-06-01', 'Penjualan Jasa Desain', 4, 0.0, 5000000.0, 'INV-001', 1, 'admin'))
    cursor.execute("INSERT INTO transaksi (tanggal, keterangan, akun_id, debit, kredit, bukti_transaksi, approved, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   ('2026-06-02', 'Pembelian Alat Tulis', 5, 750000.0, 0.0, 'BTT-001', 1, 'admin'))
    cursor.execute("INSERT INTO transaksi (tanggal, keterangan, akun_id, debit, kredit, bukti_transaksi, approved, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   ('2026-06-03', 'Setoran Pemilik', 1, 0.0, 3000000.0, 'SET-001', 1, 'admin'))


def reset_all_data():
    """Hapus semua data transaksi dan master data tanpa menghapus schema."""
    try:
        conn = get_db_connection(timeout=30)
        cursor = conn.cursor()
        for table in ['transaksi', 'akun', 'kategori', 'aset', 'pajak', 'users']:
            cursor.execute(f"DELETE FROM {table}")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('transaksi', 'akun', 'kategori', 'aset', 'pajak', 'users')")
        conn.commit()
        conn.close()

        # create a marker file to indicate that seeding should be skipped
        try:
            with open(SKIP_SEED_FILE, 'w') as f:
                f.write('skip')
        except Exception:
            logger.debug('Gagal membuat skip-seed flag: %s', traceback.format_exc())

        logger.info('Semua data berhasil direset')
    except Exception:
        logger.error('Gagal reset semua data: %s', traceback.format_exc())
        raise


def use_simulation_data():
    """Mengembalikan aplikasi ke data default simulasi."""
    # Remove skip flag so init_db can seed defaults, then seed directly
    try:
        if os.path.exists(SKIP_SEED_FILE):
            os.remove(SKIP_SEED_FILE)
    except Exception:
        logger.debug('Gagal menghapus skip-seed flag: %s', traceback.format_exc())

    try:
        conn = get_db_connection(timeout=30)
        cursor = conn.cursor()
        seed_default_data(cursor)
        conn.commit()
        conn.close()
        logger.info('Data simulasi default dipasang')
    except Exception:
        logger.error('Gagal menggunakan data simulasi: %s', traceback.format_exc())
        raise


def init_db(retry=5, retry_delay=1):
    """Initialize the database schema and insert default data if the app is empty.

    Retries if the database is locked.
    """
    db_path = get_db_path()
    attempt = 0
    while True:
        try:
            conn = get_db_connection(timeout=30)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS akun (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kode_akun TEXT UNIQUE,
                    nama_akun TEXT,
                    jenis_akun TEXT,
                    sub_akun TEXT,
                    saldo_awal REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transaksi (
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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kategori (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama_kategori TEXT,
                    jenis_kategori TEXT,
                    deskripsi TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aset (
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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pajak (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jenis_pajak TEXT,
                    tarif REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM akun")
            try:
                count_akun = cursor.fetchone()[0]
            except Exception:
                count_akun = 0

            # Only seed defaults when there are no akun and seeding is not skipped
            if count_akun == 0 and should_seed_defaults():
                seed_default_data(cursor)

            conn.commit()
            conn.close()
            logger.info('Database diinisialisasi: %s', db_path)
            break
        except sqlite3.OperationalError as e:
            logger.warning('OperationalError saat init_db (attempt %s): %s', attempt + 1, e)
            attempt += 1
            if attempt >= retry:
                logger.error('Gagal inisialisasi DB setelah %s percobaan', retry)
                logger.debug(traceback.format_exc())
                raise
            time.sleep(retry_delay)
        except Exception:
            logger.error('Error tak terduga saat init_db: %s', traceback.format_exc())
            raise

# Fungsi untuk mengambil data dari database
def get_data(table_name):
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(f'SELECT * FROM {table_name}', conn)
        conn.close()
        return df
    except Exception:
        logger.error('Gagal membaca table %s: %s', table_name, traceback.format_exc())
        return pd.DataFrame()

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
    try:
        conn = get_db_connection()
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
    except Exception:
        logger.error('Gagal menghitung saldo akun: %s', traceback.format_exc())
        return pd.DataFrame()

# Fungsi untuk menyimpan data ke database
def save_data(table_name, data):
    try:
        conn = get_db_connection()
        data.to_sql(table_name, conn, if_exists='append', index=False)
        conn.close()
    except Exception:
        logger.error('Gagal menyimpan data ke %s: %s', table_name, traceback.format_exc())

# Fungsi untuk mendapatkan ID akun dari nama akun
def get_akun_id(nama_akun):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM akun WHERE nama_akun = ?", (nama_akun,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception:
        logger.error('Gagal mengambil akun id untuk %s: %s', nama_akun, traceback.format_exc())
        return None

# Fungsi bantu untuk parsing angka di PDF rek koran
def normalize_amount(value):
    text = str(value or '').strip()
    if not text:
        return 0.0
    negative = text.startswith('-') or ('(' in text and ')' in text)
    text = text.replace('(', '').replace(')', '')
    text = re.sub(r'[^\u0000-\u007f]', '', text)
    text = text.replace('Rp', '').replace('IDR', '').strip()

    if text.count(',') > 0 and text.count('.') > 0:
        if text.rfind(',') > text.rfind('.'):
            # format 1.234.567,89
            text = text.replace('.', '').replace(',', '.')
        else:
            # format 1,234,567.89
            text = text.replace(',', '')
    elif text.count(',') > 0:
        parts = text.split(',')
        if len(parts[-1]) == 2:
            text = ''.join(parts[:-1]).replace('.', '') + '.' + parts[-1]
        else:
            text = ''.join(parts)
    elif text.count('.') > 0:
        parts = text.split('.')
        if len(parts[-1]) == 3:
            text = ''.join(parts)
        elif len(parts[-1]) == 2:
            text = text
        else:
            text = ''.join(parts)

    try:
        return float(text) * (-1 if negative else 1)
    except ValueError:
        return 0.0

# Fungsi bantu untuk menormalisasi tanggal dari format PDF
def normalize_date(value):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value

# Ekstrak teks dari PDF, coba pdfplumber dulu lalu PyPDF2 sebagai fallback
def extract_pdf_text(file_buffer):
    file_buffer.seek(0)
    try:
        import pdfplumber
    except ImportError as e:
        logger.error('extract_pdf_text: modul pdfplumber tidak tersedia: %s', e)
        raise

    try:
        with pdfplumber.open(file_buffer) as pdf:
            pages_text = [page.extract_text() or '' for page in pdf.pages]
            text = '\n'.join(pages_text)
            logger.debug('extract_pdf_text: pdfplumber extracted %s pages, total_chars=%s', len(pages_text), len(text))
            try:
                with open(os.path.join(BASE_DIR, 'last_extracted_preview.txt'), 'w', encoding='utf-8') as f:
                    preview = '\n'.join(pages_text[:3])
                    f.write(preview)
            except Exception:
                logger.debug('Gagal menulis preview extract_text: %s', traceback.format_exc())
            return text
    except Exception as first_error:
        logger.warning('extract_pdf_text: pdfplumber gagal, mencoba PyPDF2: %s', traceback.format_exc())
        file_buffer.seek(0)
        try:
            from PyPDF2 import PdfReader
        except ImportError as e:
            logger.error('extract_pdf_text: modul PyPDF2 tidak tersedia: %s', e)
            raise

        try:
            reader = PdfReader(file_buffer)
            pages_text = [page.extract_text() or '' for page in reader.pages]
            text = '\n'.join(pages_text)
            logger.debug('extract_pdf_text: PyPDF2 extracted %s pages, total_chars=%s', len(pages_text), len(text))
            try:
                with open(os.path.join(BASE_DIR, 'last_extracted_preview.txt'), 'w', encoding='utf-8') as f:
                    preview = '\n'.join(pages_text[:3])
                    f.write(preview)
            except Exception:
                logger.debug('Gagal menulis preview extract_text (PyPDF2): %s', traceback.format_exc())
            return text
        except Exception as second_error:
            logger.error('extract_pdf_text: gagal mengekstrak teks dari PDF dengan PyPDF2: %s', traceback.format_exc())
            raise RuntimeError('Gagal mengekstrak teks dari PDF. Pastikan file PDF valid dan lihat siska.log untuk detail.')

# Parse teks PDF menjadi DataFrame transaksi harian
def parse_bank_statement_text(text):
    rows = []
    date_pattern = re.compile(r'^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')
    header_footer_pattern = re.compile(
        r'^(LAPORAN TRANSAKSI FINANSIAL|STATEMENT OF FINANCIAL TRANSACTION|Halaman \d+ dari \d+|Page \d+ of \d+|Tanggal Laporan|Statement Date|Transaction Period|No\. Rekening|Account No|Nama Produk|Product Name|Valuta|Currency|Tanggal Transaksi|Transaction Date|Transaction Description|User ID|Debit|Credit|Balance|Saldo Awal|Total Transaksi|Opening Balance|Closing Balance|Terbilang|Revenue Stamp Paid|Biaya materai|Salinan rekening koran|Apabila terdapat perbedaan|In the case of any differences|Should there be any change of email)\b',
        re.IGNORECASE
    )
    lines = [line.strip() for line in text.splitlines() if line.strip() and not header_footer_pattern.match(line.strip())]
    logger.debug('parse_bank_statement_text: total_lines=%s', len(lines))
    try:
        with open(os.path.join(BASE_DIR, 'last_extracted_lines_preview.txt'), 'w', encoding='utf-8') as pf:
            pf.write('\n'.join(lines[:80]))
    except Exception:
        logger.debug('Gagal menulis preview lines: %s', traceback.format_exc())

    segments = []
    current_segment = []
    for line in lines:
        if date_pattern.match(line):
            if current_segment:
                segments.append(current_segment)
            current_segment = [line]
        elif current_segment:
            current_segment.append(line)
    if current_segment:
        segments.append(current_segment)

    txn_amount_pattern = re.compile(r'(?<![\dA-Za-z:/-])(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*([DK])\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)(?![\dA-Za-z:/-])')
    numeric_columns_pattern = re.compile(
        r'^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(\d{2}:\d{2}:\d{2})\s+(.*?)\s+(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s*$'
    )

    for segment in segments:
        header = segment[0]
        match = date_pattern.match(header)
        if not match:
            continue

        tanggal_raw = match.group(1)
        tanggal = normalize_date(tanggal_raw)
        description_parts = []
        debit = 0.0
        kredit = 0.0
        saldo = None
        matched_amount = False

        bristmt_match = numeric_columns_pattern.match(header)
        if bristmt_match:
            description_parts.append(bristmt_match.group(3).strip())
            debit = normalize_amount(bristmt_match.group(4))
            kredit = normalize_amount(bristmt_match.group(5))
            saldo = normalize_amount(bristmt_match.group(6))
            matched_amount = True
            for line in segment[1:]:
                if date_pattern.match(line):
                    continue
                if numeric_columns_pattern.match(line):
                    continue
                description_parts.append(line)
        else:
            # cari baris yang berisi nominal transaksi dengan format D/K
            for line in segment[1:]:
                amount_match = txn_amount_pattern.search(line)
                if amount_match and not matched_amount:
                    amount = normalize_amount(amount_match.group(1))
                    dk_flag = amount_match.group(2)
                    saldo = normalize_amount(amount_match.group(3))
                    if dk_flag == 'D':
                        debit = amount
                        kredit = 0.0
                    else:
                        debit = 0.0
                        kredit = amount
                    matched_amount = True
                    continue
                if not txn_amount_pattern.search(line):
                    description_parts.append(line)

            if not matched_amount:
                header_after_date = header[match.end():].strip()
                amount_match = txn_amount_pattern.search(header_after_date)
                if amount_match:
                    amount = normalize_amount(amount_match.group(1))
                    dk_flag = amount_match.group(2)
                    saldo = normalize_amount(amount_match.group(3))
                    if dk_flag == 'D':
                        debit = amount
                        kredit = 0.0
                    else:
                        debit = 0.0
                        kredit = amount
                    matched_amount = True
                    description_parts.append(header_after_date[:amount_match.start()].strip())
                else:
                    description_parts.append(header_after_date)

        if not matched_amount:
            continue

        description = ' '.join(description_parts).strip()
        description = re.sub(r'\s+', ' ', description)
        if not description:
            description = header[match.end():].strip()

        rows.append({
            'Tanggal': tanggal,
            'Keterangan': description,
            'Debit': debit,
            'Kredit': kredit,
            'Saldo': saldo
        })

    return pd.DataFrame(rows)

# Parse file PDF menjadi DataFrame transaksi; kembalikan pesan error bila gagal
def parse_bank_statement_pdf(uploaded_file):
    # Accept either an uploaded file-like object (with .read()) or a local file path string
    if isinstance(uploaded_file, str):
        try:
            with open(uploaded_file, 'rb') as f:
                file_buffer = io.BytesIO(f.read())
        except Exception:
            return None, f"Gagal membuka file lokal: {uploaded_file}"
    else:
        try:
            file_buffer = io.BytesIO(uploaded_file.read())
        except Exception:
            return None, "Input file tidak valid."

    text = extract_pdf_text(file_buffer)
    if text is None:
        return None, "Library PDF tidak tersedia. Install pdfplumber atau PyPDF2 terlebih dahulu."

    df = parse_bank_statement_text(text)
    if df.empty:
        # simpan preview teks dan log untuk debugging
        try:
            with open(os.path.join(BASE_DIR, 'last_extracted_full.txt'), 'w', encoding='utf-8') as f:
                f.write(text[:20000])
        except Exception:
            logger.debug('Gagal menulis last_extracted_full: %s', traceback.format_exc())
        logger.warning('parse_bank_statement_pdf: tidak ditemukan baris transaksi, previews saved to last_extracted_preview.txt and last_extracted_lines_preview.txt')
        return None, "Tidak ditemukan baris transaksi dalam PDF. Pastikan format pdf sesuai LAPORAN TRANSAKSI FINANSIAL STATEMENT OF FINANCIAL TRANSACTION. Lihat siska.log dan last_extracted_preview.txt untuk debug."

    return df, None

# Buat buffer spreadsheet dan format file yang bisa didownload
def create_spreadsheet_buffer(df):
    try:
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return buffer, 'rek_koran_transaksi_harian.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    except Exception:
        text_buffer = io.StringIO()
        df.to_csv(text_buffer, index=False)
        return text_buffer.getvalue().encode('utf-8'), 'rek_koran_transaksi_harian.csv', 'text/csv'

# Fungsi untuk menghitung ringkasan rekening koran
def summarize_bank_statement(df):
    df = df.copy()
    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    df['Kredit'] = pd.to_numeric(df['Kredit'], errors='coerce').fillna(0)
    df['Saldo'] = pd.to_numeric(df['Saldo'], errors='coerce')
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')

    total_pemasukan = df['Kredit'].sum()
    total_pengeluaran = df['Debit'].sum()
    net_cashflow = total_pemasukan - total_pengeluaran

    if df['Saldo'].notna().any():
        first_valid = df['Saldo'].first_valid_index()
        last_valid = df['Saldo'].last_valid_index()
        saldo_awal = float(df.loc[first_valid, 'Saldo']) if first_valid is not None else 0.0
        saldo_akhir = float(df.loc[last_valid, 'Saldo']) if last_valid is not None else saldo_awal + net_cashflow
        saldo_harian = df['Saldo'].ffill()
        saldo_harian = saldo_harian.bfill()
        saldo_harian = saldo_harian.fillna(saldo_awal)
    else:
        saldo_awal = 0.0
        saldo_akhir = saldo_awal + net_cashflow
        saldo_harian = saldo_awal + df['Kredit'].cumsum() - df['Debit'].cumsum()

    df['Saldo_Harian'] = saldo_harian

    def detect_category(text):
        lower_text = str(text).lower()
        rules = {
            'penjualan': 'Pendapatan',
            'jual': 'Pendapatan',
            'pemasukan': 'Pendapatan',
            'transfer': 'Transfer',
            'gaji': 'Biaya',
            'sewa': 'Biaya',
            'listrik': 'Biaya',
            'air': 'Biaya',
            'transport': 'Biaya',
            'belanja': 'Biaya',
            'pembayaran': 'Biaya'
        }
        for keyword, category in rules.items():
            if keyword in lower_text:
                return category
        return 'Lainnya'

    df['Kategori'] = df['Keterangan'].apply(detect_category)

    kategori_summary = df.groupby('Kategori', as_index=False).agg({
        'Debit': 'sum',
        'Kredit': 'sum'
    })
    kategori_summary['Net'] = kategori_summary['Kredit'] - kategori_summary['Debit']

    return {
        'saldo_awal': saldo_awal,
        'saldo_akhir': saldo_akhir,
        'total_pemasukan': total_pemasukan,
        'total_pengeluaran': total_pengeluaran,
        'net_cashflow': net_cashflow,
        'trend_df': df[['Tanggal', 'Saldo_Harian']].dropna(subset=['Tanggal']),
        'kategori_summary': kategori_summary,
        'detail_df': df
    }

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


def main():
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
            ["Dashboard", "Akun", "Transaksi", "Kategori", "Laporan", "Pajak", "Aset", "Neraca", "Print Laporan PDF", "Admin", "Konversi Rekening e-statement", "Konversi Rekening Koran Bank"]
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

    elif menu == "Konversi Rekening e-statement":
        st.title("Konversi Rekening atau e-statement Bank menjadi Tabel Transaksi Harian")
        st.markdown("Upload file PDF rekening LAPORAN TRANSAKSI FINANSIAL STATEMENT OF FINANCIAL TRANSACTION untuk di konversi menjadi tabel transaksi harian. Pastikan format standar dari Bank")
        # require per-menu authentication so only authorized users can input rekening
        if 'conv_est_authenticated' not in st.session_state:
            st.session_state['conv_est_authenticated'] = False

        if not st.session_state['conv_est_authenticated']:
            st.markdown('#### Login untuk input e-statement')
            with st.form('conv_est_login'):
                ce_user = st.text_input('Username', value='admin')
                ce_pwd = st.text_input('Password', type='password')
                ce_sub = st.form_submit_button('Login')

            if ce_sub:
                if check_credentials(ce_user, ce_pwd):
                    st.session_state['conv_est_authenticated'] = True
                    st.success('Login berhasil — Anda dapat mengunggah file.')
                    st.rerun()
                else:
                    st.error('Username atau password salah')
            # do not show uploader until authenticated
            uploaded_file = None
        else:
            col_auth_left, col_auth_right = st.columns([4,1])
            with col_auth_right:
                if st.button('Logout (e-statement)'):
                    st.session_state['conv_est_authenticated'] = False
                    st.rerun()
            uploaded_file = st.file_uploader("Pilih file rek koran atau e-statement format.pdf", type=["pdf"])

        if uploaded_file is not None:
            df, error = parse_bank_statement_pdf(uploaded_file)
            if error:
                st.error(error)
            else:
                st.success("PDF berhasil dikonversi menjadi tabel transaksi.")
                summary = summarize_bank_statement(df)

                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Saldo Awal", f"Rp {summary['saldo_awal']:,.0f}")
                col2.metric("Saldo Akhir", f"Rp {summary['saldo_akhir']:,.0f}")
                col3.metric("Total Pemasukan", f"Rp {summary['total_pemasukan']:,.0f}")
                col4.metric("Total Pengeluaran", f"Rp {summary['total_pengeluaran']:,.0f}")
                col5.metric("Net Cashflow", f"Rp {summary['net_cashflow']:,.0f}")

                st.markdown("---")
                trend_tab, kategori_tab = st.tabs(["Trend Saldo", "Kategori"])

                with trend_tab:
                    st.markdown("### Trend Saldo Harian")
                    trend_df = summary['trend_df'].set_index('Tanggal')
                    if not trend_df.empty:
                        st.line_chart(trend_df.rename(columns={'Saldo_Harian': 'Saldo Harian'}))
                    else:
                        st.info("Tidak ada data saldo harian yang dapat ditampilkan.")

                with kategori_tab:
                    st.markdown("### Kategori Transaksi")
                    st.dataframe(summary['kategori_summary'], use_container_width=True)
                    if not summary['kategori_summary'].empty:
                        kategori_chart = summary['kategori_summary'].set_index('Kategori')[['Debit', 'Kredit']]
                        st.bar_chart(kategori_chart)

                st.markdown("### Data Transaksi Harian")
                st.dataframe(summary['detail_df'], use_container_width=True)

                buffer, file_name, mime = create_spreadsheet_buffer(summary['detail_df'])
                st.download_button(
                    label="Download Spreadsheet Transaksi Harian",
                    data=buffer,
                    file_name=file_name,
                    mime=mime
                )

    elif menu == "Konversi Rekening Koran Bank":
        st.title("Konversi Rekening Koran Bank menjadi Tabel Transaksi Harian")
        st.markdown("Gunakan fitur ini untuk mengonversi file rekening koran bank (format standar) menjadi tabel transaksi harian. Anda dapat mengunggah file PDF atau menggunakan file sampel lokal.")

        # require per-menu authentication so only authorized users can input rekening
        if 'conv_koran_authenticated' not in st.session_state:
            st.session_state['conv_koran_authenticated'] = False

        if not st.session_state['conv_koran_authenticated']:
            st.markdown('#### Login untuk input Rekening Koran')
            with st.form('conv_koran_login'):
                ck_user = st.text_input('Username', value='admin')
                ck_pwd = st.text_input('Password', type='password')
                ck_sub = st.form_submit_button('Login')

            if ck_sub:
                if check_credentials(ck_user, ck_pwd):
                    st.session_state['conv_koran_authenticated'] = True
                    st.success('Login berhasil — Anda dapat mengunggah file.')
                    st.rerun()
                else:
                    st.error('Username atau password salah')
            uploaded_file2 = None
        else:
            col_auth_a, col_auth_b = st.columns([4,1])
            with col_auth_b:
                if st.button('Logout (Rekening Koran)'):
                    st.session_state['conv_koran_authenticated'] = False
                    st.rerun()

            # show uploader and sample button only when authenticated
            sample_name = "rek_koran_STIA_BNI.pdf"
            sample_path = os.path.join(BASE_DIR, sample_name)

            col_a, col_b = st.columns([3,1])
            with col_a:
                uploaded_file2 = st.file_uploader("Pilih file rek koran (PDF)", type=["pdf"], key="uploader_koran")
            with col_b:
                if os.path.exists(sample_path):
                    if st.button(f"Gunakan sampel: {sample_name}"):
                        uploaded_file2 = sample_path
                else:
                    st.info(f"File sampel {sample_name} tidak ditemukan di folder aplikasi.")

        if uploaded_file2 is not None:
            df2, error2 = parse_bank_statement_pdf(uploaded_file2)
            if error2:
                st.error(error2)
            else:
                st.success("PDF berhasil dikonversi menjadi tabel transaksi.")
                summary2 = summarize_bank_statement(df2)

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Saldo Awal", f"Rp {summary2['saldo_awal']:,.0f}")
                c2.metric("Saldo Akhir", f"Rp {summary2['saldo_akhir']:,.0f}")
                c3.metric("Total Pemasukan", f"Rp {summary2['total_pemasukan']:,.0f}")
                c4.metric("Total Pengeluaran", f"Rp {summary2['total_pengeluaran']:,.0f}")
                c5.metric("Net Cashflow", f"Rp {summary2['net_cashflow']:,.0f}")

                st.markdown("---")
                ttab, ktab = st.tabs(["Trend Saldo", "Kategori"])

                with ttab:
                    st.markdown("### Trend Saldo Harian")
                    trend_df2 = summary2['trend_df'].set_index('Tanggal')
                    if not trend_df2.empty:
                        st.line_chart(trend_df2.rename(columns={'Saldo_Harian': 'Saldo Harian'}))
                    else:
                        st.info("Tidak ada data saldo harian yang dapat ditampilkan.")

                with ktab:
                    st.markdown("### Kategori Transaksi")
                    st.dataframe(summary2['kategori_summary'], use_container_width=True)
                    if not summary2['kategori_summary'].empty:
                        kategori_chart2 = summary2['kategori_summary'].set_index('Kategori')[['Debit', 'Kredit']]
                        st.bar_chart(kategori_chart2)

                st.markdown("### Data Transaksi Harian")
                st.dataframe(summary2['detail_df'], use_container_width=True)

                buffer2, file_name2, mime2 = create_spreadsheet_buffer(summary2['detail_df'])
                st.download_button(
                    label="Download Spreadsheet Transaksi Harian",
                    data=buffer2,
                    file_name=file_name2,
                    mime=mime2
                )

    elif menu == "Aset":
        st.title("Manajemen Aset")

        st.markdown("### Daftar Aset")
        aset_df = get_aset()
        st.dataframe(aset_df, use_container_width=True)

        st.markdown("### Tambah Aset Baru")
        with st.form("form_aset"):
            col1, col2 = st.columns(2)
            with col1:
                nama_aset = st.text_input("Nama Aset", value="Aset Baru")
                jenis_aset = st.selectbox("Jenis Aset", ["Peralatan", "Kendaraan", "Bangunan", "Inventaris"], index=0)
                nilai_aset = st.number_input("Nilai Aset", min_value=0.0, step=1000.0, value=0.0)
            with col2:
                tanggal_pembelian = st.date_input("Tanggal Pembelian", value=date.today())
                umur_ekonomis = st.number_input("Umur Ekonomis (tahun)", min_value=1, step=1, value=1)
                sisa_umur = st.number_input("Sisa Umur (tahun)", min_value=0, step=1, value=1)
                depresiasi = st.number_input("Depresiasi", min_value=0.0, step=1000.0, value=0.0)

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
        saldo_akun_df = get_saldo_akun()
        total_aset = saldo_akun_df[saldo_akun_df['jenis_akun'].isin(['Aset Lancar', 'Aset Tetap'])]['saldo'].sum()
        total_kewajiban = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Kewajiban']['saldo'].sum()
        total_modal = saldo_akun_df[saldo_akun_df['jenis_akun'] == 'Ekuitas']['saldo'].sum()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Aset", f"Rp {total_aset:,.0f}")
        with col2:
            st.metric("Total Kewajiban", f"Rp {total_kewajiban:,.0f}")
        with col3:
            st.metric("Total Modal", f"Rp {total_modal:,.0f}")

        neraca_df = pd.DataFrame({
            'Kategori': ['Aset', 'Kewajiban', 'Modal'],
            'Nilai': [total_aset, total_kewajiban, total_modal]
        })
        st.dataframe(neraca_df, use_container_width=True)

    elif menu == "Print Laporan PDF":
        st.title("Print Laporan PDF")
        saldo_akun_df = get_saldo_akun()
        if saldo_akun_df.empty:
            st.info("Belum ada data akun untuk dicetak.")
        else:
            pdf_buffer = create_pdf_laporan(saldo_akun_df, 'laporan_keuangan_siska.pdf')
            st.download_button(
                label="Unduh Laporan PDF",
                data=pdf_buffer,
                file_name='laporan_keuangan_siska.pdf',
                mime='application/pdf'
            )

    elif menu == "Admin":
        st.title("Admin")
        st.markdown("Gunakan panel ini untuk mengatur data aplikasi sesuai kebutuhan demo atau reset sistem.")

        # Initialize session state for admin auth
        if 'admin_authenticated' not in st.session_state:
            st.session_state['admin_authenticated'] = False

        if not st.session_state['admin_authenticated']:
            st.markdown("#### Login Admin")
            with st.form('admin_login'):
                uname = st.text_input('Username', value='admin')
                pwd = st.text_input('Password', type='password')
                submitted = st.form_submit_button('Login')

            if submitted:
                # Menggunakan check_credentials yang sudah terintegrasi dengan Secrets
                if check_credentials(uname, pwd, allowed_roles=['admin', 'superadmin']) or (uname == "admin" and pwd == st.secrets.get("ADMIN_PASSWORD", "siska123")):
                    st.session_state['admin_authenticated'] = True
                    st.success('Login berhasil')
                    st.rerun()  # Mengganti st.rerun
                else:
                    st.error('Username atau password salah')
        else:
            st.markdown('Anda login sebagai admin.')
            col1, col2 = st.columns(2)
            with col1:
                if st.button('Reset Semua Data', use_container_width=True):
                    reset_all_data()
                    st.success('Semua data berhasil direset.')
                    st.rerun()
            with col2:
                if st.button('Gunakan Simulasi (Data Default)', use_container_width=True):
                    use_simulation_data()
                    st.success('Data simulasi default berhasil dipasang.')
                    st.rerun()

            if st.button('Logout'):
                st.session_state['admin_authenticated'] = False
                st.success('Logout berhasil')
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


if __name__ == '__main__':
    main()
