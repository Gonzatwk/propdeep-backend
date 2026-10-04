import { STRIPE_PAYMENT_LINK } from '../config'

// Botón de reserva. Sin enlace de Stripe configurado, se muestra desactivado.
export default function Cta({ children, className = '' }) {
  const base =
    'inline-flex items-center justify-center rounded-xl px-6 py-3 text-base font-semibold transition'
  if (!STRIPE_PAYMENT_LINK) {
    return (
      <span
        aria-disabled="true"
        title="El enlace de pago aún no está configurado"
        className={`${base} cursor-not-allowed bg-slate-700 text-slate-300 ${className}`}
      >
        Preventa abre muy pronto
      </span>
    )
  }
  return (
    <a
      href={STRIPE_PAYMENT_LINK}
      target="_blank"
      rel="noopener noreferrer"
      className={`${base} bg-brand text-slate-950 hover:bg-brand-dark ${className}`}
    >
      {children}
    </a>
  )
}
