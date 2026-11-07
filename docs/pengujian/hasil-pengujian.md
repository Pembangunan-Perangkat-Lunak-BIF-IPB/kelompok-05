# Hasil Pengujian VarEscape (Minggu 6–9)

Penguji: Candra Rizky P. K. (PM, merangkap Tester)  
Tanggal: 3 November 2026  
Versi diuji: gabungan branch PR #27 (frontend M9) dan PR #28 (backend M9), dijalankan lokal (PostgreSQL 16, FastAPI/uvicorn, build Vite).  
Data uji valid: `sample1_R1/R2.fastq.gz` (nf-core/viralrecon test data, SARS-CoV-2 paired-end), genom acuan MN908947.3, `epitopes.csv` (koordinat epitope protein S).  
Data uji tidak valid: FASTA berekstensi `.txt`, FASTA 51 MB, `.fastq.gz` dengan signature rusak, pasangan R1/R2 dengan header berbeda, IEDB dengan koordinat 29900–30010, satu berkas FASTQ tanpa pasangan.

## Ringkasan

| Jenis uji | Jumlah kasus | PASS | FAIL |
|---|---|---|---|
| Uji unit backend | 20 | 17 | 3 |
| Uji API end-to-end | 29 | 19 | 10 |
| Uji antarmuka end-to-end (Playwright) | 17 | 14 | 3 |
| **Total** | **66** | **50** | **16** |

## Checklist Acceptance Criteria SKPL

| Kebutuhan | Kriteria penerimaan | Kasus uji | Hasil |
|---|---|---|---|
| UC-01 Registrasi | Akun baru tersimpan berstatus PENDING_APPROVAL; email ganda ditolak | UJ-M8-01, UJ-M8-01b, FE-02, FE-03 | PASS |
| UC-02 Login | Sandi salah ditolak; akun PENDING tidak dapat masuk dan melihat pesan menunggu persetujuan | UJ-M8-02a–d, UJ-M8-03, FE-01, FE-04–06 | FAIL (akun PENDING tetap mendapat token) |
| UC-04 Validasi 3 Lapis | Format, ukuran, signature gzip, header R1/R2, dan koordinat IEDB divalidasi dengan pesan jelas | UB-01–UB-10, UJ-M7-02, UJ-M7-04, UJ-M8-04, UJ-M8-05, FE-07–FE-10 | FAIL (gzip rusak dan koordinat di luar rentang menghasilkan HTTP 500 di backend) |
| UC-05 Unggah berkas | Empat berkas valid tersimpan dan run_id dibuat | UJ-M7-01, UJ-M7-05, FE-11 | PASS |
| UC-06 Jalankan analisis | Status berubah PENDING → RUNNING → COMPLETED | UJ-M8-06, FE-12 | PASS |
| UC-07 Progres dan log | Status tiap stasiun berubah satu per satu dan log per stasiun tersedia | UJ-M8-07, UJ-M9-06 | FAIL (log kosong) |
| UC-08 Result Viewer | Varian, metrik run, filter, dan sort tampil | UJ-M8-08, UJ-M9-01, UJ-M9-03–05, FE-13 | FAIL (metrik kosong; FE menampilkan 0 varian) |
| UC-09 Skor risiko | Grantham Distance dan risk_level sesuai rumus SA | UB-11–UB-18, UJ-M9-02 | FAIL (tanpa SnpEff, Grantham bernilai 0) |
| UC-10 Visibilitas dan publik | PRIVATE hanya untuk pemilik; PUBLIC dapat dibaca tanpa login | UJ-M9-07–12, FE-14, FE-16, FE-17 | FAIL (non-pemilik dapat mengubah visibilitas; detail publik HTTP 500) |
| UC-09 Riwayat | Riwayat hanya berisi run milik pengguna | UJ-M8-09, FE-15 | PASS |

## Uji Unit Backend

