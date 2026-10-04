# PropDeep · web

Landing de PropDeep en React + Vite + Tailwind. Sustituye a la app de Lovable.

## En local

```bash
cd web
npm install
npm run dev   # http://localhost:5173
```

## Configuración

Copia `.env.example` a `.env` (en Cloudflare Pages: Settings > Variables and Secrets):

- `VITE_STRIPE_PAYMENT_LINK`: enlace de pago de Stripe de la preventa de 9 €. Vacío = el enlace por defecto de `src/config.js`.
- `VITE_CONTACT_EMAIL`: correo de contacto y reembolsos.
- `VITE_API_URL`: URL del backend. Con ella, `/historial` lee `GET /predictions` y `GET /track-record`; vacía, usa `src/data/historial.js`. El backend debe incluir el dominio de la web en `CORS_ORIGINS`.

## Contenido que falta

- `src/data/informes_ejemplo.json`: pega aquí la salida de `scripts/informes_ejemplo.py` del backend y sustituye a los huecos de `src/data/informes.js`.
- `src/data/historial.js`: historial público; las cifras se calculan solas.
- `src/pages/AvisoLegal.jsx` y `Privacidad.jsx`: nombre, NIF y domicilio (marcados en amarillo).

## Despliegue

Cloudflare Pages (gratis y permite uso comercial; el plan Hobby de Vercel no):
Root directory `web`, build command `npm run build`, output directory `dist`.
