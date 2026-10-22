import { ArrowCounterClockwise, Coins, Stack, Trash, X } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import BankChart from '../components/BankChart'
import { AvisoResponsable, Cargando, Fallo, Pagina } from '../components/Zona'
import { boletoPaper, claveLeg, cuotaTotal, legParaEnviar, useBoletoPaper } from '../lib/combinada'
import { useCuenta } from '../lib/cuenta'
import { abrev } from '../lib/equipos'
import { conSigno, euros, usePaper } from '../lib/paper'
import { nombreCasa, resultado, seleccion } from '../lib/zona'
import { fmtCuota, fmtNum, fmtPct } from '../format'

const campo = 'mt-1 block h-11 w-full border border-white/30 bg-black px-3 text-white focus:border-gold focus:outline-none'
const num = (v) => Number(String(v).replace(',', '.'))
const ARRIBA = 'text-[#2fc4a9]'
const ABAJO = 'text-[#f07a5c]'
const tono = (v) => (v > 0 ? ARRIBA : v < 0 ? ABAJO : '')
const fecha = (iso) => new Date(iso).toLocaleString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

const ESTADO = {
  won: ['Ganada', 'bg-gold text-black'],
  lost: ['Perdida', 'bg-white text-black'],
  push: ['Nula', 'border border-white/40 text-muted'],
  void: ['Anulada', 'border border-white/40 text-muted'],
  pending: ['En juego', 'border border-dashed border-white/40 text-muted'],
}

function Dato({ label, children, nota }) {
  return (
    <div className="border-r-2 border-b-2 border-white/20 p-4">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="display tnum mt-1.5 text-[1.9rem] leading-none">{children}</dd>
      {nota && <p className="mt-1 text-xs text-muted">{nota}</p>}
    </div>
  )
}

function AjustesBank({ bank, accion }) {
  const [valor, setValor] = useState(String(bank.initial))
  const [error, setError] = useState('')
  const enviar = async (reset) => {
    setError('')
    try {
      await accion('/paper/bank', { method: 'POST', body: { initial: num(valor), reset } })
    } catch (e) {
      setError(e.message)
    }
  }
  return (
    <details className="border border-white/25 p-4">
      <summary className="cursor-pointer font-semibold">Bank inicial: {euros(bank.initial)} · cambiar o empezar de cero</summary>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-sm font-semibold">Bank inicial (€)
          <input inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} className={`${campo} w-40`} />
        </label>
        <button type="button" onClick={() => enviar(false)} className="btn btn-ghost h-11 px-4">Guardar</button>
        <button type="button" onClick={() => enviar(true)} className="btn btn-ghost h-11 px-4">
          <ArrowCounterClockwise aria-hidden className="size-4" /> Empezar de cero con este bank
        </button>
      </div>
      <p className="mt-3 text-sm text-muted">
        «Guardar» cambia el punto de partida y recalcula todo. «Empezar de cero» deja fuera las apuestas anteriores (no se borran).
      </p>
      {error && <p role="alert" className="mt-2 text-gold">{error}</p>}
    </details>
  )
}

