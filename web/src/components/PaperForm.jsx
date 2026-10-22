import { Coins, Stack } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { boletoPaper, useBoletoPaper } from '../lib/combinada'
import { euros, usePaper } from '../lib/paper'
import { nombreCasa } from '../lib/zona'
import { fmtCuota, fmtNum } from '../format'

const campo = 'mt-1 block h-11 w-full border border-white/30 bg-black px-3 text-white focus:border-gold focus:outline-none'
const num = (v) => Number(String(v).replace(',', '.'))

// Apuesta simulada en euros desde el análisis de una línea (va a «Paper bets», no a «Mis picks»).
export default function PaperForm({ linea }) {
  const books = linea.books || []
  const { datos, accion } = usePaper()
  const legs = useBoletoPaper()
  const [f, setF] = useState({
    side: 'over', book: books[0] ? 0 : -1, bookmaker: '',
    odds: books[0] ? String(books[0].over_odds) : '', line: String(linea.line), stake: '',
  })
  const [estado, setEstado] = useState({ enviando: false, error: '', hecho: '' })
  const sugerido = datos?.suggested?.stake
  const stake = num(f.stake) || 0
  const odds = num(f.odds) || 0
  const enBoleto = legs.some((l) => l.line_id === linea.id)

  const elige = (side, i) => {
    const b = books[i]
    setF((x) => ({ ...x, side, book: i, ...(b ? { odds: String(side === 'over' ? b.over_odds : b.under_odds), line: String(b.line) } : {}) }))
  }
  const casa = () => (books[f.book] ? nombreCasa(books[f.book].bookmaker) : f.bookmaker)

  const apostar = async (e) => {
    e.preventDefault()
    setEstado({ enviando: true, error: '', hecho: '' })
    try {
      await accion('/paper/bets', {
        method: 'POST',
        body: { line_id: linea.id, side: f.side, odds, line: num(f.line), bookmaker: casa(), stake },
      })
      setEstado({ enviando: false, error: '', hecho: `Apuesta de ${euros(stake)} guardada en Paper bets.` })
    } catch (err) {
      setEstado({ enviando: false, error: err.message, hecho: '' })
    }
  }

  const aBoleto = () => {
    if (!(odds > 1)) return setEstado({ enviando: false, error: 'Pon la cuota de esta selección', hecho: '' })
    boletoPaper.añadir({
      line_id: linea.id, side: f.side, line: num(f.line), odds, player: linea.player, stat: linea.stat,
      commence_time: linea.game?.commence_time, away_team: linea.game?.away_team, home_team: linea.game?.home_team,
    })
    setEstado({ enviando: false, error: '', hecho: '' })
  }

  return (
    <form onSubmit={apostar} className="border-2 border-white/40 p-5 sm:p-6">
      <p className="display flex items-center gap-2 text-[1.8rem] leading-none"><Coins aria-hidden className="size-6 text-gold" /> Paper bet</p>
      <p className="mt-2 text-sm text-muted">Apuesta simulada en euros contra tu bank de práctica. No sale en «Mis picks».</p>

      <div className="mt-5 flex gap-2">
        {[['over', 'Más'], ['under', 'Menos']].map(([v, t]) => (
          <button key={v} type="button" aria-pressed={f.side === v} onClick={() => elige(v, f.book)}
            className={`h-11 border px-5 font-semibold ${f.side === v ? 'border-white bg-white text-black' : 'border-white/30'}`}>{t}</button>
        ))}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-4">
        {books.length > 0 ? (
          <label className="text-sm font-semibold sm:col-span-2">Casa
            <select value={f.book} onChange={(e) => elige(f.side, Number(e.target.value))} className={campo}>
              {books.map((b, i) => (
                <option key={`${b.bookmaker}-${b.line}`} value={i}>
                  {nombreCasa(b.bookmaker)} · {fmtNum(b.line)} · {fmtCuota(f.side === 'over' ? b.over_odds : b.under_odds)}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="text-sm font-semibold sm:col-span-2">Casa<input required value={f.bookmaker} onChange={(e) => setF((x) => ({ ...x, bookmaker: e.target.value }))} className={campo} /></label>
        )}
        <label className="text-sm font-semibold">Línea<input required inputMode="decimal" value={f.line} onChange={(e) => setF((x) => ({ ...x, line: e.target.value }))} className={campo} /></label>
        <label className="text-sm font-semibold">Cuota<input required inputMode="decimal" value={f.odds} onChange={(e) => setF((x) => ({ ...x, odds: e.target.value }))} className={campo} /></label>
      </div>

      <div className="mt-4 grid items-end gap-4 sm:grid-cols-[12rem_1fr]">
        <label className="text-sm font-semibold">Importe (€)
          <input required inputMode="decimal" placeholder={sugerido ? fmtNum(sugerido) : ''} value={f.stake}
            onChange={(e) => setF((x) => ({ ...x, stake: e.target.value }))} className={campo} />
        </label>
        <div className="tnum text-sm">
          {sugerido > 0 && (
            <button type="button" onClick={() => setF((x) => ({ ...x, stake: String(sugerido) }))} className="text-gold underline">
              Sugerido: {euros(sugerido)} (2 % del bank)
            </button>
          )}
          {stake > 0 && odds > 1 && (
            <p className="mt-1 text-muted">Si gana cobras <strong className="text-white">{euros(stake * odds)}</strong> (beneficio {euros(stake * (odds - 1))})</p>
          )}
        </div>
      </div>

      {estado.error && <p role="alert" className="mt-4 text-gold">{estado.error}</p>}
      {estado.hecho && <p role="status" className="mt-4">{estado.hecho} <Link to="/paper-bets" className="text-gold underline">Ver mi bank</Link></p>}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button type="submit" disabled={estado.enviando || !(stake > 0)} className="btn btn-gold h-12 px-6 text-lg disabled:opacity-60">
          <Coins aria-hidden className="size-5" /> {estado.enviando ? 'Guardando…' : 'Apostar (paper)'}
        </button>
        <button type="button" onClick={aBoleto} className="btn btn-ghost h-12 px-5">
          <Stack aria-hidden className="size-5" /> {enBoleto ? 'Actualizar en la combinada' : 'Añadir a combinada paper'}
        </button>
      </div>
      {enBoleto && (
        <p className="mt-3 text-sm text-muted">
          En la combinada paper ({legs.length}). <Link to="/paper-bets#boleto" className="text-gold underline">Ver y apostar la combinada</Link>
        </p>
      )}
    </form>
  )
}
