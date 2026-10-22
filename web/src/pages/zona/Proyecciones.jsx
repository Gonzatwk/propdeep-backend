import { ArrowRight, TrendDown, TrendUp } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AvisoResponsable, Cargando, Fallo, Muro, Pagina, Volver } from '../../components/Zona'
import { STAT, nombreCasa } from '../../lib/zona'
import { abrev, hora, jornada } from '../../lib/equipos'
import { useTop } from '../../lib/tablero'
import { fmtCuota, fmtNum } from '../../format'

const pc = (v) => (v == null ? '-' : `${Math.round(v * 100)} %`)
const signo = (v) => `${v > 0 ? '+' : ''}${fmtNum(v)}`

const STATS = [['todas', 'Todas'], ['pts', 'Puntos'], ['reb', 'Rebotes'], ['ast', 'Asistencias'], ['fg3m', 'Triples']]
const LADOS = [['todas', 'Por encima y por debajo'], ['over', 'Por encima'], ['under', 'Por debajo']]

function Filtros({ opciones, valor, cambiar, etiqueta }) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={etiqueta}>
      {opciones.map(([v, t]) => (
        <button
          key={v}
          type="button"
          onClick={() => cambiar(v)}
          aria-pressed={valor === v}
          className={`border px-3 py-1.5 text-sm font-semibold ${valor === v ? 'border-white bg-white text-black' : 'border-white/30 hover:border-white'}`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

function Fila({ l, i }) {
  const arriba = l.direction === 'over'
  const precio = l.best?.[l.direction]
  const Icono = arriba ? TrendUp : TrendDown
  return (
    <li className="rise" style={{ '--i': Math.min(i, 12) }}>
      <Link
        to={`/partidos/${encodeURIComponent(l.event_id)}/${l.id}`}
        className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-x-4 gap-y-2 border-2 border-white/25 bg-black px-4 py-4 transition-colors hover:border-gold sm:grid-cols-[2.5rem_1.6fr_1fr_1fr_auto] sm:px-5"
      >
        <span className="display tnum text-[2rem] leading-none text-muted">{i + 1}</span>
        <span>
          <span className="display block text-[1.7rem] leading-none sm:text-[2rem]">{l.player}</span>
          <span className="tnum mt-1 block text-sm text-muted">
            {abrev(l.game.away_team)} @ {abrev(l.game.home_team)} · {hora(l.game.commence_time)}
          </span>
        </span>
        <span className="tnum col-start-2 row-start-2 text-sm sm:col-start-auto sm:row-start-auto">
          <span className="text-muted">{STAT[l.stat]}</span> · línea <strong>{fmtNum(l.line)}</strong>
          <span className="block">
            Proyección <strong>{fmtNum(l.projection)}</strong>{' '}
            <span className={`inline-flex items-center gap-1 font-semibold ${arriba ? 'text-gold' : 'text-white'}`}>
              <Icono aria-hidden weight="bold" className="size-4" /> {signo(l.diff)}
              {l.diff_pct != null && <span className="text-muted">({signo(Math.round(l.diff_pct * 100))} %)</span>}
            </span>
          </span>
        </span>
        <span className="tnum col-start-2 row-start-3 text-xs text-muted sm:col-start-auto sm:row-start-auto sm:text-sm">
          Superó la línea: <span className="text-white">{pc(l.hit_rates?.last10)}</span> últ. 10 · <span className="text-white">{pc(l.hit_rates?.season)}</span> temp.
          {precio && (
            <span className="block">
              Mejor {arriba ? 'más' : 'menos'}: <span className="text-white">{fmtNum(precio.line)} a {fmtCuota(precio.odds)}</span> en {nombreCasa(precio.bookmaker)}
            </span>
          )}
        </span>
        <ArrowRight aria-hidden className="col-start-3 row-span-3 row-start-1 size-5 text-muted transition-transform group-hover:translate-x-1 group-hover:text-gold sm:col-start-auto sm:row-span-1 sm:row-start-auto" />
      </Link>
    </li>
  )
}

export default function Proyecciones() {
  const [params] = useSearchParams()
  const { cargando, datos, error, reintentar } = useTop(params.get('fecha'))
  const [stat, setStat] = useState('todas')
  const [lado, setLado] = useState('todas')
  const lineas = (datos?.lines || []).filter((l) => (stat === 'todas' || l.stat === stat) && (lado === 'todas' || l.direction === lado))

  return (
    <Pagina>
      <Volver to="/partidos">Partidos</Volver>
      <h1 className="display mt-6 text-[3.2rem] leading-none sm:text-[5rem]">Mejores proyecciones</h1>
      {datos?.game_date && (
        <p className="mt-3 text-lg text-muted first-letter:uppercase">Jornada del {jornada(datos.game_date)} · solo partidos por empezar</p>
      )}
      <p className="mt-4 max-w-3xl text-muted">
        Las líneas de toda la noche donde nuestra proyección más se aleja de la línea, medido frente a lo que suele variar cada jugador
        (así puntos y triples se comparan bien). Es un dato para empezar a mirar, no una recomendación: la proyección sola no ha
        demostrado ganar a las casas. Fuera los jugadores lesionados o con pocos partidos.
      </p>

      <div className="mt-8 space-y-3">
        <Filtros opciones={STATS} valor={stat} cambiar={setStat} etiqueta="Estadística" />
        <Filtros opciones={LADOS} valor={lado} cambiar={setLado} etiqueta="Proyección frente a la línea" />
      </div>

      <div className="mt-8">
        {cargando ? <Cargando /> : error ? <Fallo reintentar={reintentar} /> : lineas.length === 0 ? (
          <p className="border border-dashed border-white/40 px-6 py-12 text-center text-muted">
            No hay líneas por jugar con estos filtros. Si la jornada se está publicando, vuelve en unos minutos.
          </p>
        ) : (
          <ol className="space-y-3">
            {lineas.map((l, i) => <Fila key={l.id} l={l} i={i} />)}
          </ol>
        )}
      </div>

      {datos && !datos.viewer?.subscriber && <div className="mt-10"><Muro /></div>}
      <AvisoResponsable />
    </Pagina>
  )
}
