
import { useEffect, useState } from 'react'
import { getFilterAudit } from '../lib/api'

const fmt = (value, digits = 2) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  const n = Number(value)

  if (!Number.isFinite(n)) return '-'

  return n.toLocaleString('id-ID', {
    maximumFractionDigits: digits,
  })
}

export default function FilterAudit({ runId }) {
  const [audit, setAudit] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    setLoading(true)
    setAudit(null)
    setError('')

    getFilterAudit(runId)
      .then((response) => {
        if (active) setAudit(response)
      })
      .catch((err) => {
        if (!active) return

        if (err.status === 404) {
          setError(
            'Data audit filtering belum tersedia untuk run ini.'
          )
        } else {
          setError(err.message || 'Gagal memuat audit filtering.')
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [runId])

  return (
    <section
      className="vt"
      style={{ marginTop: 20 }}
      aria-label="Audit Quality Filtering"
    >
      <div className="vt-head">
        <div>
          <h2>Audit Quality Filtering</h2>
          <p>
            Kandidat varian yang tidak memenuhi parameter
            filtering pada Stasiun 4.
          </p>
        </div>
      </div>

      {loading && (
        <p className="muted" role="status" style={{ padding: 16 }}>
          Memuat audit filtering...
        </p>
      )}

      {!loading && error && (
        <p className="muted" role="status" style={{ padding: 16 }}>
          {error}
        </p>
      )}

      {!loading && !error && audit && (
        <>
          {audit.audit_available ? (
            <>
              <div
                style={{
                  display: 'flex',
                  gap: 12,
                  flexWrap: 'wrap',
                  padding: '14px 16px',
                }}
              >
                <span>Total kandidat: <b>{fmt(audit.total_candidates, 0)}</b></span>
                <span>PASS: <b>{fmt(audit.passed, 0)}</b></span>
                <span>FILTERED: <b>{fmt(audit.filtered, 0)}</b></span>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Posisi</th>
                      <th>REF &gt; ALT</th>
                      <th>DP</th>
                      <th>QUAL</th>
                      <th>AF</th>
                      <th>Status</th>
                      <th>Alasan Filtering</th>
                    </tr>
                  </thead>

                  <tbody>
                    {(audit.filtered_variants ?? []).map((v, i) => (
                      <tr key={`${v.chrom}:${v.position}:${v.ref}:${v.alt}:${i}`}>
                        <td>{fmt(v.position, 0)}</td>
                        <td>{v.ref ?? '-'} &gt; {v.alt ?? '-'}</td>
                        <td>{fmt(v.dp, 0)}</td>
                        <td>{fmt(v.qual, 3)}</td>
                        <td>{fmt(v.af, 4)}</td>
                        <td>FILTERED</td>
                        <td>
                          <strong>{v.filter_reason || 'Tidak tersedia'}</strong>
                        </td>
                      </tr>
                    ))}

                    {audit.filtered_variants?.length === 0 && (
                      <tr>
                        <td colSpan={7} className="empty">
                          Semua kandidat varian lolos quality filtering.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div className="vt-foot">
                <span>
                  Menampilkan {audit.filtered_variants?.length ?? 0}
                  {' '}varian terfilter
                </span>
                <span>Data audit berasal dari backend VarEscape</span>
              </div>
            </>
          ) : (
            <p className="muted" style={{ padding: 16 }}>
              Audit filtering belum tersedia untuk run ini.
            </p>
          )}
        </>
      )}
    </section>
  )
}
