# Spesifikasi Kontrak API VarEscape (Minggu 7)

Dokumen ini berisi spesifikasi teknis antarmuka *Application Programming Interface* (API) untuk platform analisis variasi genomik **VarEscape**.

---

## 1. Informasi Umum

* **Base URL**: `http://localhost:8000/api/v1`
* **Format Request/Response**: `application/json` (kecuali pada endpoint unggah berkas menggunakan `multipart/form-data`)
* **Standard Response Status Codes**:
  * `200 OK`: Permintaan berhasil diproses.
  * `201 Created`: Data/sumber daya baru berhasil dibuat.
  * `400 Bad Request`: Input data tidak valid.
  * `422 Unprocessable Entity`: Error validasi skema data dari FastAPI.
  * `500 Internal Server Error`: Kesalahan pada sisi server/database.

---

## 2. Endpoint Infrastruktur

### 2.1. Health Check
Memeriksa status operasional server *backend* dan koneksi database PostgreSQL.

* **URL**: `/health`
* **Method**: `GET`
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
    "registration_reason": "Penelitian SARS-CoV-2"
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

---

## 4. Endpoint Workbench & Analisis Genom

### 4.1. Unggah Berkas Analisis (`UC-05`)
Menerima 4 berkas mentah sequencing untuk memulai sesi *variant calling*.

* **URL**: `/analysis/upload`
* **Method**: `POST`
* **Headers**: `Content-Type: multipart/form-data`
* **Form Parameters**:
  * `sample_name` *(string, required)*: Nama sampel (contoh: `s1`).
  * `file_fastq_r1` *(file, required)*: Berkas FASTQ Read 1 (`.fastq` / `.fastq.gz`).
  * `file_fastq_r2` *(file, required)*: Berkas FASTQ Read 2 (`.fastq` / `.fastq.gz`).
  * `file_fasta` *(file, required)*: Berkas sekuens rujukan FASTA (`.fasta`).
  * `file_iedb` *(file, required)*: Berkas prediksi epitope IEDB (`.csv` / `.tsv`).
* **Response (`201 Created`)**:
  ```json
  {
    "run_id": "VE-A3F3",
    "sample_name": "s1",
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

### 4.2. Cek Status Progres Analisis
Mengambil status tahapan pipeline *variant calling* yang sedang berjalan.

* **URL**: `/analysis/{run_id}/status`
* **Method**: `GET`
* **Path Parameter**: `run_id` *(string)* - Contoh: `VE-A3F3`
* **Response (`200 OK`)**:
  ```json
  {
    "run_id": "VE-A3F3",
    "status": "RUNNING",
    "current_stage": "ALIGNMENT",
    "progress_percentage": 45
  }
  ```

### 4.3. Ambil Hasil Analisis Genom
Mengambil daftar variasi mutasi dan analisis *immune escape* dari sesi analisis yang selesai.

* **URL**: `/analysis/{run_id}/results`
* **Method**: `GET`
* **Path Parameter**: `run_id` *(string)* - Contoh: `VE-A3F3`
* **Response (`200 OK`)**:
  ```json
  {
    "run_id": "VE-A3F3",
    "sample_name": "s1",
    "variants_found": 12,
    "escape_score": 0.85,
    "variants": [
      {
        "gene": "S",
        "mutation": "D614G",
        "impact": "HIGH"
      }
    ]
  }
  ```

### 4.4. Ubah Visibilitas Hasil Analisis
Mengatur apakah hasil analisis dapat diakses oleh publik atau bersifat privat.

* **URL**: `/analysis/{run_id}/visibility`
* **Method**: `PATCH`
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