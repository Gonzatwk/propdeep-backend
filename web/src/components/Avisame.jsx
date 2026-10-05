import { CheckCircle } from '@phosphor-icons/react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { API_URL, CONTACT_EMAIL } from '../config'

const ERRORES = {
  correo: 'Revisa el correo: parece que falta algo.',
  consentimiento: 'Marca la casilla para que podamos escribirte.',
}

// Formulario "Avísame". Con el backend configurado (VITE_API_URL), el correo va a
// POST /waitlist; mientras tanto, a /api/avisame (Cloudflare Pages Function con KV).
async function apuntar(correo, acepto, web) {
  if (API_URL) {
    const r = await fetch(`${API_URL}/waitlist`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email: correo, source: 'landing' }),
    })
    return { ok: r.ok, error: r.status === 422 ? 'correo' : '' }
  }
  const r = await fetch('/api/avisame', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ correo, acepto, web }),
  })
  const datos = await r.json().catch(() => ({}))
  return { ok: r.ok && datos.ok, error: datos.error || '' }
}
export default function Avisame() {
  const [estado, setEstado] = useState('listo') // listo | enviando | hecho | error
  const [error, setError] = useState('')

  const enviar = async (e) => {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    if (f.get('web')) return setEstado('hecho')
    setEstado('enviando')
    setError('')
    try {
      const r = await apuntar(String(f.get('correo')).trim(), f.get('acepto') === 'si', '')
      if (r.ok) return setEstado('hecho')
      setError(ERRORES[r.error] || '')
      setEstado('error')
    } catch {
      setEstado('error')
    }
  }

  if (estado === 'hecho') {
    return (
      <div role="status" className="flex items-start gap-3 border-2 border-black bg-black px-5 py-4 text-white">
        <CheckCircle weight="fill" aria-hidden className="mt-0.5 size-7 shrink-0 text-gold" />
        <p className="text-lg leading-snug">
          <strong className="display block text-3xl text-gold">Apuntado</strong>
          Te escribiremos el 20 de octubre, cuando abra PropDeep.
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={enviar} className="max-w-lg">
      <label htmlFor="correo" className="text-sm font-semibold">Tu correo</label>
      <div className="mt-2 flex flex-col gap-3 sm:flex-row">
        <input
          id="correo"
          name="correo"
          type="email"
          required
          autoComplete="email"
          placeholder="nombre@correo.com"
          className="h-15 w-full min-w-0 border-2 sm:flex-1 border-black bg-white px-4 text-lg text-black placeholder:text-black/40 focus:outline-4 focus:outline-offset-2 focus:outline-black"
        />
        <button type="submit" disabled={estado === 'enviando'} className="btn btn-black h-15 px-7 text-[1.3rem] disabled:opacity-60">
          {estado === 'enviando' ? 'Enviando…' : 'Avísame'}
        </button>
      </div>
      <input type="text" name="web" tabIndex={-1} autoComplete="off" aria-hidden className="absolute -left-[9999px] size-px opacity-0" />
      <label className="mt-4 flex items-start gap-3 text-sm leading-snug">
        <input type="checkbox" name="acepto" value="si" required className="mt-0.5 size-5 shrink-0 accent-black" />
        <span>
          Quiero recibir un correo cuando abra PropDeep. He leído la{' '}
          <Link to="/privacidad" className="font-semibold underline">política de privacidad</Link>. Soy mayor de 18 años.
        </span>
      </label>
      {estado === 'error' && (
        <p role="alert" className="mt-4 border-l-4 border-black pl-3 text-sm font-semibold">
          {error || (
            <>
              No hemos podido guardarlo. Escríbenos a{' '}
              <a className="underline" href={`mailto:${CONTACT_EMAIL}?subject=Av%C3%ADsame%20cuando%20abra`}>{CONTACT_EMAIL}</a> y te apuntamos.
            </>
          )}
        </p>
      )}
    </form>
  )
}
