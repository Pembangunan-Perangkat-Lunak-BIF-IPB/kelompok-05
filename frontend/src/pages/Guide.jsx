import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import './pages.css'

// Konten statis mengikuti frame "Panduan Penggunaan - Peneliti".
// Ikon KPI/langkah di Figma berupa vektor kustom -> [PENGGANTI] singkatan teks & ikon Lucide.
const KPI = [
  ['VALIDASI LAPIS', '3 Tingkat Ketat', '3', '#0e6e6e1a', '#005454'],
  ['STASIUN KERJA', '5 Modul Otomatis', '5', '#cce2fa4d', '#4c6075'],
  ['DATABASE ACUAN', 'IEDB & NCBI', 'DB', '#e0e3e1', '#3e4948'],
]
const NODES = [
  ['Input FASTQ', 'Raw Reads', '#e6e9e7', '#005454', '#6e7979', 'R'],
  ['QC & Align', 'BAM File', '#0e6e6e', '#9eedec', '#004f50', 'Q'],
  ['SNV Variant', 'VCF Matrix', '#2165a8', '#fff', '#004881', 'V'],
  ['Pangolin', 'Lineage Calling', '#e0e3e1', '#181c1b', '#6e7979', 'P'],
  ['Escape Model', 'Risk Index', '#cce2fa', '#506579', '#506579', 'E'],
]
const EXT = (list, on) => list.map((e) => <span key={e} className={`chip ${e === on ? 'teal' : ''}`} style={{ background: e === on ? undefined : '#e0e3e1', color: e === on ? undefined : 'var(--ink)' }}>{e}</span>)

