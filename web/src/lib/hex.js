// Hexágono con vértice arriba, centrado en (x, y) y radio r.
export function hexPoints(x, y, r) {
  const pts = []
  for (let k = 0; k < 6; k++) {
    const a = (Math.PI / 180) * (60 * k - 90)
    pts.push(`${(x + r * Math.cos(a)).toFixed(1)},${(y + r * Math.sin(a)).toFixed(1)}`)
  }
  return pts.join(' ')
}

// Siete tonos de la escala divergente, de -3 (frío) a +3 (caliente).
export const escala = ['var(--c3)', 'var(--c2)', 'var(--c1)', 'var(--n0)', 'var(--h1)', 'var(--h2)', 'var(--h3)']
export const tono = (v) => escala[Math.max(-3, Math.min(3, Math.round(v))) + 3]
