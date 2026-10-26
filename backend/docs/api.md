# Spesifikasi Kontrak API VarEscape (Minggu 7)

Dokumen ini berisi spesifikasi teknis antarmuka *Application Programming Interface* (API) untuk platform analisis variasi genomik **VarEscape**.

---

## 1. Informasi Umum

* **Base URL**: `http://localhost:8000/api/v1`
* **Format Request/Response**: `application/json` (kecuali pada endpoint unggah berkas menggunakan `multipart/form-data`)
* **Autentikasi**: Endpoint yang dilindungi membutuhkan header HTTP:
  ```text
  Authorization: Bearer <access_token_jwt>
* **Standard Response Status Codes**:
  * `200 OK`: Permintaan berhasil diproses.
  * `201 Created`: Data/sumber daya baru berhasil dibuat.
  * `400 Bad Request`: Input data tidak valid.
  * `401 Unauthorized`: Token JWT tidak valid atau kedaluwarsa.
  * `404 Not Found `: Sumber daya (seperti run_id) tidak ditemukan.
  * `422 Unprocessable Entity`: Error validasi skema data dari FastAPI.
  * `500 Internal Server Error`: Kesalahan pada sisi server/database.

---

## 2. Endpoint Infrastruktur

### 2.1. Health Check
Memeriksa status operasional server *backend* dan koneksi database PostgreSQL.

* **URL**: `/health`
* **Method**: `GET`
* **Autentikasi**: Tidak diperlukan
* **Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```

---

## 3. Endpoint Autentikasi & Pengguna

### 3.1. Registrasi Pengguna Baru (`UC-01`)
Mendaftarkan akun peneliti baru ke dalam sistem.

* **URL**: `/auth/register`
* **Method**: `POST`
* **Headers**: `Content-Type: application/json`
* **Request Body**:
  ```json
  {
    "email": "peneliti@ipb.ac.id",
    "password": "Password123!",
    "full_name": "Dr. Peneliti Genom",
    "institution": "IPB University",
    "phone_number": "081234567890",
    "registration_reason": "Penelitian SARS-CoV-2",
    "role": "PUBLIC"
  }
  ```
* **Response (`201 Created`)**:
  ```json
  {
    "user_id": 1,
    "email": "peneliti@ipb.ac.id",
    "role": "RESEARCHER",
    "status_aktif": "PENDING_APPROVAL",
    "message": "Registrasi berhasil. Akun Anda menunggu persetujuan admin."
  }
  ```
### 3.2. Login Pengguna (`UC-02`)
Autentikasi akun dan penerbitan JSON Web Token (JWT).
* **URL**: `/auth/login`
* **Method**: `POST`
* **Headers**: `Content-Type: application/json`
* **Request Body**:
  ```json
  {
    "email": "peneliti@ipb.ac.id",
    "password": "Password123!"
  }
  ```
* **Response (`200 OK`)**:
  ```json
  {
  "access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
  }
  ```

---

## 4. Endpoint Workbench & Analisis Genom
### 4.1. Ambil Riwayat Analisis Pengguna
Mengambil seluruh daftar riwayat sesi analisis milik pengguna yang sedang terautentikasi.

* **URL**: `/analysis`
* **Method**: `GET`
* **Headers**: `Authorization: Bearer <jwt_token>`
* **Response (`200 OK`)**:
```json
  [
  {
    "run_id": "VE-C48A",
    "sample_name": "sampel uji 1",
    "status": "COMPLETED",
    "visibility": "PUBLIC",
    "created_at": "2026-10-26T10:00:00Z",
    "started_at": "2026-10-26T10:01:00Z",
    "completed_at": "2026-10-26T10:03:00Z"
  }
]
```
---

### 4.2. Unggah Berkas Analisis & Validasi Lapis 1–3 (`UC-04`, `UC-05`)
Menerima 4 berkas mentah sequencing (FASTQ_R1, FASTQ_R2, FASTA, IEDB) serta melakukan validasi format, header, dan rentang koordinat.

* **URL**: `/analysis/upload`
* **Method**: `POST`
* **Headers**: `Authorization: Bearer <jwt_token>, Content-Type: multipart/form-data`
* **Form Parameters**:
  * `sample_name` *(string, required)*: Nama sampel analisis (contoh: `s1`).
  * `file_fastq_r1` *(file, required)*: Berkas FASTQ Read 1 (`.fastq` / `.fastq.gz`).
  * `file_fastq_r2` *(file, required)*: Berkas FASTQ Read 2 (`.fastq` / `.fastq.gz`).
  * `file_fasta` *(file, required)*: Berkas sekuens rujukan FASTA (`.fasta`).
  * `file_iedb` *(file, required)*: Berkas prediksi epitope IEDB (`.csv` / `.tsv`/ `.gff`).
