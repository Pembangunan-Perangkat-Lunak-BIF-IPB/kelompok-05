import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getResults, getStatus, lastRun, setVisibility } from '../lib/api'
import ResultViewer from '../components/ResultViewer'

export default function Result() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let stop = false
    lastRun.set(runId)
    setData(null)
    Promise.allSettled([getResults(runId), getStatus(runId)]).then(([results, status]) => {
      if (stop) return
      const rd = results.status === 'fulfilled' ? results.value : {}
      const sd = status.status === 'fulfilled' ? status.value : {}
      if (results.status === 'rejected' && status.status === 'rejected') {
        setError(results.reason?.message || status.reason?.message || 'Hasil tidak tersedia.')
        return
      }
      setData({
        ...rd,
        run_id: runId,
        sample_name: rd.sample_name ?? sd.sample_name,
        status: rd.status ?? rd.overall_status ?? sd.overall_status,
        summary_metrics: rd.summary_metrics ?? sd.summary_metrics ?? {},
        variant_results: rd.variant_results ?? rd.variants ?? [],
      })
      setError('')
    })
    return () => { stop = true }
  }, [runId])

  async function toggle() {
    const next = data.visibility === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC'
    setSaving(true); setNotice('')
    try {
      const r = await setVisibility(runId, next)
      setData((d) => ({ ...d, visibility: r.visibility }))
      setError('')
      setNotice(r.visibility === 'PUBLIC' ? 'Hasil kini PUBLIC dan dapat dibaca Pembaca Publik.' : 'Hasil kini PRIVATE dan hanya dapat dilihat Anda.')
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }

  return (
    <>
      {error && <p className="alert error" role="alert">{error}</p>}
      {!data && !error && <p className="muted">Memuat hasil…</p>}
      {data && <ResultViewer data={data} runId={runId} mode="owner" onToggle={toggle} saving={saving} notice={notice} />}
    </>
  )
}
