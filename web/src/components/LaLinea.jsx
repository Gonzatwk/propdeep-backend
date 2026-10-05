import { useId, useState } from 'react'
import { fmtNum } from '../format'

// Jugadores y partidos ficticios, inventados solo para explicar la idea.
const JUGADORES = [
  {
    id: 'escolta',
    nombre: 'Escolta anotador',
    stat: 'puntos',
    linea: 24.5,
    cuota: 1.85,
    partidos: [18, 27, 22, 31, 24, 19, 26, 29, 21, 25, 33, 23, 17, 28, 24, 26, 20, 30, 22, 25, 27, 16, 24, 29, 23, 26, 21, 35, 25, 28],
  },
  {
    id: 'pivot',
    nombre: 'Pívot reboteador',
    stat: 'rebotes',
    linea: 10.5,
    cuota: 2.0,
    partidos: [12, 9, 14, 11, 13, 10, 15, 12, 8, 13, 11, 14, 12, 16, 10, 13, 9, 12, 14, 11, 13, 12, 10, 15, 11, 12, 13, 9, 14, 12],
  },
  {
    id: 'base',
    nombre: 'Base organizador',
    stat: 'asistencias',
    linea: 8.5,
    cuota: 1.7,
    partidos: [7, 9, 8, 6, 10, 8, 7, 9, 5, 8, 11, 7, 8, 9, 6, 8, 10, 7, 8, 9, 7, 6, 9, 8, 10, 7, 8, 9, 6, 8],
  },
]

const R = 9
const COL = R * 2 + 1.5
const pct = (x) => `${Math.round(x * 100)} %`

function Grafico({ jugador, linea }) {
  const min = Math.min(...jugador.partidos) - 1
  const max = Math.max(...jugador.partidos) + 1
  const pila = {}
  const hexes = jugador.partidos.map((p) => {
    pila[p] = (pila[p] || 0) + 1
    return { p, n: pila[p] }
  })
  const altoMax = Math.max(8, ...Object.values(pila))
  // Ancho fijo de 24 columnas para que todos los jugadores se vean a la misma escala.
  const huecos = Math.max(max - min + 1, 24)
  const margen = Math.floor((huecos - (max - min + 1)) / 2)
  const ancho = huecos * COL
  const base = altoMax * (R * 2 + 1.5) + 26
  const alto = base + 22
  const xDe = (v) => (v - min + margen) * COL + COL / 2
  const paso = max - min > 14 ? 5 : 2
  const desde = min - margen
  const hasta = max + margen
  const marcas = []
  for (let v = Math.max(0, Math.ceil(desde / paso) * paso); v <= hasta; v += paso) marcas.push(v)
  const encima = jugador.partidos.filter((p) => p > linea).length

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="w-full" role="img" aria-label={`${jugador.stat} en 30 partidos: ${encima} por encima de ${fmtNum(linea)}.`}>
      <line x1="0" x2={ancho} y1={base} y2={base} stroke="var(--white)" strokeWidth="1.5" />
      {hexes.map(({ p, n }) => (
        <circle
          key={`${jugador.id}-${p}-${n}`}
          className="bar"
          cx={xDe(p)}
          cy={base - R - 2 - (n - 1) * (R * 2 + 1.5)}
          r={R}
          fill={p > linea ? 'var(--gold)' : 'var(--black-3)'}
          stroke={p > linea ? 'var(--gold)' : 'var(--grey)'}
          strokeWidth="1"
        />
      ))}
      {marcas.map((v) => (
        <text key={v} x={xDe(v)} y={alto - 4} textAnchor="middle" fontSize="11" fill="var(--muted)">{v}</text>
      ))}
      <g style={{ transform: `translateX(${xDe(linea)}px)`, transition: 'transform 260ms var(--ease-snap)' }}>
        <line x1="0" x2="0" y1="18" y2={base} stroke="var(--white)" strokeWidth="2.5" strokeDasharray="5 4" />
        <rect x="-22" y="0" width="44" height="18" fill="var(--white)" />
        <text x="0" y="13" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--black)">{fmtNum(linea)}</text>
      </g>
    </svg>
  )
}

