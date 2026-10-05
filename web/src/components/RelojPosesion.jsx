import { useEffect, useState } from 'react'

// Reloj de posesión: baja de 24 a 0 según avanzas por la página. Al pulsarlo, vas al precio.
export default function RelojPosesion() {
  const [s, setS] = useState(24)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    let raf = 0
    const actualizar = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const max = document.documentElement.scrollHeight - innerHeight
        const p = max > 0 ? Math.min(1, scrollY / max) : 0
        setS(Math.max(0, Math.ceil(24 * (1 - p))))
        setVisible(scrollY > innerHeight * 0.6)
      })
    }
    actualizar()
    addEventListener('scroll', actualizar, { passive: true })
    return () => removeEventListener('scroll', actualizar)
  }, [])
  const urgente = s <= 5
  return (
    <a
      href="/#precio"
      aria-label="Ir al precio"
      tabIndex={visible ? undefined : -1}
      className={`fixed right-3 bottom-3 z-30 flex flex-col items-center border-2 bg-black px-2 pt-0.5 pb-1 sm:px-2.5 sm:pt-1 sm:pb-1.5 transition-[opacity,translate,border-color] duration-300 sm:right-5 ${visible ? '' : 'pointer-events-none translate-y-4 opacity-0'} sm:bottom-5 ${urgente ? 'border-gold' : 'border-white/40'}`}
    >
      <span className="text-[0.5rem] sm:text-[0.6rem] font-semibold tracking-[0.12em] text-muted uppercase">Posesión</span>
      <span key={s} className={`display tnum text-[1.5rem] sm:text-[2rem] leading-none ${urgente ? 'text-gold' : 'text-white'} reloj`}>{String(s).padStart(2, '0')}</span>
    </a>
  )
}
