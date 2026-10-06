import { Link } from 'react-router-dom'
import './pages.css'

const stats = [
  ['Validasi lapis', '3 tingkat ketat'],
  ['Stasiun kerja', '5 modul otomatis'],
  ['Panjang genom', '29.903 bp'],
  ['Database acuan', 'IEDB & GISAID'],
]

const steps = [
  ['Siapkan berkas', 'FASTQ paired-end, FASTA genom acuan, tabel epitope IEDB. Pasangan forward (_R1) dan reverse (_R2) harus memiliki jumlah header identik.'],
  ['Unggah & validasi', 'Sistem memeriksa format (BR-07 s.d. 09), header FASTA single contig (BR-10 & 11), dan batas koordinat epitope (BR-12).'],
  ['Jalankan & pantau', 'Pantau alignment, calling varian, dan anotasi secara realtime lewat log dan status 5 modul komputasi.'],
  ['Analisis & unduh', 'Interpretasikan Immune Escape Score dan ekspor laporan PDF atau TSV.'],
]

const pipeline = [
  ['Input FASTQ', 'Raw reads'],
  ['QC & Align', 'BAM file'],
  ['SNV Variant', 'VCF matrix'],
  ['Pangolin', 'Lineage calling'],
  ['Escape Model', 'Risk index'],
]

const formats = [
  ['Data sekuens (FASTQ paired-end)', '.fastq  .fq  .fastq.gz  .fq.gz', '1 GB per berkas', 'Read 1 dan Read 2 terpisah. Encoding Phred-33 / Phred-64 divalidasi otomatis.'],
  ['Genom acuan (FASTA)', '.fasta  .fa  .fna', '50 MB', 'Single continuous record dengan header standar NCBI. Non-IUPAC berlebih < 1% ambigu.'],
  ['Epitope IEDB', '.tsv  .csv  .gff', '20 MB', 'Wajib memuat kolom start_pos, end_pos, iedb_id.'],
]

export default function Guide() {
  return (
    <div className="page">
      <section className="card guide-hero">
        <div>
          <h1>Panduan Penggunaan Platform</h1>
          <p>Petunjuk alur analisis bioinformatika varian SARS-CoV-2, spesifikasi berkas, dan batasan sistem untuk evaluasi immune escape terpadu.</p>
        </div>
        <Link to="/analysis/new" className="btn btn-primary">Mulai analisis baru</Link>
      </section>

      <section className="grid-4">
        {stats.map(([k, v]) => (
          <div className="card stat" key={k}><small>{k}</small><strong>{v}</strong></div>
        ))}
      </section>

      <h2>4 tahapan eksekusi analisis</h2>
      <section className="grid-2">
        {steps.map(([title, desc], i) => (
          <article className="card step" key={title}>
            <span className="tag">Step {String(i + 1).padStart(2, '0')}</span>
            <h3>{i + 1}. {title}</h3>
            <p>{desc}</p>
          </article>
        ))}
      </section>

      <section className="card">
        <h2>Topologi eksekusi pipeline</h2>
        <p className="muted">Transisi data mentah menjadi skor risiko immune escape terukur.</p>
        <ol className="pipeline">
          {pipeline.map(([name, out]) => (
            <li key={name}><strong>{name}</strong><small>{out}</small></li>
          ))}
        </ol>
      </section>

      <section className="card">
        <h2>Spesifikasi format & batas ukuran berkas</h2>
        <p className="muted">Genom acuan default: Wuhan-Hu-1 (NC_045512.2, 29.903 bp). Maksimal 20 sampel per jalur.</p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Berkas</th><th>Format diterima</th><th>Batas maksimal</th><th>Deskripsi & validasi</th></tr></thead>
            <tbody>
              {formats.map((r) => (
                <tr key={r[0]}>{r.map((c) => <td key={c}>{c}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card note">
        <h3>Catatan validasi lapis 3 (BR-12)</h3>
        <p>Koordinat epitope harus berada dalam rentang genom acuan (1 s.d. 29.903 bp). Nilai start_pos tidak boleh lebih besar dari end_pos, dan offset tidak boleh melampaui panjang kodon Spike (21563 s.d. 25384 bp).</p>
      </section>

      <section className="card">
        <h3>Butuh konsultasi bioinformatika?</h3>
        <p className="muted">Tim VarEscape siap membantu pengecekan metadata NGS atau format tabel epitope non-standar.</p>
        <p>admin@gmail.com · Senin–Jumat, 08.00–17.00 WIB</p>
        <button className="btn" disabled title="Belum tersedia">Unduh berkas contoh (Demo ZIP)</button>
      </section>
    </div>
  )
}
