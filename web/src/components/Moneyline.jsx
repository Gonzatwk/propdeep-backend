import { Coins, PaperPlaneTilt, Stack, Trophy } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { boletoPaper, claveLeg, combinada, useBoletoPaper, useCombinada } from '../lib/combinada'
import { abrev, corto } from '../lib/equipos'
import { euros, usePaper } from '../lib/paper'
import { api } from '../lib/sesion'
import { nombreCasa } from '../lib/zona'
import { fmtCuota, fmtNum } from '../format'

const campo = 'mt-1 block h-11 w-full border border-white/30 bg-black px-3 text-white focus:border-gold focus:outline-none'
const num = (v) => Number(String(v).replace(',', '.'))
const cuotaDe = (b, lado) => (lado === 'home' ? b.home_odds : b.away_odds)

// Mejor cuota a ganador en la tarjeta de un partido (lista de Partidos).
export function MoneylineCorta({ g }) {
  const m = g.moneyline?.best
  if (!m?.home || !m?.away) return null
  return (
    <span className="tnum text-muted">
      Ganador: {abrev(g.away_team)} <strong className="text-white">{fmtCuota(m.away.odds)}</strong> · {abrev(g.home_team)} <strong className="text-white">{fmtCuota(m.home.odds)}</strong>
    </span>
  )
}

