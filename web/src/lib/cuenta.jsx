import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { API_URL } from '../config'
import { api, guardar, leer } from './sesion'

const Ctx = createContext(null)

export function CuentaProvider({ children }) {
  const [token, setToken] = useState(leer)
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(Boolean(token && API_URL))

  const refrescar = useCallback(async () => {
    const t = leer()
    if (!t || !API_URL) {
      setUsuario(null)
      setCargando(false)
      return null
    }
    try {
      const u = await api('/me', { token: t })
      setUsuario(u)
      return u
    } catch (e) {
      if (e.status === 401) {
        guardar('')
        setToken('')
      }
      setUsuario(null)
      return null
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { refrescar() }, [refrescar, token])

  const valor = useMemo(() => ({
    token,
    usuario,
    cargando,
    suscriptor: Boolean(usuario?.subscriber),
    refrescar,
    entrar: (t, u) => {
      guardar(t)
      setToken(t)
      setUsuario(u)
    },
    salir: async () => {
      try { await api('/auth/logout', { method: 'POST' }) } catch { /* da igual */ }
      guardar('')
      setToken('')
      setUsuario(null)
    },
  }), [token, usuario, cargando, refrescar])

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>
}

export const useCuenta = () => useContext(Ctx)
