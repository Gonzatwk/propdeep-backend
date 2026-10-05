import { ArrowRight, CalendarBlank, ChatCircleText } from '@phosphor-icons/react'
import { Link, useSearchParams } from 'react-router-dom'
import { AvisoDemo, AvisoResponsable, Cargando, Fallo, Muro, Pagina } from '../../components/Zona'
import { abrev, corto, hora, jornada } from '../../lib/equipos'
import { useModo, useTablero } from '../../lib/tablero'

function Vacio({ titulo, texto }) {
  return (
    <div className="border border-dashed border-white/40 px-6 py-16 text-center">
      <p className="display text-[2.6rem] leading-none text-gold sm:text-[3.2rem]">{titulo}</p>
      <p className="mx-auto mt-4 max-w-md text-muted">{texto}</p>
      <Link to="/partidos?demo=1" className="btn btn-ghost mt-8 h-12 px-6 text-lg">
        Ver una demostración <ArrowRight aria-hidden className="size-4" />
      </Link>
    </div>
  )
}

function TarjetaPartido({ g, enlace, i }) {
  return (
    <li className="rise" style={{ '--i': i }}>
      <Link
        to={enlace(`/partidos/${encodeURIComponent(g.event_id)}`)}
        className="group grid grid-cols-[1fr_auto] items-center gap-4 border-2 border-white/25 bg-black px-5 py-5 transition-colors hover:border-gold sm:grid-cols-[7rem_1fr_auto_auto] sm:px-6"
      >
        <span className="display tnum text-[2rem] leading-none text-gold sm:text-[2.4rem]">{hora(g.commence_time)}</span>
        <span className="col-span-2 row-start-2 sm:col-span-1 sm:row-start-auto">
          <span className="display block text-[2.2rem] leading-none sm:text-[2.8rem]">
            {abrev(g.away_team)} <span className="text-muted">@</span> {abrev(g.home_team)}
          </span>
          <span className="mt-1 block text-sm text-muted">{corto(g.away_team)} en {corto(g.home_team)}</span>
        </span>
        <span className="row-start-1 flex flex-col items-end gap-1 text-right text-sm sm:row-start-auto">
          <span className="tnum font-semibold">{g.lines} {g.lines === 1 ? 'línea' : 'líneas'} · {g.players} {g.players === 1 ? 'jugador' : 'jugadores'}</span>
          {g.free_lines > 0 && <span className="tnum text-muted">{g.free_lines} {g.free_lines === 1 ? 'línea gratis' : 'líneas gratis'}</span>}
          {g.started && <span className="text-xs font-semibold text-gold uppercase">Empezado</span>}
        </span>
        <ArrowRight aria-hidden className="col-start-2 row-start-2 size-6 justify-self-end text-muted transition-transform group-hover:translate-x-1 group-hover:text-gold sm:col-start-auto sm:row-start-auto" />
      </Link>
    </li>
  )
}

export default function Partidos() {
  const [params, setParams] = useSearchParams()
  const fecha = params.get('fecha')
  const { demo, enlace } = useModo()
  const { cargando, datos, error, reintentar } = useTablero(fecha)
  const juegos = datos?.games || []
  const suscriptor = datos?.viewer?.subscriber

  return (
    <Pagina>
      <AvisoDemo />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="display text-[3.4rem] leading-none sm:text-[5rem]">Partidos</h1>
        <Link to={enlace('/chat')} className="btn btn-ghost h-11 px-4">
          <ChatCircleText aria-hidden className="size-5" /> Pregunta a PropDeep
        </Link>
      </div>
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
              onClick={() => setParams(demo ? { demo: params.get('demo'), fecha: d } : { fecha: d })}
              aria-current={d === datos.game_date || undefined}
              className={`tnum border px-3 py-1.5 text-sm font-semibold ${d === datos.game_date ? 'border-gold bg-gold text-black' : 'border-white/30 hover:border-gold'}`}
            >
              {new Date(`${d}T12:00:00`).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric' })}
            </button>
          ))}
        </nav>
      )}

      {!suscriptor && juegos.length > 0 && (
        <p className="mt-6 max-w-2xl text-muted">
          Gratis ves el análisis completo de <strong className="text-white">{datos.free_lines_per_day} líneas al día</strong>. Con la suscripción, todas.
        </p>
      )}

      <div className="mt-10">
        {cargando ? (
          <Cargando />
        ) : error === 'sin-servidor' || (!error && juegos.length === 0) ? (
          <Vacio
            titulo="Los partidos llegan el 20 de octubre"
            texto="Con el primer día de la temporada regular. Aquí verás cada partido, sus jugadores y los datos de cada línea, comparada entre casas."
          />
        ) : error ? (
          <Fallo reintentar={reintentar} />
        ) : (
          <ul className="space-y-3">
            {juegos.map((g, i) => <TarjetaPartido key={g.event_id} g={g} enlace={enlace} i={i} />)}
          </ul>
        )}
      </div>

      {!suscriptor && juegos.length > 0 && <div className="mt-10"><Muro /></div>}
      <AvisoResponsable />
    </Pagina>
  )
}
