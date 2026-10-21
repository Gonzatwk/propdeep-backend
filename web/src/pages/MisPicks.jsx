import { Fingerprint, Plus, Stack, WarningCircle } from '@phosphor-icons/react'
import { useState } from 'react'
import Combinada from '../components/Combinada'
import PickForm from '../components/PickForm'
import { AvisoDemo, AvisoResponsable, Cargando, Fallo, Pagina } from '../components/Zona'
import { useCuenta } from '../lib/cuenta'
import { abrev } from '../lib/equipos'
import { api } from '../lib/sesion'
import { useModo, usePicks } from '../lib/tablero'
import { LADO, nombreCasa, STAT } from '../lib/zona'
import { fmtCuota, fmtNum, fmtPct, fmtUnidades } from '../format'

const AVISO = 'Resultados pasados no garantizan nada; a largo plazo es muy difícil ganar a la casa.'

const ESTADO = {
  won: ['Ganado', 'bg-gold text-black'],
  lost: ['Perdido', 'bg-white text-black'],
  push: ['Nulo', 'border border-white/40 text-muted'],
  void: ['Anulado', 'border border-white/40 text-muted'],
  pending: ['Pendiente', 'border border-dashed border-white/40 text-muted'],
}

const fecha = (iso, conHora = true) =>
  new Date(iso).toLocaleString('es-ES', conHora ? { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' } : { day: 'numeric', month: 'short' })

function Cifra({ label, valor }) {
  return (
    <div className="border-r-2 border-b-2 border-white/30 p-4 sm:p-5">
      <dt className="text-xs text-muted sm:text-sm">{label}</dt>
      <dd className="display tnum mt-2 text-[2.2rem] leading-none text-gold sm:text-[2.8rem]">{valor}</dd>
    </div>
  )
}

// Resultado a mano, solo para los picks que no salen de la zona (los demás se liquidan solos).
function Liquidar({ id, onHecho }) {
  const [valor, setValor] = useState('')
  const [error, setError] = useState('')
  const enviar = async (body) => {
    try {
      await api(`/picks/${id}/settle`, { method: 'POST', body })
      onHecho()
    } catch (e) {
      setError(e.message)
    }
  }
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
      <label className="sr-only" htmlFor={`res-${id}`}>Resultado</label>
      <input id={`res-${id}`} inputMode="decimal" placeholder="Resultado" value={valor} onChange={(e) => setValor(e.target.value)}
        className="h-9 w-28 border border-white/30 bg-black px-2" />
      <button type="button" className="btn btn-ghost h-9 px-3" onClick={() => enviar({ actual: Number(valor.replace(',', '.')) })} disabled={!valor}>Guardar resultado</button>
      <button type="button" className="h-9 px-3 text-muted underline" onClick={() => enviar({ void: true })}>No jugó</button>
      {error && <span role="alert" className="text-gold">{error}</span>}
    </div>
  )
}

function Pick({ p, admin, onCambio }) {
  const [texto, clase] = ESTADO[p.status] || ESTADO.pending
  const [ahora] = useState(() => Date.now())
  const empezado = new Date(p.commence_time).getTime() <= ahora
  return (
    <li className="border-b border-line py-5">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
        <div>
          <p className="text-xs text-muted">
            {p.away_team && p.home_team ? `${abrev(p.away_team)} @ ${abrev(p.home_team)} · ` : ''}Partido {fecha(p.commence_time)}
          </p>
          <p className="mt-1 text-xl font-semibold">{p.player}</p>
          <p className="tnum mt-0.5">
            {STAT[p.stat]}: <strong>{LADO[p.side]} de {fmtNum(p.line)}</strong> · cuota {fmtCuota(p.odds)} en {nombreCasa(p.bookmaker)}
            {p.stake !== 1 && <> · {fmtNum(p.stake)} u</>}
          </p>
        </div>
        <div className="text-right">
          <span className={`inline-block px-2 py-0.5 text-sm font-bold uppercase ${clase}`}>{texto}</span>
          {p.actual != null && <p className="tnum mt-1 text-sm text-muted">Hizo {fmtNum(p.actual)}</p>}
        </div>
      </div>
      {p.note && <p className="mt-2 max-w-2xl text-sm text-muted">«{p.note}»</p>}
      <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
        <Fingerprint aria-hidden className="size-3.5 shrink-0" />
        Publicado {fecha(p.published_at)}, antes del partido
        {p.content_hash && <span className="truncate" title={p.content_hash}> · huella {p.content_hash.slice(0, 12)}…</span>}
      </p>
      {admin && p.status === 'pending' && !p.auto_settle && empezado && <Liquidar id={p.id} onHecho={onCambio} />}
    </li>
  )
}

function Resumen({ r }) {
  return (
    <dl className="grid grid-cols-2 border-t-2 border-l-2 border-white/30 sm:grid-cols-4">
      <Cifra label="Publicados" valor={r.picks} />
      <Cifra label="Ganados / perdidos" valor={`${r.won} / ${r.lost}`} />
      <Cifra label="Unidades" valor={fmtUnidades(r.profit_units)} />
      <Cifra label="Rendimiento" valor={r.roi == null ? '-' : `${r.roi > 0 ? '+' : ''}${fmtPct(r.roi)}`} />
    </dl>
  )
}

function Parlay({ p }) {
  const [texto, clase] = ESTADO[p.status] || ESTADO.pending
  const cuota = p.settled_odds && p.settled_odds !== p.odds ? p.settled_odds : null
  return (
    <li className="border-b border-line py-5">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
        <div>
          <p className="text-xs text-muted">Combinada · primer partido {fecha(p.commence_time)}</p>
          <p className="tnum mt-1 text-xl font-semibold">
            {p.legs.length} selecciones · cuota {fmtCuota(p.odds)} en {nombreCasa(p.bookmaker)}
            {p.stake !== 1 && <> · {fmtNum(p.stake)} u</>}
          </p>
          {cuota && <p className="tnum text-sm text-muted">Cuota final {fmtCuota(cuota)} sin las anuladas</p>}
        </div>
        <span className={`inline-block px-2 py-0.5 text-sm font-bold uppercase ${clase}`}>{texto}</span>
      </div>
      <ul className="mt-3 space-y-1.5 border-l-2 border-white/20 pl-4">
        {p.legs.map((l) => {
          const [t, c] = ESTADO[l.status] || ESTADO.pending
          return (
            <li key={l.id} className="tnum flex flex-wrap items-center gap-x-3 text-sm">
              <span className="font-semibold">{l.player}</span>
              <span>{STAT[l.stat]}: {LADO[l.side]} de {fmtNum(l.line)} · {fmtCuota(l.odds)}</span>
              {l.away_team && l.home_team && <span className="text-muted">{abrev(l.away_team)} @ {abrev(l.home_team)}</span>}
              <span className={`px-1.5 text-xs font-bold uppercase ${c}`}>{t}</span>
              {l.actual != null && <span className="text-muted">hizo {fmtNum(l.actual)}</span>}
            </li>
          )
        })}
      </ul>
      {p.note && <p className="mt-2 max-w-2xl text-sm text-muted">«{p.note}»</p>}
      <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
        <Fingerprint aria-hidden className="size-3.5 shrink-0" />
        Publicada {fecha(p.published_at)}, antes de sus partidos
        {p.content_hash && <span className="truncate" title={p.content_hash}> · huella {p.content_hash.slice(0, 12)}…</span>}
      </p>
    </li>
  )
}

export default function MisPicks() {
  const { demo } = useModo()
  const { usuario } = useCuenta()
  const [version, setVersion] = useState(0)
  const [nuevo, setNuevo] = useState(false)
  const { cargando, datos, error, reintentar } = usePicks(version)
  const admin = Boolean(usuario?.admin) && !demo
  const r = datos?.summary
  const picks = datos?.picks || []
  const parlays = datos?.parlays || []
  const recargar = () => setVersion((v) => v + 1)

  return (
    <Pagina ancho="max-w-4xl">
      <AvisoDemo sinVista />
      <h1 className="display text-[3rem] leading-[0.95] sm:text-[4.6rem]">
        Ejemplo de mis picks <span className="hueco hueco-blanco block">con ayuda de la página</span>
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
        Son los picks del fundador de PropDeep, hechos con los datos de la página. No son del modelo ni una recomendación.
        Se publican antes del partido con su cuota y su casa, no se pueden editar ni borrar, y salen todos: también los fallados.
      </p>
      <p role="note" className="mt-6 flex items-start gap-3 border-2 border-gold px-4 py-3 font-semibold">
        <WarningCircle aria-hidden weight="bold" className="mt-0.5 size-5 shrink-0 text-gold" />
        {datos?.warning || AVISO}
      </p>

      {admin && (
        <div className="mt-8">
          {nuevo ? <PickForm onHecho={recargar} /> : (
            <button type="button" className="btn btn-ghost h-11 px-4" onClick={() => setNuevo(true)}>
              <Plus aria-hidden className="size-4" /> Publicar un pick a mano
            </button>
          )}
          <p className="mt-2 text-sm text-muted">Desde el análisis de cada línea también puedes publicarlo con la casa y la cuota ya puestas.</p>
          <div className="mt-6"><Combinada onHecho={recargar} /></div>
        </div>
      )}

      <div className="mt-10">
        {cargando ? (
          <Cargando filas={2} />
        ) : error === 'sin-servidor' || (!error && picks.length === 0 && parlays.length === 0) ? (
          <div className="border border-dashed border-white/40 px-6 py-14 text-center">
            <p className="display text-[2.4rem] leading-none text-gold sm:text-[3rem]">El primer pick llega con la temporada</p>
            <p className="mx-auto mt-4 max-w-md text-muted">La temporada regular empieza el 20 de octubre. Cada pick saldrá aquí antes de su partido.</p>
          </div>
        ) : error ? (
          <Fallo reintentar={reintentar} />
        ) : (
          <>
            {parlays.length > 0 && datos.total && (
              <div className="mb-10">
                <h2 className="display text-[2rem] leading-none">Total</h2>
                <p className="mt-1 text-sm text-muted">Picks sueltos y combinadas juntos.</p>
                <div className="mt-4"><Resumen r={datos.total} /></div>
              </div>
            )}
            {parlays.length > 0 && <h2 className="display mb-4 text-[2rem] leading-none">Picks sueltos</h2>}
            <Resumen r={r} />
            <p className="mt-3 text-sm text-muted">
              Cada pick arriesga 1 unidad salvo que diga otra cosa. {r.pending > 0 && `${r.pending} pendiente${r.pending === 1 ? '' : 's'}. `}
              {r.push_or_void > 0 && `${r.push_or_void} nulo${r.push_or_void === 1 ? '' : 's'} o anulado${r.push_or_void === 1 ? '' : 's'}, que no cuentan.`}
            </p>
            <ul className="mt-8 border-t border-line">
              {picks.map((p) => <Pick key={p.id} p={p} admin={admin} onCambio={recargar} />)}
            </ul>
            {parlays.length > 0 && (
              <section className="mt-12" aria-label="Combinadas">
                <h2 className="display mb-4 flex items-center gap-2 text-[2rem] leading-none">
                  <Stack aria-hidden className="size-7 text-gold" /> Combinadas
                </h2>
                <Resumen r={datos.parlay_summary} />
                <p className="mt-3 text-sm text-muted">
                  Una combinada gana solo si aciertan todas sus selecciones. Si una se anula, sale de la cuota, como en las casas.
                </p>
                <ul className="mt-6 border-t border-line">
                  {parlays.map((p) => <Parlay key={`c${p.id}`} p={p} />)}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
      <AvisoResponsable />
    </Pagina>
  )
}
