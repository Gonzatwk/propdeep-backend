import { EnvelopeSimple } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Pagina } from '../../components/Zona'
import { API_URL } from '../../config'
import { useCuenta } from '../../lib/cuenta'
import { api } from '../../lib/sesion'

const CLAVE = 'propdeep.siguiente'
const seguro = (r) => (r && r.startsWith('/') && !r.startsWith('//') ? r : '/partidos')
const recordar = (r) => { try { localStorage.setItem(CLAVE, seguro(r)) } catch { /* sin almacenamiento */ } }
const recuperar = () => {
  try {
    const r = localStorage.getItem(CLAVE)
    localStorage.removeItem(CLAVE)
    return seguro(r)
  } catch { return '/partidos' }
}

// Acceso sin contraseña: pides un enlace y te llega al correo.
export default function Entrar() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const navegar = useNavigate()
  const { entrar, usuario } = useCuenta()
  const [correo, setCorreo] = useState('')
  const [mayor, setMayor] = useState(false)
  const [estado, setEstado] = useState(token ? 'verificando' : 'formulario')
  const [error, setError] = useState('')
  const hecho = useRef(false)

  useEffect(() => {
    if (!token || hecho.current) return
    hecho.current = true
    api('/auth/verify', { method: 'POST', body: { token }, token: '' })
      .then(({ token: sesion, user }) => {
        entrar(sesion, user)
        navegar(recuperar(), { replace: true })
      })
      .catch((e) => {
        setError(e.message)
        setEstado('formulario')
      })
  }, [token, entrar, navegar])

  const enviar = async (e) => {
    e.preventDefault()
    setError('')
    setEstado('enviando')
    recordar(params.get('siguiente'))
    try {
      await api('/auth/login', { method: 'POST', body: { email: correo }, token: '' })
      setEstado('enviado')
    } catch (err) {
      setError(err.message)
      setEstado('formulario')
    }
  }

  if (!API_URL) {
    return (
      <Pagina ancho="max-w-xl">
        <h1 className="display text-[3rem] leading-none">Entrar</h1>
        <p className="mt-4 text-lg text-muted">Las cuentas se abren el 20 de octubre, con el inicio de la temporada.</p>
        <Link to="/#avisame" className="btn btn-gold mt-8 h-12 px-6 text-lg">Avísame cuando abra</Link>
      </Pagina>
    )
  }

  if (usuario && !token) {
    return (
      <Pagina ancho="max-w-xl">
        <h1 className="display text-[3rem] leading-none">Ya estás dentro</h1>
        <p className="mt-4 text-lg text-muted">Has entrado como {usuario.email}.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/partidos" className="btn btn-gold h-12 px-6 text-lg">Ver partidos</Link>
          <Link to="/cuenta" className="btn btn-ghost h-12 px-6 text-lg">Mi cuenta</Link>
        </div>
      </Pagina>
    )
  }

  return (
    <Pagina ancho="max-w-xl">
      <h1 className="display text-[3rem] leading-none sm:text-[4rem]">{estado === 'verificando' ? 'Entrando…' : 'Entrar'}</h1>

      {estado === 'enviado' ? (
        <div className="mt-8 border-2 border-gold p-6" role="status">
          <EnvelopeSimple aria-hidden className="size-8 text-gold" />
          <p className="mt-3 text-xl font-semibold">Revisa tu correo</p>
          <p className="mt-2 text-muted">
            Te hemos enviado un enlace a <strong className="text-white">{correo}</strong>. Caduca en 20 minutos. Si no lo ves, mira en spam.
          </p>
          <button type="button" onClick={() => setEstado('formulario')} className="mt-4 text-sm text-gold underline">Usar otro correo</button>
        </div>
      ) : estado !== 'verificando' && (
        <form onSubmit={enviar} className="mt-8 space-y-5">
          <p className="text-lg text-muted">Sin contraseña: te mandamos un enlace para entrar. Solo pedimos tu correo.</p>
          <label className="block">
            <span className="text-sm font-semibold">Correo</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              className="mt-1 h-12 w-full border-2 border-white/40 bg-black px-4 text-lg focus:border-gold focus:outline-none"
            />
          </label>
          <label className="flex items-start gap-3 text-sm leading-relaxed">
            <input type="checkbox" required checked={mayor} onChange={(e) => setMayor(e.target.checked)} className="mt-1 size-4 shrink-0 accent-[var(--gold)]" />
            <span>
              Soy mayor de 18 años y he leído la <Link to="/privacidad" className="underline hover:text-gold">política de privacidad</Link>.
            </span>
          </label>
          {error && <p role="alert" className="border border-gold px-4 py-3 text-sm">{error}</p>}
          <button type="submit" disabled={estado === 'enviando'} className="btn btn-gold h-12 w-full px-6 text-lg disabled:opacity-60">
            {estado === 'enviando' ? 'Enviando…' : 'Enviarme el enlace'}
          </button>
        </form>
      )}
      {estado === 'verificando' && <p className="mt-6 text-muted" role="status">Comprobando tu enlace…</p>}
    </Pagina>
  )
}
