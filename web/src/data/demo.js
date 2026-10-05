// Jornada de DEMOSTRACIÓN para enseñar la zona de partidos antes del 20 de octubre.
// Los jugadores son INVENTADOS y los números salen de un generador con semilla fija:
// no son análisis reales y la web los marca siempre como "Demostración".
// Tiene la misma forma que las respuestas de /board, /board/games/{id} y /board/lines/{id}.

const FECHA = '2026-10-20'
const GRATIS = 3

const PARTIDOS = [
  { id: 'demo-1', hora: '2026-10-20T23:30:00Z', casa: 'Boston Celtics', fuera: 'New York Knicks',
    jugadores: [['Marcus Delane', 'casa', 26, 5, 4, 3], ['Theo Brandt', 'casa', 15, 9, 2, 1], ['Julian Okafor', 'fuera', 24, 4, 7, 2], ['Rafa Quintero', 'fuera', 12, 6, 3, 2]] },
  { id: 'demo-2', hora: '2026-10-21T02:00:00Z', casa: 'Golden State Warriors', fuera: 'Los Angeles Lakers',
    jugadores: [['Devin Marsh', 'casa', 29, 4, 6, 4], ['Ike Salomon', 'casa', 10, 8, 3, 1], ['Andrés Vallejo', 'fuera', 22, 11, 3, 1], ['Kobe Reyes', 'fuera', 18, 3, 8, 2]] },
  { id: 'demo-3', hora: '2026-10-21T00:00:00Z', casa: 'Denver Nuggets', fuera: 'Oklahoma City Thunder',
    jugadores: [['Nikola Varga', 'casa', 25, 12, 9, 1], ['Cole Whitaker', 'casa', 14, 4, 2, 3], ['Shay Morrow', 'fuera', 31, 5, 6, 2], ['Lu Dorsey', 'fuera', 11, 7, 1, 1]] },
]
const STATS = ['pts', 'reb', 'ast', 'fg3m']
const MIN_SD = { pts: 4, reb: 2, ast: 1.8, fg3m: 1 }
const LIBROS = ['bet365', 'williamhill', 'codere', 'betfair_ex_eu']

// Generador con semilla: siempre la misma jornada.
function semilla(n) {
  let s = n
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}
const azar = semilla(20261020)
const normal = () => Math.sqrt(-2 * Math.log(azar() || 1e-9)) * Math.cos(2 * Math.PI * azar())
const r2 = (x) => Math.round(x * 100) / 100
const r4 = (x) => Math.round(x * 10000) / 10000
const media = (xs) => r2(xs.reduce((a, b) => a + b, 0) / xs.length)
const fdn = (z) => 0.5 * (1 + erf(z / Math.SQRT2))
function erf(x) {
  const t = 1 / (1 + 0.3275911 * Math.abs(x))
  const y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x)
  return x >= 0 ? y : -y
}

const es = (x, d = 1) => x.toLocaleString('es-ES', { maximumFractionDigits: d })
const ETIQUETA = { pts: 'puntos', reb: 'rebotes', ast: 'asistencias', fg3m: 'triples' }

