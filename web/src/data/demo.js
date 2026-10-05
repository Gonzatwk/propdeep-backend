// Jornada de DEMOSTRACIÓN para enseñar la zona de partidos antes del 20 de octubre.
// Los jugadores son INVENTADOS y los números salen de un generador con semilla fija:
// no son análisis reales y la web los marca siempre como "Demostración".
// Tiene la misma forma que las respuestas de /board, /board/games/{id}, /board/lines/{id} y /picks.

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
const LIBROS = ['williamhill', 'betfair_ex_eu', 'unibet_eu', 'pinnacle', 'betsson']

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
const media = (xs) => (xs.length ? r2(xs.reduce((a, b) => a + b, 0) / xs.length) : null)
const tasa = (xs, linea) => (xs.length ? Math.round((xs.filter((v) => v > linea).length / xs.length) * 1000) / 1000 : null)
const bloque = (xs, linea) => ({ games: xs.length, avg: media(xs), hit_rate: tasa(xs, linea) })

const es = (x, d = 1) => x.toLocaleString('es-ES', { maximumFractionDigits: d })
const pct = (x) => `${Math.round(x * 100)} %`
const ETIQUETA = { pts: 'puntos', reb: 'rebotes', ast: 'asistencias', fg3m: 'triples' }

// Líneas de cada casa: casi todas en la misma línea, alguna medio punto arriba o abajo.
function casas(linea) {
  const n = 3 + Math.floor(azar() * 3)
  return LIBROS.slice(0, n).map((bookmaker) => {
    const salto = azar() < 0.25 ? (azar() < 0.5 ? -1 : 1) : 0
    const l = linea + salto
    const p = Math.min(0.58, Math.max(0.42, 0.5 - salto * 0.06 + normal() * 0.025))
    const margen = 1.04 + azar() * 0.035
    return { bookmaker, line: l, over_odds: r2(1 / (p * margen)), under_odds: r2(1 / ((1 - p) * margen)) }
  }).sort((a, b) => a.line - b.line || a.bookmaker.localeCompare(b.bookmaker))
}

function mejores(books) {
  const over = [...books].sort((a, b) => a.line - b.line || b.over_odds - a.over_odds)[0]
  const under = [...books].sort((a, b) => b.line - a.line || b.under_odds - a.under_odds)[0]
  return {
    over: { bookmaker: over.bookmaker, line: over.line, odds: over.over_odds },
    under: { bookmaker: under.bookmaker, line: under.line, odds: under.under_odds },
  }
}

