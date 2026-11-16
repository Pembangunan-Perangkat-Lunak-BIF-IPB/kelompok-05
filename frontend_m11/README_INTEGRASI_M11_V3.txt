VARESCAPE M11 V3 — FRONTEND TERINTEGRASI (14 November 2026)
============================================================
Basis: frontend_m11_v3.zip yang dikirim pengguna.
Folder frontend_m11_v3 lengkap; tidak ada node_modules.

CARA PASANG DI WINDOWS CMD
  cd <lokasi>\frontend_m11_v3
  npm ci
  npm run build
  npm run dev

PERUBAHAN
- NewAnalysis.jsx: PERTAHANKAN validasi antarmuka 2 lapis dan upload otomatis.
  Catatan: backend tetap menjalankan pemeriksaan FASTQ sesuai kode backendnya.
  Pilih nama sampel dan parameter (default/custom) SEBELUM memilih FASTQ R1+R2,
  karena parameter disimpan di endpoint /upload (bukan /run).
  Setelah upload selesai, pengguna tetap klik Jalankan Analisis.
- api.js: FormData sesuai backend M11, request /run tanpa payload parameter,
  getArtifacts, cancelAnalysis, unduh hasil memakai autentikasi.
- Progress.jsx: getStatus + getResults + getArtifacts; hasil stasiun yang
  telah selesai dapat dilihat/diunduh meski keseluruhan FAILED.
  Cancel memakai confirm -> POST /analysis/{run_id}/cancel -> refresh status;
  status tidak dipalsukan menjadi CANCELLED.
- diagnostics.js: metrik dari respons backend; angka metrik format Indonesia.
  Interpretasi otomatis ditampilkan dari backend; decimal bertitik pada teks
  interpretasi diganti koma dalam tampilan.
- Result.jsx: penggabungan getResults + getStatus sehingga status dan metrik
  bisa tampil untuk run FAILED.
- ResultViewer.jsx: memakai varian modal Lihat Detail sebelumnya (tetap utuh),
  tombol PDF/ZIP hanya aktif untuk COMPLETED sesuai batas endpoint backend.
- risk.js: dukungan summary_metrics dan field variant backend.

BATASAN PENTING YANG PERLU DIKERJAKAN DI BACKEND
1. Endpoint POST /api/v1/analysis/{run_id}/cancel saat ini BELUM tersedia
   pada analysis(10).py yang telah disediakan. Selama RUNNING, tombol dapat
   mengirim permintaan, tetapi backend 404/405 tidak membatalkan proses.
   Jangan menganggap pembatalan berhasil hanya dari perubahan UI. Backend
   harus menghentikan subprocess aktif dan menyimpan status CANCELLED.
2. PDF dan ZIP untuk FAILED masih diblokir oleh _require_complete backend.
   Oleh karena itu tombol PDF/ZIP dinonaktifkan untuk FAILED. Hasil per
   stasiun berhasil tetap dapat diunduh dari Progress via /artifacts.
3. Angka metrik Progress diambil dari /results jika tersedia atau
   summary_metrics di /status. Apabila kedua endpoint tidak mengirim
   nilai, UI menampilkan '-' (bukan angka rekayasa).
4. Backend tidak boleh melabeli status anotasi SnpEff COMPLETED jika
   tidak ada varian dianotasi. Kasus 0 PASS ditangani di backend, bukan FE.
5. Interpretasi backend tetap dijadikan sumber utama; format persen di
   teks diganti koma sebagai penyesuaian tampilan, bukan perubahan nilai.

SIMPAN CADANGAN FILE LOKAL SEBELUM MENIMPA.
