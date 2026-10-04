// Valores configurables desde las variables de entorno del hosting o un .env local.
// Enlace de pago de la preventa (9 €, pago único). Es público: va en la propia web.
export const STRIPE_PAYMENT_LINK =
  import.meta.env.VITE_STRIPE_PAYMENT_LINK || 'https://buy.stripe.com/4gMeVcexVegTbC07tB2Fa00'
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || 'propdeep.soporte@gmail.com'
// URL pública del backend (p. ej. https://api.propdeep.es). Vacía = se usan los datos de src/data.
export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')

// Titular del sitio (LSSI-CE art. 10 y RGPD): aparece en el aviso legal y la política de privacidad.
export const TITULAR = {
  nombre: 'Marcela Ortiz Gonzales',
  nif: '55064885X',
  domicilio: 'Parque de Salvador Castell, 10, 46680 Algemesí (Valencia), España',
}
