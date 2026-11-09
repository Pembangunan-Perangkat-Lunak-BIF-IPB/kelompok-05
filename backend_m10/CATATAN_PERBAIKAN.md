# Catatan Perbaikan Backend VarEscape

## Cara pasang

1. Timpa file lama dengan isi zip ini (struktur folder sama: `routers/`, `utils/`). Folder `schemas/` **tidak diubah**, tetap pakai punya kalian.
2. Jalankan `migrations/001_fix_schema.sql` sekali di pgAdmin (database `varescape_db`).
3. Salin `.env.example` jadi `.env`, isi `DB_PASSWORD` dan `SECRET_KEY`.
4. Aktifkan akun untuk testing (akun `PENDING_APPROVAL` sekarang ditolak di workbench):
   `UPDATE users SET status_aktif = 'ACTIVE' WHERE email = '...';`
5. Jalankan uvicorn **dari WSL** di environment yang berisi `fastp`, `bwa-mem2`, `samtools`, `bcftools` (dan `snpEff` jika ada). Kalau tool tidak ketemu, pipeline sekarang gagal dengan pesan jelas di `pipeline_logs`.

## Error yang diperbaiki

| File | Masalah | Perbaikan |
|---|---|---|
| `utils/grantham.py`, `utils/genomics.py` | Blok tes `#if __name__` dikomen tapi isinya masih menjorok → IndentationError, server gagal start | Blok tes diperbaiki |
| `utils/validators.py` | Sisa `[cite: 14]` → NameError (500) saat koordinat IEDB di luar rentang | Dihapus; FASTQ juga dicek jumlah read & header `@` |
| `routers/public.py` | Pakai `VariantResult.pos` (kolomnya `position`) → selalu 500 | Pakai helper bersama di `utils/serializers.py` |
| `models.py` | Kolom metrik (q20, q30, mapping, depth, Ts/Tv) tidak ada → tidak pernah tersimpan; `read_depth` vs `mean_depth` | Kolom ditambah, nama disamakan `mean_depth` |
| `models.py` | Model `PipelineLog` tidak ada → error pipeline tidak terlihat | Model + tabel `pipeline_logs` |
| Endpoint results | Field respons `position/ref_allele/alt_allele`, kontrak `pos/ref/alt` → tabel FE kosong | Respons dipetakan sesuai `api.md` |
| `utils/pipeline.py` | SnpEff tidak dijalankan → Grantham selalu 0 | Stasiun 5 menjalankan `snpEff ann` (bisa diatur lewat `.env`) |
| `utils/pipeline.py` | Quality filtering tidak diterapkan | Stasiun 4 memfilter DP≥10, MQ≥30, QUAL≥30, AF≥0.20 (AF dari DP4) |
| `utils/pipeline.py` | bcftools mode diploid untuk virus, error di awal pipe tidak terdeteksi, path tidak di-quote | `--ploidy 1`, `set -o pipefail`, `shlex.quote` |
| `utils/vcf_parser.py` | Nama kolom IEDB beda dengan validator → semua varian `OUTSIDE_EPITOPE`; GFF tidak terbaca | Pembaca IEDB bersama di `utils/iedb.py` (CSV/TSV/`;`/GFF) |
| `utils/vcf_parser.py` | VCF tidak ada → diam saja, run tetap COMPLETED | Sekarang melempar error → FAILED |
| Endpoint status | Status stasiun palsu (hanya stasiun 1 RUNNING) | Dihitung dari log SUCCESS/ERROR tiap stasiun |
| Endpoint results | Run PUBLIC milik orang lain ditolak | 403 hanya untuk PRIVATE non-pemilik |

## Keamanan

- PATCH `/visibility` sekarang hanya untuk pemilik run.
- Registrasi tidak bisa memilih `ADMIN` (403). Role yang diterima: `RESEARCHER`, `PUBLIC`.
- Workbench hanya untuk akun `ACTIVE`; login akun `REJECTED` ditolak.
- Berkas unggahan disimpan dengan nama tetap (`reads_R1.fastq.gz`, `reference.fasta`, dll.) → aman dari path traversal dan nama berspasi. Berkas dihapus lagi jika validasi gagal.
- Password database tidak lagi dicetak ke terminal; tidak ada password default di kode.

## Rapikan

- `main.py`: `FastAPI()` tidak lagi dibuat dua kali (judul Swagger kembali muncul).
- `routers/analysis.py`: route `GET /analysis` ganda dihapus.
- Upload di-stream per 1 MB, tidak membaca seluruh FASTQ ke RAM.
- Semua waktu disimpan sebagai UTC timezone-aware.
- `requirements.txt`: `python-jose` dan dependensinya (`ecdsa`, `rsa`, `pyasn1`) dihapus karena tidak dipakai.
- `api.md` disesuaikan dengan perilaku baru.

## Catatan untuk tim

- **SnpEff**: nama kromosom di header FASTA harus sama dengan database SnpEff (default `NC_045512.2`). Kalau beda, log Stasiun 5 akan memberi WARNING dan Grantham tetap 0.
- **Koordinat IEDB** dianggap koordinat genom (nukleotida), sama dengan POS di VCF. Kalau berkas IEDB kalian berisi posisi asam amino, perlu dikonversi dulu.
- Cara cek kalau run gagal: `GET /analysis/{run_id}/status` → lihat `pipeline_logs` dengan `log_level: "ERROR"`.
