import { ArrowUpRight } from '@phosphor-icons/react'
import { STRIPE_PAYMENT_LINK } from '../config'

// Botón de reserva. Sin enlace de Stripe configurado, se muestra desactivado.
export default function Cta({ children = 'Reservar por 9 €', size = 'lg', className = '' }) {
  const pad = size === 'sm' ? 'px-4 py-2 text-sm' : 'px-6 py-3.5 text-base'
  if (!STRIPE_PAYMENT_LINK) {
    return (
      <span aria-disabled="true" className={`btn ${pad} cursor-not-allowed bg-surface-2 text-muted ${className}`}>
        Preventa abre muy pronto
      </span>
    )
  }
  return (
    <a href={STRIPE_PAYMENT_LINK} target="_blank" rel="noopener noreferrer" className={`btn btn-primary ${pad} ${className}`}>
      {children}
      <ArrowUpRight weight="bold" aria-hidden className="size-4" />
    </a>
  )
}