function analizar(id, partido, [nombre, lado, ...medias], i) {
  const base = medias[i]
  const stat = STATS[i]
  const sd = Math.max(base * 0.28, 0.8)
  // 40 partidos: 12 de esta temporada y 28 de la anterior (del más reciente al más antiguo).
  const valores = Array.from({ length: 40 }, () => Math.max(0, Math.round(base + normal() * sd)))
  const enCasa = valores.map(() => azar() < 0.5)
  const rivales = valores.map(() => (azar() < 0.12 ? 'rival' : 'otro'))
  const recientes = valores.slice(0, 10)
  const temporada = valores.slice(0, 12)
  const anterior = valores.slice(12)
  const proyeccion = r2(0.25 * media(valores.slice(0, 5)) + 0.35 * media(recientes) + 0.25 * media(valores.slice(0, 20)) + 0.15 * media(temporada))
  const linea = Math.floor(proyeccion + normal() * sd * 0.3) + 0.5
  const books = casas(linea)
  const ref = books.find((b) => b.line === linea) || books[0]
  const casa = lado === 'casa'
  const rival = casa ? partido.fuera : partido.casa
  const b2b = azar() < 0.2
  const splits = {
    home: bloque(valores.filter((_, k) => enCasa[k]), linea),
    away: bloque(valores.filter((_, k) => !enCasa[k]), linea),
    vs_opponent: bloque(valores.filter((_, k) => rivales[k] === 'rival'), linea),
  }
  const hit = {
    last5: tasa(valores.slice(0, 5), linea),
    last10: tasa(recientes, linea),
    season: tasa(temporada, linea),
    season_games: temporada.length,
    last_season: tasa(anterior, linea),
    last_season_games: anterior.length,
  }
  const minutos5 = r2(30 + normal() * 3)
  const minutosT = r2(30 + normal() * 2)
  const distintas = new Set(books.map((b) => b.line)).size > 1
  const informe = [
    `${nombre}: línea de ${es(linea)} ${ETIQUETA[stat]}. Nuestra proyección es de ${es(proyeccion)}.`,
    `Superó la línea en el ${pct(hit.last5)} de los últimos 5, el ${pct(hit.last10)} de los últimos 10 y el ${pct(hit.season)} de los ${hit.season_games} de esta temporada.`,
    `En casa promedia ${es(splits.home.avg)} y fuera ${es(splits.away.avg)}; esta noche juega ${casa ? 'en casa' : 'fuera'} contra ${rival}${b2b ? ', en back-to-back' : ''}.`,
    splits.vs_opponent.games ? `Contra este rival promedia ${es(splits.vs_opponent.avg)} en ${splits.vs_opponent.games} partidos recientes.` : '',
    `Minutos: ${es(minutos5)} en los últimos 5 frente a ${es(minutosT)} de media.`,
    distintas ? 'Las casas no coinciden en la línea: compara antes de decidir.' : '',
    'Es información orientativa, no una recomendación de apuesta.',
  ].filter(Boolean).join(' ')
  return {
    id,
    event_id: partido.id,
    player: nombre,
    stat,
    line: linea,
    over_odds: ref.over_odds,
    under_odds: ref.under_odds,
    bookmaker: ref.bookmaker,
    books_count: books.length,
    free: false,
    projection: proyeccion,
    hit_rates: hit,
    best: mejores(books),
    books,
    report: informe,
    notes: [],
    trends: {
      games: 40,
      last5: media(valores.slice(0, 5)),
      last10: media(recientes),
      last20: media(valores.slice(0, 20)),
      season: media(temporada),
      sd: r2(sd),
      minutes_last5: minutos5,
      minutes_season: minutosT,
      recent_values: recientes,
      season_games: temporada.length,
      last_season_games: anterior.length,
      splits,
    },
    context: { home: casa, back_to_back: b2b, opponent: rival, opponent_factor: r2(0.95 + azar() * 0.1), injury_status: null, injury_note: null },
    published_at: '2026-10-20T15:00:00+00:00',
    content_hash: null,
  }
}

let n = 1
const LINEAS = PARTIDOS.flatMap((p) =>
  p.jugadores.flatMap((j) => STATS.map((_, i) => analizar(n++, p, j, i))),
)

// Las gratis: los puntos del jugador con más proyección de cada partido, igual que el backend.
for (const p of [...PARTIDOS].sort((a, b) => a.hora.localeCompare(b.hora)).slice(0, GRATIS)) {
  const top = LINEAS.filter((l) => l.event_id === p.id && l.stat === 'pts').sort((a, b) => b.projection - a.projection)[0]
  if (top) top.free = true
}

const cabecera = (p) => ({ event_id: p.id, game_date: FECHA, home_team: p.casa, away_team: p.fuera, commence_time: p.hora })

