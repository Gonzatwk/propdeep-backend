import { hexPoints, tono } from '../lib/hex'

// Media pista de la NBA a escala (10 unidades = 1 pie), aro arriba.
const ARO = [250, 52.5]
const R = 10.5

// Valor ilustrativo por zona, al estilo de un gráfico de tiro: caliente cerca del aro y en las esquinas,
// frío en la media distancia. No son datos reales.
function bin(x, y) {
  const d = Math.hypot(x - ARO[0], y - ARO[1])
  const ruido = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453
  const j = ruido - Math.floor(ruido)
  const esquina = y < 140 && (x < 34 || x > 466)
  if (esquina) return { v: 2.2 + j, s: 0.55 + j * 0.3 }
  if (d < 48) return { v: 2.4 + j, s: 0.82 }
  if (d < 125) return j < 0.3 ? null : { v: -0.6 + j * 1.6, s: 0.3 + j * 0.3 }
  if (d < 226) return j < 0.55 ? null : { v: -2.6 + j * 1.2, s: 0.2 + j * 0.25 }
  if (d < 262) return j < 0.15 ? null : { v: 0.4 + j * 2.4, s: 0.42 + j * 0.38 }
  if (d < 300) return j < 0.75 ? null : { v: -1.5 + j * 1.5, s: 0.18 + j * 0.15 }
  return null
}

const bins = []
const w = Math.sqrt(3) * R
for (let fila = 0, y = R; y < 330; fila++, y += 1.5 * R) {
  for (let x = (fila % 2 ? w / 2 : 0) + 6; x < 500; x += w) {
    const b = bin(x, y)
    if (b) bins.push({ x, y, ...b, d: Math.round(Math.hypot(x - ARO[0], y - ARO[1]) * 1.6) })
  }
}

// Vertical (aro arriba, recortada tras el triple) o horizontal (aro a la derecha, a sangre por el borde).
// Tiro de entrada: el balón sale desde fuera del triple y entra en el aro; entonces estallan los hexágonos.
const TIRO = { h: 'M95 420Q250 -40 412 244', v: 'M70 300Q120 -70 250 46' }
const LLEGADA = 1150

function Balon({ d }) {
  const quieto = typeof window !== 'undefined' && !window.matchMedia('(prefers-reduced-motion: no-preference)').matches
  if (quieto) return null
  return (
    <g>
      <path d={d} className="tray" stroke="var(--acid)" strokeWidth="2" />
      <g opacity="0">
        <circle r="10" fill="var(--orange)" stroke="var(--cobalt-deep)" strokeWidth="1.5" />
        <path d="M-10 0H10M0 -10V10" stroke="var(--cobalt-deep)" strokeWidth="1.2" />
        <animateMotion dur="1s" begin="0.15s" path={d} fill="freeze" keyPoints="0;1" keyTimes="0;1" calcMode="spline" keySplines="0.3 0 0.7 1" />
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.9;1" dur="1.15s" begin="0.15s" fill="freeze" />
      </g>
    </g>
  )
}

export default function Court({ horizontal = false, className = '' }) {
  return (
    <svg viewBox={horizontal ? '0 0 470 500' : '0 0 500 320'} className={className} aria-hidden fill="none" style={{ '--base': `${LLEGADA}ms` }}>
      <g transform={horizontal ? 'translate(470 0) rotate(90)' : undefined}>
      <g stroke="var(--court-line)" strokeWidth="1.6">
        <path d="M0 0.7H500" />
        <path d="M170 0V190H330V0" />
        <circle cx="250" cy="190" r="60" />
        <path d="M30 0V142A237.5 237.5 0 0 0 470 142V0" />
        <path d="M210 52.5A40 40 0 0 0 290 52.5" />
        <path d="M220 40H280" strokeWidth="3" stroke="var(--on-dark)" />
      </g>
      <g>
        {bins.map((b) => (
          <polygon
            key={`${b.x}-${b.y}`}
            className="bin"
            style={{ '--d': b.d }}
            points={hexPoints(b.x, b.y, R * b.s)}
            fill={tono(b.v)}
          />
        ))}
      </g>
      <circle cx="250" cy="52.5" r="7.5" stroke="var(--orange)" strokeWidth="2.5" />
      </g>
      <Balon d={horizontal ? TIRO.h : TIRO.v} />
    </svg>
  )
}

// Clave del gráfico: siete hexágonos de frío a caliente.
export function Leyenda({ className = '' }) {
  return (
    <div className={`flex items-center gap-3 text-xs font-medium ${className}`}>
      <span>Por debajo de la línea</span>
      <svg viewBox="0 0 126 18" className="h-[18px] w-[126px] shrink-0" aria-hidden>
        {[-3, -2, -1, 0, 1, 2, 3].map((v, i) => (
          <polygon key={v} points={hexPoints(9 + i * 18, 9, 8.6)} fill={tono(v)} />
        ))}
      </svg>
      <span>Por encima</span>
    </div>
  )
}
