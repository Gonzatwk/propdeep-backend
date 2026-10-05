import { API_URL } from '../config'

// Sesión de la zona de suscriptores. El token se guarda en localStorage (no es una
// cookie): es estrictamente necesario para mantenerte dentro y no sirve para seguirte.
const CLAVE = 'propdeep.sesion'

export const leer = () => {
  try { return localStorage.getItem(CLAVE) || '' } catch { return '' }
}
export const guardar = (t) => {
  try {
    if (t) localStorage.setItem(CLAVE, t)
    else localStorage.removeItem(CLAVE)
  } catch { /* modo privado */ }
}

export class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje)
    this.status = status
  }
}

// Llamada al backend con la sesión, si la hay.
export async function api(path, { method = 'GET', body, token = leer() } = {}) {
  if (!API_URL) throw new ErrorApi(0, 'Sin servidor configurado')
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  })
  const datos = await res.json().catch(() => ({}))
  if (!res.ok) throw new ErrorApi(res.status, datos.detail || 'Algo ha fallado. Vuelve a intentarlo.')
  return datos
}
