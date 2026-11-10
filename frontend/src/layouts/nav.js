// Menu sidebar per peran (sesuai frame Figma)
export const NAV = {
  researcher: [
    { to: '/guide', label: 'Panduan' },
    { to: '/analysis/new', label: 'Analisis baru' },
    { to: '/progress', label: 'Progres' },
    { to: '/result', label: 'Hasil' },
    { to: '/history', label: 'Riwayat analisis' },
  ],
  reader: [
    { to: '/public', label: 'Berkas publik', end: true },
    { to: '/public/history', label: 'Riwayat berkas' },
    { to: '/public/result', label: 'Hasil' },
  ],
  admin: [
    { to: '/admin/accounts', label: 'Kelola akun' },
    { to: '/admin/health', label: 'Health check' },
    { to: '/admin/history', label: 'Riwayat analisis' },
  ],
}
export const ROLE_LABEL = { researcher: 'Peneliti', reader: 'Pembaca', admin: 'Administrator' }
