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
