import { Calculator } from '@phosphor-icons/react'
import { useId, useState } from 'react'
import { fmtNum, fmtPct } from '../format'

const MIN_VENTAJA = 0.03

// Extra opcional: con la cuota de otra casa, ¿sigue habiendo ventaja?
// Usa nuestra probabilidad estimada y la compara con la implícita de esa cuota.
export default function Calculadora({ probOver, linea, ladoInicial = 'over' }) {
  const id = useId()
  const [lado, setLado] = useState(ladoInicial)
  const [texto, setTexto] = useState('')
  const cuota = parseFloat(texto.replace(',', '.'))
  const valida = cuota > 1 && cuota < 50
  const prob = lado === 'over' ? probOver : 1 - probOver
  const implicita = valida ? 1 / cuota : null
  const ventaja = valida ? prob - implicita : null
  const ev = valida ? prob * cuota - 1 : null
  const hay = valida && ventaja >= MIN_VENTAJA

  return (
    <section aria-labelledby={`${id}-t`} className="border border-white/30 p-5 sm:p-6">
      <h2 id={`${id}-t`} className="flex items-center gap-2 text-lg font-semibold">
        <Calculator aria-hidden className="size-5 text-gold" /> ¿Tienes otra cuota?
      </h2>
      <p className="mt-1 text-sm text-muted">Mete la cuota decimal de tu casa y mira si con nuestra probabilidad sigue habiendo ventaja.</p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div role="group" aria-label="Lado" className="flex border border-white/40">
          {[['over', 'Más'], ['under', 'Menos']].map(([v, t]) => (
            <button
              key={v}
              type="button"
              aria-pressed={lado === v}
              onClick={() => setLado(v)}
              className={`px-4 py-2 text-sm font-semibold ${lado === v ? 'bg-white text-black' : 'hover:bg-white/10'}`}
            >
              {t} de {fmtNum(linea)}
            </button>
          ))}
        </div>
        <label className="flex flex-col gap-1 text-sm text-muted">
          Cuota
          <input
            inputMode="decimal"
            autoComplete="off"
            placeholder="1,90"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className="tnum h-10 w-28 border border-white/40 bg-black px-3 text-base text-white placeholder:text-white/30 focus:border-gold focus:outline-none"
          />
        </label>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4" aria-live="polite">
        <div><dt className="text-muted">Nuestra prob.</dt><dd className="tnum mt-0.5 font-semibold">{fmtPct(prob)}</dd></div>
        <div><dt className="text-muted">Prob. de tu cuota</dt><dd className="tnum mt-0.5 font-semibold">{fmtPct(implicita)}</dd></div>
        <div><dt className="text-muted">Ventaja</dt><dd className="tnum mt-0.5 font-semibold">{valida ? fmtPct(ventaja) : '-'}</dd></div>
        <div><dt className="text-muted">Valor esperado por 10 €</dt><dd className="tnum mt-0.5 font-semibold">{valida ? `${ev >= 0 ? '+' : ''}${fmtNum(ev * 10)} €` : '-'}</dd></div>
      </dl>
      {valida && (
        <p className={`mt-4 px-3 py-2 text-sm font-semibold ${hay ? 'bg-gold text-black' : 'border border-white/30 text-muted'}`}>
          {hay
            ? `Con esa cuota hay ${fmtPct(ventaja)} de ventaja según nuestra estimación. Sigue siendo una apuesta con riesgo.`
            : 'Con esa cuota no vemos ventaja suficiente (pedimos al menos un 3 %). Sin ventaja, no hay jugada.'}
        </p>
      )}
    </section>
  )
}
