import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getResults, lastRun, setVisibility } from '../lib/api'
import ResultViewer from '../components/ResultViewer'
import './pages.css'

export default function Result() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let stop = false
    lastRun.set(runId)
    getResults(runId)
      .then((d) => { if (!stop) { setData(d); setError('') } })
      .catch((err) => { if (!stop) setError(err.message) })
    return () => { stop = true }
  }, [runId])

  async function toggleVisibility() {
    const next = data.visibility === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC'
    setSaving(true)
    setNotice('')
    try {
      const r = await setVisibility(runId, next)
      setData((d) => ({ ...d, visibility: r.visibility }))
      setError('')
      setNotice(r.visibility === 'PUBLIC'
        ? 'Hasil kini PUBLIC dan dapat dibaca Pembaca Publik.'
        : 'Hasil kini PRIVATE dan hanya dapat dilihat Anda.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page">
      <header>
        <h1>Hasil analisis {runId}</h1>
        <p className="muted">
          {data ? <>Sampel <strong>{data.sample_name}</strong> · {data.total_variants ?? data.variant_results?.length ?? 0} varian</> : 'Memuat hasil…'}
        </p>
      </header>

      {error && <p className="msg bad" role="alert">{error}</p>}

      {data && (
        <>
          <section className="card row-between">
            <span>
              Visibilitas: <strong>{data.visibility}</strong>
              <span className="muted"> — PRIVATE hanya untuk pemilik, PUBLIC dapat dibaca Pembaca Publik.</span>
            </span>
            <button className="btn" onClick={toggleVisibility} disabled={saving}>
              {saving ? 'Menyimpan…' : `Jadikan ${data.visibility === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC'}`}
            </button>
          </section>
          {notice && <p className="msg ok" role="status">{notice}</p>}

          <ResultViewer data={data} fileName={runId} />
        </>
      )}
    </div>
  )
}
