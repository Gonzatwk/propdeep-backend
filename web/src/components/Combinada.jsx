import { PaperPlaneTilt, Stack, X } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { claveLeg, combinada, cuotaTotal, legParaEnviar, useBoletoPaper, useCombinada } from '../lib/combinada'
import { abrev } from '../lib/equipos'
import { api } from '../lib/sesion'
import { seleccion } from '../lib/zona'
import { fmtCuota } from '../format'

const campo = 'mt-1 block h-11 w-full border border-white/30 bg-black px-3 text-white focus:border-gold focus:outline-none'
const num = (v) => Number(String(v).replace(',', '.'))

// Boleto de la combinada en preparación. Las selecciones se añaden desde el análisis de cada línea.
export default function Combinada({ onHecho }) {
  const legs = useCombinada()
  const [f, setF] = useState({ bookmaker: '', odds: '', stake: '1', note: '' })
  const [estado, setEstado] = useState({ enviando: false, error: '' })
  const cambia = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const calculada = cuotaTotal(legs)

  if (legs.length === 0) {
    return (
      <div id="combinada" className="border border-dashed border-white/40 p-5 text-sm text-muted">
        <p className="flex items-center gap-2 font-semibold text-white"><Stack aria-hidden className="size-5 text-gold" /> Combinadas</p>
        <p className="mt-2">
          Para hacer una, entra en el análisis de cada línea en <Link to="/partidos" className="text-gold underline">Partidos</Link> y pulsa
          «Añadir a combinada» (o en las cuotas a ganador de cada partido). Cuando tengas dos o más, la publicas aquí.
        </p>
      </div>
    )
  }

  const enviar = async (e) => {
    e.preventDefault()
    setEstado({ enviando: true, error: '' })
    try {
      await api('/parlays', {
        method: 'POST',
        body: {
          bookmaker: f.bookmaker,
          odds: f.odds ? num(f.odds) : null,
          stake: num(f.stake) || 1,
          note: f.note || null,
          legs: legs.map(legParaEnviar),
        },
      })
      combinada.vaciar()
      setF({ bookmaker: '', odds: '', stake: '1', note: '' })
      setEstado({ enviando: false, error: '' })
      onHecho?.()
    } catch (err) {
      setEstado({ enviando: false, error: err.message })
    }
  }

  return (
    <form id="combinada" onSubmit={enviar} className="border-2 border-gold p-5 sm:p-6">
      <p className="display flex items-center gap-2 text-[1.8rem] leading-none text-gold">
        <Stack aria-hidden className="size-6" /> Combinada · {legs.length} {legs.length === 1 ? 'selección' : 'selecciones'}
      </p>
      <ul className="mt-4 divide-y divide-line border-y border-line">
        {legs.map((l) => (
          <li key={claveLeg(l)} className="flex items-center justify-between gap-3 py-3">
            <span>
              <span className="font-semibold">{l.player}</span>
              <span className="tnum block text-sm text-muted">
                {seleccion(l)} · {fmtCuota(l.odds)}
                {l.away_team && l.home_team && <> · {abrev(l.away_team)} @ {abrev(l.home_team)}</>}
              </span>
            </span>
            <button type="button" onClick={() => combinada.quitar(l)} className="p-2 text-muted hover:text-gold" aria-label={`Quitar ${l.player}`}>
              <X aria-hidden className="size-5" />
            </button>
          </li>
        ))}
      </ul>
      {legs.length < 2 && <p className="mt-3 text-sm text-muted">Añade al menos otra selección para publicarla.</p>}

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-semibold">Casa<input required value={f.bookmaker} onChange={cambia('bookmaker')} className={campo} /></label>
        <label className="text-sm font-semibold">Cuota total
          <input inputMode="decimal" placeholder={fmtCuota(calculada)} value={f.odds} onChange={cambia('odds')} className={campo} />
        </label>
        <label className="text-sm font-semibold">Unidades<input inputMode="decimal" value={f.stake} onChange={cambia('stake')} className={campo} /></label>
      </div>
      <p className="mt-2 text-xs text-muted">
        Si dejas la cuota vacía se usa {fmtCuota(calculada)} (el producto de las selecciones). Pon la de tu casa si es distinta.
      </p>
      <label className="mt-4 block text-sm font-semibold">Por qué (opcional)
        <textarea maxLength={280} rows={2} value={f.note} onChange={cambia('note')} className={`${campo} h-auto py-2`} />
      </label>
      {estado.error && <p role="alert" className="mt-4 text-gold">{estado.error}</p>}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button type="submit" disabled={estado.enviando || legs.length < 2} className="btn btn-gold h-12 px-6 text-lg disabled:opacity-60">
          <PaperPlaneTilt aria-hidden className="size-5" /> {estado.enviando ? 'Publicando…' : 'Publicar combinada'}
        </button>
        <button type="button" onClick={combinada.vaciar} className="h-12 px-3 text-sm text-muted underline">Vaciar</button>
      </div>
    </form>
  )
}

// Aviso fijo abajo mientras hay una combinada a medias (de «Mis picks» o de «Paper bets»).
export function BarraCombinada() {
  const legs = useCombinada()
  const paper = useBoletoPaper()
  if (legs.length === 0 && paper.length === 0) return null
  const clase = 'flex items-center gap-2 border-2 border-gold bg-black px-4 py-3 font-semibold shadow-lg hover:bg-gold hover:text-black'
  return (
    <div className="fixed right-4 bottom-4 z-40 flex flex-col items-end gap-2">
      {legs.length > 0 && (
        <Link to="/mis-picks#combinada" className={clase}>
          <Stack aria-hidden className="size-5" /> Combinada: {legs.length} · {fmtCuota(cuotaTotal(legs))}
        </Link>
      )}
      {paper.length > 0 && (
        <Link to="/paper-bets#boleto" className={clase}>
          <Stack aria-hidden className="size-5" /> Paper: {paper.length} · {fmtCuota(cuotaTotal(paper))}
        </Link>
      )}
    </div>
  )
}
