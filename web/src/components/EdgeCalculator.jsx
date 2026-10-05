import { useId, useState } from 'react'
import { fmtNum } from '../format'

const pct = (v) => `${fmtNum(Math.round(v * 1000) / 10)} %`

function Barra({ label, value, tone }) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span className="tnum font-mono font-semibold">{pct(value)}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-surface-2">
        <div
          className={`h-full origin-left rounded-full transition-transform duration-300 ${tone}`}
          style={{ transform: `scaleX(${value})`, transitionTimingFunction: 'var(--ease-out)' }}
        />
      </div>
    </div>
  )
}

// Calculadora educativa: compara la probabilidad que implica la cuota con una estimación propia.
export default function EdgeCalculator() {
  const id = useId()
  const [cuota, setCuota] = useState(1.9)
  const [estimada, setEstimada] = useState(0.56)
  const implicita = 1 / cuota
  const ventaja = estimada - implicita
  const ev = estimada * cuota - 1
  const conVentaja = ventaja > 0

  return (
    <div className="rounded-3xl border border-line bg-surface p-6 shadow-[var(--shadow)] sm:p-7">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Haz la cuenta</h2>
        <span className="text-xs text-muted">Calculadora de ejemplo</span>
      </div>

      <div className="mt-6 grid gap-5">
        <label htmlFor={`${id}-c`} className="grid gap-2">
          <span className="flex items-baseline justify-between text-sm">
            <span>Cuota de la casa</span>
            <span className="tnum font-mono text-lg font-semibold">{fmtNum(cuota)}</span>
          </span>
          <input id={`${id}-c`} type="range" min="1.2" max="4" step="0.01" value={cuota}
            onChange={(e) => setCuota(Number(e.target.value))} className="accent-[var(--accent)]" />
        </label>
        <label htmlFor={`${id}-e`} className="grid gap-2">
          <span className="flex items-baseline justify-between text-sm">
            <span>Tu probabilidad estimada</span>
            <span className="tnum font-mono text-lg font-semibold">{pct(estimada)}</span>
          </span>
          <input id={`${id}-e`} type="range" min="0.05" max="0.95" step="0.005" value={estimada}
            onChange={(e) => setEstimada(Number(e.target.value))} className="accent-[var(--accent)]" />
        </label>
      </div>

      <div className="mt-7 grid gap-4">
        <Barra label="La cuota implica" value={Math.min(implicita, 1)} tone="bg-muted/60" />
        <Barra label="Tu estimación" value={estimada} tone="bg-accent" />
      </div>

      <div aria-live="polite" className={`mt-7 rounded-2xl p-4 ${conVentaja ? 'bg-accent-soft' : 'bg-surface-2'}`}>
        <p className="text-lg font-semibold">
          {conVentaja ? `Ventaja de ${fmtNum(Math.round(ventaja * 1000) / 10)} puntos` : 'Sin ventaja'}
        </p>
        <p className="mt-1 text-sm text-muted">
          {conVentaja
            ? `Valor esperado de ${fmtNum(Math.round(ev * 100) / 100)} unidades por cada unidad apostada, si la estimación es buena.`
            : 'La cuota paga menos de lo que vale el riesgo. Aquí lo correcto es no apostar.'}
        </p>
      </div>
      <p className="mt-4 text-xs leading-relaxed text-muted">
        La parte difícil es estimar bien la probabilidad. Eso es lo que hace cada análisis de PropDeep.
      </p>
    </div>
  )
}
