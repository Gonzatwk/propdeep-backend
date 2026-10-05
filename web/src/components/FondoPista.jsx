import { useEffect, useRef } from 'react'
import { ARO, TIROS } from '../lib/tiros'
import Pista from './Pista'

// Tiros que se ven arriba del todo; al bajar el campo se apaga.
const CAMPO = TIROS.slice(0, 130)
const quieto = () => !window.matchMedia('(prefers-reduced-motion: no-preference)').matches

function Tiro({ t }) {
  if (t.dentro) return <circle className="tiro" cx={t.x} cy={t.y} r="4" fill="var(--gold)" />
  return (
    <path
      className="tiro"
      d={`M${t.x - 3.6} ${t.y - 3.6}l7.2 7.2m0 -7.2l-7.2 7.2`}
      stroke="var(--grey)"
      strokeWidth="1.6"
      style={{ transformOrigin: `${t.x}px ${t.y}px` }}
    />
  )
}

// Fondo fijo de toda la web: media pista en blanco y negro con un campo de tiros.
// Se ve entero arriba del todo y se apaga al bajar, para no molestar al leer.
// Arriba, cada pocos segundos entra un tiro en directo; en escritorio un foco
// dorado sigue al ratón.
export default function FondoPista() {
  const raiz = useRef(null)
  const vivo = useRef(null)
  const foco = useRef(null)

  useEffect(() => {
    let raf = 0
    const alHacerScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const k = Math.min(1, scrollY / (innerHeight * 0.9))
        raiz.current?.style.setProperty('--apagado', k.toFixed(3))
      })
    }
    alHacerScroll()
    addEventListener('scroll', alHacerScroll, { passive: true })
    return () => {
      removeEventListener('scroll', alHacerScroll)
      cancelAnimationFrame(raf)
    }
  }, [])

  // Tiros en directo: el balón vuela desde un punto del campo hasta el aro.
  useEffect(() => {
    if (quieto()) return
    const g = vivo.current
    const ns = 'http://www.w3.org/2000/svg'
    let parar = false
    let espera = 0
    const lanzar = () => {
      if (parar) return
      if (document.hidden || scrollY > innerHeight * 0.5) {
        espera = setTimeout(lanzar, 1500)
        return
      }
      const t = TIROS[Math.floor(Math.random() * TIROS.length)]
      const [x0, y0] = [t.x, t.y]
      const [x1, y1] = ARO
      const dx = x1 - x0
      const dy = y1 - y0
      const curva = Math.hypot(dx, dy) * 0.35
      const cx = (x0 + x1) / 2 - (dy / Math.hypot(dx, dy || 1)) * curva
      const cy = (y0 + y1) / 2 + (dx / Math.hypot(dx, dy || 1)) * curva
      const d = `M${x0} ${y0}Q${cx} ${cy} ${x1} ${y1}`
      const estela = document.createElementNS(ns, 'path')
      estela.setAttribute('d', d)
      estela.setAttribute('class', 'estela')
      const balon = document.createElementNS(ns, 'circle')
      balon.setAttribute('r', '7')
      balon.setAttribute('class', 'balon')
      g.append(estela, balon)
      const largo = estela.getTotalLength()
      estela.style.strokeDasharray = `${largo}`
      estela.style.strokeDashoffset = `${largo}`
      const dur = 900 + Math.random() * 400
      const inicio = performance.now()
      const paso = (ahora) => {
        if (parar) return
        const k = Math.min(1, (ahora - inicio) / dur)
        const e = 1 - Math.pow(1 - k, 2)
        const pt = estela.getPointAtLength(largo * e)
        balon.setAttribute('cx', pt.x)
        balon.setAttribute('cy', pt.y)
        estela.style.strokeDashoffset = `${largo * (1 - e)}`
        if (k < 1) return requestAnimationFrame(paso)
        balon.remove()
        const red = document.createElementNS(ns, 'circle')
        red.setAttribute('cx', x1)
        red.setAttribute('cy', y1)
        red.setAttribute('r', '8')
        red.setAttribute('class', 'onda')
        g.append(red)
        estela.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 900, delay: 300, fill: 'forwards' })
        setTimeout(() => {
          estela.remove()
          red.remove()
        }, 1400)
      }
      requestAnimationFrame(paso)
      espera = setTimeout(lanzar, 2400 + Math.random() * 1600)
    }
    espera = setTimeout(lanzar, 1800)
    return () => {
      parar = true
      clearTimeout(espera)
      g.replaceChildren()
    }
  }, [])

  // Foco dorado que sigue al ratón (solo con puntero fino).
  useEffect(() => {
    if (quieto() || !matchMedia('(hover: hover) and (pointer: fine)').matches) return
    const el = foco.current
    const mover = (e) => {
      el.style.setProperty('--fx', `${e.clientX}px`)
      el.style.setProperty('--fy', `${e.clientY}px`)
      el.style.opacity = '1'
    }
    addEventListener('pointermove', mover, { passive: true })
    return () => removeEventListener('pointermove', mover)
  }, [])

  return (
    <div ref={raiz} aria-hidden className="fondo pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <svg viewBox="-10 -10 520 490" preserveAspectRatio="xMidYMin slice" className="fondo-svg h-full w-full">
        <g className="fondo-pista">
          <Pista dibujar />
        </g>
        <g className="fondo-tiros">
          {CAMPO.map((t) => <Tiro key={t.i} t={t} />)}
        </g>
        <g ref={vivo} />
      </svg>
      <div ref={foco} className="foco" />
      <div className="velo" />
    </div>
  )
}
