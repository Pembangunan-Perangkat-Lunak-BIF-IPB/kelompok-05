import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import './pages.css'

// Konten statis mengikuti frame "Panduan Penggunaan - Peneliti".
// Ikon KPI/langkah di Figma berupa vektor kustom -> [PENGGANTI] singkatan teks & ikon Lucide.
const KPI = [
  ['VALIDASI LAPIS', '2 Tingkat Ketat', '2', '#0e6e6e1a', '#005454'],
  ['STASIUN KERJA', '4 Modul Otomatis', '4', '#cce2fa4d', '#4c6075'],
  ['DATABASE ACUAN', 'NCBI & ENA', 'DB', '#e0e3e1', '#3e4948'],
]
const NODES = [
  ['QC & Preprocessing', 'fastp (Q20/Q30 Trim)', '#e6e9e7', '#005454', '#6e7979', 'S1'],
  ['Read Alignment', 'BWA-MEM2 & SAMtools', '#0e6e6e', '#9eedec', '#004f50', 'S2'],
  ['Variant Calling', 'BCFtools (Raw VCF)', '#2165a8', '#fff', '#004881', 'S3'],
  ['Filtering & Annotation', 'SnpEff & Executive Package', '#cce2fa', '#506579', '#506579', 'S4'],
]
const EXT = (list, on) => list.map((e) => <span key={e} className={`chip ${e === on ? 'teal' : ''}`} style={{ background: e === on ? undefined : '#e0e3e1', color: e === on ? undefined : 'var(--ink)' }}>{e}</span>)

export default function Guide() {
  return (
    <>
      <div className="hero-card">
        <div>
          <h1>Panduan Penggunaan Platform</h1>
          <p>Petunjuk alur analisis bioinformatika varian SARS-CoV-2, spesifikasi berkas, dan batasan sistem untuk anotasi dampak mutasi terpadu.</p>
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
          <div className="eyebrow"><span>Alur protokol standar</span><i /><span>Pipeline ID: WGS-SARSC2-PE</span></div>
          <h2>4 Tahapan Eksekusi Analisis</h2>
        </div>
      </div>

      <div className="steps">
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 01</span><span className="step-ic"><Icon name="file" size={14} /></span></div>
            <h3>1. Siapkan berkas</h3>
            <p className="d">FASTQ paired-end dan FASTA genom acuan.</p>
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
            <p className="d">Sistem memeriksa format dan header secara otomatis.</p>
            <div className="step-box">
              <div className="lv"><b>Format MIME, ekstensi, &amp; Phred FASTQ.</b></div>
              <div className="lv"><b>Validitas FASTA single contig rujukan.</b></div>
            </div>
          </div>
          <div className="step-foot"><span>Evaluasi Syntax</span><span className="chip blue">Realtime</span></div>
        </section>
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 03</span><span className="step-ic"><Icon name="clock" size={14} /></span></div>
            <h3>3. Jalankan &amp; pantau</h3>
            <p className="d">Pantau proses alignment, calling varian, dan anotasi realtime.</p>
            <div className="step-box"><h4>Log &amp; status</h4><span>Lacak progres eksekusi 4 stasiun komputasi secara transparan via console log.</span></div>
          </div>
          <div className="step-foot"><span>Streaming Log</span><span className="chip">SSE Active</span></div>
        </section>
        <section className="step">
          <div>
            <div className="step-top"><span className="tag">STEP 04</span><span className="step-ic"><Icon name="download" size={14} /></span></div>
            <h3>4. Analisis &amp; unduh</h3>
            <p className="d">Tinjau hasil anotasi dampak mutasi (SnpEff) dan ekspor laporan terperinci.</p>
            <div className="step-box"><h4>Output siap pakai</h4><span>Unduh berkas VCF teranotasi, sekuens flanking area, dan ringkasan laporan PDF/CSV.</span></div>
          </div>
          <div className="step-foot"><span>Format Laporan</span><span className="chip teal">VCF, CSV &amp; PDF</span></div>
        </section>
      </div>

      <section className="topology">
        <div className="topo-head">
          <div><h3>Topologi Eksekusi Pipeline</h3><p>Visualisasi transisi data mentah FASTQ menjadi varian teranotasi dan laporan eksekutif terintegrasi</p></div>
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
        <div className="spec-foot"><span><Icon name="info" size={11} /> Pengunggahan file terkompresi (.gz) sangat direkomendasikan untuk mempercepat transfer data NGS.</span><small>Maks. Batch: 20 Sampel per Jalur</small></div>
      </section>

      <section className="note-bad">
        <div className="ic"><Icon name="alert" size={18} /></div>
        <div style={{ flex: 1 }}>
          <h4>Catatan penting kesesuaian berkas</h4>
          <p style={{ fontSize: 15, marginTop: 6 }}>Berkas sekuens (FASTQ) yang diunggah wajib berasal dari isolat SARS-CoV-2 karena akan dipetakan secara otomatis ke genom acuan baku sepanjang 29.903 bp (RefSeq NC_045512.2). Apabila berkas tidak sesuai, pipeline tetap berjalan selama tidak terjadi galat teknis, namun akan menghasilkan metrik penjajaran yang rendah serta hasil anotasi yang janggal pada region gen target seperti Spike ORF (21563–25384 bp).</p>
          <div className="step-box" style={{ marginTop: 12 }}>
            <div className="bar-legend"><span>Posisi 1 (5' UTR)</span><span style={{ color: 'var(--teal-d)' }}>Spike ORF (21563 - 25384 bp)</span><span>29.903 bp (3' Poly-A)</span></div>
            <div className="bar3"><i style={{ width: '72%', background: '#bec9c8' }} /><i style={{ width: '13%', background: '#005454' }} /><i style={{ width: '15%', background: '#bec9c8' }} /></div>
            <div className="bar-legend"><span>▪ Region non-Spike</span><b style={{ color: 'var(--teal-d)' }}>▪ Spike ORF (region gen target)</b></div>
          </div>
        </div>
      </section>
    </>
  )
}
