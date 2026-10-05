import { useEffect, useRef, useState } from 'react'

const disponible = () =>
  matchMedia('(hover: hover) and (pointer: fine)').matches && matchMedia('(prefers-reduced-motion: no-preference)').matches

const INTERACTIVO = 'a, button, [role="tab"], input, label, summary'

// Cursor propio en escritorio: punto dorado exacto y un aro que lo sigue con
// retraso, crece sobre enlaces y botones y suelta una onda al hacer clic.
export default function Cursor() {
  const [activo] = useState(disponible)
  const punto = useRef(null)
  const aro = useRef(null)

  useEffect(() => {
    if (!activo) return
    document.documentElement.classList.add('cursor-propio')
    let x = -100
    let y = -100
    let ax = x
    let ay = y
    let raf = 0
    const bucle = () => {
      ax += (x - ax) * 0.18
      ay += (y - ay) * 0.18
      if (aro.current) aro.current.style.transform = `translate(${ax}px, ${ay}px)`
      raf = requestAnimationFrame(bucle)
    }
    const mover = (e) => {
      x = e.clientX
      y = e.clientY
      if (punto.current) punto.current.style.transform = `translate(${x}px, ${y}px)`
      aro.current?.classList.toggle('sobre', !!e.target.closest?.(INTERACTIVO))
      if (aro.current) aro.current.style.opacity = '1'
    }
    const fuera = (e) => {
      if (e.relatedTarget) return
      if (aro.current) aro.current.style.opacity = '0'
    }
    const bajar = () => aro.current?.classList.add('pulsado')
    const subir = (e) => {
      aro.current?.classList.remove('pulsado')
      const onda = document.createElement('div')
      onda.className = 'cursor-onda'
      onda.style.left = `${e.clientX}px`
      onda.style.top = `${e.clientY}px`
      document.body.append(onda)
      setTimeout(() => onda.remove(), 650)
    }
    addEventListener('pointermove', mover, { passive: true })
    addEventListener('pointerdown', bajar)
    addEventListener('pointerup', subir)
    document.addEventListener('mouseout', fuera)
    raf = requestAnimationFrame(bucle)
    return () => {
      cancelAnimationFrame(raf)
      removeEventListener('pointermove', mover)
      removeEventListener('pointerdown', bajar)
      removeEventListener('pointerup', subir)
      document.removeEventListener('mouseout', fuera)
      document.documentElement.classList.remove('cursor-propio')
    }
  }, [activo])

  if (!activo) return null
  return (
    <>
      <div ref={aro} aria-hidden className="cursor-aro" style={{ opacity: 0 }}><span /></div>
      <div ref={punto} aria-hidden className="cursor-punto" />
    </>
  )
}
