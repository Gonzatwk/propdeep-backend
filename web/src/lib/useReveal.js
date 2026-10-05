import { useEffect } from 'react'

// Marca con .in los elementos .wipe y .lift cuando entran en pantalla.
// Sin JS o con movimiento reducido, todo se ve desde el principio.
export default function useReveal(clave) {
  useEffect(() => {
    if (!window.matchMedia('(prefers-reduced-motion: no-preference)').matches || !('IntersectionObserver' in window)) return
    document.documentElement.classList.add('js-motion')
    const io = new IntersectionObserver((entradas) => {
      for (const e of entradas) {
        if (e.isIntersecting) {
          e.target.classList.add('in')
          io.unobserve(e.target)
        }
      }
    }, { rootMargin: '0px 0px -12% 0px' })
    document.querySelectorAll('.wipe, .lift').forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [clave])
}
