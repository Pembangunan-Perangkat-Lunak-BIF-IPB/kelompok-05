import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPublicResults, viewedFiles } from '../lib/api'
import ResultViewer from '../components/ResultViewer'

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
    <>
      {error && (
        <>
          <p className="alert error" role="alert">{error}</p>
          <Link className="btn btn-ghost" style={{ marginTop: 12 }} to="/public">Kembali ke Berkas Publik</Link>
        </>
      )}
      {!data && !error && <p className="muted">Memuat hasil…</p>}
      {data && <ResultViewer data={data} runId={runId} mode="reader" />}
    </>
  )
}
