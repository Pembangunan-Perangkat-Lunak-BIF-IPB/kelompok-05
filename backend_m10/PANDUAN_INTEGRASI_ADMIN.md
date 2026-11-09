# Panduan integrasi backend Administrator dengan frontend VarEscape

## Berkas yang benar-benar ditambah/diubah

**Baru:** `routers/admin.py`, `schemas/admin.py`, `migrations/003_add_suspended_status.sql`, dokumen ini.

**Diubah:** `main.py`, `models.py`, `security.py`, `routers/auth.py`, `routers/analysis.py`, `.env.example`, `README.md`, `docs/api.md`.

Seluruh file `utils/` pipeline tetap sama dengan basis backend_integrasi sebelumnya.

## Mengapa perlu migrasi?

Frontend punya tombol **Nonaktifkan** yang mengirim status `SUSPENDED`. SQLAlchemy enum saja tidak cukup: PostgreSQL memiliki jenis enum `userstatus` tersendiri. Migrasi ini menambah nilai `SUSPENDED` tanpa menghapus baris atau tabel lama.

```sql
ALTER TYPE public.userstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
```

Jalankan lewat DBeaver pada database yang **sudah dibackup** (`varescape_db`), dan pastikan statement dijalankan sampai sukses sebelum menekan Nonaktifkan. Jika nama tipe enum pada database berbeda, jangan menebak: periksa tipe `users.status_aktif` di DBeaver dulu. Jangan menjalankan ulang migrasi `001_fix_schema.sql` tanpa audit skema.

## Cara mencoba tanpa menimpa backend yang berhasil

1. Hentikan terminal Uvicorn lama (`Ctrl+C`). Jangan menghapus `backend_integrasi` atau `venv` lama.
2. Ekstrak ZIP ke folder terpisah, misalnya `D:\VarEscape\kelompok-05\backend_admin_integrasi` (di dalamnya terdapat subfolder `backend`).
3. Di WSL, masuk ke folder hasil ekstraksi:

   ```bash
   cd /mnt/d/VarEscape/kelompok-05/backend_admin_integrasi/backend
   ```

4. Salin `.env` dari backend lama (jangan salin file ini ke chat):

   ```bash
   cp ../../backend_integrasi/.env .env
   ```

5. Gunakan virtual environment backend lama (tidak perlu pip install ulang bila paketnya sudah sama):

   ```bash
   source ../../backend_integrasi/venv/bin/activate
   ```

6. Di DBeaver, backup database dahulu, lalu jalankan `migrations/003_add_suspended_status.sql` pada `varescape_db`.
7. Pastikan `.env` berisi origin frontend, misalnya `ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`. Restart server bila mengubah `.env`.
8. Jalankan:

   ```bash
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

9. Pastikan server berjalan, lalu buka `http://127.0.0.1:8000/docs` dan cari kelompok **Administrator**. Backend lain tidak boleh aktif di port 8000 secara bersamaan.
10. Di frontend, login Administrator pada `http://localhost:3000/admin/login`; uji antrean persetujuan lalu pemantauan server.

## Membuat akun admin (jika belum ada)

`seed_admin.py` dapat membuat ADMIN + ACTIVE, tetapi jangan mengirimkan password admin di chat atau menyertakan `.env` ke ZIP. Script `seed_admin.py` lama menerima password sebagai argumen CLI; itu dapat tersimpan dalam history terminal. Pertimbangkan menggunakan mekanisme rahasia yang aman untuk lingkungan sebenarnya.

## Kontrak frontend terbaru

| Frontend | Endpoint backend | Catatan |
|---|---|---|
| `src/lib/api.js` `getAccounts` | `GET /api/v1/admin/accounts` | array akun (tanpa password/token) |
| `setAccountStatus` | `PATCH /api/v1/admin/accounts/{id}/status` | `status_aktif` sesuai tombol |
| `getAdminHealth` | `GET /api/v1/admin/health` | hanya ADMIN; metrik yang tidak ada = `null` |
| `resetAccountPassword` | `POST /api/v1/admin/accounts/{id}/reset-password` | **501** sampai mekanisme verifikasi dikembangkan |

### Kontrol akses

- `get_current_user` memeriksa status `ACTIVE` dari database pada setiap request, sehingga token yang masih berlaku tidak memberi akses ketika akun sudah `SUSPENDED`.
- `/api/v1/admin/*` hanya `ADMIN + ACTIVE`.
- `/api/v1/analysis/*` hanya `RESEARCHER + ACTIVE`.
- `/api/v1/public/*` tetap publik sesuai visibilitas hasil.

## Batasan yang masih perlu diperhatikan

- Reset password aman, pengiriman email, dan audit log permanen **belum tersedia**.
- Halaman health frontend menggambarkan HPC/Nextflow, sedangkan backend adalah FastAPI BackgroundTasks. `queue` hanya berasal dari run berstatus PENDING/RUNNING di PostgreSQL; jangan mengartikan sebagai antrean scheduler HPC nyata.
- `cpu_percent` dan telemetri I/O/daemon yang belum diinstrumentasi dikembalikan sebagai `null`, bukan angka perkiraan.
- Validasi lengkap pipeline dan hasil anotasi **belum diuji** dalam perubahan ini; jangan menganggap hasil biologis telah tervalidasi.
- Secret key default hanya aman untuk development. Gunakan `.env` yang terisi kunci kuat sebelum memperluas akses.
- Backend masih membutuhkan kontrol ukuran unggahan dan audit keamanan tambahan sebelum deployment produksi.

## Uji cepat

Dari WSL atau browser, buka `http://127.0.0.1:8000/docs` untuk memeriksa endpoint. API Administrator memakai **Bearer token** hasil login akun ADMIN; non-admin harus mendapat HTTP `403` dan tanpa token mendapat `401`/`403` sesuai handler autentikasi.

Saat beralih ke backend baru, jangan menghapus PostgreSQL lama atau menjalankan `CREATE DATABASE` ulang.
