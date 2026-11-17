
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
    { to: '/public/results', label: 'Hasil' },
  ],

  admin: [
    { to: '/admin/accounts', label: 'Kelola akun' },
    { to: '/admin/health', label: 'Health check' },
    { to: '/admin/history', label: 'Riwayat analisis' },
  ],
}

export const ROLE_LABEL = {
  researcher: 'Peneliti',
  reader: 'Pembaca',
  admin: 'Administrator',
}
