import { useCuenta } from './cuenta'
import { useModo } from './tablero'

export const STAT = { pts: 'Puntos', reb: 'Rebotes', ast: 'Asistencias', fg3m: 'Triples' }
export const LADO = { over: 'Más', under: 'Menos' }
export const PRECIO = { mensual: 15, anual: 120, prueba: 7 }

// Nombre visible de cada casa (claves de The Odds API).
const CASAS = {
  williamhill: 'William Hill', betfair_ex_eu: 'Betfair', betfair: 'Betfair', unibet_eu: 'Unibet', pinnacle: 'Pinnacle',
  betsson: 'Betsson', sport888: '888sport', marathonbet: 'Marathonbet', codere_it: 'Codere', codere: 'Codere',
  onexbet: '1xBet', tipico_de: 'Tipico', winamax_fr: 'Winamax', winamax_de: 'Winamax', leovegas: 'LeoVegas',
  leovegas_se: 'LeoVegas', betclic_fr: 'Betclic', nordicbet: 'NordicBet', coolbet: 'Coolbet', everygame: 'Everygame',
  draftkings: 'DraftKings', fanduel: 'FanDuel', betmgm: 'BetMGM', williamhill_us: 'Caesars', bovada: 'Bovada',
  betonlineag: 'BetOnline', betrivers: 'BetRivers', bet365: 'Bet365',
}
export const nombreCasa = (k) => CASAS[k] || (k ? k.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) : '-')

// Destino del botón de suscripción según el estado de la cuenta.
export function useIrASuscribir() {
  const { usuario } = useCuenta()
  const { demo } = useModo()
  if (demo) return '/cuenta'
  return usuario ? '/cuenta' : '/entrar?siguiente=/cuenta'
}