// Lo que devuelve el backend para una línea: bloqueada, sin análisis.
function resumen(l, abierta) {
  const base = {
    id: l.id, event_id: l.event_id, player: l.player, stat: l.stat, line: l.line, over_odds: l.over_odds,
    under_odds: l.under_odds, bookmaker: l.bookmaker, books_count: l.books_count, free: l.free, locked: !abierta,
  }
  if (!abierta) return base
  return { ...base, projection: l.projection, hit_rates: l.hit_rates, best: l.best }
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

// Picks de ejemplo para enseñar la sección: inventados, con aciertos Y fallos.
const PICKS = [
  ['2026-10-18', 'Marcus Delane', 'pts', 25.5, 'over', 1.87, 'williamhill', 'won', 31, 'Viene de 36 minutos de media y el rival concede mucho.'],
  ['2026-10-18', 'Kobe Reyes', 'ast', 7.5, 'under', 1.95, 'betfair_ex_eu', 'lost', 9, null],
  ['2026-10-19', 'Nikola Varga', 'reb', 11.5, 'over', 1.91, 'unibet_eu', 'won', 14, null],
  ['2026-10-19', 'Shay Morrow', 'pts', 30.5, 'under', 1.83, 'pinnacle', 'lost', 34, 'Línea alta en dos casas; en las otras, 29,5.'],
  ['2026-10-19', 'Devin Marsh', 'fg3m', 3.5, 'over', 2.05, 'betsson', 'void', null, 'No jugó: anulada en la casa.'],
  ['2026-10-20', 'Julian Okafor', 'pts', 23.5, 'over', 1.9, 'williamhill', 'pending', null, null],
]

export function demoPicks() {
  const picks = PICKS.map(([dia, player, stat, line, side, odds, bookmaker, status, actual, note], i) => ({
    id: PICKS.length - i,
    published_at: `${dia}T14:${String(10 + i).padStart(2, '0')}:00+00:00`,
    commence_time: `${dia}T23:30:00+00:00`,
    game_date: dia,
    home_team: null,
    away_team: null,
    player, stat, line, side, odds, bookmaker, stake: 1, note, status, actual,
    auto_settle: true,
    content_hash: null,
  })).reverse()
  const cerrados = picks.filter((p) => p.status === 'won' || p.status === 'lost')
  const ganados = cerrados.filter((p) => p.status === 'won')
  const beneficio = r2(ganados.reduce((a, p) => a + p.odds - 1, 0) - (cerrados.length - ganados.length))
  return {
    summary: {
      picks: picks.length,
      won: ganados.length,
      lost: cerrados.length - ganados.length,
      push_or_void: picks.filter((p) => p.status === 'void' || p.status === 'push').length,
      pending: picks.filter((p) => p.status === 'pending').length,
      hit_rate: ganados.length / cerrados.length,
      profit_units: beneficio,
      roi: r2(beneficio / cerrados.length),
      avg_odds: null,
    },
    picks,
    warning: 'Resultados pasados no garantizan nada; a largo plazo es muy difícil ganar a la casa.',
  }
}

// Conversación de ejemplo del chat, con los números de la jornada de demostración.
export function demoChat(nombreCasa) {
  const top = LINEAS.filter((l) => l.stat === 'pts')
    .sort((a, b) => b.hit_rates.last10 - a.hit_rates.last10 || b.hit_rates.last5 - a.hit_rates.last5)
    .slice(0, 3)
  const l = LINEAS.find((x) => x.stat === 'pts' && x.books.length >= 4) || LINEAS[0]
  const cuota = (x) => x.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const lista = l.books.map((b) => `- ${nombreCasa(b.bookmaker)}: ${es(b.line)}, más a ${cuota(b.over_odds)} y menos a ${cuota(b.under_odds)}`)
  return [
    { role: 'user', content: '¿Quién ha superado más veces su línea de puntos en los últimos 10 partidos?' },
    {
      role: 'assistant',
      content: `Hoy, en puntos:\n${top.map((t) => `- ${t.player}: ${pct(t.hit_rates.last10)} de los últimos 10 por encima de ${es(t.line)} (proyección ${es(t.projection)})`).join('\n')}\n\nDiez partidos son una muestra corta y la casa ya cuenta con la racha al poner la línea. Es un dato, no una recomendación.`,
    },
    { role: 'user', content: `Compara las casas para ${l.player} en puntos` },
    {
      role: 'assistant',
      content: `${l.player}, puntos:\n${lista.join('\n')}\n\nLa línea más baja para el más es ${es(l.best.over.line)} a ${cuota(l.best.over.odds)}, y la más alta para el menos, ${es(l.best.under.line)} a ${cuota(l.best.under.odds)}. Las cuotas cambian: compruébalas en la casa antes de nada.`,
    },
  ]
}
