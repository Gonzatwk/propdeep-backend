// Campo de tiros ilustrativo: posiciones y aciertos generados con una semilla fija.
// No son datos reales de ningún jugador.
export const ARO = [250, 52.5]

function semilla(a) {
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const azar = semilla(2026)

// Zonas: [peso, acierto, generador de posición]
const zonas = [
  [30, 0.62, () => polar(4 + azar() * 52, azar() * Math.PI)],
  [12, 0.43, () => [170 + azar() * 160, 40 + azar() * 150]],
  [13, 0.41, () => polar(120 + azar() * 100, 0.15 + azar() * (Math.PI - 0.3))],
  [12, 0.39, () => [azar() < 0.5 ? 6 + azar() * 20 : 474 + azar() * 20, 8 + azar() * 125]],
  [33, 0.36, () => polar(240 + azar() * 40, 0.42 + azar() * (Math.PI - 0.84))],
]

function polar(r, a) {
  return [ARO[0] + Math.cos(a) * r, ARO[1] + Math.sin(a) * r]
}

const total = zonas.reduce((s, z) => s + z[0], 0)

export const TIROS = Array.from({ length: 260 }, (_, i) => {
  let r = azar() * total
  const zona = zonas.find((z) => (r -= z[0]) < 0) || zonas[0]
  const [x, y] = zona[2]()
  return { i, x, y, dentro: azar() < zona[1] }
})
