import { ArrowUpRight } from '@phosphor-icons/react'
import { useRef } from 'react'
import { STRIPE_PAYMENT_LINK } from '../config'

// Botón de reserva, con un leve efecto imán hacia el ratón.
// Sin enlace de Stripe configurado, se muestra desactivado.
export default function Cta({ children = 'Reservar por 9 €', size = 'lg', tono = 'gold', className = '' }) {
  const ref = useRef(null)
  const pad = size === 'sm' ? 'h-9 px-4 text-[0.95rem]' : 'h-15 px-8 text-[1.4rem]'
  if (!STRIPE_PAYMENT_LINK) {
    return (
      <span aria-disabled="true" className={`btn ${pad} cursor-not-allowed bg-black-3 text-muted ${className}`}>
        Preventa abre muy pronto
      </span>
    )
  }
  const iman = (e) => {
    if (size === 'sm' || e.pointerType !== 'mouse' || !matchMedia('(prefers-reduced-motion: no-preference)').matches) return
    const r = ref.current.getBoundingClientRect()
    const x = (e.clientX - r.left - r.width / 2) * 0.18
    const y = (e.clientY - r.top - r.height / 2) * 0.3
    ref.current.style.transform = `translate(${x}px, ${y}px)`
  }
  const soltar = () => { if (ref.current) ref.current.style.transform = '' }
  return (
    <a
      ref={ref}
      href={STRIPE_PAYMENT_LINK}
      target="_blank"
      rel="noopener noreferrer"
      onPointerMove={iman}
      onPointerLeave={soltar}
      className={`btn btn-${tono} ${pad} ${className}`}
    >
      {children}
      <ArrowUpRight weight="bold" aria-hidden className={size === 'sm' ? 'size-4' : 'size-6'} />
    </a>
  )
}
