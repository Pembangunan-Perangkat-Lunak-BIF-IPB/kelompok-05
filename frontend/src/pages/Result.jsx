import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getResults, lastRun, setVisibility } from '../lib/api'
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
    getResults(runId).then((d) => { if (!stop) { setData(d); setError('') } }).catch((err) => { if (!stop) setError(err.message) })
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
