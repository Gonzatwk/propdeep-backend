import { useSyncExternalStore } from 'react'

// Combinada en preparación: las selecciones se guardan en este navegador hasta publicarla.
const CLAVE = 'propdeep.combinada'
const avisos = new Set()

function leer() {
  try { return JSON.parse(localStorage.getItem(CLAVE)) || [] } catch { return [] }
}
let actual = leer()

function guardar(legs) {
  actual = legs
  try { localStorage.setItem(CLAVE, JSON.stringify(legs)) } catch { /* sin almacenamiento */ }
  avisos.forEach((f) => f())
}

// Una selección por línea: volver a añadirla la sustituye (otro lado u otra cuota).
export const combinada = {
  añadir: (leg) => guardar([...actual.filter((l) => l.line_id !== leg.line_id), leg]),
  quitar: (leg) => guardar(actual.filter((l) => l.line_id !== leg.line_id)),
  vaciar: () => guardar([]),
}

export const cuotaTotal = (legs) => legs.reduce((a, l) => a * l.odds, 1)

export function useCombinada() {
  return useSyncExternalStore(
    (f) => { avisos.add(f); return () => avisos.delete(f) },
    () => actual,
  )
}
