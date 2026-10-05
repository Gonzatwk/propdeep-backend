// Nombre completo de The Odds API -> abreviatura y nombre corto.
const EQUIPOS = {
  'Atlanta Hawks': ['ATL', 'Hawks'],
  'Boston Celtics': ['BOS', 'Celtics'],
  'Brooklyn Nets': ['BKN', 'Nets'],
  'Charlotte Hornets': ['CHA', 'Hornets'],
  'Chicago Bulls': ['CHI', 'Bulls'],
  'Cleveland Cavaliers': ['CLE', 'Cavaliers'],
  'Dallas Mavericks': ['DAL', 'Mavericks'],
  'Denver Nuggets': ['DEN', 'Nuggets'],
  'Detroit Pistons': ['DET', 'Pistons'],
  'Golden State Warriors': ['GSW', 'Warriors'],
  'Houston Rockets': ['HOU', 'Rockets'],
  'Indiana Pacers': ['IND', 'Pacers'],
  'Los Angeles Clippers': ['LAC', 'Clippers'],
  'LA Clippers': ['LAC', 'Clippers'],
  'Los Angeles Lakers': ['LAL', 'Lakers'],
  'Memphis Grizzlies': ['MEM', 'Grizzlies'],
  'Miami Heat': ['MIA', 'Heat'],
  'Milwaukee Bucks': ['MIL', 'Bucks'],
  'Minnesota Timberwolves': ['MIN', 'Timberwolves'],
  'New Orleans Pelicans': ['NOP', 'Pelicans'],
  'New York Knicks': ['NYK', 'Knicks'],
  'Oklahoma City Thunder': ['OKC', 'Thunder'],
  'Orlando Magic': ['ORL', 'Magic'],
  'Philadelphia 76ers': ['PHI', '76ers'],
  'Phoenix Suns': ['PHX', 'Suns'],
  'Portland Trail Blazers': ['POR', 'Trail Blazers'],
  'Sacramento Kings': ['SAC', 'Kings'],
  'San Antonio Spurs': ['SAS', 'Spurs'],
  'Toronto Raptors': ['TOR', 'Raptors'],
  'Utah Jazz': ['UTA', 'Jazz'],
  'Washington Wizards': ['WAS', 'Wizards'],
}

export const abrev = (n) => EQUIPOS[n]?.[0] || (n || '').slice(0, 3).toUpperCase()
export const corto = (n) => EQUIPOS[n]?.[1] || n

// Hora del partido en la zona horaria de quien mira (España o Latinoamérica).
export const hora = (iso) =>
  iso ? new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) : '-'
export const diaLargo = (iso) =>
  iso ? new Date(iso).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' }) : ''
// Jornada americana ("2026-10-20") -> "martes 20 de octubre".
export const jornada = (d) => (d ? diaLargo(`${d}T12:00:00`) : '')
