# VarEscape — Tahap Integrasi Backend Minggu 9–10

Versi ini adalah **perbaikan kontrak API, kontrol ekspor, dan dokumentasi**, dibuat dari `VarEscape_backend_admin_kompatibel.zip`. Tidak menghitung ulang metrik, memperbarui pipeline biologis, atau memigrasikan database secara otomatis.

## A. Apa yang berubah

- `routers/analysis.py`: `GET /api/v1/analysis/{run_id}/status` sekarang menyertakan `created_at`, `started_at`, `completed_at` (nilai waktu run asli dari DB), dan endpoint ekspor `GET /api/v1/analysis/{run_id}/export/{format}`.
- `utils/serializers.py`: setiap entri `pipeline_logs` menambahkan `created_at` penuh (ISO 8601), **tanpa menghilangkan** `timestamp` jam-menit-detik yang sudah dibaca frontend.
- `tests/test_status_exports.py`: tes terisolasi SQLite (tanpa koneksi database produksi) untuk status, ekspor, dan perlindungan PRIVATE.
- README dan panduan ini: langkah uji dan batasan.

### Format ekspor

| Format | URL | Ketentuan |
|---|---|---|
| CSV | `/analysis/{run_id}/export/csv` | Hanya pemilik, run `COMPLETED`, isi tabel `variant_results` |
| TSV | `/analysis/{run_id}/export/tsv` | Hanya pemilik, run `COMPLETED`, isi tabel `variant_results` |
| Annotated VCF | `/analysis/{run_id}/export/vcf` | Hanya pemilik, run `COMPLETED`, file `variants.ann.vcf` harus ada serta mempunyai header dan anotasi ANN |
| Run Log | `/analysis/{run_id}/export/logs` | Hanya pemilik, bisa juga saat RUNNING/FAILED |
| Konfigurasi | `/analysis/{run_id}/export/config` | Hanya pemilik, JSON pengaturan server saat ini (tanpa `.env`/password), **bukan** konfigurasi historis saat run |

Status HTTP: `403` bukan pemilik, `404` run atau berkas tidak ditemukan, `409` hasil belum final/anotasi tidak ada, `400` format tidak dikenal.

> Ketika `COMPLETED` tampil, itu hanya menandakan pipeline selesai secara perangkat lunak. Validitas anotasi, kualitas referensi, dan evaluasi biologis perlu verifikasi terpisah. Jangan mengartikan `grantham_score=0` secara otomatis sebagai hasil valid.

## B. Cara pemasangan tanpa merusak backend lama

1. Pastikan backend lama yang bekerja tetap dibackup, dan buat **backup database** PostgreSQL sebelum mengganti kode/migrasi.
2. Ekstrak ZIP ini ke `D:\VarEscape\kelompok-05\backend_minggu10`. Setelah ekstraksi seharusnya ada `backend_minggu10/backend/main.py`.
3. Di WSL:

   ```bash
   cd /mnt/d/VarEscape/kelompok-05/backend_minggu10/backend
   cp ../../backend_integrasi/.env .env
   source ../../backend_integrasi/venv/bin/activate
   python -m pip check
   ```

   Jika lokasi `backend_integrasi` berbeda, sesuaikan path sumbernya. **Jangan tampilkan password dari `.env` di chat.**
4. **Penting:** agar upload/VCF lama tidak hilang dari jangkauan, pada `.env` revisi tambahkan/pertahankan path upload lama jika memang data lama berada di sana:

   ```dotenv
   UPLOAD_DIR=/mnt/d/VarEscape/kelompok-05/backend_integrasi/uploads
   ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

   Ini menggunakan lokasi fisik yang sama untuk run lama dan baru. Jangan memindahkan atau menghapus `backend_integrasi/uploads` selama database masih menyimpan path tersebut. Jika sebelumnya memakai path lain, pakai path lama yang benar.
5. Jika belum melakukannya dan akan memakai status akun `SUSPENDED`, jalankan **setelah backup** migrasi `migrations/003_add_suspended_status.sql` melalui DBeaver (periksa dulu apakah nilai `SUSPENDED` sudah ada).
6. Hentikan Uvicorn lama (Ctrl+C), lalu di direktori baru jalankan:

   ```bash
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

7. Pastikan `http://127.0.0.1:8000/api/v1/health` menampilkan server dan database sehat, lalu cek `/docs` untuk endpoint `/analysis/{run_id}/status` dan `/analysis/{run_id}/export/{format}`.
8. Login sebagai akun `RESEARCHER` yang `ACTIVE`, buka `/docs`, klik **Authorize**, masukkan token yang valid, lalu tes status dengan `run_id` milikmu yang sudah ada. Token bersifat rahasia, jangan tempel di laporan publik.

### Uji status UC-07 (bukti screenshot)

- `GET /api/v1/analysis/{run_id}/status`, dengan `run_id` dari riwayat asli, bukan contoh statis.
- Simpan respons yang memuat `overall_status`, `created_at`, `started_at`, `completed_at`, `stations` (lima), dan `pipeline_logs` (`station_number`, `timestamp`, `created_at`, `log_level`, `message`).
- `started_at` bisa `null` bila run masih PENDING, dan `completed_at` bisa `null` bila belum selesai.

