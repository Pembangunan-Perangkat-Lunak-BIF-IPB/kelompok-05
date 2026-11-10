import { Link } from 'react-router-dom'

export default function Placeholder({ title }) {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#f8fafc', padding: 24 }}>
      <div className="card" style={{ maxWidth: 420, textAlign: 'center' }}>
        <h1 className="page-title" style={{ fontSize: 20 }}>{title}</h1>
        <p className="page-sub">Halaman yang Anda cari tidak tersedia.</p>
        <Link className="btn btn-primary" style={{ marginTop: 16 }} to="/">Kembali ke beranda</Link>
      </div>
    </div>
  )
}