| ID | Fitur | Kebutuhan | Langkah | Harapan | Aktual | Status |
|---|---|---|---|---|---|---|
| UB-01 | Header R1/R2 cocok | UC-04, BR-10 | validate_fastq_pairs pada pasangan read1/1–read1/2 | Diterima tanpa galat | Diterima tanpa galat | PASS |
| UB-02 | Header R1/R2 tidak cocok | UC-04, BR-10 | Read kedua R2 diberi ID berbeda (readX) | Ditolak HTTP 422 | HTTP 422: Validasi Lapis 2 Gagal: Header FASTQ R1 ('read2') dan R2 ('readX') tidak cocok pada baris 5. | PASS |
| UB-03 | FASTQ .gz format Illumina 1.8+ | UC-04, BR-10 | Pasangan .gz dengan header "A1 1:N:0" dan "A1 2:N:0" | Diterima tanpa galat | Diterima tanpa galat | PASS |
| UB-04 | FASTA satu contig | UC-04, BR-11 | FASTA 1 contig 29.903 bp | Mengembalikan panjang 29903 | Panjang = 29903 | PASS |
| UB-05 | FASTA lebih dari satu contig | UC-04, BR-11 | FASTA berisi 2 contig | Ditolak HTTP 422 | HTTP 422: Validasi Lapis 2 Gagal: Berkas FASTA memiliki 2 contig. Diperlukan tepat 1 contig genom acuan. | PASS |
| UB-06 | FASTA tanpa header | UC-04, BR-11 | FASTA tanpa baris ">" | Ditolak HTTP 422 | HTTP 422: Validasi Lapis 2 Gagal: Berkas FASTA tidak memiliki header contig (memulai dengan '>'). | PASS |
| UB-07 | Koordinat epitope dalam rentang | UC-04, BR-12 | Epitope 22500–22520 dan 23050–23070, genom 29.903 bp | Diterima tanpa galat | Diterima tanpa galat | PASS |
| UB-08 | Koordinat epitope di luar 1–29.903 | UC-04, BR-12 | Epitope 29900–30010 | Ditolak HTTP 422 dengan pesan Lapis 3 | NameError: name 'cite' is not defined | FAIL |
| UB-09 | Berkas IEDB format TSV dengan kolom start/end | UC-04, BR-12 | TSV kolom "start" dan "end" | Diterima tanpa galat | Diterima tanpa galat | PASS |
| UB-10 | Koordinat epitope bukan angka | UC-04, BR-12 | start_pos = "abc" | Ditolak HTTP 422 | HTTP 422: Validasi Lapis 3 Gagal: Baris 2 nilai koordinat [abc-120] bukan integer yang valid. | PASS |
| UB-11 | Parsing perubahan asam amino SnpEff | UC-09 | parse_snpeff_amino_acid_change("S: p.Asn501Tyr") | ("N", "Y") | ('N', 'Y') | PASS |
| UB-12 | Nilai Grantham N→Y | UC-09 | get_grantham_score("N", "Y") | 143 (Grantham 1974) | 143 | PASS |
| UB-13 | Nilai Grantham simetris | UC-09 | get_grantham_score("Y", "N") | 143 | 143 | PASS |
| UB-14 | Batas risk_level (HIGH > 100, MODERATE 51–100, LOW 0–50) | UC-09, BR-14 | calculate_risk_level pada G = 143, 101, 100, 51, 50, 0 dan di luar epitope | Sesuai rumus SA | 143→HIGH, 101→HIGH, 100→MODERATE, 51→MODERATE, 50→LOW, 0→LOW, 180 (luar)→OUTSIDE_EPITOPE | PASS |
| UB-15 | Pemetaan posisi ke epitope | UC-09 | is_in_iedb_epitope pada 22510 (dalam) dan 22600 (luar) | True lalu False | (True, False) | PASS |
| UB-16 | Syarat varian PASS (DP ≥ 10, MQ ≥ 30, QUAL ≥ 30, AF ≥ 0,20) | BR-14 | check_variant_pass pada 6 kombinasi termasuk nilai batas | Hanya varian yang memenuhi keempat syarat yang PASS | Semua 6 kombinasi sesuai | PASS |
| UB-17 | Rasio Ts/Tv | UC-08 | 2 transisi (A>G, C>T) dan 2 transversi (A>C, G>T) | Ts = 2, Tv = 2, rasio 1,0 | (2, 2, 1.0) | PASS |
| UB-18 | Parser VCF menghitung Grantham dari anotasi ANN | UC-09 | VCF berisi N501Y (23063) di dalam epitope 23050–23070 | Grantham 143, risk_level HIGH | 3 baris; posisi 23063 → Grantham 143, risk HIGH | PASS |
| UB-19 | Varian di bawah threshold tidak disimpan | BR-14 | VCF berisi varian 22000 dengan DP = 4 dan QUAL = 12 | Varian tidak masuk variant_results | Varian 22000 (DP=4, QUAL=12) tersimpan | FAIL |
| UB-20 | Kolom snpeff_effect terisi | UC-08 | Parser VCF pada varian dengan anotasi ANN | snpeff_effect berisi p.Asn501Tyr | snpeff_effect = None | FAIL |