* **Response (`201 Created`)**:
  ```json
  {
  "run_id": "VE-C48A",
  "sample_name": "sampel uji 1",
  "status": "PENDING",
  "uploaded_files_summary": [
    {
      "file_type": "FASTQ_R1",
      "file_name": "sample_R1.fastq",
      "validation_status": "PASS"
    },
    {
      "file_type": "FASTQ_R2",
      "file_name": "sample_R2.fastq",
      "validation_status": "PASS"
    },
    {
      "file_type": "FASTA",
      "file_name": "reference.fasta",
      "validation_status": "PASS"
    },
    {
      "file_type": "IEDB",
      "file_name": "epitopes.csv",
      "validation_status": "PASS"
    }
  ]
  }
  ```
---
### 4.3. Pemicu Eksekusi Pipeline (`UC-06`)
Memicu eksekusi pipeline bioinformatika (5 stasiun) secara asynchronous di latar belakang (background task).

* **URL**: `/analysis/{run_id}/run`
* **Method**: `POST`
* **Headers**: `Authorization: Bearer <jwt_token>`
* **Path Parameter**: `run_id` *(string)* - Contoh: `VE-C48A`
* **Response (`200 OK`)**:
  ```json
  {
  "run_id": "VE-C48A",
  "status": "RUNNING",
  "message": "Pipeline analisis berhasil dipicu di latar belakang"
  }
  ```
---
### 4.4. Cek Status Progres 5 Stasiun (`UC-07`)
Mengambil status aktual dari 5 tahapan stasiun pemrosesan pipeline.

* **URL**: `/analysis/{run_id}/status`
* **Method**: `GET`
* **HEADRERS**: `Authorization: Bearer <jwt_token>`
* **Path Parameter**: `run_id` *(string)* - Contoh: `VE-C48A`
* **Response (`200 OK`)**:
  ```json
  {
  "run_id": "VE-C48A",
  "sample_name": "sampel uji 1",
  "overall_status": "COMPLETED",
  "stations": [
    {
      "station": 1,
      "name": "Quality Control (fastp)",
      "status": "COMPLETED"
    },
    {
      "station": 2,
      "name": "Read Mapping (BWA-MEM2)",
      "status": "COMPLETED"
    },
    {
      "station": 3,
      "name": "Variant Calling (BCFtools)",
      "status": "COMPLETED"
    },
    {
      "station": 4,
      "name": "Quality Filtering",
      "status": "COMPLETED"
    },
    {
      "station": 5,
      "name": "Epitope Mapping & Grantham",
      "status": "COMPLETED"
    }
  ]
  }
  ```
---
### 4.5. Ambil Hasil Analisis Varian
Mengambil daftar variansi mutasi genom hasil pemrosesan pipeline dari tabel database variant_results.

* **URL**: `/analysis/{run_id}/results`
* **Method**: `GET`
* Headers**: `Authorization: Bearer <jwt_token>`
* **Path Parameter**: `run_id` *(string)*- Contoh: VE-C48A
* **Response (`200 OK`)**:
  ```json
  {
  "run_id": "VE-C48A",
  "sample_name": "sampel uji 1",
  "visibility": "PUBLIC",
  "total_variants": 1,
  "variant_results": [
    {
      "id": 1,
      "run_id": "VE-C48A",
      "position": 21563,
      "ref_allele": "A",
      "alt_allele": "G",
      "qual": "225",
      "dp": 45,
      "snpeff_effect": null,
      "grantham_score": null,
      "risk_level": null
    }
  ]
  }
  ```
---
### 4.6. Ubah Visibilitas Hasil Analisis
Mengatur status akses publikasi analisis (PUBLIC atau PRIVATE).

* **URL**: `/analysis/{run_id}/visibility`
* **Method**: `PATCH`
* Headers**: `Authorization: Bearer <jwt_token>, Content-Type: application/json`
* **Path Parameter**: `run_id` *(string)*
* **Request Body**:
  ```json
  {
    "visibility": "PUBLIC"
  }
  ```
* **Response (`200 OK`)**:
  ```json
  {
    "run_id": "VE-A3F3",
    "visibility": "PUBLIC",
    "message": "Visibilitas analisis berhasil diperbarui."
  }
  ```