// Cuotas a ganador del partido con todas las casas. El autor puede apostarlas desde aquí.
export default function Moneyline({ g, autor }) {
  const ml = g.moneyline
  const [lado, setLado] = useState(null)
  const [ahora] = useState(() => Date.now())
  if (!ml?.books?.length) return null
  const { best } = ml
  const empezado = new Date(g.commence_time).getTime() <= ahora
  const equipos = [['away', g.away_team], ['home', g.home_team]]

  return (
    <section aria-labelledby="ml-titulo" className="mt-8 border-2 border-white/25 p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="ml-titulo" className="display flex items-center gap-2 text-[1.9rem] leading-none">
          <Trophy aria-hidden className="size-6 text-gold" /> Ganador del partido
        </h2>
        <p className="text-sm text-muted">Mejor cuota de {ml.books.length} {ml.books.length === 1 ? 'casa' : 'casas'}{autor ? ' · pulsa un equipo para apostarlo' : ''}</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {equipos.map(([k, team]) => {
          const b = best[k]
          const contenido = (
            <>
              <span className="display block text-[2rem] leading-none">{abrev(team)}</span>
              <span className="block text-sm text-muted">{corto(team)}</span>
              <span className="display tnum mt-2 block text-[2.4rem] leading-none text-gold">{fmtCuota(b?.odds)}</span>
              <span className="block text-xs text-muted">{nombreCasa(b?.bookmaker)}</span>
            </>
          )
          return autor ? (
            <button key={k} type="button" aria-pressed={lado === k} onClick={() => setLado(lado === k ? null : k)}
              className={`border-2 p-4 text-left transition-colors ${lado === k ? 'border-gold bg-gold/10' : 'border-white/20 hover:border-gold'}`}>
              {contenido}
            </button>
          ) : (
            <div key={k} className="border-2 border-white/20 p-4">{contenido}</div>
          )
        })}
      </div>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-semibold text-gold">Comparar casas</summary>
        <table className="tnum mt-3 w-full text-left">
          <thead className="text-muted">
            <tr><th className="py-1.5 font-semibold">Casa</th><th className="py-1.5 text-right font-semibold">{abrev(g.away_team)}</th><th className="py-1.5 text-right font-semibold">{abrev(g.home_team)}</th></tr>
          </thead>
          <tbody>
            {ml.books.map((b) => (
              <tr key={b.bookmaker} className="border-t border-line">
                <td className="py-1.5">{nombreCasa(b.bookmaker)}</td>
                {['away', 'home'].map((k) => (
                  <td key={k} className={`py-1.5 text-right ${cuotaDe(b, k) === best[k]?.odds ? 'font-bold text-gold' : ''}`}>{fmtCuota(cuotaDe(b, k))}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-muted">Cuotas de antes del partido; se actualizan cada hora mientras el servidor está encendido.</p>
      </details>

      {autor && lado && <Apostar key={lado} g={g} lado={lado} empezado={empezado} team={lado === 'home' ? g.home_team : g.away_team} />}
    </section>
  )
}

function Apostar({ g, lado, team, empezado }) {
  const books = [...g.moneyline.books].sort((a, b) => cuotaDe(b, lado) - cuotaDe(a, lado))
  const [book, setBook] = useState(0)
  const [odds, setOdds] = useState(String(cuotaDe(books[0], lado)))
  const [unidades, setUnidades] = useState('1')
  const [importe, setImporte] = useState('')
  const [estado, setEstado] = useState({ enviando: false, error: '', hecho: '' })
  const { datos, accion } = usePaper()
  const legs = useCombinada()
  const paperLegs = useBoletoPaper()
  const sugerido = datos?.suggested?.stake
  const cuota = num(odds) || 0
  const stake = num(importe) || 0
  const base = { stat: 'ml', event_id: g.event_id, team, side: 'over', odds: cuota, bookmaker: nombreCasa(books[book].bookmaker) }
  const leg = { ...base, player: team, line: 0, commence_time: g.commence_time, away_team: g.away_team, home_team: g.home_team }
  const clave = claveLeg(leg)

  const elige = (i) => { setBook(i); setOdds(String(cuotaDe(books[i], lado))) }
  const hacer = async (fn, hecho) => {
    if (!(cuota > 1)) return setEstado({ enviando: false, error: 'Pon una cuota válida', hecho: '' })
    setEstado({ enviando: true, error: '', hecho: '' })
    try {
      await fn()
      setEstado({ enviando: false, error: '', hecho })
    } catch (err) {
      setEstado({ enviando: false, error: err.message, hecho: '' })
    }
  }
  const aBoleto = (boleto, nombre) => {
    if (!(cuota > 1)) return setEstado({ enviando: false, error: 'Pon una cuota válida', hecho: '' })
    boleto.añadir(leg)
    setEstado({ enviando: false, error: '', hecho: `${abrev(team)} gana, añadido a la ${nombre}.` })
  }

  return (
    <div className="mt-5 border-t-2 border-gold pt-5">
      <p className="font-semibold">Apostar: <span className="text-gold">gana {corto(team)}</span></p>
      <div className="mt-3 grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-semibold sm:col-span-2">Casa
          <select value={book} onChange={(e) => elige(Number(e.target.value))} className={campo}>
            {books.map((b, i) => <option key={b.bookmaker} value={i}>{nombreCasa(b.bookmaker)} · {fmtCuota(cuotaDe(b, lado))}</option>)}
          </select>
        </label>
        <label className="text-sm font-semibold">Cuota<input inputMode="decimal" value={odds} onChange={(e) => setOdds(e.target.value)} className={campo} /></label>
      </div>

      {empezado && <p className="mt-3 text-sm text-muted">El partido ya ha empezado: solo puedes apuntarlo en Paper bets. Pon la cuota que te dé tu casa en directo.</p>}
      <div className="mt-5 grid gap-5 md:grid-cols-2">
        {!empezado && <div className="border border-gold/60 p-4">
          <p className="text-sm font-semibold text-gold">Mis picks</p>
          <label className="mt-2 block text-sm font-semibold">Unidades<input inputMode="decimal" value={unidades} onChange={(e) => setUnidades(e.target.value)} className={campo} /></label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" disabled={estado.enviando} className="btn btn-gold h-11 px-4 disabled:opacity-60"
              onClick={() => hacer(() => api('/picks', { method: 'POST', body: { ...base, stake: num(unidades) || 1 } }), 'Publicado en Mis picks. Ya no se puede editar.')}>
              <PaperPlaneTilt aria-hidden className="size-5" /> Publicar pick
            </button>
            <button type="button" onClick={() => aBoleto(combinada, 'combinada')} className="btn btn-ghost h-11 px-4">
              <Stack aria-hidden className="size-5" /> {legs.some((l) => claveLeg(l) === clave) ? 'Actualizar en combinada' : 'A la combinada'}
            </button>
          </div>
        </div>}
        <div className="border border-white/40 p-4">
          <p className="text-sm font-semibold">Paper bets</p>
          <label className="mt-2 block text-sm font-semibold">Importe (€)
            <input inputMode="decimal" placeholder={sugerido ? fmtNum(sugerido) : ''} value={importe} onChange={(e) => setImporte(e.target.value)} className={campo} />
          </label>
          <p className="tnum mt-1 min-h-5 text-xs text-muted">
            {sugerido > 0 && <button type="button" onClick={() => setImporte(String(sugerido))} className="mr-2 text-gold underline">Sugerido: {euros(sugerido)}</button>}
            {stake > 0 && cuota > 1 && <>Cobras {euros(stake * cuota)}</>}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" disabled={estado.enviando || !(stake > 0)} className="btn btn-ghost h-11 px-4 disabled:opacity-60"
              onClick={() => hacer(() => accion('/paper/bets', { method: 'POST', body: { ...base, stake } }), `Apuesta de ${euros(stake)} guardada en Paper bets.`)}>
              <Coins aria-hidden className="size-5" /> Apostar (paper)
            </button>
            <button type="button" onClick={() => aBoleto(boletoPaper, 'combinada paper')} className="btn btn-ghost h-11 px-4">
              <Stack aria-hidden className="size-5" /> {paperLegs.some((l) => claveLeg(l) === clave) ? 'Actualizar' : 'A combinada paper'}
            </button>
          </div>
        </div>
      </div>
      {estado.error && <p role="alert" className="mt-4 text-gold">{estado.error}</p>}
      {estado.hecho && (
        <p role="status" className="mt-4">
          {estado.hecho} <Link to="/mis-picks" className="text-gold underline">Mis picks</Link> · <Link to="/paper-bets" className="text-gold underline">Paper bets</Link>
        </p>
      )}
    </div>
  )
}