function Boleto({ sugerido, accion }) {
  const legs = useBoletoPaper()
  const [f, setF] = useState({ bookmaker: '', odds: '', stake: '' })
  const [estado, setEstado] = useState({ enviando: false, error: '' })
  const calculada = cuotaTotal(legs)
  const odds = f.odds ? num(f.odds) : calculada
  const stake = num(f.stake) || 0

  if (legs.length === 0) {
    return (
      <p id="boleto" className="border border-dashed border-white/30 p-4 text-sm text-muted">
        <Stack aria-hidden className="mr-1 inline size-4 text-gold" /> Para una combinada paper, entra en el análisis de cada línea en{' '}
        <Link to="/partidos" className="text-gold underline">Partidos</Link> y pulsa «Añadir a combinada paper».
      </p>
    )
  }

  const enviar = async (e) => {
    e.preventDefault()
    setEstado({ enviando: true, error: '' })
    try {
      await accion('/paper/parlays', {
        method: 'POST',
        body: {
          bookmaker: f.bookmaker, odds: f.odds ? num(f.odds) : null, stake,
          legs: legs.map(legParaEnviar),
        },
      })
      boletoPaper.vaciar()
      setF({ bookmaker: '', odds: '', stake: '' })
      setEstado({ enviando: false, error: '' })
    } catch (err) {
      setEstado({ enviando: false, error: err.message })
    }
  }

  return (
    <form id="boleto" onSubmit={enviar} className="border-2 border-gold p-5">
      <p className="display flex items-center gap-2 text-[1.7rem] leading-none text-gold">
        <Stack aria-hidden className="size-6" /> Combinada paper · {legs.length}
      </p>
      <ul className="mt-3 divide-y divide-line border-y border-line">
        {legs.map((l) => (
          <li key={claveLeg(l)} className="flex items-center justify-between gap-3 py-2.5 text-sm">
            <span><strong>{l.player}</strong> · {seleccion(l)} · {fmtCuota(l.odds)}</span>
            <button type="button" onClick={() => boletoPaper.quitar(l)} className="p-1.5 text-muted hover:text-gold" aria-label={`Quitar ${l.player}`}>
              <X aria-hidden className="size-4" />
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-semibold">Casa<input required value={f.bookmaker} onChange={(e) => setF((x) => ({ ...x, bookmaker: e.target.value }))} className={campo} /></label>
        <label className="text-sm font-semibold">Cuota total
          <input inputMode="decimal" placeholder={fmtCuota(calculada)} value={f.odds} onChange={(e) => setF((x) => ({ ...x, odds: e.target.value }))} className={campo} />
        </label>
        <label className="text-sm font-semibold">Importe (€)
          <input required inputMode="decimal" placeholder={sugerido ? fmtNum(sugerido) : ''} value={f.stake} onChange={(e) => setF((x) => ({ ...x, stake: e.target.value }))} className={campo} />
        </label>
      </div>
      <p className="tnum mt-2 text-sm text-muted">
        {sugerido > 0 && (
          <button type="button" onClick={() => setF((x) => ({ ...x, stake: String(sugerido) }))} className="mr-3 text-gold underline">
            Sugerido: {euros(sugerido)}
          </button>
        )}
        {stake > 0 && <>Si gana cobras <strong className="text-white">{euros(stake * odds)}</strong> (beneficio {euros(stake * (odds - 1))})</>}
      </p>
      {legs.length < 2 && <p className="mt-2 text-sm text-muted">Añade al menos otra selección.</p>}
      {estado.error && <p role="alert" className="mt-3 text-gold">{estado.error}</p>}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="submit" disabled={estado.enviando || legs.length < 2 || !(stake > 0)} className="btn btn-gold h-12 px-6 text-lg disabled:opacity-60">
          <Coins aria-hidden className="size-5" /> {estado.enviando ? 'Guardando…' : 'Apostar combinada'}
        </button>
        <button type="button" onClick={boletoPaper.vaciar} className="text-sm text-muted underline">Vaciar</button>
      </div>
    </form>
  )
}

function Seleccion({ l }) {
  return (
    <span className="tnum">
      <strong className="font-semibold">{l.player}</strong> · {seleccion(l)}
      {l.away_team && l.home_team && <span className="text-muted"> · {abrev(l.away_team)} @ {abrev(l.home_team)}</span>}
    </span>
  )
}

function Apuesta({ b, accion }) {
  const [texto, clase] = ESTADO[b.status] || ESTADO.pending
  const combinada = b.kind === 'parlay'
  const legs = combinada ? b.legs : [b]
  const quitable = b.status === 'pending'
  const [error, setError] = useState('')
  const quitar = async () => {
    try {
      await accion(`/paper/bets/${b.kind}/${b.id}`, { method: 'DELETE' })
    } catch (e) {
      setError(e.message)
    }
  }
  return (
    <li className="grid gap-3 border-b border-line py-4 sm:grid-cols-[1fr_auto]">
      <div>
        <p className="text-xs text-muted">{combinada ? `Combinada de ${legs.length}` : 'Sencilla'} · {fecha(b.commence_time)} · {nombreCasa(b.bookmaker)}</p>
        <ul className="mt-1 space-y-0.5">
          {legs.map((l) => (
            <li key={l.id} className="flex flex-wrap items-center gap-x-2">
              <Seleccion l={l} />
              {combinada && <span className="text-sm text-muted">{fmtCuota(l.odds)}</span>}
              {combinada && l.status !== 'pending' && <span className={`px-1 text-[0.7rem] font-bold uppercase ${(ESTADO[l.status] || ESTADO.pending)[1]}`}>{(ESTADO[l.status] || ESTADO.pending)[0]}</span>}
              {l.actual != null && <span className="text-sm text-muted">{resultado(l)}</span>}
            </li>
          ))}
        </ul>
        {error && <p role="alert" className="mt-1 text-sm text-gold">{error}</p>}
      </div>
      <div className="tnum flex items-center gap-4 sm:justify-end sm:text-right">
        <div>
          <p className="text-sm">{euros(b.stake)} a {fmtCuota(b.settled_odds || b.odds)}</p>
          {b.status === 'pending'
            ? <p className="text-sm text-muted">Cobras {euros(b.potential_return)}</p>
            : <p className={`font-semibold ${tono(b.profit)}`}>{conSigno(b.profit)}</p>}
        </div>
        <span className={`px-2 py-0.5 text-xs font-bold uppercase ${clase}`}>{texto}</span>
        {quitable && (
          <button type="button" onClick={quitar} className="p-1.5 text-muted hover:text-gold" aria-label="Quitar esta apuesta">
            <Trash aria-hidden className="size-4" />
          </button>
        )}
      </div>
    </li>
  )
}

export default function PaperBets() {
  const { usuario, cargando: cargandoCuenta } = useCuenta()
  const { cargando, datos, error, recargar, accion } = usePaper()
  const [vista, setVista] = useState('abiertas')

  if (!cargandoCuenta && !usuario?.admin) return <Navigate to="/mis-picks" replace />
  if (cargando) return <Pagina><Cargando filas={3} /></Pagina>
  if (error || !datos) return <Pagina><Fallo reintentar={recargar} /></Pagina>

  const { bank: k, curve, bets, suggested } = datos
  const abiertas = bets.filter((b) => b.status === 'pending')
  const cerradas = bets.filter((b) => b.status !== 'pending')
  const lista = vista === 'abiertas' ? abiertas : cerradas

  return (
    <Pagina>
      <h1 className="display text-[3.4rem] leading-none sm:text-[5rem]">Paper bets</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        Tu bank de práctica en euros: apuestas como si fueran de verdad, se liquidan solas con el resultado real y aquí ves si vas ganando o perdiendo. Solo lo ves tú.
      </p>

      <section aria-label="Bank" className="mt-8 grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="border-2 border-white/25 p-4 sm:p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm text-muted">Bank actual</p>
              <p className="display tnum text-[3.6rem] leading-none sm:text-[4.4rem]">{euros(k.current)}</p>
            </div>
            <p className={`display tnum text-[2rem] leading-none ${tono(k.profit)}`}>
              {conSigno(k.profit)}{k.initial ? <span className="ml-2 text-lg">({k.profit >= 0 ? '+' : ''}{fmtPct(k.profit / k.initial)})</span> : null}
            </p>
          </div>
          <div className="mt-4">
            {curve.length > 1
              ? <BankChart curve={curve} initial={k.initial} />
              : <p className="border border-dashed border-white/25 px-4 py-12 text-center text-muted">La gráfica empieza cuando se liquide tu primera apuesta.</p>}
          </div>
        </div>
        <dl className="grid grid-cols-2 self-start border-t-2 border-l-2 border-white/20">
          <Dato label="Rendimiento (ROI)"><span className={tono(k.roi)}>{k.roi == null ? '-' : `${k.roi > 0 ? '+' : ''}${fmtPct(k.roi)}`}</span></Dato>
          <Dato label="Acierto" nota={`${k.won} ganadas · ${k.lost} perdidas`}>{k.hit_rate == null ? '-' : fmtPct(k.hit_rate)}</Dato>
          <Dato label="Peor racha">{k.worst_losing_streak} {k.worst_losing_streak === 1 ? 'fallo' : 'fallos'}</Dato>
          <Dato label="Caída máxima" nota="Desde el punto más alto">{euros(k.max_drawdown, 0)}</Dato>
          <Dato label="En juego" nota={`${k.pending} ${k.pending === 1 ? 'apuesta' : 'apuestas'}`}>{euros(k.at_risk, 0)}</Dato>
          <Dato label="Disponible" nota={`Sugerido por apuesta: ${euros(suggested.stake)}`}>{euros(k.available, 0)}</Dato>
        </dl>
      </section>

      <div className="mt-6"><AjustesBank key={k.initial} bank={k} accion={accion} /></div>
      <div className="mt-6"><Boleto sugerido={suggested.stake} accion={accion} /></div>

      <section aria-label="Apuestas" className="mt-10">
        <div className="flex flex-wrap items-center gap-2" role="tablist">
          {[['abiertas', `En juego (${abiertas.length})`], ['cerradas', `Liquidadas (${cerradas.length})`]].map(([v, t]) => (
            <button key={v} type="button" role="tab" aria-selected={vista === v} onClick={() => setVista(v)}
              className={`border px-4 py-2 font-semibold ${vista === v ? 'border-white bg-white text-black' : 'border-white/30 hover:border-white'}`}>{t}</button>
          ))}
        </div>
        {lista.length === 0 ? (
          <p className="mt-6 text-muted">
            {vista === 'abiertas'
              ? <>No tienes apuestas en juego. Entra en una línea de <Link to="/partidos" className="text-gold underline">Partidos</Link> y usa «Paper bet».</>
              : 'Todavía no se ha liquidado ninguna.'}
          </p>
        ) : (
          <ul className="mt-4 border-t border-line">
            {lista.map((b) => <Apuesta key={`${b.kind}-${b.id}`} b={b} accion={accion} />)}
          </ul>
        )}
      </section>

      <p className="mt-10 text-sm text-muted">
        El importe sugerido es el {Math.round(suggested.pct * 100)} % de lo que tienes disponible: apostar siempre una parte pequeña y fija del bank aguanta mejor las rachas malas.
      </p>
      <AvisoResponsable />
    </Pagina>
  )
}
