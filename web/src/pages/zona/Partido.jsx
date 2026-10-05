import { ArrowRight, LockSimple } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AvisoDemo, AvisoResponsable, Bloqueada, Cargando, Fallo, Muro, Pagina, Volver,
} from '../../components/Zona'
import { STAT, useIrASuscribir } from '../../lib/zona'
import { abrev, corto, diaLargo, hora } from '../../lib/equipos'
import { useModo, usePartido } from '../../lib/tablero'
import { fmtCuota, fmtNum } from '../../format'

const pc = (v) => (v == null ? '-' : `${Math.round(v * 100)} %`)

const FILTROS = [['todas', 'Todas'], ['pts', 'Puntos'], ['reb', 'Rebotes'], ['ast', 'Asistencias'], ['fg3m', 'Triples']]

function Linea({ l, enlace, eventId }) {
  const destinoMuro = useIrASuscribir()
  const cuerpo = (
    <>
      <span className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-semibold text-muted">{STAT[l.stat]}</span>
        {l.free && <span className="bg-white px-1.5 text-[0.7rem] font-bold text-black uppercase">Gratis</span>}
      </span>
      <span className="display tnum mt-1 block text-[2.4rem] leading-none">{fmtNum(l.line)}</span>
      <span className="tnum mt-1 block text-xs text-muted">
        Más {fmtCuota(l.over_odds)} · Menos {fmtCuota(l.under_odds)} · {l.books_count} {l.books_count === 1 ? 'casa' : 'casas'}
      </span>
      <span className="mt-3 block min-h-7">
        {l.locked ? <Bloqueada /> : (
          <span className="tnum block text-sm">
            <span className="text-muted">Proyección</span> <strong className="font-semibold">{fmtNum(l.projection)}</strong>
            <span className="mt-1 block text-xs text-muted">
              Superó la línea: <span className="text-white">{pc(l.hit_rates?.last5)}</span> últ. 5 · <span className="text-white">{pc(l.hit_rates?.last10)}</span> últ. 10
            </span>
          </span>
        )}
      </span>
    </>
  )
  const clase = 'group block h-full border bg-black p-4 transition-colors'
  if (l.locked) {
    return (
      <Link to={destinoMuro} className={`${clase} border-white/15 hover:border-white/40`} aria-label={`${l.player}, ${STAT[l.stat]} ${l.line}: bloqueada, ver suscripción`}>
        {cuerpo}
      </Link>
    )
  }
  return (
    <Link to={enlace(`/partidos/${encodeURIComponent(eventId)}/${l.id}`)} className={`${clase} border-white/25 hover:border-gold`}>
      {cuerpo}
      <span className="mt-3 flex items-center gap-1 text-sm font-semibold text-gold opacity-80 group-hover:opacity-100">
        Ver análisis <ArrowRight aria-hidden className="size-3.5 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  )
}

export default function Partido() {
  const { eventId } = useParams()
  const { enlace } = useModo()
  const { cargando, datos, error, reintentar } = usePartido(eventId)
  const [filtro, setFiltro] = useState('todas')

  if (cargando) return <Pagina><Cargando filas={4} /></Pagina>
  if (error || !datos) {
    return (
      <Pagina>
        <Volver to={enlace('/partidos')}>Partidos</Volver>
        <div className="mt-8">
          {error === 404 ? <p className="display text-[2.4rem] text-gold">Este partido no está en la jornada</p> : <Fallo reintentar={reintentar} />}
        </div>
      </Pagina>
    )
  }

  const { game: g, lines, viewer } = datos
  const bloqueadas = lines.filter((l) => l.locked).length
  const visibles = lines.filter((l) => filtro === 'todas' || l.stat === filtro)
  const jugadores = [...new Set(visibles.map((l) => l.player))]

  return (
    <Pagina>
      <AvisoDemo />
      <Volver to={enlace('/partidos')}>Partidos</Volver>
      <header className="mt-6 border-b-2 border-white pb-6">
        <h1 className="display text-[3.2rem] leading-none sm:text-[5rem]">
          {abrev(g.away_team)} <span className="hueco hueco-blanco">@</span> {abrev(g.home_team)}
        </h1>
        <p className="mt-2 text-lg text-muted">
          {corto(g.away_team)} en {corto(g.home_team)} · <span className="first-letter:uppercase">{diaLargo(g.commence_time)}</span>, {hora(g.commence_time)}
        </p>
      </header>

      {!viewer.subscriber && bloqueadas > 0 && (
        <p className="mt-6 flex items-start gap-2 text-muted">
          <LockSimple aria-hidden weight="bold" className="mt-1 size-4 shrink-0 text-gold" />
          <span>Ves el análisis de {lines.length - bloqueadas} de {lines.length} líneas. Las demás se abren con la suscripción o cuando empieza el partido.</span>
        </p>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-2" role="group" aria-label="Filtrar líneas">
        {FILTROS.map(([v, t]) => (
          <button
            key={v}
            type="button"
            onClick={() => setFiltro(v)}
            aria-pressed={filtro === v}
            className={`border px-3 py-1.5 text-sm font-semibold ${filtro === v ? 'border-white bg-white text-black' : 'border-white/30 hover:border-white'}`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-8 space-y-10">
        {jugadores.length === 0 && <p className="text-muted">Ninguna línea con estos filtros.</p>}
        {jugadores.map((j) => (
          <section key={j} aria-label={j}>
            <h2 className="display text-[1.9rem] leading-none sm:text-[2.2rem]">{j}</h2>
            <ul className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              {visibles.filter((l) => l.player === j).map((l) => (
                <li key={l.id}><Linea l={l} enlace={enlace} eventId={g.event_id} /></li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {!viewer.subscriber && bloqueadas > 0 && <div className="mt-12"><Muro bloqueadas={bloqueadas} /></div>}
      <AvisoResponsable />
    </Pagina>
  )
}
