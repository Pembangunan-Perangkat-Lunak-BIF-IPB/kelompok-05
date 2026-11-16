# VarEscape — Referensi REST API (backend M11, empat stasiun)

**Dokumen:** backend/docs/api.md  
**Cakupan:** implementasi FastAPI yang diserahkan tim pada 15 November 2026.

> **Peringatan versi:** kontrak di bawah berasal dari file backend M11 terbaru yang diserahkan, **belum tentu sesuai dengan branch main GitHub sebelum kode M11 disinkronkan**. Setelah menjalankan backend, gunakan **http://127.0.0.1:8000/docs** dan **/openapi.json** sebagai sumber kebenaran endpoint dari instance yang benar-benar berjalan. Contoh payload di sini bersifat ilustratif, bukan rekaman hasil biologis nyata.

## 1. Informasi umum

| Properti | Nilai |
|---|---|
| API base URL | http://127.0.0.1:8000/api/v1 |
| Framework | FastAPI, Python, SQLAlchemy, PostgreSQL |
| Format biasa | JSON (application/json) |
| Unggah berkas | multipart/form-data |
| Unduhan | FileResponse/Response dengan Content-Disposition attachment |
| Auth | JWT Bearer |
| OpenAPI | http://127.0.0.1:8000/docs |
| Reference | SARS-CoV-2 NC_045512.2, panjang 29.903 nt |
| Pipeline | 4 stasiun, bukan 5 |

Untuk endpoint terlindungi, kirim header:

~~~http
Authorization: Bearer TOKEN_JWT
~~~

**Jangan menaruh token di URL**. Gunakan HTTPS pada deployment non-lokal.

### Peran dan hak akses

- **RESEARCHER + ACTIVE:** workbench /analysis (daftar milik sendiri, upload, run, cancel, status, hasil, audit, unduhan, visibilitas).
- **ADMIN + ACTIVE:** /admin (daftar pengguna, status akun, riwayat semua pengguna termasuk PRIVATE, health).
- **Tanpa login:** /public dan /api/v1/health.
- **PUBLIC:** role registrasi pembaca; tidak diberi izin menjalankan workbench.
- **PENDING_APPROVAL:** dapat login, tetapi akses endpoint terlindungi menolak dengan 403 sampai disetujui.
- **REJECTED / SUSPENDED:** login ditolak dengan 403; token lama tidak boleh dipakai mengakses endpoint terlindungi.

### HTTP status codes

| Code | Makna |
|---|---|
| 200 | GET/PATCH/POST berhasil sesuai endpoint |
| 201 | Registrasi dan upload berhasil |
| 202 | Permintaan pembatalan diterima; pipeline belum tentu berhenti |
| 400 | Format ekstensi, status run, atau input tidak sah |
| 401 | Kredensial login/token salah atau token kedaluwarsa |
| 403 | Hak akses kurang, status akun tidak ACTIVE, atau run milik pengguna lain |
| 404 | Run/akun/artefak/fitur file belum tersedia |
| 409 | Konflik status run, perubahan status akun, atau hasil belum siap |
| 413 | Ukuran unggah melebihi batas |
| 422 | Validasi request Pydantic atau isi FASTQ gagal |
| 501 | Reset password administrator belum diimplementasikan |
| 503 | Koneksi PostgreSQL untuk health tidak tersedia |
| 500 | Error server tak terduga; baca traceback/log backend |

Respons error FastAPI biasa menggunakan format JSON:

~~~json
{"detail":"Pesan kesalahan"}
~~~

## 2. Inventaris endpoint

### Infrastruktur dan autentikasi

| Method | URL lengkap relatif ke /api/v1 | Autentikasi |
|---|---|---|
| GET | /health | Tidak |
| POST | /auth/register | Tidak |
| POST | /auth/login | Tidak |

