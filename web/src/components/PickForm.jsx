import { PaperPlaneTilt } from '@phosphor-icons/react'
import { useState } from 'react'
import { api } from '../lib/sesion'
import { nombreCasa, STAT } from '../lib/zona'
import { fmtCuota, fmtNum } from '../format'

const campo = 'mt-1 block h-11 w-full border border-white/30 bg-black px-3 text-white focus:border-gold focus:outline-none'

// Formulario para que Gonza publique un pick. Con `linea`, sale de una línea de la zona
// (jugador, partido y casas ya puestos); sin ella, se rellena a mano.
export default function PickForm({ linea, onHecho }) {
  const books = linea?.books || []
  const [f, setF] = useState({
    side: 'over',
    book: books[0] ? 0 : -1,
    bookmaker: '',
    odds: books[0] ? String(books[0].over_odds) : '',
    line: linea ? String(linea.line) : '',
    player_name: '',
    stat: 'pts',
    commence_time: '',
    away_team: '',
    home_team: '',
    stake: '1',
    note: '',
  })
  const [estado, setEstado] = useState({ enviando: false, error: '', hecho: false })
  const cambia = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const num = (v) => Number(String(v).replace(',', '.'))

  // Al cambiar de casa o de lado, la cuota y la línea se rellenan con las de esa casa.
  const elige = (side, i) => {
    const b = books[i]
    setF((x) => ({ ...x, side, book: i, ...(b ? { odds: String(side === 'over' ? b.over_odds : b.under_odds), line: String(b.line) } : {}) }))
  }

  const enviar = async (e) => {
    e.preventDefault()
    const b = books[f.book]
    const body = {
      side: f.side,
      odds: num(f.odds),
      bookmaker: b ? nombreCasa(b.bookmaker) : f.bookmaker,
      stake: num(f.stake) || 1,
      note: f.note || null,
      line: num(f.line),
      ...(linea
        ? { line_id: linea.id }
        : {
            player_name: f.player_name,
            stat: f.stat,
            commence_time: f.commence_time ? new Date(f.commence_time).toISOString() : null,
            away_team: f.away_team || null,
            home_team: f.home_team || null,
          }),
    }
    setEstado({ enviando: true, error: '', hecho: false })
    try {
      await api('/picks', { method: 'POST', body })
      setEstado({ enviando: false, error: '', hecho: true })
      onHecho?.()
    } catch (err) {
      setEstado({ enviando: false, error: err.message, hecho: false })
    }
  }

  if (estado.hecho) {
    return <p role="status" className="border border-gold px-5 py-4">Publicado. Ya está en «Ejemplo de mis picks» y no se puede editar.</p>
  }

  return (
    <form onSubmit={enviar} className="border-2 border-gold p-5 sm:p-6">
      <p className="display text-[1.8rem] leading-none text-gold">Publicar como mi pick</p>
      <p className="mt-2 text-sm text-muted">Solo lo ves tú. Se publica con fecha y huella antes del partido, y después no se puede editar ni borrar.</p>

      {!linea && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-semibold">Jugador<input required value={f.player_name} onChange={cambia('player_name')} className={campo} /></label>
          <label className="text-sm font-semibold">Estadística
            <select value={f.stat} onChange={cambia('stat')} className={campo}>
              {Object.entries(STAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="text-sm font-semibold">Visitante<input value={f.away_team} onChange={cambia('away_team')} className={campo} /></label>
          <label className="text-sm font-semibold">Local<input value={f.home_team} onChange={cambia('home_team')} className={campo} /></label>
          <label className="text-sm font-semibold">Hora del partido<input required type="datetime-local" value={f.commence_time} onChange={cambia('commence_time')} className={campo} /></label>
          <label className="text-sm font-semibold">Casa<input required value={f.bookmaker} onChange={cambia('bookmaker')} className={campo} /></label>
        </div>
      )}

      <fieldset className="mt-5">
        <legend className="text-sm font-semibold">Lado</legend>
        <div className="mt-1 flex gap-2">
          {[['over', 'Más'], ['under', 'Menos']].map(([v, t]) => (
            <button key={v} type="button" aria-pressed={f.side === v} onClick={() => elige(v, f.book)}
              className={`h-11 border px-5 font-semibold ${f.side === v ? 'border-gold bg-gold text-black' : 'border-white/30'}`}>
              {t}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="mt-5 grid gap-4 sm:grid-cols-4">
        {books.length > 0 && (
          <label className="text-sm font-semibold sm:col-span-2">Casa
            <select value={f.book} onChange={(e) => elige(f.side, Number(e.target.value))} className={campo}>
              {books.map((b, i) => (
                <option key={`${b.bookmaker}-${b.line}`} value={i}>
                  {nombreCasa(b.bookmaker)} · {fmtNum(b.line)} · {fmtCuota(f.side === 'over' ? b.over_odds : b.under_odds)}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="text-sm font-semibold">Línea<input required inputMode="decimal" value={f.line} onChange={cambia('line')} className={campo} /></label>
        <label className="text-sm font-semibold">Cuota<input required inputMode="decimal" value={f.odds} onChange={cambia('odds')} className={campo} /></label>
        <label className="text-sm font-semibold">Unidades<input inputMode="decimal" value={f.stake} onChange={cambia('stake')} className={campo} /></label>
      </div>

      <label className="mt-5 block text-sm font-semibold">Por qué (opcional, se publica)
        <textarea maxLength={280} rows={2} value={f.note} onChange={cambia('note')} className={`${campo} h-auto py-2`} />
      </label>

      {estado.error && <p role="alert" className="mt-4 text-gold">{estado.error}</p>}
      <button type="submit" disabled={estado.enviando} className="btn btn-gold mt-5 h-12 px-6 text-lg disabled:opacity-60">
        <PaperPlaneTilt aria-hidden className="size-5" /> {estado.enviando ? 'Publicando…' : 'Publicar pick'}
      </button>
    </form>
  )
}
