import { ArrowSquareOut, Fingerprint, Plus, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { AvisoResponsable, Cargando, Fallo, Pagina } from '../components/Zona'
import { API_URL } from '../config'
import { api } from '../lib/sesion'
import { fmtCuota, fmtNum, fmtPct, fmtUnidades } from '../format'

const ESTADO = {
  won: ['Ganado', 'bg-gold text-black'],
  lost: ['Perdido', 'bg-white text-black'],
  push: ['Nulo', 'border border-white/40 text-muted'],
  void: ['Anulado', 'border border-white/40 text-muted'],
  pending: ['Pendiente', 'border border-dashed border-white/40 text-muted'],
}
const campo = 'mt-1 block h-11 w-full border border-white/30 bg-black px-3 text-white focus:border-gold focus:outline-none'
const fecha = (iso) => new Date(iso).toLocaleString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const num = (v) => Number(String(v).replace(',', '.'))

function useEnvio(onHecho) {
  const [estado, setEstado] = useState({ enviando: false, error: '' })
  const enviar = async (ruta, body, limpiar) => {
    setEstado({ enviando: true, error: '' })
    try {
      await api(ruta, { method: 'POST', body })
      setEstado({ enviando: false, error: '' })
      limpiar?.()
      onHecho()
    } catch (e) {
      setEstado({ enviando: false, error: e.message })
    }
  }
  return [estado, enviar]
}

function NuevoTipster({ onHecho }) {
  const [f, setF] = useState({ name: '', url: '' })
  const [estado, enviar] = useEnvio(onHecho)
  return (
    <form
      className="grid gap-3 border border-white/30 p-5 sm:grid-cols-[1fr_1.4fr_auto] sm:items-end"
      onSubmit={(e) => { e.preventDefault(); enviar('/tipsters', f, () => setF({ name: '', url: '' })) }}
    >
      <label className="text-sm">Nombre<input required className={campo} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
      <label className="text-sm">Dónde publica (enlace)<input required type="url" placeholder="https://t.me/..." className={campo} value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} /></label>
      <button type="submit" disabled={estado.enviando} className="btn btn-ghost h-11 px-4"><Plus aria-hidden className="size-4" /> Añadir tipster</button>
      {estado.error && <p role="alert" className="text-sm text-gold sm:col-span-3">{estado.error}</p>}
    </form>
  )
}

const VACIO = { posted_at: '', event_start: '', event: '', selection: '', odds: '', stake: '1', evidence_url: '' }

function NuevoPick({ tipster, onHecho }) {
  const [f, setF] = useState(VACIO)
  const [estado, enviar] = useEnvio(onHecho)
  const cambia = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const iso = (v) => new Date(v).toISOString()
  return (
    <form
      className="mt-4 grid gap-3 border border-white/20 p-4 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault()
        enviar(`/tipsters/${tipster}/picks`, {
          ...f, posted_at: iso(f.posted_at), event_start: iso(f.event_start), odds: num(f.odds), stake: num(f.stake),
        }, () => setF(VACIO))
      }}
    >
      <label className="text-sm">Cuándo lo publicó<input required type="datetime-local" className={campo} value={f.posted_at} onChange={cambia('posted_at')} /></label>
      <label className="text-sm">Empieza el partido<input required type="datetime-local" className={campo} value={f.event_start} onChange={cambia('event_start')} /></label>
      <label className="text-sm">Partido<input required placeholder="Lakers - Celtics" className={campo} value={f.event} onChange={cambia('event')} /></label>
      <label className="text-sm">Pick, tal cual lo dio<input required placeholder="LeBron más de 24,5 puntos" className={campo} value={f.selection} onChange={cambia('selection')} /></label>
      <label className="text-sm">Cuota<input required inputMode="decimal" className={campo} value={f.odds} onChange={cambia('odds')} /></label>
      <label className="text-sm">Unidades (1 si no lo dice)<input required inputMode="decimal" className={campo} value={f.stake} onChange={cambia('stake')} /></label>
      <label className="text-sm sm:col-span-2">
        Prueba: enlace al mensaje o a la captura con su fecha
        <input required type="url" className={campo} value={f.evidence_url} onChange={cambia('evidence_url')} />
      </label>
      <button type="submit" disabled={estado.enviando} className="btn btn-gold h-11 px-4 sm:col-span-2">Registrar pick</button>
      {estado.error && <p role="alert" className="text-sm text-gold sm:col-span-2">{estado.error}</p>}
    </form>
  )
}

function Resultado({ id, onHecho }) {
  const [estado, enviar] = useEnvio(onHecho)
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
      {[['won', 'Ganado'], ['lost', 'Perdido'], ['push', 'Nulo'], ['void', 'Anulado']].map(([r, t]) => (
        <button key={r} type="button" disabled={estado.enviando} className="btn btn-ghost h-8 px-3" onClick={() => enviar(`/tipster-picks/${id}/settle`, { result: r })}>{t}</button>
      ))}
      {estado.error && <span role="alert" className="text-gold">{estado.error}</span>}
    </div>
  )
}

