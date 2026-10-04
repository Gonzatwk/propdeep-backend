# PropDeep · web

Landing de PropDeep en React + Vite + Tailwind. Sustituye a la app de Lovable.

## En local

```bash
cd web
npm install
npm run dev   # http://localhost:5173
```

## Configuración

Copia `.env.example` a `.env` (en Vercel: Settings > Environment Variables):

- `VITE_STRIPE_PAYMENT_LINK`: enlace de pago de Stripe de la preventa de 9 €. Vacío = botón "Preventa abre muy pronto".
- `VITE_CONTACT_EMAIL`: correo de contacto y reembolsos.

## Contenido que falta

- `src/data/informes.js`: los 3 informes de ejemplo, con datos reales (ahora son huecos marcados).
- `src/data/historial.js`: historial público; las cifras se calculan solas.
- `src/pages/AvisoLegal.jsx` y `Privacidad.jsx`: nombre, NIF y domicilio (marcados en amarillo).

## Despliegue en Vercel

Importar el repo, con **Root Directory = `web`**. Vite se detecta solo.
