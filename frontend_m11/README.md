# VarEscape Frontend

React 19 + Vite + react-router-dom v7, CSS biasa (tanpa Tailwind). Struktur sama dengan `frontend_m9`.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build
```

API: `VITE_API_URL` (default `http://localhost:8000/api/v1`), semua lewat `src/lib/api.js`.
Font Public Sans dimuat dari Google Fonts (`index.html`).

## Rute
| Rute | Layar |
|---|---|
| `/` | Landing (hero + animasi read pileup) |
| `/login`, `/register` | Masuk / Daftar Peneliti |
| `/public/login` | Masuk Pembaca (guest) |
| `/admin/login` | Masuk Administrator |
| `/guide`, `/analysis/new`, `/analysis/:id/progress`, `/analysis/:id/result`, `/history` | Peneliti |
| `/public`, `/public/history`, `/public/:id/result` | Pembaca |
| `/admin/accounts`, `/admin/health` | Administrator |

## TODO backend (belum ada di kode referensi)
- `GET /admin/accounts`, `PATCH /admin/accounts/{id}/status`, `POST .../reset-password` (Kelola Akun)
- `GET /admin/health` (fallback ke `/health`); nama field telemetri adalah asumsi (Health Check)
- Unduh ZIP laporan, unduh VCF, batalkan analisis, restart daemon, berkas contoh: tombol dinonaktifkan
- Respons login sebaiknya membawa `user.role` (dipakai validasi login Administrator)

## Pengganti aset
Ikon kecil = SVG Lucide inline (`src/components/Icon.jsx`), bukan ikon asli Figma.
Ikon KPI/langkah di Panduan diganti singkatan teks/ikon Lucide.
Logo = `Logo_BIFIVE.png` (src/assets/logo.png).

## Landing
Animasi: `src/lib/pileup.js` (mesin murni) + `src/pages/Landing.jsx` (Canvas 2D + rAF, hormati `prefers-reduced-motion`).
Data mutasi (N501Y, dst.) hanya contoh, bukan hasil analisis.

## Revisi M11
- `/analysis/new`: label "Opsional" dihapus; ditambah kartu **Parameter Analisis** (Default / Custom, 6 parameter) di antara validasi 3 lapis dan tombol jalankan. Payload `POST /analysis/{id}/run`: `{ execution_mode, parameters }` (default -> `parameters: {}`). Aturan/rentang di `src/lib/params.js`.
- Sidebar: membuka hasil dari Riwayat menandai tab **Hasil** (`layouts/Layout.jsx`).
- `/analysis/:id/progress`: pipeline jadi **4 stasiun** (stasiun 5 dihapus). Di "Log pipeline per stasiun" tiap stasiun menampilkan metrik, interpretasi otomatis, dan tombol unduh (`src/lib/diagnostics.js`). Unduhan memakai `fetch` + token (`downloadFile` di `api.js`).
- Teks "SARS-CoV-2" dikembalikan seperti m10 (Login, Register, footer Auth, Panduan, Riwayat, Berkas publik).

### Kontrak backend yang diasumsikan (sesuaikan bila beda)
`GET /analysis/{id}/status` membawa `stations_diagnostic.station_1..4` = `{ status_code, badge_color, interpretation, metrics: {...}, download_files: [{label, url}] }`, plus opsional `effective_parameters`. Bila `interpretation` kosong, FE menghitungnya dari `metrics` dengan aturan yang sama dengan rancangan. Rute unduh bawaan bila `download_files` tidak dikirim: `/analysis/{id}/download/stasion{N}/{html|fastq|bam|bai|vcf|csv|zip}`.
