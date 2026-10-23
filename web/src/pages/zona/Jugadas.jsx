import { ArrowRight, CalendarBlank, LockSimple } from '@phosphor-icons/react'
import { Link, useSearchParams } from 'react-router-dom'
import { AvisoResponsable, Cargando, Fallo, Muro, Pagina } from '../../components/Zona'
import { fmtNum, fmtPct } from '../../format'
import { abrev, hora, jornada } from '../../lib/equipos'
import { useJugadas } from '../../lib/tablero'
import { LADO, STAT } from '../../lib/zona'

// Resultado de una jugada ya liquidada.
const RESULTADO = {
  won: ['Acertada', 'bg-gold text-black'],
  lost: ['Fallada', 'border border-white/60 text-white'],
  push: ['Nula', 'border border-white/30 text-muted'],
  void: ['Anulada', 'border border-white/30 text-muted'],
}

function Partido({ g }) {
  return (
    <p className="tnum text-sm text-muted">
      {abrev(g.away_team)} @ {abrev(g.home_team)} · {hora(g.commence_time)}
    </p>
  )
}

function Nota({ valor }) {
  return (
    <p className="shrink-0 text-right">
      <span className="display tnum block text-[3.4rem] leading-[0.85] text-gold">{valor}</span>
      <span className="text-xs font-semibold text-muted uppercase">Nota</span>
    </p>
  )
}

function Tarjeta({ c, i }) {
  if (c.locked) {
    return (
      <li className="rise flex items-start justify-between gap-4 border-2 border-white/15 bg-black px-5 py-5" style={{ '--i': i }}>
        <div>
          <Partido g={c.game} />
          <p className="mt-2 flex items-center gap-2 font-semibold">
            <LockSimple aria-hidden weight="bold" className="size-4 text-gold" /> {STAT[c.stat]} · con la suscripción
          </p>
        </div>
        <Nota valor={c.score} />
      </li>
    )
  }
  const resultado = RESULTADO[c.status]
  return (
    <li className="rise border-2 border-white/25 bg-black px-5 py-5 sm:px-6" style={{ '--i': i }}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <Partido g={c.game} />
          <p className="display mt-1 text-[2.2rem] leading-none sm:text-[2.6rem]">{c.player}</p>
          <p className="mt-2 text-lg font-semibold">
            {STAT[c.stat]}: <span className="text-gold">{LADO[c.side]} de {fmtNum(c.line)}</span>
          </p>
          <p className="mt-1 text-sm text-muted">
            Probabilidad estimada <strong className="tnum text-white">{fmtPct(c.prob)}</strong>
          </p>
        </div>
        <Nota valor={c.score} />
      </div>
      {c.reasons?.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-white/15 pt-4 text-[0.95rem]">
          {c.reasons.map((r) => <li key={r} className="before:mr-2 before:text-gold before:content-['·']">{r}</li>)}
        </ul>
      )}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {resultado ? (
          <span className={`tnum px-2 py-1 text-xs font-bold uppercase ${resultado[1]}`}>
            {resultado[0]}{c.actual != null && ` · hizo ${fmtNum(c.actual)}`}
          </span>
        ) : <span />}
        <Link
          to={`/partidos/${encodeURIComponent(c.game.event_id)}/${c.line_id}`}
          className="inline-flex items-center gap-1 text-sm font-semibold underline decoration-grey underline-offset-4 hover:decoration-gold"
        >
          Ver el análisis de la línea <ArrowRight aria-hidden className="size-4" />
        </Link>
      </div>
    </li>
  )
}

function Historial({ h }) {
  if (!h?.settled) {
    return <p className="text-muted">Todavía no hay jugadas liquidadas. Cada una se queda guardada antes de su partido y se resuelve sola.</p>
  }
  return (
    <p className="max-w-2xl text-lg">
      <strong className="tnum">{h.won}</strong> acertadas de <strong className="tnum">{h.settled}</strong> ({fmtPct(h.hit_rate)}).
      La probabilidad media que dimos era del <strong className="tnum">{fmtPct(h.avg_prob)}</strong>: si las dos cifras se parecen, la estimación está bien calibrada.
    </p>
  )
}

export default function Jugadas() {
  const [params, setParams] = useSearchParams()
  const fecha = params.get('fecha')
  const { cargando, datos, error, reintentar } = useJugadas(fecha)
  const tarjetas = datos?.cards || []
  const suscriptor = datos?.viewer?.subscriber
  const bloqueadas = tarjetas.filter((c) => c.locked).length

  return (
    <Pagina>
      <h1 className="display text-[3.4rem] leading-none sm:text-[5rem]">Mejores jugadas</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">
        Las líneas de la jornada con la nota más alta. La nota (0-100) resume lo que dicen sus datos: forma, rival, casa o fuera,
        minutos y precio del mercado. La probabilidad es nuestra estimación a partir del mercado sin margen.
        No es una recomendación ni una garantía: la decisión es tuya.
      </p>
      {datos?.game_date && (
        <p className="mt-3 flex items-center gap-2 text-lg text-muted first-letter:uppercase">
          <CalendarBlank aria-hidden className="size-5" /> Jornada del {jornada(datos.game_date)} · horas en tu zona horaria
        </p>
      )}
      {datos?.dates?.length > 1 && (
        <nav aria-label="Jornadas" className="mt-6 flex flex-wrap gap-2">
          {datos.dates.slice(-7).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setParams({ fecha: d })}
              aria-current={d === datos.game_date || undefined}
              className={`tnum border px-3 py-1.5 text-sm font-semibold ${d === datos.game_date ? 'border-gold bg-gold text-black' : 'border-white/30 hover:border-gold'}`}
            >
              {new Date(`${d}T12:00:00`).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric' })}
            </button>
          ))}
        </nav>
      )}

      <div className="mt-10">
        {cargando ? (
          <Cargando />
        ) : error && error !== 'sin-servidor' && error !== 404 ? (
          <Fallo reintentar={reintentar} />
        ) : tarjetas.length === 0 ? (
          <div className="border border-dashed border-white/40 px-6 py-16 text-center">
            <p className="display text-[2.6rem] leading-none text-gold sm:text-[3.2rem]">Sin jugadas en esta jornada</p>
            <p className="mx-auto mt-4 max-w-md text-muted">
              Salen cuando se publican los partidos y solo las líneas con nota de 60 o más. Mientras, mira los{' '}
              <Link to="/partidos" className="underline">partidos</Link>.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {tarjetas.map((c, i) => <Tarjeta key={c.id} c={c} i={i} />)}
          </ul>
        )}
      </div>

      {!suscriptor && bloqueadas > 0 && <div className="mt-10"><Muro /></div>}

      <section className="mt-14 border-t border-white/25 pt-8">
        <h2 className="display text-[2.2rem] leading-none">Cómo le ha ido al feed</h2>
        <div className="mt-4"><Historial h={datos?.history} /></div>
        {datos?.disclaimer && <p className="mt-4 max-w-2xl text-sm text-muted">{datos.disclaimer}</p>}
      </section>
      <AvisoResponsable />
    </Pagina>
  )
}

