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
├── frontend/          # kode tampilan (Raihan)
├── backend/           # kode server dan migrasi basis data (Afifah)
└── docs/
    └── pengujian/     # checklist dan skenario uji (Guruh)
```

## Prasyarat

Install dulu sebelum menjalankan aplikasi (versi diisi Raihan dan Afifah):

- Git
- Node.js versi …
- Python versi …
- PostgreSQL versi …

## Cara Menjalankan

### 1. Ambil kode

```bash
git clone https://github.com/Pembangunan-Perangkat-Lunak-BIF-IPB/kelompok-05.git
cd kelompok-05
```

### 2. Siapkan basis data

<!-- Diisi Afifah: cara membuat database, username/password, file .env -->

```bash
# contoh: createdb varescape
```

### 3. Jalankan backend

<!-- Diisi Afifah -->

```bash
cd backend
# perintah install dependency
# perintah menjalankan migrasi tabel
# perintah menjalankan server
```

Cek berhasil: buka `http://localhost:…/health` → harus muncul status `ok` dan database `connected`.

### 4. Jalankan frontend

<!-- Diisi Raihan -->

```bash
cd frontend
# perintah install dependency
# perintah menjalankan frontend
```

Cek berhasil: buka `http://localhost:…` → tampil halaman beranda.

## Kendala Umum

<!-- Diisi Guruh dari hasil mencoba README ini di laptop sendiri -->

| Masalah | Solusi |
| --- | --- |
| … | … |

## Tautan

- GitHub Project: https://github.com/users/candrarizkyk/projects/1
- Prototype Figma: https://www.figma.com/proto/MYJ4HR4Lh39ukfgmDuwA5Z/Update-W6-High-Fidelity-VarEscape-BIFIVE---FIX?page-id=0%3A1&node-id=4007-284&p=f&viewport=410%2C229%2C0.05&t=nt7iCAxbEMk6XiCp-1&scaling=min-zoom&content-scaling=fixed&starting-point-node-id=4007%3A284&show-proto-sidebar=1
