# VarEscape — Backend FastAPI

Kode backend API (FastAPI, SQLAlchemy, PostgreSQL). Jalankan dan uji secara lokal sebelum digunakan pada server publik.

## Prasyarat
- Python 3.10+ dan PostgreSQL
- WSL Ubuntu untuk menjalankan backend beserta dependensi lingkungan yang dibutuhkan
- Node.js dan npm untuk frontend terpisah

## Menjalankan backend di WSL

```bash
cd /mnt/d/VarEscape/kelompok-05/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Isi **DB_PASSWORD** dan **SECRET_KEY** dengan nilai pribadi di `.env`. Jangan commit/unggah `.env`.
Periksa `DB_HOST`, `DB_PORT`, `DB_NAME`, dan `ALLOWED_ORIGINS` sesuai konfigurasi aktual. Contoh untuk frontend lokal port 3000:

```dotenv
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Untuk database lama, **backup dan audit skema sebelum menjalankan migrasi** `migrations/001_fix_schema.sql`.
Migrasi tersebut mengasumsikan timestamp lama adalah UTC; bila data lama dibuat dalam waktu setempat, asumsi ini perlu direvisi sebelum eksekusi. `create_all()` tidak menambah kolom pada tabel yang telah ada.

Jalankan:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Cek `http://127.0.0.1:8000/api/v1/health` dan `http://127.0.0.1:8000/docs`.

## Menjalankan frontend (terminal terpisah)

```bash
cd /mnt/d/VarEscape/kelompok-05/frontend
npm ci
cp .env.example .env
npm run dev
```

Buka `http://localhost:3000`. Pastikan `VITE_API_URL` mengarah ke API yang dapat diakses dari **browser** pengguna, bukan hanya alamat yang dapat diakses dari terminal WSL. Jika mengganti `.env`, restart proses frontend/backend terkait.

## Catatan keamanan dan validitas
- `SECRET_KEY` bawaan kode hanya untuk development; gunakan secret acak yang kuat.
- Pengguna baru berstatus `PENDING_APPROVAL`; endpoint workbench memerlukan status `ACTIVE`.
- Endpoint /admin memerlukan ADMIN + ACTIVE, sementara workbench /analysis memerlukan RESEARCHER + ACTIVE. Uji ulang sebelum deployment publik.
- Belum ada batas ukuran file secara ketat di backend; validasi di browser bukan kontrol keamanan.
- File referensi bundel `data/references/reference.fasta` hanya 210 basa walaupun header menyatakan genom lengkap. Jangan menyimpulkan validitas analisis dari contoh itu.
- Komponen anotasi dan penilaian biologis belum diaudit secara end-to-end. Nilai tidak tersedia tidak boleh disamakan dengan hasil numerik nol.

Lihat `docs/api.md` dan `PANDUAN_INTEGRASI_ADMIN.md` untuk kontrak admin, migrasi status SUSPENDED, dan cara menerapkan perubahan dengan aman.

## Integrasi Administrator (frontend React)

- `GET /api/v1/admin/accounts` — daftar akun bukan ADMIN
- `PATCH /api/v1/admin/accounts/{id}/status` — `ACTIVE`, `REJECTED`, `SUSPENDED`
- `GET /api/v1/admin/health` — koneksi DB, memori Linux/WSL, storage dan run PENDING/RUNNING
- `POST /api/v1/admin/accounts/{id}/reset-password` — **belum aktif (HTTP 501)**; perlu tautan reset satu kali via email

**Penting:** jalankan `migrations/003_add_suspended_status.sql` setelah backup database dan sebelum memakai fitur Nonaktifkan. File `.env` asli tidak ada di ZIP; gunakan milikmu sendiri.


## Tambahan Minggu 9–10: Status UC-07 dan Ekspor

Baca [`PANDUAN_MINGGU9_MINGGU10.md`](PANDUAN_MINGGU9_MINGGU10.md) untuk instalasi aman, contoh pengujian Swagger, query DBeaver, dan sisa pekerjaan yang belum divalidasi.

- `GET /api/v1/analysis/{run_id}/status` sekarang mengirim `created_at`, `started_at`, `completed_at` dan waktu ISO pada setiap log.
- `GET /api/v1/analysis/{run_id}/export/{format}` menerima `csv`, `tsv`, `vcf`, `logs`, atau `config`, hanya untuk pemilik run (peneliti aktif).
- `COMPLETED` adalah status eksekusi, bukan bukti validitas hasil biologis.
