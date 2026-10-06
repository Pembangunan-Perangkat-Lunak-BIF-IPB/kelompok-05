# VarEscape

Aplikasi web yang menggabungkan *variant calling* dan *immune escape analysis* dalam satu antarmuka, dilengkapi auto-diagnostics per tahap, export konfigurasi ke YAML, dan penyimpanan data di PostgreSQL.

Proyek mata kuliah Pembangunan Perangkat Lunak — Kelompok 5, Bioinformatika IPB University.

## Anggota

| Nama | Peran |
| --- | --- |
| Candra | Project Manager |
| Talitha | System Analyst |
| Raihan | Frontend |
| Afifah | Backend |
| Guruh | Tester |

## Struktur Folder

```
kelompok-05/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── layouts/
│   │   │   ├── Layout.jsx
│   │   │   └── nav.js
│   │   ├── lib/
│   │   │   ├── api.js
│   │   │   └── validators.js
│   │   ├── pages/
│   │   │   ├── Placeholder.jsx
│   │   │   ├── Guide.jsx
│   │   │   ├── NewAnalysis.jsx
│   │   │   └── pages.css
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── .gitignore
│   ├── database.py
│   ├── main.py
│   └── models.py
└── docs/
    └── pengujian/
```

## Prasyarat

Install dulu sebelum menjalankan aplikasi:

- Git
- Node.js versi 20.19 atau lebih baru (dikembangkan dengan v24.21.0)
- Python versi 3.10 atau lebih baru
- PostgreSQL versi 14 atau lebih baru
- DBeaver (atau PostgreSQL GUI Client yang lain)

Pengguna Windows disarankan memakai Command Prompt (CMD).

## Cara Menjalankan

### 1. Ambil kode

```bash
git clone https://github.com/Pembangunan-Perangkat-Lunak-BIF-IPB/kelompok-05.git
cd kelompok-05
```

### 2. Siapkan basis data

Pastikan layanan PostgreSQL sudah aktif di perangkat yang digunakan, lalu buat basis data baru lewat DBeaver, pgAdmin, atau terminal SQL:

```sql
CREATE DATABASE varescape_db;
```

Selanjutnya, buat file bernama `.env` di dalam folder `backend/` dan atur URL koneksi basis data yang sudah dibuat:

```
DATABASE_URL=postgresql+psycopg://postgres:password_anda@localhost:5432/varescape_db
```

### 3. Jalankan backend

```bash
# Masuk ke folder backend
cd backend

# (Opsional) Buat dan aktifkan virtual environment
python -m venv venv
venv\Scripts\activate

# Perintah install dependency
pip install fastapi uvicorn sqlalchemy "psycopg[binary]" python-dotenv

# Perintah menjalankan server (tabel basis data otomatis terbuat saat server startup)
uvicorn main:app --reload --port 8000
```

Cek berhasil: buka `http://localhost:8000/api/v1/health` → harus muncul status `healthy` dan database `connected`.
### Endpoint API 

- **Autentikasi:**
  - `POST /api/v1/auth/register` — Registrasi akun pengguna baru
  - `POST /api/v1/auth/login` — Autentikasi & penerbitan Token JWT
- **Workbench Analysis:**
  - `POST /api/v1/analysis/upload` — Unggah berkas sampel (FASTQ, FASTA, IEDB)
  - `GET /api/v1/analysis/{run_id}/status` — Cek status pemrosesan analisis
  - `GET /api/v1/analysis/{run_id}/results` — Penarikan hasil analisis varian
  - `PATCH /api/v1/analysis/{run_id}/visibility` — Pembaruan visibilitas (`PUBLIC`/`PRIVATE`)

📄 **Dokumentasi Lengkap:** Detail spesifikasi REST API dapat dilihat pada berkas [`docs/api.md`](docs/api.md).

### 4. Jalankan frontend

```bash
# Jalankan perintah berikut pada Terminal Command Prompt
# Pindah direktori ke folder kelompok-05 yang berisi semua file yang dibutuhkan
cd frontend
npm install
npm run dev
```

Cek berhasil: buka `http://localhost:3000` pada browser → otomatis menuju halaman Login
Peneliti (placeholder). Halaman dengan sidebar dapat dibuka lewat `/guide`,
`/analysis/new`, `/history`, `/public`, dan `/admin/accounts`.

## Kendala Umum

| Masalah | Solusi |
| --- | --- |
| Skrip diblokir PowerShell (aktivasi `venv` atau `npm -v` gagal karena kebijakan eksekusi) | Gunakan Command Prompt (CMD), atau di PowerShell jalankan `npm.cmd` sebagai pengganti `npm` |
| `ImportError: no pq wrapper available` saat menjalankan backend | Jalankan `pip install "psycopg[binary]"` |
| `database "varescape_db" does not exist` saat server dinyalakan | Buat basis data dulu dengan `CREATE DATABASE varescape_db;` (langkah 2) |

## Tautan

- Repository: https://github.com/Pembangunan-Perangkat-Lunak-BIF-IPB/kelompok-05
- GitHub Project: https://github.com/orgs/Pembangunan-Perangkat-Lunak-BIF-IPB/projects/16
- Prototype Figma: https://www.figma.com/proto/MYJ4HR4Lh39ukfgmDuwA5Z/Update-W6-High-Fidelity-VarEscape-BIFIVE---FIX?page-id=0%3A1&node-id=4007-284&p=f&viewport=410%2C229%2C0.05&t=nt7iCAxbEMk6XiCp-1&scaling=min-zoom&content-scaling=fixed&starting-point-node-id=4007%3A284&show-proto-sidebar=1