## Uji API End-to-End

| ID | Minggu | Fitur | Kebutuhan | Langkah | Harapan | Aktual | Status |
|---|---|---|---|---|---|---|---|
| UJ-M8-01 | M8 | Registrasi akun Peneliti | UC-01 | POST /auth/register dengan data Peneliti baru | HTTP 201, akun tersimpan berstatus PENDING_APPROVAL | HTTP 201: {"message": "Registrasi berhasil", "user_id": 1}; status di DB = PENDING_APPROVAL | PASS |
| UJ-M8-01b | M8 | Registrasi email yang sudah terdaftar | UC-01 | POST /auth/register dengan email yang sama | Ditolak HTTP 400 | HTTP 400: {"detail": "Email sudah terdaftar"} | PASS |
| UJ-M8-02a | M8 | Login dengan kata sandi salah | UC-02 | POST /auth/login dengan sandi salah | Ditolak HTTP 401 | HTTP 401: {"detail": "Email atau password salah"} | PASS |
| UJ-M8-02b | M8 | Login akun berstatus PENDING_APPROVAL | UC-02 | POST /auth/login sebelum akun disetujui | Respons login memuat status_aktif PENDING_APPROVAL agar frontend menampilkan pesan menunggu persetujuan | HTTP 200; user.status_aktif = None | FAIL |
| UJ-M8-02c | M8 | Akses API memakai token akun PENDING_APPROVAL | UC-02 | GET /analysis dengan token akun yang belum disetujui | Ditolak (akun belum aktif) | HTTP 200: [] | FAIL |
| UJ-M8-02d | M8 | Login akun aktif | UC-02 | POST /auth/login setelah akun disetujui | HTTP 200 dengan access_token | access_token diterima | PASS |
| UJ-M8-03 | M8 | Akses endpoint Peneliti tanpa login | UC-02 | GET /analysis tanpa header Authorization | Ditolak HTTP 401/403 | HTTP 401: {"detail": "Not authenticated"} | PASS |
| UJ-M7-01 | M7 | Unggah 4 berkas valid | UC-05, FR-01 | POST /analysis/upload dengan R1, R2, FASTA, IEDB valid | HTTP 201, run_id dibuat, keempat berkas PASS | HTTP 201: {"run_id": "VE-D266", "sample_name": "sample1 SARS-CoV-2 nf-core", "status": "PENDING", "uploaded_files_summary": [{"file_type": "FASTQ_R1", "file_name": "sample1_R1.fastq.gz", "validation_status": "PASS"}, {"f | PASS |
| UJ-M7-05 | M7 | Data unggahan tersimpan | UC-05 | Periksa tabel analysis_runs dan uploaded_files | 1 baris analysis_runs berstatus PENDING dan 4 baris uploaded_files | analysis_runs = [('PENDING',)]; uploaded_files = 4 baris | PASS |
| UJ-M7-02 | M7 | Unggah berkas dengan ekstensi salah | UC-05, Lapis 1 | FASTA diunggah dengan ekstensi .txt | Ditolak HTTP 400 dengan pesan format | HTTP 400: {"detail": "Format berkas FASTA Genom Acuan tidak valid (reference.txt). Ekstensi yang diizinkan: ('.fasta', '.fa', '.fna')"} | PASS |
| UJ-M7-04 | M7 | Unggah .gz dengan signature rusak | UC-05, Lapis 1 | R1 berupa berkas .fastq.gz yang isinya rusak | Ditolak HTTP 400/422 dengan pesan gzip tidak valid | HTTP 500: "Internal Server Error" | FAIL |
| UJ-M8-04 | M8 | Header R1/R2 tidak cocok | UC-04, BR-10 | R2 read kedua diberi ID berbeda | Ditolak HTTP 422 oleh Validasi Lapis 2 | HTTP 422: {"detail": "Validasi Lapis 2 Gagal: Header FASTQ R1 ('M03352:174:000000000-J3R29:1:1102:10416:1755') dan R2 ('READ_BERBEDA') tidak cocok pada baris 5."} | PASS |
| UJ-M8-05 | M8 | Koordinat epitope di luar 1–29.903 | UC-04, BR-12 | IEDB berisi epitope 29900–30010 | Ditolak HTTP 422 oleh Validasi Lapis 3 | HTTP 500: "Internal Server Error" | FAIL |
| UJ-M8-06 | M8 | Jalankan analisis | UC-06 | POST /analysis/VE-D266/run | Status berubah dari PENDING ke RUNNING | HTTP 200: {"run_id": "VE-D266", "status": "RUNNING", "message": "Pipeline analisis berhasil dipicu di latar belakang"} | PASS |
| UJ-M8-07 | M8 | Pantau status 5 stasiun | UC-07 | Polling GET /status tiap 2 detik sampai selesai | Status tiap stasiun berubah satu per satu sampai COMPLETED atau FAILED | Akhir: COMPLETED dalam ±14 detik; urutan status: PENDING['PENDING'] → RUNNING['PENDING', 'RUNNING'] → COMPLETED['COMPLETED'] | PASS |
| UJ-M9-06 | M9 | Log setiap stasiun tersedia | UC-07 | Periksa pipeline_logs pada respons GET /status | Log per stasiun (1–5) tersedia | 0 baris log | FAIL |
| UJ-M8-08 | M8 | Lihat hasil berdasarkan run_id | UC-08 | GET /analysis/VE-D266/results | Tabel varian dari variant_results tampil | HTTP 200: {"run_id": "VE-D266", "sample_name": "sample1 SARS…; VCF berisi 19 varian, variant_results berisi 19 varian | PASS |
| UJ-M8-09 | M8 | Riwayat analisis milik pengguna | UC-09 | GET /analysis dengan token Peneliti A | Daftar memuat run milik Peneliti A saja | 1 run dikembalikan | PASS |
| UJ-M9-01 | M9 | Ringkasan metrik run | UC-08 | Periksa metrik Q20/Q30, mapping rate, read depth, Ts/Tv pada GET /results | Seluruh metrik terisi angka | metrik = {} | FAIL |
| UJ-M9-02 | M9 | Grantham Distance dan risk_level per varian | UC-09, BR-14 | Periksa grantham_score dan risk_level setiap varian | Varian missense di dalam epitope memiliki Grantham > 0 dan risk_level sesuai rumus | sebaran risk_level = {'LOW': 2, 'OUTSIDE_EPITOPE': 17}; Grantham > 0 = 0 varian | FAIL |
| UJ-M9-03 | M9 | Anotasi efek SnpEff | UC-08 | Periksa kolom snpeff_effect | snpeff_effect terisi | 0 dari 19 varian memiliki snpeff_effect | FAIL |
| UJ-M9-04 | M9 | Urutan default hasil | UC-08 | Periksa urutan varian pada GET /results | Urut risk_level tertinggi lalu posisi naik | 19 varian, urutan sesuai | PASS |
| UJ-M9-05 | M9 | Filter hasil (rentang posisi, risk_level) | UC-08 | GET /results?min_pos=241&max_pos=5476 dan ?risk_level=outside_epitope | Hanya varian yang sesuai filter dikembalikan | rentang: 10 varian; risk_level OUTSIDE_EPITOPE: 17 varian | PASS |
| UJ-M9-07 | M9 | Hasil PRIVATE dibuka Peneliti lain | UC-10, BR-21 | Peneliti B membuka GET /results milik Peneliti A | Ditolak HTTP 403/404 | HTTP 403: {"detail": "Anda tidak memiliki hak akses untuk melihat hasil analisis PRIVATE ini."} | PASS |
| UJ-M9-08 | M9 | Peneliti lain mengubah visibilitas | UC-10, BR-21 | Peneliti B memanggil PATCH /visibility pada run milik Peneliti A | Ditolak HTTP 403, visibilitas tetap PRIVATE | HTTP 200: {"run_id": "VE-D266", "visibility": "PUBLIC", "message": "Visibilitas analisis berhasil diubah menjadi VisibilityType.PUBLIC"}; visibilitas di DB = PUBLIC | FAIL |
| UJ-M9-09 | M9 | Hasil PRIVATE dibuka Pembaca Publik | UC-10, BR-22 | GET /public/analyses/{run_id}/results tanpa token | Ditolak HTTP 403 | HTTP 403: {"detail": "Analisis ini berstatus PRIVATE dan tidak dapat diakses publik."} | PASS |
| UJ-M9-10 | M9 | Pemilik mengubah visibilitas menjadi PUBLIC | UC-10 | Peneliti A memanggil PATCH /visibility | HTTP 200, visibilitas menjadi PUBLIC | HTTP 200: {"run_id": "VE-D266", "visibility": "PUBLIC", "message": "Visibilitas analisis berhasil diubah menjadi VisibilityType.PUBLIC"} | PASS |
| UJ-M9-11 | M9 | Katalog Berkas Publik tanpa login | UC-10, BR-23 | GET /public/analyses tanpa token | HTTP 200, hanya run berstatus PUBLIC | HTTP 200: [{"visibility": "PUBLIC", "user_id": 1, "created_at": "2026-11-03T15:5…; 1 run PUBLIC | PASS |
| UJ-M9-12 | M9 | Detail hasil PUBLIC tanpa login | UC-10, BR-23 | GET /public/analyses/{run_id}/results tanpa token | HTTP 200 berisi varian dan metrik | HTTP 500: "Internal Server Error" | FAIL |

## Uji Antarmuka End-to-End

| ID | Skenario | Catatan | Status |
|---|---|---|---|
| FE-01 | Rute terlindungi tanpa login dialihkan ke /login | http://localhost:3000/login | PASS |
| FE-02 | Validasi kata sandi < 8 karakter di halaman daftar | pesan muncul: true | PASS |
| FE-03 | Pendaftaran berhasil, status menunggu persetujuan | status DB: PENDING_APPROVAL | PASS |
| FE-04 | Login akun PENDING ditolak dengan pesan menunggu persetujuan | URL setelah login: http://localhost:3000/guide | FAIL |
| FE-05 | Login salah sandi menampilkan pesan galat | Email atau password salah | PASS |
| FE-06 | Login akun ACTIVE berhasil | http://localhost:3000/guide | PASS |
| FE-07 | Lapis 1: ekstensi salah ditolak di FE | BerkasUkuran1. Format2. Header3. KoordinatStatusFASTQ_R1-----FASTQ_R2-----wrong.txt1 KBFormat harus .fasta, .fa, .fna--GagalIEDB----- | PASS |
| FE-08 | Lapis 1: FASTA > 50 MB ditolak di FE | BerkasUkuran1. Format2. Header3. KoordinatStatusFASTQ_R1-----FASTQ_R2-----big.fasta51 MBUkuran maksimal 50 MB--GagalIEDB----- | PASS |
| FE-09 | Lapis 1: gzip rusak ditolak di FE | BerkasUkuran1. Format2. Header3. KoordinatStatusbad_R1.fastq.gz1 KBSignature gzip tidak valid--Gagalbad_R2.fastq.gz1 KBSignature gzip tidak valid--GagalFASTA-----IEDB----- | PASS |
| FE-10 | Pasangan R1/R2 tidak lengkap ditolak | Pilih tepat 2 berkas dengan penamaan _R1 dan _R2 | PASS |
| FE-11 | Unggah berkas valid, validasi 3 lapis PASS, tombol eksekusi aktif | run_id VE-EE6A | PASS |
| FE-12 | Jalankan analisis menuju halaman progres | http://localhost:3000/analysis/VE-EE6A/progress | PASS |
| FE-13 | Progres selesai lalu hasil tampil dengan tabel varian | Pipeline COMPLETED dan API mengembalikan 19 varian di kunci "variants", namun FE membaca "variant_results" sehingga tabel menampilkan 0 varian | FAIL |
| FE-14 | Pengaturan visibilitas dari halaman hasil (inspeksi varian tidak dapat diuji karena tabel kosong) | visibility DB menjadi PUBLIC | PASS |
| FE-15 | Halaman riwayat menampilkan analisis | run_id ada: true | PASS |
| FE-16 | Katalog publik menampilkan analisis PUBLIC | run_id ada: true | PASS |
| FE-17 | Hasil publik dapat dibuka pembaca | baris 0 Server tidak dapat dihubungi. Pastikan backend berjalan di port 8000. | FAIL |

## Daftar Bug

| ID | Bug | Kasus uji | Peran | Lokasi |
|---|---|---|---|---|
| BUG-01 | Respons login tidak memuat `user.status_aktif` karena `response_model=TokenResponse`, dan akun PENDING_APPROVAL tetap mendapat token serta dapat memanggil API | UJ-M8-02b, UJ-M8-02c, FE-04 | BE | routers/auth.py |
| BUG-02 | Unggah `.fastq.gz` dengan isi rusak menghasilkan HTTP 500, bukan 400/422 | UJ-M7-04 | BE | utils/validators.py |
| BUG-03 | Koordinat IEDB di luar 1–29.903 menghasilkan HTTP 500 (NameError dari sisa teks `[cite: 14]`) | UJ-M8-05, UB-08 | BE | utils/validators.py baris 128 |
| BUG-04 | Status stasiun tidak berubah satu per satu (hanya stasiun 1 yang pernah RUNNING) | UJ-M8-07 | BE | services/pipeline |
| BUG-05 | Log per stasiun tidak tersimpan (belum ada model PipelineLog), halaman Progres kosong | UJ-M9-06 | BE | models.py |
| BUG-06 | Metrik Q20/Q30, mapping rate, read depth, Ts/Tv tidak dihitung dan disimpan (`summary_metrics` bernilai null) | UJ-M9-01 | BE | models.py, pipeline |
| BUG-07 | SnpEff belum dijalankan sehingga `snpeff_effect` kosong dan Grantham bernilai 0 untuk semua varian | UJ-M9-02, UJ-M9-03, UB-20 | BE | pipeline stasiun 5 |
| BUG-08 | Filter varian PASS (`check_variant_pass`) tidak dipanggil; varian DP=2 ikut tersimpan | UB-19 | BE | pipeline stasiun 4 |
| BUG-09 | PATCH /analysis/{run_id}/visibility tidak memeriksa pemilik; Peneliti lain dapat membuat hasil menjadi PUBLIC | UJ-M9-08 | BE | routers/analysis.py |
| BUG-10 | GET /public/analyses/{run_id}/results menghasilkan HTTP 500 (`VariantResult.pos` seharusnya `position`) | UJ-M9-12, FE-17 | BE | routers/public.py |
| BUG-11 | Frontend membaca `variant_results`, sedangkan backend mengirim `variants`; halaman Hasil menampilkan 0 varian walaupun 19 varian tersimpan | FE-13 | FE + BE | ResultViewer.jsx, Result.jsx |
| BUG-12 | Pesan visibilitas menampilkan `VisibilityType.PUBLIC`, bukan `PUBLIC` | UJ-M9-10 | BE | routers/analysis.py |

## Uji Regresi Bug M7

TC-04 (registrasi FAIL pada Minggu 7) diuji ulang dan kini PASS (UJ-M8-01, FE-03).
