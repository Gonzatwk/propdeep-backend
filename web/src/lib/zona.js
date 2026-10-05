import { useCuenta } from './cuenta'
import { useModo } from './tablero'

export const STAT = { pts: 'Puntos', reb: 'Rebotes', ast: 'Asistencias', fg3m: 'Triples' }
export const LADO = { over: 'Más', under: 'Menos' }
export const PRECIO = { mensual: 15, anual: 120, pro: 25, pase: 5, prueba: 7 }
// Subida anunciada del plan mensual. Quien se suscriba antes mantiene su precio mientras siga.
// El día de la subida hay que crear el precio nuevo en Stripe y cambiar STRIPE_PRICE_MONTHLY.
export const SUBIDA = { fecha: '2027-01-01', mensual: 19 }
export const subidaPendiente = () => new Date() < new Date(`${SUBIDA.fecha}T00:00:00+01:00`)
export const TEXTO_SUBIDA = `El 1 de enero el plan mensual sube a ${SUBIDA.mensual} €. Si entras antes, mantienes ${PRECIO.mensual} € mientras sigas suscrito.`

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
