import { useSyncExternalStore } from 'react'

// Boletos en preparación (la combinada de «Mis picks» y la de «Paper bets»): las selecciones
// se guardan en este navegador hasta publicarlas.
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
    // Una selección por línea: volver a añadirla la sustituye (otro lado u otra cuota).
    añadir: (leg) => guardar([...actual.filter((l) => l.line_id !== leg.line_id), leg]),
    quitar: (leg) => guardar(actual.filter((l) => l.line_id !== leg.line_id)),
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
