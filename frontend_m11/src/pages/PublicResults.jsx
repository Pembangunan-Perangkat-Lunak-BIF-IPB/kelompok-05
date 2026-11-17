
import './publicResults.css'

import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  getPublicAnalyses,
  viewedFiles,
} from '../lib/api'

// Format tanggal Indonesia.
function formatDate(value) {
  if (!value) return '-'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleDateString('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

// Ambil jumlah varian PASS jika tersedia di respons API.
// Tidak mengarang angka jika backend tidak mengirimkannya.
function getPassCount(run) {
  const candidates = [
    run.passed_variant_count,
    run.pass_variant_count,
    run.summary_metrics?.passed_variant_count,
    run.summary_metrics?.pass_variant_count,
  ]

  const count = candidates.find(
    (value) =>
      value !== null &&
      value !== undefined &&
      value !== '' &&
      Number.isFinite(Number(value))
  )

  return count === undefined
    ? null
    : Number(count)
}

export default function PublicResults() {
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  // Hanya sebagai penanda hasil terakhir dibuka.
  // Tidak menyebabkan redirect otomatis.
  const lastViewed =
    viewedFiles.list()[0]?.run_id ?? null

  useEffect(() => {
    let active = true

    async function loadAnalyses() {
      setLoading(true)

      try {
        const response = await getPublicAnalyses()

        if (!active) return

        const items = Array.isArray(response)
          ? response
          : Array.isArray(response?.items)
            ? response.items
            : []

        // Hanya tampilkan analisis PUBLIC
        // yang telah menyelesaikan pipeline.
        const completed = items.filter(
          (run) =>
            String(run.visibility ?? '').toUpperCase() ===
              'PUBLIC' &&
            String(run.status ?? '').toUpperCase() ===
              'COMPLETED'
        )

        setAnalyses(completed)
        setError('')
      } catch (err) {
        if (!active) return

        setError(
          err.message ||
          'Gagal mengambil daftar hasil analisis publik.'
        )
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadAnalyses()

    return () => {
      active = false
    }
  }, [])

  // Pencarian nama berkas, sampel, dan Run ID.
  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase()

    if (!keyword) {
      return analyses
    }

    return analyses.filter((run) => {
      const filename = `${run.run_id}_results`

      const searchable = [
        filename,
        run.run_id,
        run.sample_name,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return searchable.includes(keyword)
    })
  }, [analyses, query])

  return (
    <div className="public-results-page">

      {/* Judul halaman */}
      <div className="public-results-heading">
        <h1>Hasil Analisis Publik</h1>

        <p>
          Daftar hasil analisis varian SARS-CoV-2
          yang telah dipublikasikan oleh peneliti.
          Pilih salah satu berkas untuk melihat
          hasil variant calling, filtering,
          dan anotasi mutasi.
        </p>
      </div>

      {/* Pencarian */}
      <div className="public-results-toolbar">
        <input
          type="search"
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          placeholder="Cari nama berkas, sampel, atau Run ID..."
          aria-label="Cari hasil analisis publik"
        />

        <span>
          Menampilkan {filtered.length} dari{' '}
          {analyses.length} hasil
        </span>
      </div>

      {/* Status memuat */}
      {loading && (
        <div className="public-results-message">
          Memuat hasil analisis publik...
        </div>
      )}

      {/* Pesan error */}
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}

      {/* Tabel daftar hasil */}
      {!loading && !error && (
        <div className="public-results-table-wrap">
          <div className="public-results-table-scroll">
            <table className="public-results-table">
              <thead>
                <tr>
                  <th>NAMA BERKAS</th>
                  <th>VARIAN</th>
                  <th>RUN ID TERKAIT</th>
                  <th>SAMPEL</th>
                  <th>TANGGAL RILIS</th>
                  <th>AKSI</th>
                </tr>
              </thead>

              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="public-results-empty"
                    >
                      {analyses.length === 0
                        ? 'Belum ada hasil analisis publik yang selesai.'
                        : 'Tidak ada hasil yang sesuai pencarian.'}
                    </td>
                  </tr>
                ) : (
                  filtered.map((run) => {
                    const passCount =
                      getPassCount(run)

                    const isLastViewed =
                      run.run_id === lastViewed

                    return (
                      <tr key={run.run_id}>

                        {/* Nama berkas */}
                        <td>
                          <div className="public-results-file">
                            <span className="public-results-file-icon">
                              ▤
                            </span>

                            <div>
                              <strong>
                                {run.run_id}_results
                              </strong>

                              <small>
                                Hasil analisis varian &
                                anotasi mutasi
                              </small>
                            </div>
                          </div>
                        </td>

                        {/* Jumlah varian */}
                        <td className="public-results-number">
                          {passCount === null
                            ? '—'
                            : passCount}
                        </td>

                        {/* Run ID */}
                        <td>
                          <div className="public-results-run">
                            <code>
                              {run.run_id}
                            </code>

                            {isLastViewed && (
                              <span
                                className="public-results-last"
                                title="Terakhir dilihat"
                              />
                            )}
                          </div>
                        </td>

                        {/* Nama sampel */}
                        <td>
                          <strong className="public-results-sample">
                            {run.sample_name || '-'}
                          </strong>
                        </td>

                        {/* Tanggal */}
                        <td className="public-results-date">
                          {formatDate(
                            run.completed_at ??
                            run.created_at
                          )}
                        </td>

                        {/* Tombol detail */}
                        <td>
                          <Link
                            className="public-results-button"
                            to={`/public/${encodeURIComponent(
                              run.run_id
                            )}/result`}
                          >
                            ▤ Buka hasil
                          </Link>
                        </td>

                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Footer tabel */}
          <div className="public-results-foot">
            <span>
              Menampilkan {filtered.length} hasil analisis
            </span>

            <span>
              Hanya analisis PUBLIC berstatus COMPLETED
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