export default function LaLinea() {
  const id = useId()
  const [actual, setActual] = useState(JUGADORES[0].id)
  const [ajustes, setAjustes] = useState(() => Object.fromEntries(JUGADORES.map((j) => [j.id, { linea: j.linea, cuota: j.cuota }])))
  const jugador = JUGADORES.find((j) => j.id === actual)
  const { linea, cuota } = ajustes[actual]
  const cambiar = (campo) => (e) => setAjustes((a) => ({ ...a, [actual]: { ...a[actual], [campo]: Number(e.target.value) } }))

  const encima = jugador.partidos.filter((p) => p > linea).length
  const frecuencia = encima / jugador.partidos.length
  const implicita = 1 / cuota
  const masAMenudo = frecuencia > implicita
  const min = Math.min(...jugador.partidos)
  const max = Math.max(...jugador.partidos)

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6">
      <div role="tablist" aria-label="Jugador de ejemplo" className="flex flex-wrap gap-2">
        {JUGADORES.map((j) => (
          <button
            key={j.id}
            role="tab"
            type="button"
            aria-selected={j.id === actual}
            onClick={() => setActual(j.id)}
            className={`btn h-11 px-4 text-lg ${j.id === actual ? 'btn-gold [--sweep:var(--gold)]' : 'btn-ghost text-white'}`}
          >
            {j.nombre}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-x-12 gap-y-8 panel border-2 border-white/30 p-5 sm:p-8 lg:grid-cols-[1.25fr_1fr]">
        <figure className="lg:row-span-2">
          <Grafico jugador={jugador} linea={linea} />
          <figcaption className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted">
            <span>Cada círculo es un partido. Últimos 30, {jugador.stat} por partido.</span>
            <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-full bg-gold" /> Por encima</span>
            <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-full border border-grey bg-black-3" /> Por debajo</span>
          </figcaption>
        </figure>

        <ol className="space-y-6">
          <li>
            <p className="text-sm font-semibold text-muted">1. La casa pone una línea</p>
            <label htmlFor={`${id}-l`} className="mt-1 block text-lg leading-snug">
              ¿Hará <strong>más de {fmtNum(linea)} {jugador.stat}</strong>?
            </label>
            <input id={`${id}-l`} type="range" className="slider" min={min - 0.5} max={max - 0.5} step={1} value={linea} onChange={cambiar('linea')} />
          </li>
          <li>
            <p className="text-sm font-semibold text-muted">2. Y una cuota</p>
            <label htmlFor={`${id}-c`} className="mt-1 block text-lg leading-snug">
              Paga <strong>{fmtNum(cuota)}</strong> por euro: la casa calcula que pasa el <strong className="tnum">{pct(implicita)}</strong> de las veces.
            </label>
            <input id={`${id}-c`} type="range" className="slider" min={1.3} max={3} step={0.05} value={cuota} onChange={cambiar('cuota')} />
          </li>
          <li>
            <p className="text-sm font-semibold text-muted">3. Y lo comparas con los datos</p>
            <p className="mt-1 text-lg leading-snug">
              En sus últimos 30 partidos la superó <strong className="tnum">{encima} veces</strong>: el <strong className="tnum">{pct(frecuencia)}</strong>.
            </p>
          </li>
        </ol>

        <div aria-live="polite" className={`relative overflow-hidden p-5 transition-colors duration-300 ${masAMenudo ? 'bg-gold text-black' : 'border-2 border-white text-white'}`}>
          <p className="display text-[2.4rem] leading-none">{masAMenudo ? 'Más que la cuota' : 'Menos que la cuota'}</p>
          <p className="mt-2 leading-snug">
            {masAMenudo
              ? `En estos partidos pasó más a menudo (${pct(frecuencia)}) de lo que la cuota da por hecho (${pct(implicita)}).`
              : `En estos partidos pasó menos a menudo (${pct(frecuencia)}) de lo que la cuota da por hecho (${pct(implicita)}).`}
            {' '}Es un dato, no una garantía: el pasado no asegura el próximo partido y la casa ya tiene en cuenta mucho de esto.
          </p>
        </div>
      </div>
      <p className="mt-4 text-sm text-muted">
        Jugadores y datos ficticios. Un análisis real también tiene en cuenta los minutos, el rival y las bajas.
      </p>
    </div>
  )
}
