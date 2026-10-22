import { useCallback, useEffect, useState } from 'react'
import { useCuenta } from './cuenta'
import { api } from './sesion'

export const euros = (v, dec = 2) =>
  v == null ? '-' : new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', minimumFractionDigits: dec, maximumFractionDigits: dec }).format(v)
export const conSigno = (v) => (v == null ? '-' : `${v > 0 ? '+' : ''}${euros(v)}`)

// Estado del bank simulado. Las acciones devuelven el estado nuevo y lo sustituyen.
export function usePaper() {
  const { token, cargando: cargandoCuenta } = useCuenta()
  const [estado, setEstado] = useState({ cargando: true, datos: null, error: null })
  const cargar = useCallback(() => {
    if (cargandoCuenta) return
    api('/paper')
      .then((datos) => setEstado({ cargando: false, datos, error: null }))
      .catch((e) => setEstado({ cargando: false, datos: null, error: e.status || 'red' }))
  }, [cargandoCuenta, token]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { cargar() }, [cargar])
  const accion = async (ruta, opciones) => {
    const datos = await api(ruta, opciones)
    setEstado({ cargando: false, datos, error: null })
    return datos
  }
  return { ...estado, recargar: cargar, accion }
}
