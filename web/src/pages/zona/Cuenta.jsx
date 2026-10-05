import { CheckCircle } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { AvisoResponsable, Cargando, Pagina } from '../../components/Zona'
import { PRECIO } from '../../lib/zona'
import { API_URL } from '../../config'
import { useCuenta } from '../../lib/cuenta'
import { api } from '../../lib/sesion'

const fecha = (iso) => (iso ? new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' }) : '')

function Planes({ elegido, setElegido, conPrueba }) {
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
      {plan('monthly', 'Mensual', `${PRECIO.mensual} €`, 'Al mes. Cancelas cuando quieras.')}
      {plan('yearly', 'Anual', `${PRECIO.anual} €`, 'Al año. Equivale a 10 € al mes.')}
    </fieldset>
  )
}

function Estado({ u }) {
  if (u.status === 'trialing') return <>Prueba gratis activa hasta el <strong>{fecha(u.current_period_end)}</strong>. Después se cobrará el plan elegido{u.cancel_at_period_end ? ', aunque la has cancelado y no se renovará' : ''}.</>
  if (u.cancel_at_period_end) return <>Suscripción cancelada. Mantienes el acceso hasta el <strong>{fecha(u.current_period_end)}</strong>.</>
  if (u.status === 'past_due') return <>No hemos podido cobrar la última cuota. Revisa tu tarjeta en «Gestionar suscripción».</>
  return <>Suscripción activa. Se renueva el <strong>{fecha(u.current_period_end)}</strong>.</>
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
        </section>
      ) : !esperando && (
        <section className="mt-8">
          <Planes elegido={elegido} setElegido={setElegido} conPrueba={usuario.trial_available} />
          <button type="button" disabled={ocupado} onClick={() => ir('/billing/checkout', { plan: elegido })} className="btn btn-gold mt-6 h-12 w-full px-6 text-lg disabled:opacity-60">
            {ocupado ? 'Abriendo Stripe…' : usuario.trial_available ? `Empezar los ${PRECIO.prueba} días gratis` : 'Suscribirme'}
          </button>
          <p className="mt-3 text-sm text-muted">
            Pago seguro con Stripe.{usuario.trial_available ? ` No se cobra nada hasta el día ${PRECIO.prueba + 1}; si cancelas antes, no pagas.` : ''} Puedes cancelar cuando quieras.
          </p>
          {usuario.has_billing && (
            <button type="button" onClick={() => ir('/billing/portal')} className="mt-4 text-sm underline hover:text-gold">Ver facturas anteriores</button>
          )}
        </section>
      )}

      {error && <p role="alert" className="mt-6 border border-gold px-4 py-3 text-sm">{error}</p>}

      <div className="mt-12 flex flex-wrap gap-x-6 gap-y-3 border-t border-line pt-6 text-sm">
        <button type="button" onClick={async () => { await salir(); navegar('/') }} className="underline hover:text-gold">Cerrar sesión</button>
        <button type="button" onClick={borrar} className="text-muted underline hover:text-white">Borrar mi cuenta</button>
      </div>
      <AvisoResponsable />
    </Pagina>
  )
}
