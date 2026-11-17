// Menu sidebar per peran (sesuai frame Figma)
export const NAV = {
  researcher: [
    { to: '/guide', label: 'Panduan', icon: 'info' },
    { to: '/analysis/new', label: 'Analisis baru', icon: 'upload' },
    { to: '/progress', label: 'Progres', icon: 'clock' },
    { to: '/result', label: 'Hasil', icon: 'check-circle' },
    { to: '/history', label: 'Riwayat analisis', icon: 'file' },
  ],
  reader: [
    { to: '/public', label: 'Berkas publik', end: true, icon: 'globe' },
    { to: '/public/history', label: 'Riwayat berkas', icon: 'clock' },
    { to: '/public/result', label: 'Hasil', icon: 'check-circle' },
  ],
  admin: [
    { to: '/admin/accounts', label: 'Kelola akun', icon: 'user' },
    { to: '/admin/health', label: 'Health check', icon: 'server' },
    { to: '/admin/history', label: 'Riwayat analisis', icon: 'clock' },
  ],
}
export const ROLE_LABEL = { researcher: 'Peneliti', reader: 'Pembaca', admin: 'Administrator' }
