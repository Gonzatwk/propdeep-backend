# Backend de PropDeep

API en FastAPI que analiza player props de la NBA con datos reales y guarda un historial
público de todas las predicciones.

## Cómo funciona un análisis

1. **Datos del jugador** (Balldontlie): partidos de esta temporada y la anterior, solo los
   anteriores al partido analizado.
2. **Tendencias**: medias de los últimos 5, 10 y 20 partidos, de la temporada, minutos y
   porcentaje de veces que superó la línea.
3. **Contexto**: local o visitante, back-to-back, lesión, y en puntos cuánto concede el rival
   frente a la media de la liga (ajuste máximo del 5 %).
4. **Probabilidad**: distribución normal (Poisson en triples) alrededor de la proyección,
   mezclada al 50 % con la probabilidad del mercado sin margen (`MODEL_WEIGHT`).
5. **Ventaja**: probabilidad estimada menos la implícita en la cuota (con margen). Por debajo
   del 3 % (`MIN_EDGE`) el veredicto es "sin ventaja". Jugadores fuera, en duda o con menos de
   5 partidos nunca son jugada.
6. **Informe**: Claude redacta la explicación en español solo con esos números. Sin clave de
   Claude se usa una plantilla.

## Endpoints

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/predictions` | Historial público completo |
| GET | `/track-record` | Acierto, beneficio en unidades y ROI, total y por confianza |
| POST | `/analyze` | Analiza una prop sin publicarla |
| POST | `/admin/publish` | Analiza y publica en el historial (cabecera `x-admin-token`) |
| GET | `/admin/scan?game_date=AAAA-MM-DD` | Analiza las props de la jornada con The Odds API |
| POST | `/admin/settle` | Liquida las pendientes con el resultado real |
| POST | `/admin/board?game_date=AAAA-MM-DD` | Analiza todas las props de la jornada y las publica en la zona de partidos |
| GET | `/admin/metrics` | Embudo de validación: pruebas iniciadas, pago tras la prueba, bajas |
| GET | `/board` | Partidos de la jornada (por defecto, la próxima con partidos por jugar) |
| GET | `/board/games/{event_id}` | Jugadores y líneas del partido; las bloqueadas van sin veredicto |
| GET | `/board/lines/{id}` | Informe completo (402 si hace falta suscripción) |
| POST | `/auth/login` · `/auth/verify` · `/auth/logout` | Acceso por enlace mágico, solo con el correo |
| GET / DELETE | `/me` | Estado de la cuenta / borrar la cuenta |
| POST | `/billing/checkout` · `/billing/portal` | Stripe Checkout (prueba de 7 días) y portal de cliente |
| POST | `/stripe/webhook` | Único sitio donde se da o quita el acceso |
| POST | `/waitlist` | Correos del formulario de aviso de la landing |

## Zona de partidos y muro de pago

- Cada línea de `/admin/board` se publica en el historial con su hash. Gratis se ven
  `FREE_LINES_PER_DAY` líneas por jornada (la de más ventaja de los primeros partidos); el
  resto solo con suscripción. Al empezar el partido, todo se abre y `/predictions` lo enseña.
- Claude solo redacta las líneas con ventaja; las de "sin ventaja" llevan la plantilla.
- La sesión es un token en la cabecera `Authorization: Bearer` (sin cookies).

## Stripe (suscripción)

1. En Stripe, crea un producto "PropDeep" con dos precios recurrentes: 15 € al mes y 120 € al año.
   Copia sus id (`price_...`) en `STRIPE_PRICE_MONTHLY` y `STRIPE_PRICE_YEARLY`.
2. `STRIPE_SECRET_KEY`: la clave secreta (`sk_test_...` para probar).
3. Webhook a `https://TU-API/stripe/webhook` con los eventos `checkout.session.completed`,
   `customer.subscription.created`, `customer.subscription.updated` y
   `customer.subscription.deleted`. Su "signing secret" va en `STRIPE_WEBHOOK_SECRET`.
4. Activa el portal de cliente (Settings > Billing > Customer portal) para que puedan cancelar.

Lo publicado no se edita: cada predicción guarda un hash SHA-256 de su contenido.

## En local

```bash
pip install -r requirements-dev.txt
cp .env.example .env   # y rellena las claves
pytest
uvicorn main:app --reload
python -m scripts.informes_ejemplo 2026-10-21
```

## Planes de las APIs

- **Balldontlie ALL-STAR** (9,99 $/mes): necesario para `/stats` y `/player_injuries`.
- **The Odds API**: cada partido cuesta (mercados × regiones) créditos; 4 mercados en `eu` = 4.

## Backtest

`scripts/backtest.py` repasa una temporada pasada (por defecto la 2025-26) con la misma función
`analyze` de producción y solo con datos previos a cada partido. Descarga la temporada de Balldontlie
una vez (unos 10-15 minutos por el límite de 60 peticiones/minuto) y la guarda en `backtest_cache/`.

```bash
python -m scripts.backtest --lineas proxy                      # gratis: calibración del modelo
python -m scripts.backtest --lineas odds-api --stats pts --estimar   # cuántos créditos haría falta
python -m scripts.backtest --lineas odds-api --stats pts --max-creditos 19000
```

- `proxy` usa una línea inventada (media de los 10 previos): dice si las probabilidades están bien
  calibradas, no si se gana al mercado.
- `odds-api` usa cuotas históricas reales (solo planes de pago de The Odds API: 10 créditos por
  mercado y región y partido). Todo lo descargado queda en caché y no se vuelve a pagar.
- Resultados en `backtest_out/<modo>/resumen.json` y `lineas.csv`.
