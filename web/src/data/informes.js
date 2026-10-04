// Informes de ejemplo de la landing.
// IMPORTANTE: mientras `pendiente` sea true, la tarjeta se muestra como hueco vacío.
// Rellenar solo con análisis reales generados con datos reales, nunca inventados.
export const FECHA_EJEMPLOS = null // p. ej. '2026-10-22'

export const informes = [
  {
    tipo: 'Prop con ventaja clara',
    pendiente: true,
    jugador: null, // 'Nombre Apellido'
    partido: null, // 'LAL @ DEN'
    prop: null, // 'Puntos: más de 27,5'
    cuota: null, // 2.05 (decimal)
    probImplicita: null, // 0.488
    probEstimada: null, // 0.55
    confianza: null, // 'Alta' | 'Media' | 'Baja'
    veredicto: null, // 'Con ventaja' | 'Sin ventaja'
    porque: [], // tres frases
  },
  { tipo: 'Prop sin ventaja ("no apostamos")', pendiente: true, porque: [] },
  { tipo: 'Prop con confianza baja', pendiente: true, porque: [] },
]
