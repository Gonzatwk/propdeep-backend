import { ArrowUpRight } from '@phosphor-icons/react'
import { STRIPE_PAYMENT_LINK } from '../config'

// Botón de reserva. Sin enlace de Stripe configurado, se muestra desactivado.
export default function Cta({ children = 'Reservar por 9 €', size = 'lg', className = '' }) {
  const pad = size === 'sm' ? 'h-9 px-4 text-[0.95rem]' : 'h-14 px-7 text-xl'
  if (!STRIPE_PAYMENT_LINK) {
    return (
      <span aria-disabled="true" className={`btn ${pad} cursor-not-allowed bg-line-soft text-muted ${className}`}>
        Preventa abre muy pronto
      </span>
    )
  }
  return (
    <a href={STRIPE_PAYMENT_LINK} target="_blank" rel="noopener noreferrer" className={`btn btn-primary ${pad} ${className}`}>
      {children}
      <ArrowUpRight weight="bold" aria-hidden className={size === 'sm' ? 'size-4' : 'size-5'} />
    </a>
  )
}