export default function Guide() {
  return (
    <>
      <div className="hero-card">
        <div>
          <h1>Panduan Penggunaan Platform</h1>
          <p>Petunjuk alur analisis bioinformatika varian, spesifikasi berkas, dan batasan sistem untuk evaluasi immune escape terpadu.</p>
        </div>
        <Link to="/analysis/new" className="btn btn-primary btn-sm"><Icon name="play" size={10} /> Mulai Analisis Baru</Link>
      </div>

      <div className="kpis">
        {KPI.map(([l, v, t, bg, fg]) => (
          <div className="kpi" key={l}><div className="kpi-ic" style={{ background: bg, color: fg }}>{t}</div><div><small>{l}</small><b>{v}</b></div></div>
        ))}
      </div>

      <div className="sec-head">
        <div>
          <div className="eyebrow"><span>Alur protokol standar</span><i /></div>
          <h2>4 Tahapan Eksekusi Analisis</h2>
        </div>
      </div>

      <div className="steps">
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 01</span><span className="step-ic"><Icon name="file" size={14} /></span></div>
            <h3>1. Siapkan berkas</h3>
            <p className="d">FASTQ paired-end, FASTA genom acuan, tabel epitope IEDB.</p>
            <div className="step-box">
              <h4>Format pasangan</h4>
              <code>sample_R1.fastq.gz<br />sample_R2.fastq.gz</code>
              <span>Pastikan pasangan forward (<b>_R1</b>) &amp; reverse (<b>_R2</b>) memiliki jumlah header identik.</span>
            </div>
          </div>
          <div className="step-foot"><span>Integritas MD5</span><span className="chip">Opsional</span></div>
        </section>
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 02</span><span className="step-ic"><Icon name="check-circle" size={14} /></span></div>
            <h3>2. Unggah &amp; validasi</h3>
            <p className="d">Sistem memeriksa format, header, dan koordinat secara otomatis.</p>
            <div className="step-box">
              <div className="lv"><b>Format MIME, ekstensi, &amp; Phred FASTQ.</b></div>
              <div className="lv"><b>Validitas FASTA single contig rujukan.</b></div>
              <div className="lv"><b>Batas koordinat epitope linear terhadap locus.</b></div>
            </div>
          </div>
          <div className="step-foot"><span>Evaluasi Syntax</span><span className="chip blue">Realtime</span></div>
        </section>
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 03</span><span className="step-ic"><Icon name="clock" size={14} /></span></div>
            <h3>3. Jalankan &amp; pantau</h3>
            <p className="d">Pantau proses alignment, calling varian, dan anotasi realtime.</p>
            <div className="step-box"><h4>Log &amp; status</h4><span>Lacak progres eksekusi 5 modul komputasi secara transparan via console log.</span></div>
          </div>
          <div className="step-foot"><span>Streaming Log</span><span className="chip">SSE Active</span></div>
        </section>
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 04</span><span className="step-ic"><Icon name="download" size={14} /></span></div>
            <h3>4. Analisis &amp; unduh</h3>
            <p className="d">Interpretasikan Immune Escape Score dan ekspor laporan terperinci.</p>
            <div className="step-box"><h4>Output siap pakai</h4><span>Unduh matriks VCF, visualisasi mutasi kodon Spike, dan ringkasan PDF/CSV.</span></div>
          </div>
          <div className="step-foot"><span>Format Laporan</span><span className="chip teal">PDF &amp; TSV</span></div>
        </section>
      </div>

      <section className="topology">
        <div className="topo-head">
          <div><h3>Topologi Eksekusi Pipeline</h3><p>Visualisasi transisi data mentah menjadi skor risiko immune escape terukur</p></div>
          <div className="ready"><i />Cluster Execution Daemon Ready</div>
        </div>
        <div className="topo">
          {NODES.map(([a, b, bg, fg, sub, t]) => (
            <div className="node" key={a}><div className="ic" style={{ background: bg, color: fg }}>{t}</div><b>{a}</b><small style={{ color: sub }}>{b}</small></div>
          ))}
        </div>
      </section>

      <section className="spec">
        <div className="spec-head">
          <div><h3><Icon name="info" size={14} /> Spesifikasi Format &amp; Batas Ukuran Berkas</h3><p>Semua berkas diperiksa integritasnya sebelum dialokasikan ke compute cluster.</p></div>
        </div>
        <div className="spec-row th"><div>Berkas</div><div>Format yang diterima</div><div style={{ textAlign: 'right' }}>Batas maksimal</div><div>Deskripsi &amp; validasi</div></div>
        <div className="spec-row">
          <div className="name"><b>Data Sekuens</b><small>FASTQ Paired-End</small></div>
          <div><div className="exts">{EXT(['.fastq', '.fq', '.fastq.gz', '.fq.gz'], '.fastq.gz')}</div><p>Read 1 &amp; Read 2 terpisah</p></div>
          <div className="lim">1 GB<small>per berkas</small></div>
          <div><p>Sekuens mentah hasil sekuensing NGS paired-end Illumina/MGI.</p><div className="sub">Validasi encoding Phred-33 / Phred-64 otomatis</div></div>
        </div>
        <div className="spec-row">
          <div className="name"><b>Genom Acuan</b><small>Reference FASTA</small></div>
          <div><div className="exts">{EXT(['.fasta', '.fa', '.fna'])}</div><p>Single continuous record</p></div>
          <div className="lim">50 MB<small>uncompressed</small></div>
          <div><p>Genom rujukan lengkap dengan header sekuens standar NCBI.</p><div className="sub">Validasi non-IUPAC berlebih (&lt; 1% ambigu)</div></div>
        </div>
        <div className="spec-row">
          <div className="name"><b>Epitope IEDB</b><small>Epitope Coordinate Map</small></div>
          <div><div className="exts">{EXT(['.tsv', '.csv', '.gff'])}</div><p>UTF-8 encoded delimiters</p></div>
          <div className="lim">20 MB<small>tabular format</small></div>
          <div><p>Anotasi koordinat epitope linear/konformasi B-cell &amp; T-cell dari IEDB.</p><div className="sub">Wajib memuat kolom: start_pos, end_pos, iedb_id</div></div>
        </div>
        <div className="spec-foot"><span><Icon name="info" size={11} /> Pengunggahan file terkompresi (.gz) sangat direkomendasikan untuk mempercepat transfer data NGS.</span><small>Maks. Batch: 20 Sampel per Jalur</small></div>
      </section>

      <section className="note-bad">
        <div className="ic"><Icon name="alert" size={18} /></div>
        <div style={{ flex: 1 }}>
          <h4>Catatan penting validasi lapis 3 <span className="chip" style={{ background: 'var(--bad-bg)', color: '#93000a' }}>KOORDINAT BOUNDARY FAIL-SAFE</span></h4>
          <h3>Contoh: Integritas Rentang Koordinat Epitope Terhadap Panjang Genom</h3>
          <p style={{ fontSize: 15 }}>Koordinat epitope harus berada dalam rentang panjang genom acuan (1 s.d. 29.903 bp) untuk mencegah kegagalan validasi lapis 3. Nilai posisi awal (start_pos) tidak boleh lebih besar dari posisi akhir (end_pos), dan offset tidak boleh melampaui panjang kodon Spike protein (21563 s.d. 25384 bp).</p>
          <div className="step-box" style={{ marginTop: 12 }}>
            <div className="bar-legend"><span>Posisi 1 (5' UTR)</span><span style={{ color: 'var(--teal-d)' }}>Spike ORF (21563 - 25384 bp)</span><span>29.903 bp (3' Poly-A)</span></div>
            <div className="bar3"><i style={{ width: '72%', background: '#bec9c8' }} /><i style={{ width: '13%', background: '#005454' }} /><i style={{ width: '15%', background: '#bec9c8' }} /></div>
            <div className="bar-legend"><span>▪ Non-Spike Region</span><b style={{ color: 'var(--teal-d)' }}>▪ Receptor Binding Domain &amp; Spike Core</b></div>
          </div>
        </div>
      </section>
    </>
  )
}
