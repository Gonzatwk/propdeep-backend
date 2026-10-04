const pct = new Intl.NumberFormat('es-ES', { style: 'percent', maximumFractionDigits: 1 })
const num = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 })

export const fmtPct = (v) => (v == null ? '—' : pct.format(v))
export const fmtNum = (v) => (v == null ? '—' : num.format(v))
export const fmtUnidades = (v) => (v == null ? '—' : `${v > 0 ? '+' : ''}${num.format(v)} u`)
