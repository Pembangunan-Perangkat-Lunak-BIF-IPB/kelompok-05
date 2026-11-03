import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPublicResults, viewedFiles } from '../lib/api'
import ResultViewer from '../components/ResultViewer'
import './pages.css'

// Hasil Berkas Publik: Result Viewer hanya baca (tanpa visibilitas, tanpa ubah data)
export default function PublicResult() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stop = false
    setData(null)
    getPublicResults(runId)
      .then((d) => {
        if (stop) return
        setData(d)
        setError('')
        viewedFiles.add({ run_id: runId, sample_name: d.sample_name })
      })
      .catch((err) => {
        if (stop) return
        setError(err.status === 403 || err.status === 404
          ? 'Berkas ini tidak tersedia untuk umum. Mungkin tidak ditemukan atau berstatus PRIVATE.'
          : err.message)
      })
    return () => { stop = true }
  }, [runId])

  return (
    <div className="page">
      <header>
        <h1>Hasil berkas publik {runId}</h1>
        <p className="muted">
          {data ? <>Sampel <strong>{data.sample_name}</strong> · hanya baca</> : 'Memuat hasil…'}
        </p>
      </header>

      {error && (
        <>
          <p className="msg bad" role="alert">{error}</p>
          <Link className="btn" to="/public">Kembali ke Berkas Publik</Link>
        </>
      )}
      {data && <ResultViewer data={data} fileName={runId} />}
    </div>
  )
}
