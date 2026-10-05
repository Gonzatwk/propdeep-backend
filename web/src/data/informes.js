import ejemplosApi from './informes_ejemplo.json'
import { aInforme } from '../api'

// Informes de ejemplo de la landing.
// Si informes_ejemplo.json (salida de scripts/informes_ejemplo.py del backend) tiene
// contenido, se usa ese archivo y esta lista se ignora.
// IMPORTANTE: mientras `pendiente` sea true, la tarjeta se muestra como hueco vacío.
// Rellenar solo con análisis reales generados con datos reales, nunca inventados.
export const FECHA_EJEMPLOS = null // p. ej. '2026-10-22'

export const informes = [
  { tipo: 'Puntos', pendiente: true },
  { tipo: 'Rebotes', pendiente: true },
  { tipo: 'Asistencias', pendiente: true },
]


export const informesLanding = ejemplosApi.length ? ejemplosApi.map(aInforme) : informes
