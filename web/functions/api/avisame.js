// Cloudflare Pages Function: guarda el correo de quien quiere que le avisemos
// cuando abra PropDeep. Sin cookies ni servicios de terceros: los correos van
// a un espacio KV del propio proyecto de Cloudflare, enlazado como AVISOS.
const CORREO = /^[^\s@]{1,64}@[^\s@]+\.[^\s@]{2,}$/

const json = (cuerpo, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { 'content-type': 'application/json; charset=utf-8' } })

export async function onRequestPost({ request, env }) {
  if (!env.AVISOS) return json({ ok: false, error: 'sin_almacen' }, 503)

  let datos
  try {
    datos = await request.json()
  } catch {
    return json({ ok: false, error: 'formato' }, 400)
  }

  // Campo trampa: las personas no lo ven; si viene relleno, es un bot.
  if (datos.web) return json({ ok: true })

  const correo = String(datos.correo || '').trim().toLowerCase()
  if (correo.length > 254 || !CORREO.test(correo)) return json({ ok: false, error: 'correo' }, 400)
  if (datos.acepto !== true) return json({ ok: false, error: 'consentimiento' }, 400)

  const clave = `correo:${correo}`
  if (!(await env.AVISOS.get(clave))) {
    await env.AVISOS.put(
      clave,
      JSON.stringify({ correo, fecha: new Date().toISOString(), consentimiento: 'aviso de apertura y política de privacidad' }),
    )
  }
  return json({ ok: true })
}

export const onRequest = () => json({ ok: false, error: 'metodo' }, 405)
