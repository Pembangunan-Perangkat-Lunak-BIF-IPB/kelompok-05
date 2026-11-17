
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPublicResults, viewedFiles } from '../lib/api'
import ResultViewer from '../components/ResultViewer'

// Detail satu hasil analisis PUBLIC.
// Pengguna Pembaca hanya memiliki akses read-only.
export default function PublicResult() {
  const { runId } = useParams()

  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    setData(null)
    setError('')

    async function loadResult() {
      try {
        const response = await getPublicResults(runId)

        if (!active) return

        setData(response)

        // Simpan hasil terakhir dilihat hanya sebagai penanda.
        // Tidak digunakan untuk mengalihkan menu Hasil.
        viewedFiles.add({
          run_id: runId,
          sample_name: response.sample_name,
        })
      } catch (err) {
        if (!active) return

        if (err.status === 403 || err.status === 404) {
          setError(
            'Hasil analisis ini tidak tersedia untuk publik. ' +
            'Berkas mungkin tidak ditemukan atau berstatus PRIVATE.'
          )
        } else {
          setError(
            err.message || 'Gagal memuat detail hasil analisis.'
          )
        }
      }
    }

    loadResult()

    return () => {
      active = false
    }
  }, [runId])

  return (
    <>
      {error && (
        <div>
          <p className="alert error" role="alert">
            {error}
          </p>

          <Link
            className="btn btn-ghost"
            style={{ marginTop: 12 }}
            to="/public/results"
          >
            Kembali ke Daftar Hasil
          </Link>
        </div>
      )}

      {!data && !error && (
        <p className="muted">
          Memuat detail hasil analisis...
        </p>
      )}

      {data && (
        <>
          <div style={{ marginBottom: 16 }}>
            <Link
              className="btn btn-ghost"
              to="/public/results"
            >
              ← Kembali ke Daftar Hasil
            </Link>
          </div>

          <ResultViewer
            data={data}
            runId={runId}
            mode="reader"
          />
        </>
      )}
    </>
  )
}
