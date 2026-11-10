import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import logo from '../assets/logo.png'
import { CFG, Pileup, computeScene, drawScene } from '../lib/pileup'
import './landing.css'

const CONTACT = 'admin@gmail.com'
const INPUTS = ['FASTQ R1/R2', 'FASTA', 'IEDB']

// Kanvas "read pileup": animasi di kode, Figma hanya menyimpan satu frame diam.
function PileupCanvas() {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const pileup = new Pileup()
    let raf = 0
    let start = 0
    let w = 0
    let h = 0

    const frame = (t) => {
      ctx.clearRect(0, 0, w, h)
      drawScene(ctx, computeScene(pileup, w, h, t))
    }

    const loop = (now) => {
      if (!start) start = now
      frame((now - start) / 1000)
      raf = requestAnimationFrame(loop)
    }

    const run = () => {
      cancelAnimationFrame(raf)
      start = 0
      if (mq.matches) frame(CFG.staticT) // gambar diam
      else raf = requestAnimationFrame(loop)
    }

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = Math.round(w * dpr)
      canvas.height = Math.round(h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      run()
    }

    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    mq.addEventListener('change', run)
    resize()
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      mq.removeEventListener('change', run)
    }
  }, [])

  return <canvas ref={ref} className="lp-pileup" aria-hidden="true" />
}

function ContactDialog({ onClose }) {
  const [copied, setCopied] = useState(false)
  const closeRef = useRef(null)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function copy() {
    try {
      await navigator.clipboard.writeText(CONTACT)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = CONTACT
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  return (
    <div className="lp-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="lp-modal" role="dialog" aria-modal="true" aria-labelledby="lp-contact-title">
        <button ref={closeRef} className="lp-modal-x" onClick={onClose} aria-label="Tutup">
          <Icon name="x" size={18} />
        </button>
        <h2 id="lp-contact-title">Hubungi Kami</h2>
        <div className="lp-contact-row">
          <Icon name="mail" size={18} />
          <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
          <button className="lp-copy" onClick={copy}>
            <Icon name={copied ? 'check' : 'copy'} size={14} />
            {copied ? 'Tersalin' : 'Salin'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Landing() {
  const [open, setOpen] = useState(false)
  const aboutRef = useRef(null)

  function close() {
    setOpen(false)
    aboutRef.current?.focus()
  }

  return (
    <div className="landing">
      <div className="lp-grid" aria-hidden="true" />
      <div className="lp-glow" aria-hidden="true" />

      <header className="lp-top">
        <div className="lp-brand">
          <img src={logo} alt="" width="32" height="32" />
          <span>VarEscape</span>
        </div>
        <button ref={aboutRef} className="lp-about" onClick={() => setOpen(true)}>About Us</button>
      </header>

      <main className="lp-main">
        <h1 className="lp-title">
          <span>Temukan varian dan petakan</span>{' '}
          <span>immune escape dengan presisi.</span>
        </h1>
        <Link to="/login" className="lp-cta">
          Mulai Analisis <Icon name="arrow-right" size={18} />
        </Link>
        <div className="lp-inputs">
          <span className="lp-inputs-label">Input:</span>
          {INPUTS.map((i) => <span key={i} className="lp-chip">{i}</span>)}
        </div>
      </main>

      <PileupCanvas />
      {open && <ContactDialog onClose={close} />}
    </div>
  )
}
