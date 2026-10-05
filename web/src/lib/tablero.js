import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { API_URL } from '../config'
import { demoLinea, demoPartido, demoTablero } from '../data/demo'
import { useCuenta } from './cuenta'
import { api } from './sesion'

// Modo demostración: ?demo=1 (vista gratis) o ?demo=suscriptor (todo desbloqueado).
export function useModo() {
  const [params] = useSearchParams()
  const demo = params.get('demo')
  const sufijo = demo ? `?demo=${demo}` : ''
  return { demo: Boolean(demo), demoSuscriptor: demo === 'suscriptor', enlace: (ruta) => `${ruta}${sufijo}` }
}

// Carga genérica: en demo usa los datos de ejemplo; si no, el backend con la sesión.
function useCarga(demoFn, ruta, deps) {
  const { demo, demoSuscriptor } = useModo()
  const { token, cargando: cargandoCuenta } = useCuenta()
  const [estado, setEstado] = useState({ cargando: true, datos: null, error: null })

  const cargar = useCallback(() => {
    if (demo) {
      const d = demoFn(demoSuscriptor)
      setEstado(d?.error ? { cargando: false, datos: null, error: d.error } : { cargando: false, datos: d, error: d ? null : 404 })
      return
    }
    if (!API_URL) {
      setEstado({ cargando: false, datos: null, error: 'sin-servidor' })
      return
    }
    if (cargandoCuenta) return
    setEstado((e) => ({ ...e, cargando: true, error: null }))
    api(ruta)
      .then((datos) => setEstado({ cargando: false, datos, error: null }))
      .catch((e) => setEstado({ cargando: false, datos: null, error: e.status || 'red' }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo, demoSuscriptor, token, cargandoCuenta, ruta, ...deps])

  useEffect(() => { cargar() }, [cargar])
  return { ...estado, reintentar: cargar }
}

export const useTablero = (fecha) =>
  useCarga(demoTablero, fecha ? `/board?game_date=${fecha}` : '/board', [fecha])

export const usePartido = (id) =>
  useCarga((s) => demoPartido(id, s), `/board/games/${encodeURIComponent(id)}`, [id])

export const useLinea = (id) =>
  useCarga((s) => demoLinea(id, s), `/board/lines/${encodeURIComponent(id)}`, [id])