### Uji ekspor

- Di Swagger: panggil `GET /api/v1/analysis/{run_id}/export/csv`, `/tsv`, `/logs`, `/config`, `/vcf` menggunakan **run milikmu**.
- VCF anotasi yang belum tersedia harus mengembalikan `404`/`409`, bukan file VCF mentah yang dilabeli seolah sudah teranotasi.
- Coba token akun peneliti lain: permintaan ekspor run milik orang lain harus `403`.
- Frontend yang sedang digunakan **belum otomatis menekan tombol unduh untuk seluruh lima endpoint baru**. Integrasi tombol untuk TSV/VCF/log/config adalah langkah frontend lanjutan bila dibutuhkan.

### SQL read-only untuk bukti DBeaver

```sql
SELECT run_id, status, visibility, created_at, started_at, completed_at,
       q20_rate, q30_rate, mapping_rate, mean_depth, tstv_ratio
FROM public.analysis_runs
ORDER BY created_at DESC
LIMIT 10;

-- Ganti run_id dengan ID run nyata milikmu.
SELECT station_number, log_level, created_at, LEFT(message, 160) AS message
FROM public.pipeline_logs
WHERE run_id = 'ISI_RUN_ID_NYATA'
ORDER BY id;

SELECT run_id, position, ref_allele, alt_allele, snpeff_effect,
       grantham_score, risk_level
FROM public.variant_results
WHERE run_id = 'ISI_RUN_ID_NYATA'
ORDER BY position
LIMIT 20;
```

Jangan membocorkan alamat email, token, password, data sampel sensitif, atau path sistem pengguna saat mengambil screenshot.

## C. Cakupan pekerjaan checklist

**Minggu 9**

1. UC-07 waktu dan log: **ditambahkan** di revisi ini; uji langsung masih perlu.
2. Quality Filtering dan Epitope Mapping: **sudah ada** di pipeline sebelum revisi ini; tidak kami modifikasi dan belum diverifikasi secara ilmiah.
3. Q20/Q30, mapping rate, mean depth, Ts/Tv: **kolom dan logika penyimpanan sudah ada** pada backend sebelumnya; validasi data hasil masih perlu.
4. SnpEff dan IEDB: **sudah ada mekanisme dalam kode**, tetapi kelengkapan/akurasi anotasi dan penyimpanan relasi epitope masih perlu penilaian khusus; jangan dianggap selesai hanya karena HTTP 200.
5. Hasil PRIVATE: kontrol pemilik untuk endpoint status/ekspor dan hasil milik sendiri tersedia; uji token peneliti lain.
6. Bukti request/response dan `variant_results`: **harus diambil dari laptop & DB nyata** menggunakan panduan di atas, tidak bisa dihasilkan dengan screenshot sintetis.
7. Blok kode `README.md`: **sudah rapi**, bagian ini tidak diubah oleh patch selain menambahkan dokumentasi.

**Minggu 10**

1. Admin login/persetujuan/penolakan: berasal dari backend admin sebelum revisi ini (perlu migrasi `SUSPENDED` dan pengujian nyata).
2. Health Check publik/admin: sudah ada sebelum revisi ini (perlu uji langsung).
3. Ekspor CSV/TSV/Annotated VCF/Run Log/Konfigurasi: **endpoint ditambahkan**; VCF hanya apabila berkas anotasi tersedia. Tidak menjamin validitas ilmiah.
4. `run_id`: endpoint berbasis parameter `run_id`; frontend memilih ID saat navigasi riwayat (tetap perlu uji UI nyata).
5. Guest: halaman publik dapat membaca data `PUBLIC` tanpa login melalui `/api/v1/public/...`. **Login Guest tersendiri belum dibuat** karena pola guest yang ada bersifat anonim. Jika spesifikasi UC mewajibkan autentikasi Guest, ini masih tugas tersendiri.
6. Kelola akun: daftar akun, persetujuan, penolakan, suspend sudah ada; **reset password masih HTTP 501** dan memerlukan verifikasi aman.

## D. Tes otomatis

Di virtual environment proyek:

```bash
python -m pip install pytest
python -m pytest -q tests/test_status_exports.py
```

Enam tes mengarah ke database SQLite sementara (bukan PostgreSQL `varescape_db`). Lulus tes tidak menggantikan pengujian end-to-end dengan PostgreSQL dan browser.

## E. Batasan khusus

- Tidak mengubah `utils/pipeline.py`, `utils/snpeff.py`, `utils/vcf_parser.py` atau algoritme penilaian biologis.
- Skor nol ketika anotasi tidak tersedia **masih merupakan risiko interpretasi**, belum selesai pada revisi ini.
- Ekspor konfigurasi tidak menyimpan snapshot pengaturan run pada saat eksekusi; ekspor secara eksplisit diberi label konfigurasi server **saat ini**.
- Belum ada batas ukuran upload server-side yang ketat; jangan expose aplikasi ke internet publik sebelum ditangani.
- Validasi ilmiah data referensi dan hasil anotasi perlu review khusus.
