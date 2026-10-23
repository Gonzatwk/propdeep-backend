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
   **Compañero fuera**: si el parte de lesiones da fuera o en duda a un compañero importante (jugó 3
   de los 5 últimos partidos del equipo con 24 minutos o más), la proyección se multiplica por la
   media del jugador sin él frente a con él (con su equipo actual), encogida según la muestra
   (`n / (n + 8)`) y con tope del ±25 %. Hacen falta 3 partidos sin él y 5 con él. Solo cambia la
   proyección con `TEAMMATE_ADJUST=1`; apagado, el análisis enseña igual la media con y sin él.
4. **Probabilidad**: distribución normal (Poisson en triples) alrededor de la proyección,
   mezclada al 20 % con la probabilidad del mercado sin margen (`MODEL_WEIGHT`). En el backtest de
   la 2025-26 con cuotas reales, al 50 % perdía (-2,8 %); los datos le dan al modelo un 6-10 % de
   peso, y al 20 % quedaba en torno a +2 % sin ser significativo (`scripts/analisis_peso.py`).
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
| POST | `/admin/analyze` | Analiza una prop sin publicarla (admin: devuelve el veredicto interno) |
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
| GET | `/billing/plans` | Planes que se pueden contratar (los que tienen precio en Stripe) |
| POST | `/billing/checkout` · `/billing/portal` | Stripe Checkout (mensual, anual, Pro o pase) y portal de cliente |
| POST | `/billing/pause` · `/billing/resume` | Pausar los cobros un mes en vez de cancelar, o reanudar |
| POST | `/admin/trial-reminders` | Correo del día 5 de la prueba (también lo lanza `/admin/board`) |
| GET | `/tipsters` | Auditoría de tipsters (pública solo con `TIPSTERS_PUBLIC=true`; antes, solo el autor) |
| POST | `/tipsters` · `/tipsters/{id}/picks` · `/tipster-picks/{id}/settle` | Alta de tipster, registro de un pick con su prueba y resultado (autor) |
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
- El enlace de acceso sale por Resend (`RESEND_API_KEY`, `MAIL_FROM` en un dominio verificado) o
  por SMTP. Railway bloquea el SMTP en los planes Free, Trial y Hobby, así que allí va con Resend.

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
   Añade en el portal los productos mensual, anual y Pro para que se pueda cambiar de plan.
5. Opcionales: precio Pro (25 € al mes, recurrente) en `STRIPE_PRICE_PRO` y pase de 7 días (5 €,
   **pago único**) en `STRIPE_PRICE_PASS`. Sin ellos, esos planes no se ofrecen. Con el Pro activo,
   el chat completo (`CHAT_MESSAGES_PER_DAY`) es del Pro y el resto tiene `CHAT_MESSAGES_PER_DAY_BASIC`.
6. Subida del 1 de enero de 2027: ese día crea un precio mensual nuevo de 19 € y pon su id en
   `STRIPE_PRICE_MONTHLY`. Las suscripciones que ya existen siguen en su precio de 15 €.

Pausa: `/billing/pause` usa `pause_collection` de Stripe (sin cobro y sin acceso durante 30 días,
se reanuda sola). Mientras dura, la cuenta queda como `paused`.

Lo publicado no se edita: cada predicción guarda un hash SHA-256 de su contenido.

## Uso personal en el PC (Windows)

Sin Stripe, Railway ni correo. En `.env`:

```
ADMIN_TOKEN=algo-largo
ADMIN_EMAILS=tu-correo
ODDS_REGIONS=us,eu
CORS_ORIGINS=http://localhost:5173
WEB_URL=http://localhost:5173
LOCAL_LOGIN=1
AUTO_JORNADA=1
```

Doble clic en `propdeep.bat`: abre el backend, la web (`npm run dev` con
`VITE_API_URL=http://localhost:8000`) y el navegador. En `/entrar` pones tu correo y entras
sin enlace (`LOCAL_LOGIN` solo vale con `WEB_URL` en localhost y para `ADMIN_EMAILS`).

Con `AUTO_JORNADA`, cada `AUTO_EVERY_MINUTES` el servidor liquida lo terminado y analiza los
partidos que empiezan en menos de `AUTO_HOURS_BEFORE` horas y aún no están publicados (cada
partido una vez: mercados x regiones créditos, 8 con `us,eu`). La jornada cambia a las 06:00 UTC.
Una línea por jugador y estadística: si la casa la mueve, se queda la primera.
También trae las cuotas a ganador (moneyline) de toda la jornada como mucho cada hora (1 crédito
por región, 2 con `us,eu`). Se ven en Partidos y en cada partido, y se pueden apostar en Mis picks,
Paper bets y combinadas (`stat: "ml"`, `event_id`, `team`); se liquidan solas con el marcador final.

## En local

```bash
pip install -r requirements-dev.txt
cp .env.example .env   # y rellena las claves
pytest
uvicorn main:app --reload
python -m scripts.informes_ejemplo 2026-10-21
python -m scripts.picks_hoy 2026-10-21   # jornada para uso personal: jugadas con la mejor cuota
```

`picks_hoy` analiza la línea principal de cada jugador, busca la mejor cuota de más y de menos entre las
casas que dan esa misma línea y marca como jugada solo lo que llega a `MIN_EDGE`. Guarda todo en
`picks_AAAA-MM-DD.csv` (se abre con Excel). `--casas bet365,williamhill` limita a tus casas y
`--regions us,eu` cambia las regiones de The Odds API.

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
- `python -m scripts.analisis_peso backtest_out/odds-api-casas/lineas.csv` dice qué peso merece el
  modelo frente al mercado (ajustado solo con meses anteriores) y el ROI de la regla por mitades.
- El backtest incluye el ajuste por compañero fuera ("fuera" = no jugó ese partido; no hay parte de
  lesiones histórico). `--sin-companeros` lo quita. `python -m scripts.analisis_companeros
  backtest_out/odds-api-casas/lineas.csv` dice si el ajuste aporta algo que la casa no tenga ya.
