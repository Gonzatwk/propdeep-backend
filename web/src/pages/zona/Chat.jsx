import { ArrowRight, PaperPlaneRight } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AvisoDemo, AvisoResponsable, Cargando, Fallo, Muro, Pagina } from '../../components/Zona'
import { API_URL } from '../../config'
import { demoChat } from '../../data/demo'
import { useCuenta } from '../../lib/cuenta'
import { ErrorApi, api } from '../../lib/sesion'
import { useModo } from '../../lib/tablero'
import { nombreCasa } from '../../lib/zona'

const MAX_TEXTO = 2000 // el servidor no lee más por mensaje
const MAX_HISTORIAL = 12 // mensajes previos que se reenvían

const SUGERENCIAS = [
  '¿Qué partidos hay hoy?',
  '¿Quién ha superado más veces su línea de puntos en los últimos 10 partidos?',
  '¿Qué casa tiene la línea de rebotes más baja en el primer partido?',
  '¿Qué jugadores juegan back-to-back hoy?',
]

const RESPUESTA_DEMO = 'En la demostración el chat no responde preguntas nuevas. Desde el 20 de octubre, con la suscripción, te contesto con los datos reales de cada jornada.'

function avisoDeError(e) {
  if (e?.name === 'TimeoutError') return 'La respuesta está tardando demasiado. Vuelve a intentarlo.'
  if (!(e instanceof ErrorApi)) return 'No hemos podido conectar. Comprueba tu conexión y vuelve a intentarlo.'
  if (e.status === 429) return 'Has llegado al límite de mensajes de hoy. Mañana tienes más.'
  if (e.status === 401) return 'Tu sesión ha caducado. Vuelve a entrar para seguir.'
  if (e.status === 503) return 'El chat no está disponible ahora mismo. Vuelve a intentarlo más tarde.'
  return 'No hemos podido responder. Vuelve a intentarlo.'
}

function Burbuja({ m }) {
  if (m.role === 'user') {
    return (
      <li className="ml-auto max-w-[85%] border border-white/30 bg-black-2 px-4 py-3">
        <p className="sr-only">Tú:</p>
        <p className="whitespace-pre-line break-words">{m.content}</p>
      </li>
    )
  }
  return (
    <li className="max-w-[92%] border-l-2 border-gold pl-4">
      <p className="text-xs font-bold tracking-wide text-gold uppercase">PropDeep</p>
      <p className="mt-1 whitespace-pre-line break-words leading-relaxed">{m.content}</p>
    </li>
  )
}

