import { Fingerprint } from '@phosphor-icons/react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import PickForm from '../../components/PickForm'
import {
  AvisoDemo, AvisoResponsable, Cargando, Fallo, Muro, Pagina, Tasa, Volver,
} from '../../components/Zona'
import { useCuenta } from '../../lib/cuenta'
import { nombreCasa, STAT } from '../../lib/zona'
import { abrev, corto, hora } from '../../lib/equipos'
import { useLinea, useModo } from '../../lib/tablero'
import { fmtCuota, fmtNum, fmtPct } from '../../format'

// Últimos 10 partidos frente a la línea: oro por encima, gris por debajo.
function Ultimos({ valores, linea }) {
  const xs = [...valores].reverse() // del más antiguo al más reciente
  const max = Math.max(linea * 1.6, ...xs, 1)
  const h = 120
  const y = (v) => h - (v / max) * (h - 14)
  return (
    <figure>
      <svg viewBox={`0 0 ${xs.length * 30} ${h + 18}`} className="h-40 w-full" role="img" aria-label={`Últimos ${xs.length} partidos frente a la línea de ${linea}`}>
        {xs.map((v, i) => (
          <g key={i}>
            <rect x={i * 30 + 5} y={y(v)} width="20" height={h - y(v)} fill={v > linea ? 'var(--gold)' : 'var(--black-3)'} />
            <text x={i * 30 + 15} y={y(v) - 4} textAnchor="middle" fontSize="10" fill="var(--muted)" className="tnum">{v}</text>
          </g>
        ))}
        <line x1="0" x2={xs.length * 30} y1={y(linea)} y2={y(linea)} stroke="var(--white)" strokeWidth="1.5" strokeDasharray="4 3" />
        <text x="2" y={h + 14} fontSize="10" fill="var(--muted)">Más antiguo</text>
        <text x={xs.length * 30 - 2} y={h + 14} fontSize="10" fill="var(--muted)" textAnchor="end">Último</text>
      </svg>
      <figcaption className="mt-1 text-xs text-muted">Línea discontinua: {fmtNum(linea)}. En oro, los partidos por encima.</figcaption>
    </figure>
  )
}

function Fila({ label, valor }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line py-2.5 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="tnum text-right font-semibold">{valor ?? '-'}</dd>
    </div>
  )
}

const pc = (v) => (v == null ? '-' : `${Math.round(v * 100)} %`)

