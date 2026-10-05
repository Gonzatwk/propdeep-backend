import { useId, useState } from 'react'
import { hexPoints } from '../lib/hex'
import { fmtNum } from '../format'

// Jugador ficticio: puntos en sus últimos 30 partidos. Datos inventados para el ejemplo.
const PARTIDOS = [18, 27, 22, 31, 24, 19, 26, 29, 21, 25, 33, 23, 17, 28, 24, 26, 20, 30, 22, 25, 27, 16, 24, 29, 23, 26, 21, 35, 25, 28]
const MIN = 15
const MAX = 36
const R = 9
const COL = R * Math.sqrt(3) + 1.5

const pct = (x) => `${Math.round(x * 100)} %`
const uno = (x) => x.toFixed(1).replace('.', ',')

export default function LaLinea() {
  const id = useId()
  const [linea, setLinea] = useState(24.5)
  const [cuota, setCuota] = useState(1.85)

  const encima = PARTIDOS.filter((p) => p > linea).length
  const frecuencia = encima / PARTIDOS.length
  const implicita = 1 / cuota
  const ventaja = (frecuencia - implicita) * 100
  const hayVentaja = ventaja >= 3

  // Columnas de hexágonos apilados, una por valor de puntos.
  const pila = {}
  const hexes = PARTIDOS.map((p) => {
    pila[p] = (pila[p] || 0) + 1
    return { p, n: pila[p] }
  })
  const ancho = (MAX - MIN + 1) * COL
  const alto = 6 * R * 1.6 + 34
  const xDe = (v) => (v - MIN) * COL + COL / 2
  const xLinea = xDe(linea)

  return (
    <div className="border-y border-ink bg-paper">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[1.35fr_1fr] lg:gap-14 lg:py-12">
        <figure>
          <svg viewBox={`0 0 ${ancho} ${alto}`} className="w-full" role="img" aria-label={`Puntos en 30 partidos. ${encima} por encima de ${fmtNum(linea)}.`}>
            <line x1="0" x2={ancho} y1={alto - 22} y2={alto - 22} stroke="var(--ink)" />
            {hexes.map(({ p, n }) => (
              <polygon
                key={`${p}-${n}`}
                className="bar"
                points={hexPoints(xDe(p), alto - 22 - R - 2 - (n - 1) * R * 1.62, R)}
                fill={p > linea ? 'var(--h3)' : 'var(--c3)'}
              />
            ))}
            {Array.from({ length: (MAX - MIN) / 5 + 1 }, (_, i) => MIN + i * 5).map((v) => (
              <text key={v} x={xDe(v)} y={alto - 5} textAnchor="middle" fontSize="11" fill="var(--muted)" className="tnum">{v}</text>
            ))}
            <line x1={xLinea} x2={xLinea} y1="14" y2={alto - 22} stroke="var(--ink)" strokeWidth="2" strokeDasharray="4 3" />
            <text x={xLinea} y="10" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--ink)">{fmtNum(linea)}</text>
          </svg>
          <figcaption className="mt-3 text-xs text-muted">
            Puntos de un jugador ficticio en sus últimos 30 partidos. Datos inventados para el ejemplo.
          </figcaption>
        </figure>

        <div className="flex flex-col">
          <label htmlFor={`${id}-l`} className="flex items-baseline justify-between text-sm font-medium">
            Línea de puntos <span className="tnum display text-2xl">{fmtNum(linea)}</span>
          </label>
          <input id={`${id}-l`} type="range" className="slider" min={MIN + 0.5} max={MAX - 1.5} step={1} value={linea} onChange={(e) => setLinea(Number(e.target.value))} />

          <label htmlFor={`${id}-c`} className="mt-4 flex items-baseline justify-between text-sm font-medium">
            Cuota del «más de» <span className="tnum display text-2xl">{fmtNum(cuota)}</span>
          </label>
          <input id={`${id}-c`} type="range" className="slider" min={1.3} max={3} step={0.05} value={cuota} onChange={(e) => setCuota(Number(e.target.value))} />

          <dl className="mt-6 grid grid-cols-2 border-t border-line">
            <div className="border-r border-line py-3 pr-4">
              <dt className="text-xs text-muted">Superó la línea</dt>
              <dd className="tnum display mt-1 text-4xl text-hot">{pct(frecuencia)}</dd>
            </div>
            <div className="py-3 pl-4">
              <dt className="text-xs text-muted">La cuota implica</dt>
              <dd className="tnum display mt-1 text-4xl">{pct(implicita)}</dd>
            </div>
          </dl>

          <p aria-live="polite" className={`mt-2 px-4 py-3 text-sm leading-snug ${hayVentaja ? 'bg-hot text-on-ink' : 'bg-ink text-on-ink'}`}>
            {hayVentaja ? (
              <><strong className="font-semibold">Ventaja de {uno(ventaja)} puntos</strong> con estos números, antes de mirar el contexto.</>
            ) : (
              <><strong className="font-semibold">Sin ventaja.</strong> Aquí lo correcto es no apostar.</>
            )}
          </p>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            La frecuencia es solo el punto de partida. Cada análisis la ajusta por minutos, rival y contexto.
          </p>
        </div>
      </div>
    </div>
  )
}