function analizar(id, partido, [nombre, lado, ...medias], i) {
  const base = medias[i]
  const stat = STATS[i]
  const sd = Math.max(base * 0.28, MIN_SD[stat] * 0.6)
  const valores = Array.from({ length: 20 }, () => Math.max(0, Math.round(base + normal() * sd)))
  const recientes = valores.slice(0, 10)
  const proyeccion = r2(0.25 * media(valores.slice(0, 5)) + 0.35 * media(recientes) + 0.4 * media(valores))
  const linea = Math.floor(proyeccion + normal() * sd * 0.3) + 0.5
  const sigma = Math.max(r2(Math.sqrt(valores.reduce((a, v) => a + (v - media(valores)) ** 2, 0) / 20)), MIN_SD[stat])
  const pModelo = 1 - fdn((linea - proyeccion) / sigma)
  const margen = 1.045 + azar() * 0.02
  // Cuotas típicas de props (entre 1,75 y 2,20); la ventaja sale de que el modelo se separe.
  const pMercadoReal = Math.min(0.56, Math.max(0.44, 0.5 + (pModelo - 0.5) * 0.4 + normal() * 0.03))
  const over = r2(1 / (pMercadoReal * margen))
  const under = r2(1 / ((1 - pMercadoReal) * margen))
  const pMercado = (1 / over) / (1 / over + 1 / under)
  const pFinal = 0.5 * pModelo + 0.5 * pMercado
  const eOver = pFinal - 1 / over
  const eUnder = 1 - pFinal - 1 / under
  const [ladoMejor, ventaja, cuota] = eOver >= eUnder ? ['over', eOver, over] : ['under', eUnder, under]
  const hay = ventaja >= 0.03
  const confianza = !hay ? 'sin ventaja' : ventaja >= 0.06 ? 'alta' : ventaja >= 0.04 ? 'media' : 'baja'
  const pLado = ladoMejor === 'over' ? pFinal : 1 - pFinal
  const casa = lado === 'casa'
  const rival = casa ? partido.fuera : partido.casa
  const b2b = azar() < 0.2
  const superadas = recientes.filter((v) => v > linea).length
  const informe = [
    `${nombre}: línea de ${es(linea)} ${ETIQUETA[stat]}. Proyectamos ${es(proyeccion)}.`,
    `Promedia ${es(media(recientes))} en sus últimos 10 partidos y superó la línea en ${superadas} de ellos.`,
    `Juega ${casa ? 'en casa' : 'fuera'} contra ${rival}${b2b ? ', en back-to-back' : ''}.`,
    `Estimamos un ${es(pFinal * 100)} % para el más frente al ${es(pMercado * 100)} % que marca el mercado sin margen.`,
    hay
      ? `Vemos valor en el ${ladoMejor === 'over' ? 'más' : 'menos'} a cuota ${es(cuota, 2)} (ventaja de ${es(ventaja * 100)} puntos). Confianza ${confianza}.`
      : 'Sin ventaja: no recomendamos jugar esta prop.',
  ].join(' ')
  return {
    id,
    event_id: partido.id,
    player: nombre,
    stat,
    line: linea,
    over_odds: over,
    under_odds: under,
    bookmaker: LIBROS[id % LIBROS.length],
    free: false,
    side: hay ? ladoMejor : null,
    odds: hay ? cuota : null,
    confidence: confianza,
    edge: r4(Math.max(ventaja, 0)),
    probability: r4(hay ? pLado : pFinal),
    prob_over: r4(pFinal),
    prob_over_market: r4(pMercado),
    projection: proyeccion,
    status: hay ? 'pending' : 'no_bet',
    actual: null,
    report: informe,
    reasons: [],
    expected_value: hay ? r4(pLado * cuota - 1) : null,
    trends: {
      games: 20,
      last5: media(valores.slice(0, 5)),
      last10: media(recientes),
      last20: media(valores),
      season: media(valores),
      sd: sigma,
      minutes_last5: r2(30 + normal() * 3),
      minutes_season: r2(30 + normal() * 2),
      hit_rate_last10: superadas / 10,
      recent_values: recientes,
    },
    context: { home: casa, back_to_back: b2b, opponent: rival, opponent_factor: 1, injury_status: null, injury_note: null },
    published_at: '2026-10-20T15:00:00+00:00',
    content_hash: null,
  }
}

let n = 1
const LINEAS = PARTIDOS.flatMap((p) =>
  p.jugadores.flatMap((j) => STATS.map((_, i) => analizar(n++, p, j, i))),
)

// Las gratis: la de más ventaja de cada partido, igual que el backend.
for (const p of [...PARTIDOS].sort((a, b) => a.hora.localeCompare(b.hora)).slice(0, GRATIS)) {
  const mejor = LINEAS.filter((l) => l.event_id === p.id && l.side).sort((a, b) => b.edge - a.edge)[0]
  if (mejor) mejor.free = true
}

const cabecera = (p) => ({ event_id: p.id, game_date: FECHA, home_team: p.casa, away_team: p.fuera, commence_time: p.hora })

// Lo que devuelve el backend para una línea bloqueada: sin veredicto ni probabilidades.
function resumen(l, abierta) {
  const base = {
    id: l.id, event_id: l.event_id, player: l.player, stat: l.stat, line: l.line,
    over_odds: l.over_odds, under_odds: l.under_odds, bookmaker: l.bookmaker, free: l.free, locked: !abierta,
  }
  if (!abierta) return base
  const { report: _r, reasons: _re, trends: _t, context: _c, published_at: _p, content_hash: _h, expected_value: _e, ...resto } = l
  return { ...resto, locked: false }
}

const visor = (suscriptor) => ({ logged_in: suscriptor, subscriber: suscriptor })

export function demoTablero(suscriptor) {
  return {
    game_date: FECHA,
    dates: [FECHA],
    free_lines_per_day: GRATIS,
    viewer: visor(suscriptor),
    games: [...PARTIDOS].sort((a, b) => a.hora.localeCompare(b.hora)).map((p) => {
      const ls = LINEAS.filter((l) => l.event_id === p.id)
      return {
        ...cabecera(p),
        lines: ls.length,
        players: p.jugadores.length,
        with_edge: ls.filter((l) => l.side).length,
        free_lines: ls.filter((l) => l.free).length,
        started: false,
      }
    }),
  }
}

export function demoPartido(id, suscriptor) {
  const p = PARTIDOS.find((x) => x.id === id)
  if (!p) return null
  return {
    game: cabecera(p),
    viewer: visor(suscriptor),
    lines: LINEAS.filter((l) => l.event_id === id).map((l) => resumen(l, suscriptor || l.free)),
  }
}

export function demoLinea(id, suscriptor) {
  const l = LINEAS.find((x) => String(x.id) === String(id))
  if (!l) return { error: 404 }
  if (!suscriptor && !l.free) return { error: 402 }
  return { ...l, game: cabecera(PARTIDOS.find((p) => p.id === l.event_id)) }
}
