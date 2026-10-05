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

- `VITE_CONTACT_EMAIL`: correo de contacto. Vacío = el de `src/config.js`, donde también están los datos del titular.
- `VITE_API_URL`: URL del backend. Con ella, `/historial` lee `GET /predictions` y `GET /track-record`; vacía, usa `src/data/historial.js`. El backend debe incluir el dominio de la web en `CORS_ORIGINS`.

## Contenido que falta

- `src/data/informes_ejemplo.json`: pega aquí la salida de `scripts/informes_ejemplo.py` del backend y sustituye a los huecos de `src/data/informes.js`.
- `src/data/historial.js`: historial público; las cifras se calculan solas.

## Despliegue

Cloudflare Pages (gratis y permite uso comercial; el plan Hobby de Vercel no):
Root directory `web`, build command `npm run build`, output directory `dist`.

## Formulario «Avísame»

Con `VITE_API_URL` configurada, el formulario de la sección de precio guarda el correo en el backend (`POST /waitlist`). Mientras el backend no esté desplegado, lo envía a `/api/avisame`, una Cloudflare Pages Function (`functions/api/avisame.js`) que lo guarda en un espacio KV del propio proyecto. Sin cookies ni servicios de terceros.

Para activarlo, una sola vez en el panel de Cloudflare:

1. Storage & Databases > KV > Create: crea un espacio llamado `propdeep-avisos`.
2. Workers & Pages > propdeep > Settings > Bindings > Add > KV namespace: nombre de la variable `AVISOS`, espacio `propdeep-avisos`. Hazlo en Production y en Preview.
3. Vuelve a desplegar (Deployments > Retry deployment).

Los correos se ven en Storage & Databases > KV > propdeep-avisos, una clave `correo:<email>` por persona. Sin el enlace `AVISOS`, el formulario pide a la persona que escriba al correo de contacto.
