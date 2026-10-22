import { useId, useMemo, useState } from 'react'
import { euros } from '../lib/paper'

// Colores de polaridad sobre el fondo negro (validados para daltonismo): por encima del bank
// inicial, verde; por debajo, rojo. La línea de referencia y el signo del texto también lo dicen.
const ARRIBA = '#139c86'
const ABAJO = '#e0583a'
const W = 720
const H = 260
const M = { top: 16, right: 16, bottom: 28, left: 64 }

const fechaCorta = (t) => new Date(t).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
const fechaLarga = (t) => new Date(t).toLocaleString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

function ticks(lo, hi, n = 4) {
  const paso = (hi - lo) / n
  const mag = 10 ** Math.floor(Math.log10(paso || 1))
  const bonito = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((m) => m >= paso) || paso
  const out = []
  for (let v = Math.ceil(lo / bonito) * bonito; v <= hi + 1e-9; v += bonito) out.push(Math.round(v * 100) / 100)
  return out
}

// Bank a lo largo del tiempo: línea escalonada (el bank cambia al liquidarse cada apuesta).
export default function BankChart({ curve, initial }) {
  const id = useId().replace(/:/g, '')
  const [foco, setFoco] = useState(null)

  const g = useMemo(() => {
    const pts = curve.map((p, i) => ({ ...p, i }))
    const vals = pts.map((p) => p.bank).concat(initial)
    let lo = Math.min(...vals)
    let hi = Math.max(...vals)
    const pad = Math.max((hi - lo) * 0.12, initial * 0.02, 1)
    lo -= pad
    hi += pad
    const iw = W - M.left - M.right
    const ih = H - M.top - M.bottom
    // Eje x por orden de liquidación: así un día con muchas apuestas no se aplasta.
    const x = (i) => M.left + (pts.length > 1 ? (i / (pts.length - 1)) * iw : iw / 2)
    const y = (v) => M.top + (1 - (v - lo) / (hi - lo)) * ih
    let d = `M${x(0)},${y(pts[0].bank)}`
    for (let i = 1; i < pts.length; i++) d += ` H${x(i)} V${y(pts[i].bank)}`
    const area = `${d} V${y(initial)} H${x(0)} Z`
    return { pts, x, y, d, area, base: y(initial), yt: ticks(lo, hi), iw, ih }
  }, [curve, initial])

  const mover = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    let mejor = 0
    g.pts.forEach((p, i) => { if (Math.abs(g.x(i) - px) < Math.abs(g.x(mejor) - px)) mejor = i })
    setFoco(mejor)
  }
  const p = foco != null ? g.pts[foco] : null
  const fin = g.pts[g.pts.length - 1]
  const etiquetasX = g.pts.length > 1 ? [g.pts[0], fin] : [fin]

  return (
    <figure className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block h-auto w-full touch-none select-none"
        role="img"
        aria-label={`Evolución del bank: de ${euros(initial)} a ${euros(fin.bank)} en ${g.pts.length - 1} apuestas liquidadas`}
        onPointerMove={mover}
        onPointerLeave={() => setFoco(null)}
      >
        <defs>
          <clipPath id={`arriba-${id}`}><rect x="0" y="0" width={W} height={g.base} /></clipPath>
          <clipPath id={`abajo-${id}`}><rect x="0" y={g.base} width={W} height={H - g.base} /></clipPath>
        </defs>
        {g.yt.map((v) => (
          <g key={v}>
            <line x1={M.left} x2={W - M.right} y1={g.y(v)} y2={g.y(v)} stroke="var(--line)" strokeWidth="1" />
            <text x={M.left - 8} y={g.y(v)} dy="0.32em" textAnchor="end" className="tnum fill-[var(--grey)] text-[11px]">{euros(v, 0)}</text>
          </g>
        ))}
        <path d={g.area} fill={ARRIBA} fillOpacity="0.18" clipPath={`url(#arriba-${id})`} />
        <path d={g.area} fill={ABAJO} fillOpacity="0.18" clipPath={`url(#abajo-${id})`} />
        <line x1={M.left} x2={W - M.right} y1={g.base} y2={g.base} stroke="var(--muted)" strokeWidth="1" strokeDasharray="4 4" />
        <text x={W - M.right} y={g.base - 6} textAnchor="end" className="fill-[var(--muted)] text-[11px]">Inicial {euros(initial, 0)}</text>
        <path d={g.d} fill="none" stroke={ARRIBA} strokeWidth="2" strokeLinejoin="round" clipPath={`url(#arriba-${id})`} />
        <path d={g.d} fill="none" stroke={ABAJO} strokeWidth="2" strokeLinejoin="round" clipPath={`url(#abajo-${id})`} />
        <circle cx={g.x(fin.i)} cy={g.y(fin.bank)} r="4" fill={fin.bank >= initial ? ARRIBA : ABAJO} stroke="var(--black)" strokeWidth="2" />
        {etiquetasX.map((q) => (
          <text key={q.i} x={g.x(q.i)} y={H - 8} textAnchor={q.i === 0 ? 'start' : 'end'} className="fill-[var(--grey)] text-[11px]">{fechaCorta(q.t)}</text>
        ))}
        {p && (
          <g pointerEvents="none">
            <line x1={g.x(p.i)} x2={g.x(p.i)} y1={M.top} y2={H - M.bottom} stroke="var(--muted)" strokeWidth="1" />
            <circle cx={g.x(p.i)} cy={g.y(p.bank)} r="5" fill={p.bank >= initial ? ARRIBA : ABAJO} stroke="var(--black)" strokeWidth="2" />
          </g>
        )}
      </svg>
      {p && (
        <div
          className="tnum pointer-events-none absolute top-2 border border-white/30 bg-black px-3 py-2 text-sm"
          style={{ left: `${(g.x(p.i) / W) * 100}%`, transform: `translateX(${g.x(p.i) > W / 2 ? '-105%' : '5%'})` }}
        >
          <p className="font-semibold">{euros(p.bank)}</p>
          <p className="text-xs text-muted">{p.i === 0 ? 'Inicio' : `Tras la apuesta ${p.i}`} · {fechaLarga(p.t)}</p>
        </div>
      )}
      <figcaption className="sr-only">
        {g.pts.map((q) => `${fechaLarga(q.t)}: ${euros(q.bank)}`).join('; ')}
      </figcaption>
    </figure>
  )
}
