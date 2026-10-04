// Lectura del backend FastAPI (GET /predictions y GET /track-record).
// Todo lo de aquí convierte la respuesta de la API a la forma que usa la web.
import { API_URL } from './config'
import { fmtNum } from './format'

const STAT = { pts: 'Puntos', reb: 'Rebotes', ast: 'Asistencias', fg3m: 'Triples' }
const LADO = { over: 'más', under: 'menos' }
const RESULTADO = { pending: 'pendiente', won: 'ganada', lost: 'perdida', push: 'nula', void: 'nula', no_bet: 'pendiente' }

export const statLabel = (s) => STAT[s] || s
export const capitalizar = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s)

export async function getJson(path) {
  if (!API_URL) return null
  const res = await fetch(`${API_URL}${path}`, { signal: AbortSignal.timeout(10000) })
  if (!res.ok) throw new Error(`${path}: ${res.status}`)
  return res.json()
}

// Una predicción de la API -> entrada de historial (ver src/data/historial.js).
export function aEntrada(p) {
  return {
    id: p.id,
    publicado: p.published_at,
    partido: p.game_date ? new Date(`${p.game_date}T12:00:00`).toLocaleDateString('es-ES') : '—',
    jugador: p.player,
    prop: statLabel(p.stat),
    lado: LADO[p.side] || '',
    linea: p.line,
    cuota: p.odds,
    probEstimada: p.probability,
    confianza: capitalizar(p.confidence),
    jugada: Boolean(p.side),
    resultado: RESULTADO[p.status] || 'pendiente',
    informe: p.report,
    hash: p.content_hash,
  }
}

// Bloque de /track-record -> misma forma que resumen() de src/data/historial.js.
export function aResumen(b) {
  if (!b) return null
  return {
    jugadas: b.picks,
    resueltas: b.settled,
    ganadas: b.won,
    acierto: b.hit_rate,
    beneficio: b.profit_units,
    roi: b.roi,
  }
}

// Una entrada de informes_ejemplo.json (scripts/informes_ejemplo.py) -> tarjeta de la landing.
export function aInforme({ partido, casa, informe, analisis: a }) {
  const over = a.side !== 'under'
  const tipo = !a.side
    ? 'Prop sin ventaja ("no apostamos")'
    : a.confidence === 'baja'
      ? 'Prop con confianza baja'
      : 'Prop con ventaja clara'
  return {
    tipo,
    pendiente: false,
    jugador: a.player,
    partido: casa ? `${partido} · ${casa}` : partido,
    prop: a.side ? `${statLabel(a.stat)}: ${LADO[a.side]} de ${fmtNum(a.line)}` : `${statLabel(a.stat)}: línea ${fmtNum(a.line)}`,
    cuota: a.odds_taken ?? (over ? a.over_odds : a.under_odds),
    probImplicita: over ? a.prob_over_market : 1 - a.prob_over_market,
    probEstimada: over ? a.prob_over_final : 1 - a.prob_over_final,
    confianza: capitalizar(a.confidence),
    veredicto: a.side ? 'Con ventaja' : 'Sin ventaja',
    porque: (a.reasons || []).slice(0, 3),
    informe,
  }
}
