import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getResults, setVisibility } from '../lib/api'
import './pages.css'

export default function Result() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let stop = false
    getResults(runId)
      .then((d) => { if (!stop) { setData(d); setError('') } })
      .catch((err) => { if (!stop) setError(err.message) })
    return () => { stop = true }
  }, [runId])

  async function toggleVisibility() {
    const next = data.visibility === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC'
    setSaving(true)
    try {
      const r = await setVisibility(runId, next)
      setData((d) => ({ ...d, visibility: r.visibility }))
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const variants = data?.variant_results ?? []

  return (
    <div className="page">
      <header>
        <h1>Hasil analisis {runId}</h1>
        <p className="muted">
          {data ? <>Sampel <strong>{data.sample_name}</strong> · {data.total_variants} varian</> : 'Memuat hasil…'}
        </p>
      </header>

      {error && <p className="msg bad" role="alert">{error}</p>}

      {data && (
        <>
          <section className="card row-between">
            <span>Visibilitas: <strong>{data.visibility}</strong></span>
            <button className="btn" onClick={toggleVisibility} disabled={saving}>
              Jadikan {data.visibility === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC'}
            </button>
          </section>

          <section className="card">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>Posisi</th><th>Ref</th><th>Alt</th><th>QUAL</th><th>DP</th><th>Efek SnpEff</th><th>Grantham</th><th>Risiko</th></tr>
                </thead>
                <tbody>
                  {variants.map((v) => (
                    <tr key={v.id}>
                      <td>{v.position}</td><td>{v.ref_allele}</td><td>{v.alt_allele}</td>
                      <td>{v.qual ?? '-'}</td><td>{v.dp ?? '-'}</td>
                      <td>{v.snpeff_effect ?? '-'}</td><td>{v.grantham_score ?? '-'}</td><td>{v.risk_level ?? '-'}</td>
                    </tr>
                  ))}
                  {!variants.length && <tr><td colSpan={8}>Belum ada varian. Pipeline analisis belum menghasilkan data.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