Root aplikasi juga menyediakan **GET /** (di luar prefix /api/v1).

### Workbench peneliti

| Method | Path | Keterangan |
|---|---|---|
| GET | /analysis | Riwayat analisis milik peneliti |
| POST | /analysis/upload | Upload FASTQ dan konfigurasi |
| POST | /analysis/{run_id}/run | Jalankan pipeline |
| POST | /analysis/{run_id}/cancel | Minta pembatalan |
| GET | /analysis/{run_id}/status | Status, stasiun, log dan metrik |
| GET | /analysis/{run_id}/results | Varian PASS + metrik |
| GET | /analysis/{run_id}/filter-audit | Audit kandidat PASS/FILTERED |
| GET | /analysis/{run_id}/artifacts | Daftar file hasil yang tersedia |
| GET | /analysis/{run_id}/artifacts/{artifact_id} | Download satu artefak |
| GET | /analysis/{run_id}/export/{format} | Ekspor csv/tsv/vcf/logs/config/pdf/zip |
| PATCH | /analysis/{run_id}/visibility | Atur PUBLIC / PRIVATE |

### Publik (tanpa JWT)

| Method | Path | Keterangan |
|---|---|---|
| GET | /public/analyses | Katalog analisis berstatus PUBLIC |
| GET | /public/analyses/{run_id}/results | Hasil analisis PUBLIC |

### Administrator (ADMIN + ACTIVE)

| Method | Path | Keterangan |
|---|---|---|
| GET | /admin/accounts | Semua akun non-admin |
| PATCH | /admin/accounts/{user_id}/status | Setujui/tolak/nonaktifkan/aktifkan |
| POST | /admin/accounts/{user_id}/reset-password | Belum aktif, HTTP 501 |
| GET | /admin/analyses | Riwayat seluruh peneliti, PUBLIC dan PRIVATE |
| GET | /admin/health | Koneksi DB, telemetri WSL, run aktif |

## 3. Infrastruktur

### GET /health

Tidak memerlukan token. Mengecek ketersediaan API dan PostgreSQL.

~~~bash
curl -i http://127.0.0.1:8000/api/v1/health
~~~

Contoh sukses:

~~~json
{"status":"healthy","database":"connected"}
~~~

Jika database gagal, mengembalikan **503** tanpa membocorkan kredensial.

## 4. Autentikasi dan alur akun

### POST /auth/register

**Content-Type:** application/json.

~~~json
{
  "email": "peneliti@example.test",
  "password": "GantiDenganPasswordAman",
  "full_name": "Peneliti Contoh",
  "institution": "Laboratorium Contoh",
  "phone_number": "081234567890",
  "registration_reason": "Pengujian pipeline SARS-CoV-2",
  "role": "RESEARCHER"
}
~~~

Role self-register yang diterima: **RESEARCHER** atau **PUBLIC**. Role ADMIN tidak boleh didaftarkan sendiri (403). Email terdaftar menghasilkan 400.

Contoh **201**:

~~~json
{
  "user_id": 7,
  "email": "peneliti@example.test",
  "role": "RESEARCHER",
  "status_aktif": "PENDING_APPROVAL",
  "message": "Registrasi berhasil. Akun Anda menunggu persetujuan admin."
}
~~~

### POST /auth/login

~~~json
{
  "email": "peneliti@example.test",
  "password": "GantiDenganPasswordAman"
}
~~~

Contoh **200**:

~~~json
{
  "access_token": "JWT_DISENSOR",
  "token_type": "bearer",
  "user": {
    "id": 7,
    "email": "peneliti@example.test",
    "role": "RESEARCHER",
    "status_aktif": "ACTIVE"
  }
}
~~~

Tidak ada endpoint publik untuk registrasi ADMIN. Admin dibuat menggunakan script seed_admin.py lokal. Password disimpan dalam bentuk hash, JWT menggunakan HS256 dengan waktu kedaluwarsa ACCESS_TOKEN_EXPIRE_MINUTES.

### Contoh alur cURL

~~~bash
BASE=http://127.0.0.1:8000/api/v1
curl -sS "$BASE/health"
curl -sS -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"peneliti@example.test","password":"PASSWORD_LOKAL"}'
~~~

Simpan JWT hasil login secara aman sebagai variabel shell sementara, bukan di repository.

## 5. Workbench: riwayat, upload, parameter

### GET /analysis

**Syarat:** RESEARCHER + ACTIVE.

Respons berupa **array** riwayat analisis yang dimiliki token saat ini, urut terbaru:

~~~json
[
  {
    "run_id": "VE-EXAMPLE123",
    "sample_name": "Sampel Contoh",
    "status": "COMPLETED",
    "visibility": "PRIVATE",
    "execution_mode": "default",
    "annotation_status": "COMPLETED",
    "created_at": "2026-11-15T09:00:00+00:00",
    "started_at": "2026-11-15T09:01:00+00:00",
    "completed_at": "2026-11-15T09:10:00+00:00",
    "parameters": {
      "min_dp": 10,
      "min_mq": 30,
      "min_base_quality": 20,
      "max_depth": 10000,
      "min_qual": 30.0,
      "min_af": 0.2
    }
  }
]
~~~

Respons sebenarnya juga dapat memuat metrik/counters melalui serializer run. Nilai angka pada contoh bukan hasil eksperimen nyata.

### POST /analysis/upload

**Syarat:** RESEARCHER + ACTIVE.  
**Content-Type:** multipart/form-data.  
**Status sukses:** 201.

Form:

| Field | Tipe | Wajib | Catatan |
|---|---|---|---|
| sample_name | string | Ya | Tidak boleh kosong |
| file_fastq_r1 | UploadFile | Ya | .fastq, .fq, .fastq.gz, .fq.gz |
| file_fastq_r2 | UploadFile | Tidak di signature backend | Dianjurkan untuk paired-end; nama R1/R2 sesuai pasangan |
| execution_mode | string | Tidak | default atau custom |
| min_dp | int | Bila custom | >= 1; default 10 |
| min_mq | int | Bila custom | 0–60; default 30 |
| min_base_quality | int | Bila custom | 0–60; default 20 |
| max_depth | int | Bila custom | 100–100000; default 10000 |
| min_qual | float | Bila custom | >= 0; default 30.0 |
| min_af | float | Bila custom | 0.01–1; default 0.20 |

**Perubahan dari versi lama:** tidak ada lagi form file_fasta dan file_iedb. Referensi **NC_045512.2** diambil dari backend/reference/NC_045512.2.fasta. Server memeriksa panjang genom sistem **29.903 nt** dan menolak instalasi yang referensinya tidak valid.

Backend melakukan validasi ekstensi dan struktur FASTQ; ukuran maksimum pada implementasi ini **1 GiB per FASTQ** (R1 dan R2). Berkas referensi yang dikelola sistem mempunyai batas konfigurasi tersendiri, tetapi tidak diunggah pengguna lewat endpoint ini.

Contoh default dengan FASTQ paired-end:

~~~bash
curl -X POST "$BASE/analysis/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "sample_name=sample_uji" \
  -F "file_fastq_r1=@/path/sample_R1.fastq.gz" \
  -F "file_fastq_r2=@/path/sample_R2.fastq.gz" \
  -F "execution_mode=default"
~~~

Contoh custom: tambahkan seluruh enam parameter dengan -F. Jika salah satu parameter custom tidak diisi, validasi menghasilkan **422**.

Contoh respons **201** (disingkat):

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "sample_name": "sample_uji",
  "status": "PENDING",
  "execution_mode": "default",
  "parameters": {
    "min_dp": 10,
    "min_mq": 30,
    "min_base_quality": 20,
    "max_depth": 10000,
    "min_qual": 30.0,
    "min_af": 0.2
  },
  "uploaded_files_summary": [
    {"file_type":"FASTQ_R1","file_name":"sample_R1.fastq.gz","validation_status":"PASS"},
    {"file_type":"FASTQ_R2","file_name":"sample_R2.fastq.gz","validation_status":"PASS"},
    {"file_type":"FASTA","file_name":"NC_045512.2.fasta","validation_status":"PASS"}
  ],
  "validation_results": {
    "FASTQ_R1": {
      "format": "PASS",
      "header": "PASS",
      "sequence_integrity": "PASS",
      "read_count": 1000
    }
  }
}
~~~

Nilai/detail validasi mengikuti fungsi validators.py yang terpasang; contoh menggambarkan bentuk informasi, bukan seluruh field untuk setiap format.

## 6. Mulai, batalkan, dan pantau pipeline

### POST /analysis/{run_id}/run

Hanya pemilik run dengan status **PENDING** dapat memicu. Server mengubah status menjadi RUNNING secara atomik kemudian memulai FastAPI BackgroundTasks.

~~~bash
curl -X POST "$BASE/analysis/VE-EXAMPLE123/run" \
  -H "Authorization: Bearer $TOKEN"
~~~

Contoh:

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "status": "RUNNING",
  "message": "Pipeline analisis berhasil dipicu di latar belakang"
}
~~~

Permintaan kedua pada run yang sudah dimulai ditolak; jangan menganggap endpoint idempoten untuk memulai ulang.

### POST /analysis/{run_id}/cancel

**Status sukses: 202 Accepted**, hanya saat run RUNNING dan hanya oleh pemilik.

~~~bash
curl -X POST "$BASE/analysis/VE-EXAMPLE123/cancel" \
  -H "Authorization: Bearer $TOKEN"
~~~

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "status": "CANCELLATION_REQUESTED",
  "message": "Permintaan diterima. Tunggu /status sampai status CANCELLED; proses masih mungkin berjalan."
}
~~~

**202 bukan berarti CANCELLED sudah terjadi.** Periksa GET /status sampai terminal. Backend menulis marker pembatalan untuk pemeriksaan oleh pipeline.

### GET /analysis/{run_id}/status

**Owner only.** Menggabungkan status run, **empat stasiun**, metrik, interpretasi deskriptif, timestamps, dan log.

Contoh struktur (nilai dipersingkat):

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "sample_name": "sample_uji",
  "overall_status": "COMPLETED",
  "created_at": "2026-11-15T09:00:00+00:00",
  "started_at": "2026-11-15T09:01:00+00:00",
  "completed_at": "2026-11-15T09:10:00+00:00",
  "cancellation_requested": false,
  "stations": [
    {"station":1,"name":"Quality Control (fastp)","status":"COMPLETED"},
    {"station":2,"name":"Read Mapping (BWA-MEM2)","status":"COMPLETED"},
    {"station":3,"name":"Variant Calling (BCFtools)","status":"COMPLETED"},
    {"station":4,"name":"Quality Filtering & SnpEff Annotation","status":"COMPLETED"}
  ],
  "summary_metrics": {
    "q20_before": null,
    "q30_before": null,
    "q20_rate": null,
    "q30_rate": null,
    "reads_before": null,
    "reads_after": null,
    "passed_reads_pct": null,
    "adapter_trimmed_pct": null,
    "mapping_rate": null,
    "mean_depth": null,
    "unmapped_reads": null,
    "genome_coverage_pct": null,
    "genome_coverage_30x_pct": null,
    "raw_variant_count": null,
    "raw_snp_count": null,
    "raw_indel_count": null,
    "tstv_ratio": null,
    "passed_variant_count": null,
    "filtered_variant_count": null,
    "annotated_variant_count": null,
    "annotation_status": "COMPLETED"
  },
  "station_interpretations": {},
  "pipeline_logs": [
    {
      "station_number": 1,
      "timestamp": "09:01:02",
      "created_at": "2026-11-15T09:01:02+00:00",
      "log_level": "INFO",
      "message": "Memulai Stasiun 1..."
    }
  ]
}
~~~

Null berarti data belum tersedia, **bukan angka 0**. Station interpretations berasal dari fungsi backend; sebagian entri bisa null ketika tidak ada data.

Status run: **PENDING, RUNNING, COMPLETED, FAILED, CANCELLED**. Status annotation: **PENDING, COMPLETED, FAILED, SKIPPED**.

Saat **0 PASS**, filtering boleh selesai dengan SnpEff **SKIPPED**, dan run keseluruhan tetap **COMPLETED** jika tidak ada error teknis.

## 7. Hasil dan audit filtering

### GET /analysis/{run_id}/results

Query opsional:

| Parameter | Tipe | Keterangan |
|---|---|---|
| snpeff_effect | string | Filter efek anotasi |
| min_pos | integer | Posisi genom minimal |
| max_pos | integer | Posisi genom maksimal |

**Tidak ada parameter risk_level pada endpoint terbaru.** Fitur klasifikasi epitope/Grantham lama tidak dipakai.

Respons (potongan representatif):

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "sample_name": "sample_uji",
  "status": "COMPLETED",
  "visibility": "PRIVATE",
  "started_at": null,
  "completed_at": null,
  "summary_metrics": {
    "q20_rate": null,
    "q30_rate": null,
    "mapping_rate": null,
    "mean_depth": null,
    "tstv_ratio": null,
    "tstv_note": null,
    "tstv_transition_count": null,
    "tstv_transversion_count": null,
    "total_variants": 1,
    "raw_variant_count": 2,
    "raw_snp_count": 2,
    "raw_indel_count": 0,
    "passed_variant_count": 1,
    "filtered_variant_count": 1,
    "annotation_status": "COMPLETED",
    "annotated_variant_count": 1
  },
  "variants": [
    {
      "id": 10,
      "run_id": "VE-EXAMPLE123",
      "pos": 100,
      "ref": "A",
      "alt": "G",
      "qual": 50.0,
      "dp": 30,
      "mq": 60.0,
      "af": 0.8,
      "chrom": "NC_045512.2",
      "snpeff_effect": "missense_variant",
      "gene_name": "ORF1ab",
      "impact": "MODERATE",
      "hgvs_c": null,
      "hgvs_p": null,
      "flank_left": null,
      "flank_right": null,
      "annotation_status": "PRESENT"
    }
  ]
}
~~~

Nilai pos/mutasi pada contoh **fiktif untuk kontrak API**, bukan varian yang sudah diverifikasi. Respons nyata memiliki lebih banyak field di summary_metrics termasuk jumlah efek dan QC. Field pos/ref/alt adalah nama JSON; nama kolom database position/ref_allele/alt_allele.

**Ts/Tv:** serializer hasil menghitung dari SNP PASS (bila run COMPLETED). Statistik raw Ts/Tv dari VCF mentah adalah metrik berbeda. Jika tidak ada transversion, ratio **null / tidak terdefinisi**; jangan memaksa 0 sebagai rasio. Bila daftar varian hasil sedang difilter menurut query, perhatikan implementasi perhitungan metrik agar tidak salah menganggapnya statistik run keseluruhan.

### GET /analysis/{run_id}/filter-audit

**Owner only.** Sumber: tabel **variant_filter_results** (kandidat PASS + FILTERED), bukan tabel variant_results yang berisi hasil PASS.

Contoh ketika beberapa kandidat terfilter:

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "audit_available": true,
  "total_candidates": 2,
  "passed": 1,
  "filtered": 1,
  "filtered_variants": [
    {
      "position": 101,
      "ref": "C",
      "alt": "T",
      "chrom": "NC_045512.2",
      "dp": 1,
      "qual": 12.0,
      "af": 1.0,
      "filter_status": "FILTERED",
      "filter_reason": "DP<10; QUAL<30.0"
    }
  ]
}
~~~

Contoh tidak ada baris audit dan raw count tidak lebih dari 0:

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "audit_available": false,
  "total_candidates": 0,
  "passed": 0,
  "filtered": 0,
  "filtered_variants": []
}
~~~

**404** jika raw_variant_count lebih dari 0 tetapi data audit lama belum tersimpan. Ini **bukan** hasil FILTERED 0. Audit tidak memiliki properti penentuan signifikansi klinis.

## 8. Berkas hasil dan unduhan

### GET /analysis/{run_id}/artifacts

Sumber daftar file nyata yang sudah ada, dengan stasiun selesai berdasarkan log SUCCESS:

~~~json
{
  "run_id": "VE-EXAMPLE123",
  "artifacts": [
    {
      "station": 1,
      "artifact_id": "fastp_html",
      "label": "Laporan QC fastp (HTML)",
      "filename": "fastp.html",
      "size_bytes": 12345,
      "url": "/analysis/VE-EXAMPLE123/artifacts/fastp_html"
    }
  ]
}
~~~

Nilai size_bytes contoh bukan ukuran file tertentu.

### GET /analysis/{run_id}/artifacts/{artifact_id}

Daftar artifact_id yang dikenal:

| Stasiun | artifact_id | Filename |
|---|---|---|
| 1 | fastp_html | fastp.html |
| 1 | fastp_json | fastp.json |
| 1 | clean_r1 | clean_R1.fq |
| 1 | clean_r2 | clean_R2.fq |
| 2 | aligned_bam | aligned.bam |
| 2 | aligned_bai | aligned.bam.bai |
| 2 | alignment_flagstat | alignment.flagstat.txt |
| 2 | alignment_coverage | alignment.coverage.tsv |
| 3 | raw_vcf | variants.vcf |
| 3 | variants_stats | variants.stats.txt |
| 4 | filtered_vcf | variants.filtered.vcf |
| 4 | annotated_vcf | variants.ann.vcf |

**Catatan:** file dapat tidak tersedia, misalnya clean_r2 saat single-end, atau annotated_vcf saat 0 PASS/SnpEff SKIPPED. Tidak ada akses ke path sembarang; backend menggunakan allowlist.

Contoh:

~~~bash
curl -L "$BASE/analysis/VE-EXAMPLE123/artifacts/raw_vcf" \
  -H "Authorization: Bearer $TOKEN" \
  -o variants.vcf
~~~

### GET /analysis/{run_id}/export/{format}

| format | Isi | Kondisi |
|---|---|---|
| csv | VariantResult PASS + anotasi, aman terhadap formula spreadsheet | COMPLETED |
| tsv | Sama dengan delimiter tab | COMPLETED |
| vcf | variants.ann.vcf hasil SnpEff | COMPLETED dan annotated VCF tersedia/valid |
| logs | Log hasil stasiun | Pemilik run; dapat pada terminal non-COMPLETED |
| config | JSON setting saat ini + parameter run, tanpa kredensial | Pemilik run |
| pdf | Laporan dari data tersimpan, metrik, interpretasi, audit filtering | Run terminal dan setidaknya ada artefak |
| zip | Paket artefak, metadata, log, CSV/TSV, PDF | Run terminal dan setidaknya ada artefak |

**Terminal:** COMPLETED/FAILED/CANCELLED. CSV/TSV/VCF memerlukan COMPLETED, sedangkan PDF/ZIP dapat memuat hasil parsial yang sudah tersimpan pada FAILED/CANCELLED. VCF yang belum ada dapat menghasilkan 404; jangan menganggap semua run memiliki file anotasi.

Ekspor **config** memiliki properti:

~~~json
{"configuration_scope":"current_backend_settings_not_historical_run_snapshot"}
~~~

Ini berarti sebagian nilai konfigurasi server adalah **nilai saat download**, bukan selalu snapshot historis run. Nilai rahasia seperti DB_PASSWORD dan SECRET_KEY tidak dikirim.

Contoh:

~~~bash
curl -L "$BASE/analysis/VE-EXAMPLE123/export/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -o report.pdf

curl -L "$BASE/analysis/VE-EXAMPLE123/export/zip" \
  -H "Authorization: Bearer $TOKEN" \
  -o result.zip
~~~

Perhatikan Content-Disposition untuk nama file yang diberikan server. Pelaporan PDF menggunakan report_generator.py terbaru; data audit perlu diteruskan dari router analysis.py agar tabel FILTERED muncul. File PDF untuk 0 PASS tetap menjelaskan SnpEff SKIPPED, bukan menampilkan anotasi fiktif.

## 9. Visibilitas dan akses pembaca publik

### PATCH /analysis/{run_id}/visibility

**Pemilik run saja.** Body:

~~~json
{"visibility":"PUBLIC"}
~~~

atau:

~~~json
{"visibility":"PRIVATE"}
~~~

Contoh **200**:

~~~json
{
  "run_id":"VE-EXAMPLE123",
  "visibility":"PUBLIC",
  "message":"Visibilitas analisis berhasil diubah menjadi PUBLIC"
}
~~~

Default saat upload adalah PRIVATE.

### GET /public/analyses

Tanpa JWT. Mengembalikan array run dengan visibility PUBLIC, diurutkan berdasarkan waktu pembuatan terbaru.

### GET /public/analyses/{run_id}/results

Tanpa JWT, tetapi **hanya** untuk visibility PUBLIC. Parameter opsional:

- snpeff_effect (string)
- min_pos (integer)
- max_pos (integer)

PRIVATE menghasilkan 403; run yang tidak ditemukan menghasilkan 404. Bentuk respons mengikuti build_results_response: summary_metrics dan variants. Unduhan artefak private **tidak** otomatis dibuka melalui endpoint public.

## 10. Administrator

Semua endpoint /admin memakai dependensi **require_admin** dan membutuhkan akun **ADMIN + ACTIVE**.

### GET /admin/accounts

Mengembalikan array pengguna dengan role selain ADMIN:

~~~json
[
  {
    "id":3,
    "user_id":3,
    "email":"peneliti@example.test",
    "full_name":"Peneliti Contoh",
    "institution":"IPB University",
    "role":"RESEARCHER",
    "account_role":"RESEARCHER",
    "status_aktif":"ACTIVE",
    "created_at":"2026-11-15T08:00:00+00:00"
  }
]
~~~

Role database PUBLIC ditampilkan sebagai READER untuk kompatibilitas tabel frontend, dan **account_role** tetap memuat role asli PUBLIC.

### PATCH /admin/accounts/{user_id}/status

Contoh permintaan:

~~~json
{"status_aktif":"SUSPENDED"}
~~~

Transisi status yang didukung:

| Sebelum | Sesudah |
|---|---|
| PENDING_APPROVAL | ACTIVE atau REJECTED |
| ACTIVE | SUSPENDED |
| SUSPENDED | ACTIVE |
| REJECTED | Tidak ada transisi dalam endpoint ini |

Permintaan berulang dengan status sama bersifat aman; perubahan yang tidak diizinkan menghasilkan 409; mengubah akun ADMIN sendiri lewat endpoint ini ditolak 403.

**Wajib:** enum PostgreSQL **userstatus** harus mencakup nilai SUSPENDED. Jika belum, PATCH akan menyebabkan database error; jalankan migrasi yang disetujui sebelum menguji.

### POST /admin/accounts/{user_id}/reset-password

Selalu menghasilkan **501 Not Implemented** pada akun valid non-admin. Ini disengaja: reset password butuh verifikasi dan token sekali pakai yang aman.

### GET /admin/analyses

Daftar **semua** run (termasuk PRIVATE) untuk kebutuhan monitoring admin. Tidak mengunduh berkas FASTQ.

Contoh:

~~~json
[
  {
    "run_id":"VE-EXAMPLE123",
    "sample_name":"Sampel Contoh",
    "owner_id":3,
    "owner_name":"Peneliti Contoh",
    "owner_email":"peneliti@example.test",
    "visibility":"PRIVATE",
    "status":"COMPLETED",
    "created_at":"2026-11-15T09:00:00+00:00",
    "started_at":"2026-11-15T09:01:00+00:00",
    "completed_at":"2026-11-15T09:10:00+00:00"
  }
]
~~~

### GET /admin/health

Memeriksa DB dan menampilkan observasi terbatas dari host WSL/Linux: node_id, cpu_cores, RAM terpakai/tersedia, disk terpakai/total, serta queue dari run dengan status PENDING/RUNNING. Nilai CPU utilization, temperature, daemon_status, HPC scheduler dan I/O detail dapat **null** karena tidak diukur. Queue bukan bukti adanya scheduler cluster eksternal.

## 11. Siklus eksekusi, filtering dan interpretasi ilmiah

Urutan REST standar:

1. POST /auth/register
2. Admin menyetujui akun peneliti (PATCH /admin/accounts/{id}/status)
3. POST /auth/login sebagai peneliti
4. POST /analysis/upload
5. POST /analysis/{run_id}/run
6. Poll GET /analysis/{run_id}/status
7. GET /analysis/{run_id}/results
8. GET /analysis/{run_id}/filter-audit
9. GET /analysis/{run_id}/artifacts dan GET /export/pdf atau /export/zip
10. Opsional PATCH /visibility untuk menerbitkan hasil.

Default quality filter:

| Parameter | Default | Sumber |
|---|---|---|
| DP | 10 | min_dp |
| MQ | 30 | min_mq |
| Base quality | 20 | min_base_quality |
| Max depth | 10000 | max_depth |
| QUAL | 30 | min_qual |
| AF | 0.20 | min_af |

Jika field filtering wajib tidak tersedia, implementasi dapat memberi alasan seperti DP_MISSING/MQ_MISSING/QUAL_MISSING/AF_MISSING. FILTERED berarti **tidak lolos aturan threshold**, bukan berarti mutasi biologis pasti tidak ada.

BCFtools digunakan untuk organisme haploid (ploidy 1). Rasio Ts/Tv dihitung dari SNP yang relevan; metrik raw VCF dan PASS harus dilabeli berbeda.

**Status COMPLETED** membuktikan eksekusi pipeline, **bukan** validitas diagnostik, fenotipe, signifikansi klinis, transmisi, atau immune escape. Bandingkan dengan benchmark/Galaxy bila ingin menyampaikan validasi ilmiah.

## 12. Contoh pengujian kontrak API

Gunakan Swagger UI untuk pengujian manual:

1. GET /health tanpa token.
2. POST /auth/register user baru.
3. Pastikan endpoint /analysis menolak PENDING_APPROVAL (403).
4. Buat/login ADMIN; PATCH akun menjadi ACTIVE.
5. Login peneliti dan upload FASTQ valid.
6. Pastikan run PENDING → RUNNING → COMPLETED/FAILED/CANCELLED dengan empat stasiun.
7. Periksa filtering 0 PASS: SnpEff SKIPPED dengan status COMPLETED jika tidak ada error teknis.
8. Pastikan /filter-audit merekam alasan kandidat FILTERED.
9. Coba unduhan PDF/ZIP/artefak.
10. Pastikan peneliti lain tidak dapat mengunduh run bukan miliknya.
11. Pastikan /public hanya menampilkan PUBLIC.
12. Uji admin/accounts/analyses dan penonaktifan status SUSPENDED.

Untuk uji Python lokal (sesuaikan dengan test suite yang sudah diperbarui):

~~~bash
python -m pytest tests -q
~~~

Jangan menafsirkan tes yang masih memakai IEDB/5-stasiun atau kontrak lama sebagai hasil pengujian implementasi M11. Uji unit tidak menggantikan end-to-end dengan FASTQ riil.

## 13. Troubleshooting HTTP dan integrasi

| Respons/gejala | Penyebab umum | Pemeriksaan |
|---|---|---|
| 401 | token expired/salah | login ulang, header Bearer |
| 403 pada /analysis | akun belum ACTIVE atau bukan RESEARCHER | status DB, role |
| 403 pada /admin | bukan ADMIN+ACTIVE | token dan role |
| 403 pada PRIVATE | pemilik tidak cocok | run.user_id, token |
| 404 pada /admin/analyses | router backend lama | gunakan admin.py terbaru; include_router |
| 404 annotated VCF | SnpEff SKIPPED atau file tidak tersedia | annotation_status, artifacts |
| 409 export | run belum memenuhi kondisi | periksa /status |
| 422 upload | FASTQ rusak/param custom tidak lengkap | respons detail |
| 413 upload | ukuran > batas | ukuran file |
| 500 enum SUSPENDED | tipe PostgreSQL userstatus lama | migrasi enum |
| 500 PDF | report_generator, data audit, nilai interpretasi | traceback Uvicorn |
| 503 health | PostgreSQL tidak tersambung | systemctl, DB_* |
| CORS di browser | origin frontend belum diizinkan | ALLOWED_ORIGINS |
| 0 PASS | kandidat gagal threshold | /filter-audit, coverage, raw VCF |

## 14. File sumber kontrak dan perawatan dokumen

- **main.py:** pendaftaran router dan health.
- **routers/auth.py:** register dan login.
- **routers/analysis.py:** workbench, file, ekspor, status dan audit.
- **routers/public.py:** katalog dan hasil publik.
- **routers/admin.py:** manajemen akun, riwayat dan telemetri.
- **schemas/auth.py, schemas/analysis.py, schemas/admin.py:** skema input.
- **utils/serializers.py:** struktur JSON hasil, run, stasiun dan log.
- **utils/result_interpretation.py:** interpretasi diagnostik.
- **utils/report_generator.py:** laporan PDF.
- **models.py:** tabel dan ENUM.
- **README.md:** instalasi WSL, DB, referensi, frontend, tools.

**Prinsip pemeliharaan:** saat endpoint atau nama field berubah, perbarui OpenAPI dan dokumen ini **bersamaan dengan commit kode**. Jangan mengirim dokumen versi M11 kepada tester jika source code yang tersedia masih versi Minggu 7.
