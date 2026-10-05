import { Fingerprint } from '@phosphor-icons/react'
import { useParams } from 'react-router-dom'
import Calculadora from '../../components/Calculadora'
import {
  AvisoDemo, AvisoResponsable, Cargando, Confianza, Fallo, Muro, Pagina, Veredicto, Volver,
} from '../../components/Zona'
import { LADO, STAT } from '../../lib/zona'
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

function Barra({ label, valor, oro }) {
  return (
    <div>
      <div className="flex justify-between text-sm"><span className="text-muted">{label}</span><span className="tnum font-semibold">{fmtPct(valor)}</span></div>
      <div className="mt-1 h-2.5 bg-black-3"><div className={`h-full ${oro ? 'bg-gold' : 'bg-white/60'}`} style={{ width: `${Math.max(0, Math.min(1, valor)) * 100}%` }} /></div>
    </div>
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

export default function Informe() {
  const { eventId, lineId } = useParams()
  const { enlace } = useModo()
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
  const lado = l.side || 'over'
  const cuota = lado === 'over' ? l.over_odds : l.under_odds
  const nuestra = lado === 'over' ? l.prob_over : 1 - l.prob_over
  const implicita = 1 / cuota
  const mercado = lado === 'over' ? l.prob_over_market : 1 - l.prob_over_market

  return (
    <Pagina ancho="max-w-4xl">
      <AvisoDemo />
      <Volver to={volver}>{abrev(g.away_team)} @ {abrev(g.home_team)}</Volver>

      <header className="mt-6 border-b-2 border-white pb-6">
        <p className="text-sm text-muted">{corto(g.away_team)} en {corto(g.home_team)} · {hora(g.commence_time)}</p>
        <h1 className="display mt-2 text-[3rem] leading-none sm:text-[4.4rem]">{l.player}</h1>
        <p className="mt-2 text-xl font-semibold">{STAT[l.stat]} · línea {fmtNum(l.line)}</p>
        <div className="mt-5 flex flex-wrap items-center gap-4">
          <Veredicto linea={l} grande />
          {l.side && <Confianza nivel={l.confidence} />}
        </div>
      </header>

      <section className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Probabilidad del {LADO[lado].toLowerCase()} de {fmtNum(l.line)}</h2>
          <Barra label="Nuestra estimación" valor={nuestra} oro />
          <Barra label={`Implícita en la cuota ${fmtCuota(cuota)}`} valor={implicita} />
          <Barra label="Mercado sin margen" valor={mercado} />
          <p className="text-sm text-muted">
            {l.side
              ? <>Ventaja de <strong className="text-white">{fmtPct(l.edge)}</strong>{l.expected_value != null && <> · valor esperado {l.expected_value >= 0 ? '+' : ''}{fmtNum(l.expected_value * 10)} € por cada 10 €</>}.</>
              : 'La diferencia no llega al 3 % que pedimos: sin ventaja, no hay jugada.'}
          </p>
        </div>
        <div>
          <h2 className="text-lg font-semibold">Últimos partidos</h2>
          {t.recent_values?.length ? <Ultimos valores={t.recent_values} linea={l.line} /> : <p className="mt-2 text-muted">Sin datos.</p>}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Informe</h2>
        <p className="mt-3 text-lg leading-relaxed whitespace-pre-line">{l.report}</p>
        {l.reasons?.length > 0 && <ul className="mt-3 list-disc pl-5 text-muted">{l.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
      </section>

      <section className="mt-10 grid gap-x-10 md:grid-cols-2">
        <dl>
          <h2 className="mb-2 text-lg font-semibold">Tendencias</h2>
          <Fila label="Proyección" valor={fmtNum(l.projection)} />
          <Fila label="Media últimos 5" valor={fmtNum(t.last5)} />
          <Fila label="Media últimos 10" valor={fmtNum(t.last10)} />
          <Fila label="Media últimos 20" valor={fmtNum(t.last20)} />
          <Fila label="Media de la temporada" valor={fmtNum(t.season)} />
          <Fila label="Superó la línea (últimos 10)" valor={fmtPct(t.hit_rate_last10)} />
          <Fila label="Minutos (últimos 5 / temporada)" valor={`${fmtNum(t.minutes_last5)} / ${fmtNum(t.minutes_season)}`} />
        </dl>
        <dl className="mt-8 md:mt-0">
          <h2 className="mb-2 text-lg font-semibold">Rival y contexto</h2>
          <Fila label="Rival" valor={c.opponent} />
          <Fila label="Juega" valor={c.home == null ? '-' : c.home ? 'En casa' : 'Fuera'} />
          <Fila label="Back-to-back" valor={c.back_to_back ? 'Sí' : 'No'} />
          {l.stat === 'pts' && <Fila label="Puntos que concede el rival" valor={c.opponent_factor ? `${c.opponent_factor >= 1 ? '+' : ''}${fmtPct(c.opponent_factor - 1)} vs media` : '-'} />}
          <Fila label="Lesiones" valor={c.injury_status ? `${c.injury_status}${c.injury_note ? ` · ${c.injury_note}` : ''}` : 'Sin parte'} />
          <Fila label="Cuotas (casa)" valor={`${fmtCuota(l.over_odds)} / ${fmtCuota(l.under_odds)}${l.bookmaker ? ` · ${l.bookmaker}` : ''}`} />
        </dl>
      </section>

      {l.prob_over != null && <div className="mt-10"><Calculadora probOver={l.prob_over} linea={l.line} ladoInicial={lado} /></div>}

      {l.content_hash && (
        <p className="mt-8 flex items-start gap-2 text-xs break-all text-muted">
          <Fingerprint aria-hidden className="size-4 shrink-0" />
          Publicado el {new Date(l.published_at).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })} y guardado en el historial. Huella: {l.content_hash}
        </p>
      )}
      <AvisoResponsable />
    </Pagina>
  )
}
