# Backend de PropDeep

API en FastAPI que analiza player props de la NBA con datos reales. Es información orientativa:
el backtest de 2025-26 con cuotas reales no mostró ventaja frente a las casas, así que la web
enseña datos (proyección, veces que superó la línea, desgloses, rival y las líneas de cada casa)
y nunca un "más/menos" como recomendación. El veredicto interno del modelo se guarda solo para
seguir midiéndolo (`/admin/predictions`).

## Cómo funciona un análisis

1. **Datos del jugador** (Balldontlie): partidos de esta temporada y la anterior, solo los
   anteriores al partido analizado.
2. **Tendencias**: medias de los últimos 5, 10 y 20 partidos, de la temporada, minutos y
   porcentaje de veces que superó la línea (últimos 5, últimos 10, esta temporada y la anterior),
   más el desglose en casa, fuera y contra el rival del día.
   Las líneas de todas las casas se guardan con el análisis (comparador); la principal es la que
   más casas ofrecen.
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
| GET | `/picks` | "Ejemplo de mis picks": todos los picks del autor, con su resumen |
| POST | `/picks` | Publica un pick antes del partido (correo en `ADMIN_EMAILS` o `x-admin-token`) |
| POST | `/picks/{id}/settle` | Resultado de un pick que no sale de la zona (los demás se liquidan solos) |
| GET | `/admin/predictions` | Veredictos internos del modelo (no públicos) |
| GET | `/admin/track-record` | Acierto y ROI de esos veredictos, para seguir midiendo el modelo |
| POST | `/analyze` | Analiza una prop sin publicarla |
| POST | `/admin/publish` | Analiza y publica en el historial (cabecera `x-admin-token`) |
| GET | `/admin/scan?game_date=AAAA-MM-DD` | Analiza las props de la jornada con The Odds API |
| POST | `/admin/settle` | Liquida predicciones y picks pendientes con el resultado real |
| POST | `/admin/board?game_date=AAAA-MM-DD` | Analiza todas las props de la jornada y las publica en la zona de partidos |
| GET | `/admin/metrics` | Embudo de validación: pruebas iniciadas, pago tras la prueba, bajas |
| GET | `/board` | Partidos de la jornada (por defecto, la próxima con partidos por jugar) |
| GET | `/board/games/{event_id}` | Jugadores y líneas del partido; las bloqueadas van sin análisis |
| GET | `/board/lines/{id}` | Análisis completo con el comparador de casas (402 si hace falta suscripción) |
| GET / POST | `/chat` | Estado del chat (mensajes que quedan hoy) / pregunta al chat (suscriptores) |
| POST | `/auth/login` · `/auth/verify` · `/auth/logout` | Acceso por enlace mágico, solo con el correo |
| GET / DELETE | `/me` | Estado de la cuenta / borrar la cuenta |
| POST | `/billing/checkout` · `/billing/portal` | Stripe Checkout (prueba de 7 días) y portal de cliente |
| POST | `/stripe/webhook` | Único sitio donde se da o quita el acceso |
| POST | `/waitlist` | Correos del formulario de aviso de la landing |

## Zona de partidos y muro de pago

- Cada línea de `/admin/board` se guarda con su hash. Gratis se ven `FREE_LINES_PER_DAY`
  líneas por jornada (los puntos del jugador con más proyección de los primeros partidos, sin
  usar el veredicto del modelo); el resto solo con suscripción. Al empezar el partido, se abre.
- Claude redacta los puntos de cada jugador y las líneas gratis, sin ver el veredicto del
  modelo; el resto lleva la plantilla.
- Los correos de `ADMIN_EMAILS` ven todas las líneas y pueden publicar picks desde la web.
- La sesión es un token en la cabecera `Authorization: Bearer` (sin cookies).

## Chat (suscriptores)

- Claude responde en español con tres herramientas que leen la zona de partidos: `partidos`,
  `buscar_lineas` (por jugador, equipo, partido o estadística, y ordenadas por veces por encima
  de la línea) y `detalle_linea`. No ve el veredicto interno del modelo y tiene prohibido decir
  qué apostar o hablar de "valor"; si alguien habla de recuperar pérdidas, recomienda jugarbien.es.
- Solo para suscriptores y `ADMIN_EMAILS`. Sin `ANTHROPIC_API_KEY` responde 503.
- Límite de `CHAT_MESSAGES_PER_DAY` mensajes por persona y día (30 por defecto); si la respuesta
  falla por nuestra parte, el mensaje no cuenta. `CHAT_EFFORT` ajusta el esfuerzo del modelo y
  `CHAT_MODEL` permite usar otro modelo solo para el chat (vacío = `ANTHROPIC_MODEL`).
- No se guardan las conversaciones: la web reenvía los últimos mensajes y el servidor solo cuenta
  cuántos manda cada persona al día.

## Ejemplo de mis picks

- Son los picks del autor, no del modelo. Se publican antes del partido (después se rechazan),
  no se editan ni se borran y salen todos, también los fallados, con su cuota y su casa.
- Si salen de una línea de la zona se liquidan solos con `/admin/settle`; si no, con
  `/picks/{id}/settle`, una sola vez.

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
- `--todas-casas` (con `odds-api`) guarda la línea principal de cada casa en `backtest_out/odds-api-casas/`,
  para comparar casas y buscar la mejor cuota. Sale de la caché: no vuelve a pagar lo descargado.
- Resultados en `backtest_out/<modo>/resumen.json` y `lineas.csv`.
