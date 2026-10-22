import { CheckCircle } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { AvisoResponsable, Cargando, Pagina } from '../../components/Zona'
import { PRECIO, TEXTO_SUBIDA, subidaPendiente } from '../../lib/zona'
import { API_URL } from '../../config'
import { useCuenta } from '../../lib/cuenta'
import { api } from '../../lib/sesion'

const fecha = (iso) => (iso ? new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' }) : '')

const TODOS = ['monthly', 'pro', 'yearly', 'pass']

function Planes({ elegido, setElegido, conPrueba, disponibles = TODOS }) {
  const plan = (valor, titulo, precio, detalle) => (
    <label className={`flex cursor-pointer items-center justify-between gap-4 border-2 p-5 ${elegido === valor ? 'border-gold' : 'border-white/30 hover:border-white/60'}`}>
      <span className="flex items-center gap-3">
        <input type="radio" name="plan" value={valor} checked={elegido === valor} onChange={() => setElegido(valor)} className="size-4 accent-[var(--gold)]" />
        <span>
          <span className="block text-lg font-semibold">{titulo}</span>
          <span className="block text-sm text-muted">{detalle}</span>
        </span>
      </span>
      <span className="display tnum shrink-0 text-[2.4rem] leading-none">{precio}</span>
    </label>
  )
  return (
    <fieldset className="space-y-3">
      <legend className="mb-3 text-lg font-semibold">{conPrueba ? `Elige tu plan. Los primeros ${PRECIO.prueba} días son gratis.` : 'Elige tu plan'}</legend>
      {disponibles.includes('monthly') && plan('monthly', 'Mensual', `${PRECIO.mensual} €`, 'Al mes. Todo el análisis y 5 preguntas de chat al día. Cancelas cuando quieras.')}
      {disponibles.includes('pro') && plan('pro', 'Pro', `${PRECIO.pro} €`, 'Al mes. Todo el análisis y el chat completo, 30 preguntas al día.')}
      {disponibles.includes('yearly') && plan('yearly', 'Anual', `${PRECIO.anual} €`, `Al año. 4 meses gratis frente a pagar mes a mes (${PRECIO.mensual * 12} €).`)}
      {disponibles.includes('pass') && plan('pass', 'Pase de 7 días', `${PRECIO.pase} €`, 'Pago único. Sin renovación y sin prueba gratis.')}
      {subidaPendiente() && disponibles.includes('monthly') && <p className="pt-1 text-sm font-semibold">{TEXTO_SUBIDA}</p>}
    </fieldset>
  )
}

function Estado({ u }) {
  if (u.pass_until && !['active', 'trialing', 'past_due'].includes(u.status)) return <>Pase de 7 días activo hasta el <strong>{fecha(u.pass_until)}</strong>. No se renueva solo.</>
  if (u.status === 'trialing') return <>Prueba gratis activa hasta el <strong>{fecha(u.current_period_end)}</strong>. Después se cobrará el plan elegido{u.cancel_at_period_end ? ', aunque la has cancelado y no se renovará' : ''}.</>
  if (u.cancel_at_period_end) return <>Suscripción cancelada. Mantienes el acceso hasta el <strong>{fecha(u.current_period_end)}</strong>.</>
  if (u.status === 'past_due') return <>No hemos podido cobrar la última cuota. Revisa tu tarjeta en «Gestionar suscripción».</>
  return <>Suscripción activa. Se renueva el <strong>{fecha(u.current_period_end)}</strong>.</>
}

function BotonPago({ plan, prueba, ocupado, pagar }) {
  const pase = plan === 'pass'
  const texto = ocupado ? 'Abriendo Stripe…' : pase ? `Comprar el pase por ${PRECIO.pase} €` : prueba ? `Empezar los ${PRECIO.prueba} días gratis` : 'Suscribirme'
  return (
    <>
      <button type="button" disabled={ocupado} onClick={() => pagar(plan)} className="btn btn-gold mt-6 h-12 w-full px-6 text-lg disabled:opacity-60">
        {texto}
      </button>
      <p className="mt-3 text-sm text-muted">
        Pago seguro con Stripe.{' '}
        {pase ? 'Se cobra una vez y da 7 días de acceso completo. No se renueva.'
          : `${prueba ? `No se cobra nada hasta el día ${PRECIO.prueba + 1}; te avisamos por correo dos días antes y, si cancelas, no pagas. ` : ''}Puedes cancelar cuando quieras.`}
      </p>
    </>
  )
}

// Sin servidor (antes del 20 de octubre) o en la demostración: planes sin botón de pago.
function Proximamente() {
  const [elegido, setElegido] = useState('monthly')
  return (
    <Pagina ancho="max-w-2xl">
      <h1 className="display text-[3rem] leading-none sm:text-[4rem]">Suscripción</h1>
      <p className="mt-4 text-lg text-muted">
        El análisis de todas las líneas de cada partido: proyección, veces que superó la línea, casa y fuera, rival, líneas de cada casa e informe. Abre el 20 de octubre, con la temporada.
      </p>
      <div className="mt-8"><Planes elegido={elegido} setElegido={setElegido} conPrueba /></div>
      <Link to="/#avisame" className="btn btn-gold mt-6 h-12 px-6 text-lg">Avísame cuando abra</Link>
      <AvisoResponsable />
    </Pagina>
  )
}

export default function Cuenta() {
  const [params] = useSearchParams()
  const navegar = useNavigate()
  const { usuario, cargando, refrescar, salir } = useCuenta()
  const [elegido, setElegido] = useState('monthly')
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [esperando, setEsperando] = useState(params.get('pago') === 'ok')
  const [disponibles, setDisponibles] = useState(null)

  useEffect(() => {
    if (!API_URL) return
    api('/billing/plans').then((r) => setDisponibles(r.plans)).catch(() => setDisponibles([]))
  }, [])

  // Al volver de Stripe el acceso llega por webhook: lo esperamos unos segundos.
  useEffect(() => {
    if (!esperando || !API_URL) return
    let intentos = 0
    const id = setInterval(async () => {
      intentos += 1
      const u = await refrescar()
      if (u?.subscriber || intentos >= 10) {
        clearInterval(id)
        setEsperando(false)
      }
    }, 2000)
    return () => clearInterval(id)
  }, [esperando, refrescar])

  if (!API_URL) return <Proximamente />
  if (cargando) return <Pagina ancho="max-w-2xl"><Cargando filas={2} /></Pagina>
  if (!usuario) return <Navigate to="/entrar?siguiente=/cuenta" replace />

  const ir = async (ruta, body) => {
    setError('')
    setOcupado(true)
    try {
      const { url } = await api(ruta, { method: 'POST', body })
      window.location.assign(url)
    } catch (e) {
      setError(e.message)
      setOcupado(false)
    }
  }

  // Pausar o reanudar: el cambio llega por webhook, así que refrescamos unos segundos después.
  const cambiarPausa = async (ruta) => {
    setError('')
    setOcupado(true)
    try {
      const antes = usuario.status
      await api(ruta, { method: 'POST' })
      for (let i = 0; i < 8; i += 1) {
        await new Promise((r) => setTimeout(r, 1500))
        if ((await refrescar())?.status !== antes) break
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  const borrar = async () => {
    if (!window.confirm('¿Borrar tu cuenta? Se eliminará tu correo de PropDeep. No se puede deshacer.')) return
    try {
      await api('/me', { method: 'DELETE' })
      await salir()
      navegar('/', { replace: true })
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <Pagina ancho="max-w-2xl">
      <h1 className="display text-[3rem] leading-none sm:text-[4rem]">Mi cuenta</h1>
      <p className="mt-3 text-muted">{usuario.email}</p>

      {esperando && <p role="status" className="mt-8 border border-gold px-4 py-3">Confirmando el pago con Stripe…</p>}

      {usuario.subscriber ? (
        <section className="mt-8 border-2 border-gold p-6">
          <p className="flex items-start gap-3 text-lg">
            <CheckCircle aria-hidden weight="fill" className="mt-1 size-6 shrink-0 text-gold" />
            <span><Estado u={usuario} /></span>
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/partidos" className="btn btn-gold h-12 px-6 text-lg">Ver partidos</Link>
            {usuario.has_billing && (
              <button type="button" disabled={ocupado} onClick={() => ir('/billing/portal')} className="btn btn-ghost h-12 px-6 text-lg">
                Gestionar suscripción
              </button>
            )}
          </div>
          <p className="mt-4 text-sm text-muted">Desde «Gestionar suscripción» cambias de plan o de tarjeta, descargas facturas o cancelas.</p>
          {usuario.status === 'active' && !usuario.cancel_at_period_end && (
            <div className="mt-6 border-t border-line pt-5">
              <p className="font-semibold">¿Pensando en dejarlo?</p>
              <p className="mt-1 text-sm text-muted">Puedes pausar un mes: no se te cobra, no ves los análisis y vuelves con el mismo precio. Se reanuda sola.</p>
              <button type="button" disabled={ocupado} onClick={() => cambiarPausa('/billing/pause')} className="mt-3 text-sm font-semibold underline hover:text-gold disabled:opacity-60">
                Pausar un mes
              </button>
            </div>
          )}
        </section>
      ) : usuario.status === 'paused' ? (
        <section className="mt-8 border-2 border-white/40 p-6">
          <p className="text-lg">
            Suscripción en pausa{usuario.paused_until ? <> hasta el <strong>{fecha(usuario.paused_until)}</strong></> : ''}. No se cobra nada y conservas tu precio.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" disabled={ocupado} onClick={() => cambiarPausa('/billing/resume')} className="btn btn-gold h-12 px-6 text-lg disabled:opacity-60">Reanudar ahora</button>
            <button type="button" disabled={ocupado} onClick={() => ir('/billing/portal')} className="btn btn-ghost h-12 px-6 text-lg">Gestionar suscripción</button>
          </div>
        </section>
      ) : !esperando && (
        <section className="mt-8">
          {disponibles === null ? <Cargando filas={2} /> : disponibles.length === 0 ? (
            <p className="border border-gold px-4 py-3">La suscripción todavía no está activada. Vuelve en unos días.</p>
          ) : (
            <>
              <Planes elegido={disponibles.includes(elegido) ? elegido : disponibles[0]} setElegido={setElegido} conPrueba={usuario.trial_available} disponibles={disponibles} />
              <BotonPago
                plan={disponibles.includes(elegido) ? elegido : disponibles[0]}
                prueba={usuario.trial_available}
                ocupado={ocupado}
                pagar={(plan) => ir('/billing/checkout', { plan })}
              />
            </>
          )}
          {usuario.has_billing && (
            <button type="button" onClick={() => ir('/billing/portal')} className="mt-4 text-sm underline hover:text-gold">Ver facturas anteriores</button>
          )}
        </section>
      )}

      {error && <p role="alert" className="mt-6 border border-gold px-4 py-3 text-sm">{error}</p>}

      {usuario.admin && (
        <div className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <span className="font-semibold">Herramientas del autor:</span>
          <Link to="/dato-del-dia" className="underline hover:text-gold">Dato del día para redes</Link>
          <Link to="/tipsters" className="underline hover:text-gold">Auditoría de tipsters</Link>
        </div>
      )}

      <div className="mt-12 flex flex-wrap gap-x-6 gap-y-3 border-t border-line pt-6 text-sm">
        <button type="button" onClick={async () => { await salir(); navegar('/') }} className="underline hover:text-gold">Cerrar sesión</button>
        <button type="button" onClick={borrar} className="text-muted underline hover:text-white">Borrar mi cuenta</button>
      </div>
      <AvisoResponsable />
    </Pagina>
  )
}