function Tipster({ t, admin, onCambio }) {
  const r = t.summary
  const [nuevo, setNuevo] = useState(false)
  const [ahora] = useState(() => Date.now())
  const cifras = [
    ['Picks', r.picks],
    ['Ganados / perdidos', `${r.won} / ${r.lost}`],
    ['Unidades', fmtUnidades(r.profit_units)],
    ['Rendimiento', r.roi == null ? '-' : `${r.roi > 0 ? '+' : ''}${fmtPct(r.roi)}`],
  ]
  return (
    <section className="border-t-2 border-white pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="display text-[2.4rem] leading-none">{t.name}</h2>
        <a href={t.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-muted underline hover:text-white">
          Dónde publica <ArrowSquareOut aria-hidden className="size-3.5" />
        </a>
      </div>
      <dl className="tnum mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {cifras.map(([l, v]) => (
          <div key={l}><dt className="text-xs text-muted">{l}</dt><dd className="display mt-1 text-[2rem] leading-none text-gold">{v}</dd></div>
        ))}
      </dl>
      {admin && (nuevo ? <NuevoPick tipster={t.id} onHecho={onCambio} /> : (
        <button type="button" className="btn btn-ghost mt-4 h-10 px-3" onClick={() => setNuevo(true)}><Plus aria-hidden className="size-4" /> Registrar un pick</button>
      ))}
      <ul className="mt-4">
        {t.picks.map((p) => {
          const [texto, clase] = ESTADO[p.status] || ESTADO.pending
          return (
            <li key={p.id} className="border-b border-line py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs text-muted">{p.event} · {fecha(p.event_start)}</p>
                  <p className="mt-1 font-semibold">{p.selection}</p>
                  <p className="tnum text-sm text-muted">Cuota {fmtCuota(p.odds)}{p.stake !== 1 && <> · {fmtNum(p.stake)} u</>}</p>
                </div>
                <span className={`px-2 py-0.5 text-sm font-bold uppercase ${clase}`}>{texto}</span>
              </div>
              <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                <span>Lo publicó {fecha(p.posted_at)}</span>
                <a href={p.evidence_url} target="_blank" rel="noopener noreferrer" className="underline hover:text-white">Ver la prueba</a>
                <span className="inline-flex items-center gap-1" title={p.content_hash}><Fingerprint aria-hidden className="size-3.5" /> {p.content_hash.slice(0, 12)}…</span>
              </p>
              {admin && p.status === 'pending' && new Date(p.event_start).getTime() <= ahora && <Resultado id={p.id} onHecho={onCambio} />}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// Auditoría de tipsters: privada (solo el autor) hasta que el servidor la haga pública.
export default function Tipsters() {
  const [version, setVersion] = useState(0)
  const [estado, setEstado] = useState({ cargando: true, datos: null, error: null })
  const recargar = () => setVersion((v) => v + 1)

  useEffect(() => {
    if (!API_URL) {
      setEstado({ cargando: false, datos: null, error: 404 })
      return
    }
    api('/tipsters')
      .then((datos) => setEstado({ cargando: false, datos, error: null }))
      .catch((e) => setEstado({ cargando: false, datos: null, error: e.status || 'red' }))
  }, [version])

  const { cargando, datos, error } = estado
  if (cargando) return <Pagina ancho="max-w-4xl"><Cargando filas={3} /></Pagina>
  if (error === 404) {
    return (
      <Pagina ancho="max-w-4xl">
        <p className="display text-[2.6rem] leading-none text-gold">Muy pronto</p>
        <p className="mt-4 max-w-xl text-lg text-muted">Estamos registrando los picks públicos de los tipsters más seguidos para enseñar sus números reales.</p>
      </Pagina>
    )
  }
  if (error) return <Pagina ancho="max-w-4xl"><Fallo reintentar={recargar} /></Pagina>

  return (
    <Pagina ancho="max-w-4xl">
      <h1 className="display text-[3rem] leading-[0.95] sm:text-[4.6rem]">
        Tipsters, <span className="hueco hueco-blanco">con sus números</span>
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">{datos.note}</p>
      {datos.admin && !datos.public && (
        <p role="note" className="mt-6 flex items-start gap-3 border-2 border-gold px-4 py-3">
          <WarningCircle aria-hidden weight="bold" className="mt-0.5 size-5 shrink-0 text-gold" />
          Solo lo ves tú. Se hace pública con TIPSTERS_PUBLIC=true en el servidor. Antes, revisa que cada pick tenga su prueba con fecha.
        </p>
      )}
      {datos.admin && <div className="mt-8"><NuevoTipster onHecho={recargar} /></div>}
      <div className="mt-10 space-y-12">
        {datos.tipsters.length === 0 && <p className="text-muted">Todavía no hay tipsters registrados.</p>}
        {datos.tipsters.map((t) => <Tipster key={t.id} t={t} admin={datos.admin} onCambio={recargar} />)}
      </div>
      <AvisoResponsable />
    </Pagina>
  )
}
