import { useCuenta } from './cuenta'
import { useModo } from './tablero'

export const STAT = { pts: 'Puntos', reb: 'Rebotes', ast: 'Asistencias', fg3m: 'Triples' }
export const LADO = { over: 'Más', under: 'Menos' }
export const PRECIO = { mensual: 15, anual: 120, prueba: 7 }

// Destino del botón de suscripción según el estado de la cuenta.
export function useIrASuscribir() {
  const { usuario } = useCuenta()
  const { demo } = useModo()
  if (demo) return '/cuenta'
  return usuario ? '/cuenta' : '/entrar?siguiente=/cuenta'
}