// Casa, fuera y contra el rival: partidos, media y % sobre la línea.
function Desglose({ splits, rival }) {
  const filas = [['En casa', splits.home], ['Fuera', splits.away], [`Contra ${rival || 'este rival'}`, splits.vs_opponent]]
  return (
    <table className="tnum mt-3 w-full text-sm">
      <thead>
        <tr className="border-b border-white text-left text-xs text-muted">
          <th scope="col" className="py-2 font-semibold">Dónde</th>
          <th scope="col" className="py-2 text-right font-semibold">Partidos</th>
          <th scope="col" className="py-2 text-right font-semibold">Media</th>
          <th scope="col" className="py-2 text-right font-semibold">Superó la línea</th>
        </tr>
      </thead>
      <tbody>
        {filas.map(([t, b]) => (
          <tr key={t} className="border-b border-line">
            <th scope="row" className="py-2.5 text-left font-medium">{t}</th>
            <td className="py-2.5 text-right">{b?.games ?? 0}</td>
            <td className="py-2.5 text-right">{b?.games ? fmtNum(b.avg) : '-'}</td>
            <td className="py-2.5 text-right font-semibold">{b?.games ? pc(b.hit_rate) : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// Líneas de cada casa. En oro, la mejor opción para el más y para el menos.
function Comparador({ books, best }) {
  const es = (b, lado) => best?.[lado] && best[lado].bookmaker === b.bookmaker && best[lado].line === b.line
  const celda = (b, lado, cuota) => (
    <td className={`py-2.5 text-right ${es(b, lado) ? 'font-bold text-gold' : ''}`}>
      {fmtCuota(cuota)}{es(b, lado) && <span className="sr-only"> (mejor para el {lado === 'over' ? 'más' : 'menos'})</span>}
    </td>
  )
  return (
    <>
      <table className="tnum mt-3 w-full text-sm">
        <thead>
          <tr className="border-b border-white text-left text-xs text-muted">
            <th scope="col" className="py-2 font-semibold">Casa</th>
            <th scope="col" className="py-2 text-right font-semibold">Línea</th>
            <th scope="col" className="py-2 text-right font-semibold">Más</th>
            <th scope="col" className="py-2 text-right font-semibold">Menos</th>
          </tr>
        </thead>
        <tbody>
          {books.map((b) => (
            <tr key={`${b.bookmaker}-${b.line}`} className="border-b border-line">
              <th scope="row" className="py-2.5 text-left font-medium">{nombreCasa(b.bookmaker)}</th>
              <td className="py-2.5 text-right">{fmtNum(b.line)}</td>
              {celda(b, 'over', b.over_odds)}
              {celda(b, 'under', b.under_odds)}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted">
        En oro, la mejor opción de cada lado: para el más, la línea más baja; para el menos, la más alta; a igualdad, la cuota más alta.
        Las cuotas cambian: compruébalas en la casa antes de nada.
      </p>
    </>
  )
}

export default function Informe() {
  const { eventId, lineId } = useParams()
  const { enlace, demo } = useModo()
  const { usuario } = useCuenta()
  const [ahora] = useState(() => Date.now())
  const { cargando, datos: l, error, reintentar } = useLinea(lineId)
  const volver = enlace(`/partidos/${encodeURIComponent(eventId)}`)

  if (cargando) return <Pagina ancho="max-w-4xl"><Cargando filas={3} /></Pagina>
  if (error === 402) {
    return (
      <Pagina ancho="max-w-4xl">
        <AvisoDemo />
        <Volver to={volver}>Volver al partido</Volver>
        <div className="mt-8"><Muro /></div>
      </Pagina>
    )
  }
  if (error || !l) {
    return (
      <Pagina ancho="max-w-4xl">
        <Volver to={volver}>Volver al partido</Volver>
        <div className="mt-8">{error === 404 ? <p className="display text-[2.4rem] text-gold">No encontramos esta línea</p> : <Fallo reintentar={reintentar} />}</div>
      </Pagina>
    )
  }

  const t = l.trends || {}
  const c = l.context || {}
  const g = l.game || {}
  const h = l.hit_rates || {}
  const books = l.books?.length ? l.books : [{ bookmaker: l.bookmaker, line: l.line, over_odds: l.over_odds, under_odds: l.under_odds }]
  const diferencia = l.projection != null ? l.projection - l.line : null
  const porJugar = g.commence_time && new Date(g.commence_time).getTime() > ahora

  return (
    <Pagina ancho="max-w-4xl">
      <AvisoDemo />
      <Volver to={volver}>{abrev(g.away_team)} @ {abrev(g.home_team)}</Volver>

      <header className="mt-6 border-b-2 border-white pb-6">
        <p className="text-sm text-muted">{corto(g.away_team)} en {corto(g.home_team)} · {hora(g.commence_time)}</p>
        <h1 className="display mt-2 text-[3rem] leading-none sm:text-[4.4rem]">{l.player}</h1>
        <p className="mt-2 text-xl font-semibold">{STAT[l.stat]} · línea {fmtNum(l.line)}</p>
        <div className="mt-5 flex flex-wrap items-end gap-x-8 gap-y-3">
          <p>
            <span className="block text-xs text-muted">Nuestra proyección</span>
            <span className="display tnum text-[2.8rem] leading-none text-gold">{fmtNum(l.projection)}</span>
          </p>
          {diferencia != null && (
            <p className="tnum pb-1 text-sm text-muted">
              {fmtNum(Math.abs(Math.round(diferencia * 10) / 10))} {diferencia >= 0 ? 'por encima' : 'por debajo'} de la línea
            </p>
          )}
        </div>
      </header>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Cuántas veces superó la línea de {fmtNum(l.line)}</h2>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Tasa grande etiqueta="Últimos 5" valor={h.last5} partidos={Math.min(5, t.games ?? 5)} />
          <Tasa grande etiqueta="Últimos 10" valor={h.last10} partidos={Math.min(10, t.games ?? 10)} />
          <Tasa grande etiqueta="Esta temporada" valor={h.season} partidos={h.season_games} />
          <Tasa grande etiqueta="Temporada anterior" valor={h.last_season} partidos={h.last_season_games} />
        </div>
      </section>

      <section className="mt-10 grid gap-8 md:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold">Últimos partidos</h2>
          {t.recent_values?.length ? <Ultimos valores={t.recent_values} linea={l.line} /> : <p className="mt-2 text-muted">Sin datos.</p>}
        </div>
        <div>
          <h2 className="text-lg font-semibold">Casa, fuera y rival</h2>
          {t.splits ? <Desglose splits={t.splits} rival={c.opponent && corto(c.opponent)} /> : <p className="mt-2 text-muted">Sin datos.</p>}
          <p className="mt-2 text-xs text-muted">Esta temporada y la anterior.</p>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Líneas por casa</h2>
        <Comparador books={books} best={l.best} />
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Informe</h2>
        <p className="mt-3 text-lg leading-relaxed whitespace-pre-line">{l.report}</p>
        {l.notes?.length > 0 && <ul className="mt-3 list-disc pl-5 text-muted">{l.notes.map((r) => <li key={r}>{r}</li>)}</ul>}
      </section>

      <section className="mt-10 grid gap-x-10 md:grid-cols-2">
        <dl>
          <h2 className="mb-2 text-lg font-semibold">Medias y minutos</h2>
          <Fila label="Media últimos 5" valor={fmtNum(t.last5)} />
          <Fila label="Media últimos 10" valor={fmtNum(t.last10)} />
          <Fila label="Media últimos 20" valor={fmtNum(t.last20)} />
          <Fila label="Media de la temporada" valor={fmtNum(t.season)} />
          <Fila label="Minutos (últimos 5 / temporada)" valor={`${fmtNum(t.minutes_last5)} / ${fmtNum(t.minutes_season)}`} />
        </dl>
        <dl className="mt-8 md:mt-0">
          <h2 className="mb-2 text-lg font-semibold">Rival y contexto</h2>
          <Fila label="Rival" valor={c.opponent} />
          <Fila label="Juega" valor={c.home == null ? '-' : c.home ? 'En casa' : 'Fuera'} />
          <Fila label="Back-to-back" valor={c.back_to_back ? 'Sí' : 'No'} />
          {l.stat === 'pts' && <Fila label="Puntos que concede el rival" valor={c.opponent_factor ? `${c.opponent_factor >= 1 ? '+' : ''}${fmtPct(c.opponent_factor - 1)} vs media` : '-'} />}
          <Fila label="Lesiones" valor={c.injury_status ? `${c.injury_status}${c.injury_note ? ` · ${c.injury_note}` : ''}` : 'Sin parte'} />
        </dl>
      </section>

      {usuario?.admin && !demo && porJugar && <div className="mt-10"><PickForm linea={l} /></div>}

      {l.content_hash && (
        <p className="mt-8 flex items-start gap-2 text-xs break-all text-muted">
          <Fingerprint aria-hidden className="size-4 shrink-0" />
          Datos publicados el {new Date(l.published_at).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}. Huella: {l.content_hash}
        </p>
      )}
      <AvisoResponsable />
    </Pagina>
  )
}
