// Conversión de los informes de ejemplo de la API a la forma que usa la landing.
import { fmtCuota } from './format'

const STAT = { pts: 'Puntos', reb: 'Rebotes', ast: 'Asistencias', fg3m: 'Triples' }

export const statLabel = (s) => STAT[s] || s

// Una entrada de informes_ejemplo.json (scripts/informes_ejemplo.py) -> tarjeta de la landing.
export function aInforme({ partido, casa, informe, analisis: a }) {
  const t = a.trends || {}
  return {
    tipo: statLabel(a.stat),
    pendiente: false,
    jugador: a.player,
    partido: casa ? `${partido} · ${casa}` : partido,
    prop: `${statLabel(a.stat)}: línea ${String(a.line).replace('.', ',')}`,
    cuotas: `${fmtCuota(a.over_odds)} / ${fmtCuota(a.under_odds)}`,
    proyeccion: a.projection,
    superoUltimos10: t.hit_rate_last10,
    mediaUltimos10: t.last10,
    informe,
  }
}
