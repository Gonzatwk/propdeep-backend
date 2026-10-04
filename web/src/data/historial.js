// Historial público de predicciones. Se añade una entrada ANTES de cada partido
// y solo se rellena `resultado` cuando termina. No se borran ni editan entradas.
//
// Forma de cada entrada:
// {
//   publicado: '2026-10-22T17:00:00+02:00', // fecha y hora de publicación
//   partido: 'LAL @ DEN',
//   jugador: 'Nombre Apellido',
//   prop: 'Puntos',
//   lado: 'más',            // 'más' | 'menos'
//   linea: 27.5,
//   cuota: 2.05,            // decimal
//   probEstimada: 0.55,
//   confianza: 'Alta',      // 'Alta' | 'Media' | 'Baja'
//   jugada: true,           // false si el análisis concluyó "sin ventaja"
//   resultado: 'pendiente', // 'pendiente' | 'ganada' | 'perdida' | 'nula'
// }
export const historial = []

// Rendimiento con apuesta fija de 1 unidad, solo sobre las jugadas resueltas.
export function resumen(entradas, filtro = () => true) {
  const jugadas = entradas.filter((e) => e.jugada && filtro(e))
  const resueltas = jugadas.filter((e) => e.resultado === 'ganada' || e.resultado === 'perdida')
  const ganadas = resueltas.filter((e) => e.resultado === 'ganada').length
  const beneficio = resueltas.reduce(
    (acc, e) => acc + (e.resultado === 'ganada' ? e.cuota - 1 : -1),
    0,
  )
  return {
    jugadas: jugadas.length,
    resueltas: resueltas.length,
    ganadas,
    acierto: resueltas.length ? ganadas / resueltas.length : null,
    beneficio,
    roi: resueltas.length ? beneficio / resueltas.length : null,
  }
}
