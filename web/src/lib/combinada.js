import { useSyncExternalStore } from 'react'

// Boletos en preparación (la combinada de «Mis picks» y la de «Paper bets»): las selecciones
// se guardan en este navegador hasta publicarlas.
// Una selección por línea, y una apuesta a ganador por partido.
export const claveLeg = (l) => (l.stat === 'ml' ? `ml:${l.event_id}` : l.line_id)
// Lo que se manda al servidor de cada selección.
export const legParaEnviar = ({ line_id, side, line, odds, stat, event_id, team }) =>
  (stat === 'ml' ? { stat, event_id, team, side: 'over', odds } : { line_id, side, line, odds })

function crearBoleto(clave) {
  const avisos = new Set()
  const leer = () => {
    try { return JSON.parse(localStorage.getItem(clave)) || [] } catch { return [] }
  }
  let actual = leer()
  const guardar = (legs) => {
    actual = legs
    try { localStorage.setItem(clave, JSON.stringify(legs)) } catch { /* sin almacenamiento */ }
    avisos.forEach((f) => f())
  }
  const suscribir = (f) => { avisos.add(f); return () => avisos.delete(f) }
  return {
    // Volver a añadir la misma selección la sustituye (otro lado, otro equipo u otra cuota).
    añadir: (leg) => guardar([...actual.filter((l) => claveLeg(l) !== claveLeg(leg)), leg]),
    quitar: (leg) => guardar(actual.filter((l) => claveLeg(l) !== claveLeg(leg))),
    vaciar: () => guardar([]),
    // eslint-disable-next-line react-hooks/rules-of-hooks
    use: () => useSyncExternalStore(suscribir, () => actual),
  }
}

export const combinada = crearBoleto('propdeep.combinada')
export const boletoPaper = crearBoleto('propdeep.paper')

export const cuotaTotal = (legs) => legs.reduce((a, l) => a * l.odds, 1)

export const useCombinada = () => combinada.use()
export const useBoletoPaper = () => boletoPaper.use()