function Conversacion({ inicial, demo, quedanInicial, limite }) {
  const [mensajes, setMensajes] = useState(inicial)
  const [texto, setTexto] = useState('')
  const [pensando, setPensando] = useState(false)
  const [error, setError] = useState('')
  const [quedan, setQuedan] = useState(quedanInicial)
  const final = useRef(null)
  const vistos = useRef(inicial.length)

  // Baja hasta el último mensaje cuando llega uno nuevo (no al abrir la página).
  useEffect(() => {
    if (mensajes.length === vistos.current && !pensando) return
    vistos.current = mensajes.length
    final.current?.scrollIntoView({ block: 'end' })
  }, [mensajes.length, pensando])

  const enviar = async (pregunta) => {
    const q = pregunta.trim().slice(0, MAX_TEXTO)
    if (!q || pensando || quedan === 0) return
    const antes = mensajes
    const nuevos = [...antes, { role: 'user', content: q }]
    setMensajes(nuevos)
    setTexto('')
    setError('')
    if (demo) {
      setMensajes([...nuevos, { role: 'assistant', content: RESPUESTA_DEMO }])
      return
    }
    setPensando(true)
    try {
      const historial = nuevos.slice(-MAX_HISTORIAL).map((m) => ({ role: m.role, content: m.content.slice(0, MAX_TEXTO) }))
      const r = await api('/chat', { method: 'POST', body: { messages: historial }, timeout: 90000 })
      setMensajes([...nuevos, { role: 'assistant', content: r.reply }])
      setQuedan(r.remaining)
    } catch (e) {
      // La pregunta vuelve al cuadro para poder reenviarla.
      setMensajes(antes)
      setTexto(q)
      setError(avisoDeError(e))
      if (e?.status === 429) setQuedan(0)
    } finally {
      setPensando(false)
    }
  }

  const alPulsar = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      enviar(texto)
    }
  }

  return (
    <>
      {mensajes.length > 0 && (
        <ol aria-label="Conversación" className="mt-10 space-y-6">
          {mensajes.map((m, i) => <Burbuja key={i} m={m} />)}
        </ol>
      )}
      <p aria-live="polite" className={mensajes.length ? 'mt-6 min-h-6 text-muted' : 'sr-only'}>
        {pensando && <span className="animate-pulse">Consultando los datos…</span>}
      </p>
      <div ref={final} />

      {mensajes.length === 0 && (
        <div className="mt-10">
          <p className="text-sm font-semibold text-muted">Prueba con:</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {SUGERENCIAS.map((s) => (
              <li key={s}>
                <button type="button" onClick={() => enviar(s)} disabled={pensando} className="border border-white/30 px-3 py-2 text-left text-sm hover:border-gold disabled:opacity-50">
                  {s}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p role="alert" className="mt-6 border border-gold px-4 py-3">{error}</p>}

      <form
        className="mt-6 border-2 border-white/30 bg-black focus-within:border-gold"
        onSubmit={(e) => {
          e.preventDefault()
          enviar(texto)
        }}
      >
        <label htmlFor="pregunta" className="sr-only">Tu pregunta</label>
        <textarea
          id="pregunta"
          rows={2}
          maxLength={MAX_TEXTO}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={alPulsar}
          placeholder="Pregunta por un partido, un jugador o una línea"
          className="block w-full resize-none bg-transparent px-4 py-3 text-white placeholder:text-grey"
          style={{ outline: 'none' }} // el borde del formulario ya marca el foco
        />
        <div className="flex items-center justify-between gap-3 border-t border-line px-4 py-2">
          <p className="text-xs text-muted">
            {demo ? 'Demostración: respuestas de ejemplo' : quedan === 0 ? 'Sin mensajes hasta mañana' : <span className="tnum">Te quedan {quedan} de {limite} mensajes hoy</span>}
          </p>
          <button type="submit" disabled={pensando || !texto.trim() || quedan === 0} className="btn btn-gold h-10 px-4 disabled:opacity-50">
            Enviar <PaperPlaneRight aria-hidden className="size-4" />
          </button>
        </div>
      </form>
      <p className="mt-3 text-xs text-muted">Enter para enviar, Mayús + Enter para otra línea. No guardamos tus conversaciones.</p>
    </>
  )
}

// Estado del chat para la cuenta: cargando, sin acceso o listo.
function useEstadoChat(activo) {
  const correo = useCuenta().usuario?.email
  const [estado, setEstado] = useState({ cargando: true, datos: null, error: null })
  const [intento, setIntento] = useState(0)
  useEffect(() => {
    if (!activo || !correo) return
    let vivo = true
    api('/chat')
      .then((datos) => vivo && setEstado({ cargando: false, datos, error: null }))
      .catch((e) => vivo && setEstado({ cargando: false, datos: null, error: e.status || 'red' }))
    return () => { vivo = false }
  }, [activo, correo, intento])
  const reintentar = () => {
    setEstado({ cargando: true, datos: null, error: null })
    setIntento((n) => n + 1)
  }
  return { ...estado, reintentar }
}

function Contenido() {
  const { demo } = useModo()
  const { usuario, cargando: cargandoCuenta } = useCuenta()
  const [ejemplo] = useState(() => demoChat(nombreCasa))
  const real = !demo && Boolean(API_URL)
  const chat = useEstadoChat(real)

  if (demo) return <Conversacion inicial={ejemplo} demo />
  if (!API_URL) {
    return (
      <div className="mt-10 border border-dashed border-white/40 px-6 py-12 text-center">
        <p className="display text-[2.4rem] leading-none text-gold sm:text-[3rem]">El chat abre el 20 de octubre</p>
        <p className="mx-auto mt-4 max-w-md text-muted">Con la primera jornada de la temporada regular y la suscripción.</p>
        <Link to="/chat?demo=1" className="btn btn-ghost mt-8 h-12 px-6 text-lg">
          Ver una demostración <ArrowRight aria-hidden className="size-4" />
        </Link>
      </div>
    )
  }
  if (cargandoCuenta) return <div className="mt-10"><Cargando filas={2} /></div>
  if (!usuario) {
    return (
      <div className="mt-10 border-2 border-gold p-6 sm:p-8">
        <p className="display text-[2rem] leading-none text-gold sm:text-[2.4rem]">Entra para preguntar</p>
        <p className="mt-3 max-w-xl text-muted">El chat es para suscriptores. Entra con tu correo; si aún no tienes suscripción, puedes probarla gratis.</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link to="/entrar?siguiente=/chat" className="btn btn-gold h-12 px-6 text-lg">Entrar</Link>
          <Link to="/chat?demo=1" className="btn btn-ghost h-12 px-6 text-lg">Ver una demostración</Link>
        </div>
      </div>
    )
  }
  if (chat.cargando) return <div className="mt-10"><Cargando filas={2} /></div>
  if (chat.error === 402) return <div className="mt-10"><Muro /></div>
  if (chat.error) return <div className="mt-10"><Fallo reintentar={chat.reintentar} /></div>
  if (!chat.datos.enabled) {
    return <p className="mt-10 border border-gold px-5 py-4">El chat no está disponible ahora mismo. Vuelve a intentarlo más tarde.</p>
  }
  return <Conversacion inicial={[]} quedanInicial={chat.datos.remaining} limite={chat.datos.limit} />
}

export default function Chat() {
  return (
    <Pagina ancho="max-w-3xl">
      <AvisoDemo sinVista />
      <h1 className="display text-[3.4rem] leading-none sm:text-[5rem]">Pregunta a PropDeep</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">
        Pregunta en español por los partidos y las líneas del día. Responde con los datos de PropDeep (proyección, veces
        que superó la línea, rival, casas) y no te dirá qué apostar: la decisión es tuya.
      </p>
      <Contenido />
      <AvisoResponsable />
    </Pagina>
  )
}
