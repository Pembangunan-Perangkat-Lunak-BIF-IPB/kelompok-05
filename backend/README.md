# VarEscape Backend Engine

Layanan backend API untuk platform **VarEscape** yang dibangun menggunakan **FastAPI**, **SQLAlchemy ORM**, dan **PostgreSQL**.

---

## Prasyarat (Prerequisites)

Sebelum menjalankan proyek ini, pastikan komputer/laptop Anda telah terpasang:
- **Python 3.10+**
- **PostgreSQL 14+**
- **DBeaver** (atau PostgreSQL GUI Client )

---

## Langkah Instalasi & Memulai Server

### 1. Masuk ke Folder Project
Buka terminal/Command Prompt (CMD) dan navigasi ke folder backend:
```cmd
cd varescape-backend

### 2. Membuat dan Mengaktifkan Virtual Environment
Buat virtual environment (jika belum ada):
```python -m venv venv

Aktifkan virtual environment:
### Windows (Comman Prompt/CMD):
```venv\Scripts\activate
### Windows (PowerShell):
```.\venv\Scripts\Activate.ps1
### Linux/macOS:
```source venv/bin/activate

(pastikan tanda (venv) muncul di awal baris perintah terminal)

### 2. Menginstal Dependensi
Jalankan perintah berikut untuk menginstal semua library yang dibutuhkan:
```pip install fastapi uvicorn sqlalchemy "psycopg[binary]" python-dotenv

## Konfigurasi Basis Data (PostgreSQL)
### 1.  Buat Database Baru:
Buka DBeaver, hubungkan ke PostgreSQL lokal Anda, lalu jalankan perintah SQL berikut:
```CREATE DATABASE varescape_db;

### 2. Buat File Environment Variable (.env):
Buat file bernama .env di dalam folder varescape-backend/ dan isi dengan konfigurasi koneksi database Anda:
```DATABASE_URL=postgresql://<USERNAME_POSTGRES>:<PASSWORD_POSTGRES>@localhost:5432/varescape_db

Sesuaikan <USERNAME_POSTGRES> dan <PASSWORD_POSTGRES> dengan kredensial PostgreSQL lokal Anda.

## Menjalankan Development Server
Jalankan server Uvicorn dengan perintah berikut:
```uvicorn main:app --reload --port 8000

Jika berhasil, terminal akan menampilkan log:
```INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
Catatan: Saat server pertama kali menyala, skema tabel users, analysis_runs, dan uploaded_files akan otomatis digenerate di PostgreSQL.

##Verifikasi & Endpoint Pengujian
### Health Check API:
Buka browser dan akses:

http://127.0.0.1:8000/api/v1/health

Respon JSON:
```{
  "status": "healthy",
  "database": "connected",
  "message": "Server backend dan PostgreSQL VarEscape siap digunakan!"
}

### Dokumentasi Interaktif (Swagger UI):
Akses di http://127.0.0.1:8000/docs

Autentikasi:

POST /api/v1/auth/register — Registrasi akun pengguna baru

POST /api/v1/auth/login — Authentikasi & penerbitan Token JWT

Workbench Analysis:

POST /api/v1/analysis/upload — Unggah berkas sampel (FASTQ, FASTA, IEDB)

GET /api/v1/analysis/{run_id}/status — Cek status pemrosesan analisis

GET /api/v1/analysis/{run_id}/results — Penarikan hasil analisis varian

PATCH /api/v1/analysis/{run_id}/visibility — Update visibilitas (PUBLIC/PRIVATE)

##Spesifikasi Lengkap API: Untuk detail skema request/response dan contoh payload, silakan baca berkas docs/api.md.
